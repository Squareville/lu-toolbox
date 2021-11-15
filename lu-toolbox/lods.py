import bpy
from bpy.props import BoolProperty, FloatProperty
from math import radians

class LUTB_PT_lods(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "LODs"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "lutb_decimate")
        layout.prop(scene, "lutb_use_lod2")
        layout.operator("lutb.create_sort_lods")

        layout.separator()

        layout.label(text="Distances")
        layout.prop(scene, "lutb_lod0")
        layout.prop(scene, "lutb_lod1")
        layout.prop(scene, "lutb_lod2")
        layout.prop(scene, "lutb_cull")
        
        layout.operator("lutb.setup_lod_data")

class LUTB_OT_create_sort_lods(bpy.types.Operator):
    """Sort objects into LOD collections"""
    bl_idname = "lutb.create_sort_lods"
    bl_label = "Create and Sort LODs"  

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        scene = context.scene

        collections = []
        objects = list(sorted(filter(lambda obj: obj.name[-6:-1] == "_LOD_", context.selected_objects), key=lambda obj: obj.name[-1]))

        for i in range(3 if scene.lutb_use_lod2 else 2):
            name = f"LOD_{i}"
            collection = bpy.data.collections.get(name)
            if not collection:
                collection = bpy.data.collections.new(name)
            if not name in scene.collection.children:
                scene.collection.children.link(collection)

            collections.append(collection)

        lod_memory = {}

        for obj in objects:
            previous_users_collection = obj.users_collection
            name, lod = obj.name.split("_LOD_")

            if lod == "0":
                collections[0].objects.link(obj)
                lod_memory[name] = [obj, None, None]

            elif lod == "1":
                if name in lod_memory:
                    collections[1].objects.link(obj)
                    lod_memory[name][1] = obj
                else:
                    self.report({"WARNING"}, f"Failed sorting \"{obj.name}\", \"{name}_LOD_0\" is not selected.")
                    continue

            elif scene.lutb_use_lod2 and obj.name.endswith("LOD_2"):
                if name in lod_memory:
                    collections[2].objects.link(obj)
                    lod_memory[name][2] = obj
                else:
                    self.report({"WARNING"}, f"Failed sorting \"{obj.name}\", \"{name}_LOD_0\" is not selected.")
                    continue

            else:
                continue

            for collection in previous_users_collection:
                collection.objects.unlink(obj)

        selection = []

        for name, (lod_0, lod_1, lod_2) in lod_memory.items():
            if not lod_1:
                lod_1 = lod_0.copy()
                lod_1.data = lod_0.data.copy()
                lod_1.name = f"{lod_0.name[:-6]}_LOD_1"
                lod_1.data.name = f"{lod_0.name[:-6]}_LOD_1"

                collections[1].objects.link(lod_1)

                if scene.lutb_decimate:
                    context.view_layer.objects.active = lod_1
                    bpy.ops.object.select_all(action="DESELECT")
                    lod_1.select_set(True)

                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.select_all(action="SELECT")
                    bpy.ops.mesh.remove_doubles()
                    bpy.ops.mesh.tris_convert_to_quads()
                    bpy.ops.object.mode_set(mode="OBJECT")

                    decimate = lod_1.modifiers.new("Decimate", "DECIMATE")
                    decimate.decimate_type = "COLLAPSE"
                    decimate.ratio = 0.6
                    edge_split = lod_1.modifiers.new("EdgeSplit", "EDGE_SPLIT")
                    edge_split.split_angle = radians(48)

            if scene.lutb_use_lod2 and not lod_2:
                lod_2 = lod_0.copy()
                lod_2.data = lod_0.data.copy()
                lod_2.name = f"{lod_0.name[:-6]}_LOD_2"
                lod_2.data.name = f"{lod_0.name[:-6]}_LOD_2"

                collections[2].objects.link(lod_2)

                if scene.lutb_decimate:
                    context.view_layer.objects.active = lod_2
                    bpy.ops.object.select_all(action="DESELECT")
                    lod_2.select_set(True)

                    bpy.ops.object.mode_set(mode="EDIT")
                    bpy.ops.mesh.select_all(action="SELECT")
                    bpy.ops.mesh.remove_doubles()
                    bpy.ops.mesh.tris_convert_to_quads()
                    bpy.ops.object.mode_set(mode="OBJECT")

                    decimate = lod_2.modifiers.new("Decimate", "DECIMATE")
                    decimate.decimate_type = "COLLAPSE"
                    decimate.ratio = 0.4
                    edge_split = lod_2.modifiers.new("EdgeSplit", "EDGE_SPLIT")
                    edge_split.split_angle = radians(55)

            selection.append(lod_0)
            selection.append(lod_1)
            if scene.lutb_use_lod2:
                selection.append(lod_2)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in selection:
            obj.select_set(True)
            
        return {"FINISHED"}

class LUTB_OT_setup_lod_data(bpy.types.Operator):
    """Group LODs into \"SceneNode\"s and assign custom props"""
    bl_idname = "lutb.setup_lod_data"
    bl_label = "Setup LOD Data"  

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        scene = context.scene

        lod_memory = {}

        for obj in filter(lambda obj: obj.name[-6:-1] == "_LOD_" and obj.name[-1] in ("0", "1", "2"), context.selected_objects):
            name = obj.name[:-6]
            if not name in lod_memory:
                lod_memory[name] = [obj]
            else:
                lod_memory[name].append(obj)

        for name, lod_objects in lod_memory.items():
            parents = set(map(lambda obj: obj.parent, lod_objects)) - {None}

            if len(parents) == 0:
                parent = bpy.data.objects.new("SceneNode", None)
                scene.collection.objects.link(parent)

            elif len(parents) == 1:
                parent = parents.pop()
                if not parent.name.startswith("SceneNode"):
                    self.report({"ERROR"}, f"Fatal: LOD for \"{name}\" is parented to non \"SceneNode\" object.")
                    return {"CANCELLED"}

            else:
                self.report({"ERROR"}, f"Fatal: LODs for \"{name}\" have multiple different parents.")
                return {"CANCELLED"}

            parent["type"] = "NiLODNode"
            for obj in lod_objects:
                obj.parent = parent

                if obj.name.endswith("_LOD_0"):
                    obj["near_extent"] = scene.lutb_lod0
                    obj["far_extent"] = scene.lutb_lod1
                elif obj.name.endswith("_LOD_1"):
                    obj["near_extent"] = scene.lutb_lod1
                    obj["far_extent"] = scene.lutb_lod2
                elif obj.name.endswith("_LOD_2"):
                    obj["near_extent"] = scene.lutb_lod2
                    obj["far_extent"] = scene.lutb_cull

        return {"FINISHED"}


def register():
    bpy.utils.register_class(LUTB_OT_create_sort_lods)
    bpy.utils.register_class(LUTB_OT_setup_lod_data)
    bpy.utils.register_class(LUTB_PT_lods)

    bpy.types.Scene.lutb_decimate = BoolProperty(name="Decimate", default=True)
    bpy.types.Scene.lutb_use_lod2 = BoolProperty(name="Use LOD 2", default=True)
    bpy.types.Scene.lutb_lod0 = FloatProperty(name="LOD 0", soft_min=0.0, default=0.0, soft_max=25.0)
    bpy.types.Scene.lutb_lod1 = FloatProperty(name="LOD 1", soft_min=0.0, default=25.0, soft_max=50.0)
    bpy.types.Scene.lutb_lod2 = FloatProperty(name="LOD 2", soft_min=0.0, default=50.0, soft_max=500.0)
    bpy.types.Scene.lutb_cull = FloatProperty(name="Cull", soft_min=1000.0, default=10000.0, soft_max=50000.0)

def unregister():
    del bpy.types.Scene.lutb_decimate
    del bpy.types.Scene.lutb_use_lod2
    del bpy.types.Scene.lutb_lod0
    del bpy.types.Scene.lutb_lod1
    del bpy.types.Scene.lutb_lod2
    del bpy.types.Scene.lutb_cull

    bpy.utils.unregister_class(LUTB_PT_lods)
    bpy.utils.unregister_class(LUTB_OT_setup_lod_data)
    bpy.utils.unregister_class(LUTB_OT_create_sort_lods)
