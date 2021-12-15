import bpy, bmesh
from bpy.props import BoolProperty, FloatProperty, PointerProperty, IntProperty
from mathutils import Color
import random

from .remove_hidden_faces import LUTB_OT_remove_hidden_faces

MATERIALS_OPAQUE = {
    "26": (0.006, 0.006, 0.006, 1.0),
    "199": (0.072272, 0.082283, 0.093059, 1.0),
    "194": (0.332452, 0.283149, 0.283149, 1.0),
    "208": (0.768151, 0.768151, 0.693872, 1.0),
    "1": (0.904661, 0.904661, 0.904661, 1.0),
    "154": (0.215861, 0.002428, 0.01096, 1.0),
    "21": (0.730461, 0.0, 0.004025, 1.0),
    "308": (0.03434, 0.015209, 0.0, 1.0),
    "192": (0.104617, 0.011612, 0.003677, 1.0),
    "138": (0.262251, 0.177888, 0.084376, 1.0),
    "5": (0.693872, 0.491021, 0.194618, 1.0),
    "38": (0.391572, 0.046665, 0.007499, 1.0),
    "18": (0.672443, 0.168269, 0.051269, 1.0),
    "106": (0.799103, 0.124772, 0.009134, 1.0),
    "191": (0.887923, 0.318547, 0.0, 1.0),
    "283": (0.913099, 0.533276, 0.250158, 1.0),
    "24": (0.991102, 0.552011, 0.0, 1.0),
    "226": (1.0, 0.768151, 0.141263, 1.0),
    "329": (0.913099, 0.896269, 0.679542, 1.0),
    "141": (0.0, 0.03434, 0.008023, 1.0),
    "151": (0.114435, 0.223228, 0.130137, 1.0),
    "28": (0.0, 0.198069, 0.021219, 1.0),
    "37": (0.0, 0.304987, 0.017642, 1.0),
    "119": (0.296138, 0.47932, 0.003035, 1.0),
    "326": (0.760525, 0.947307, 0.323143, 1.0),
    "140": (0.0, 0.0185, 0.052861, 1.0),
    "23": (0.0, 0.095307, 0.391572, 1.0),
    "102": (0.06301, 0.262251, 0.564712, 1.0),
    "135": (0.111932, 0.174647, 0.262251, 1.0),
    "212": (0.242281, 0.520996, 0.83077, 1.0),
    "268": (0.025187, 0.007499, 0.184475, 1.0),
    "124": (0.332452, 0.0, 0.147027, 1.0),
    "221": (0.730461, 0.038204, 0.258183, 1.0),
    "222": (0.846873, 0.341914, 0.53948, 1.0),
}

MATERIALS_TRANSPARENT = {
    "40": (0.854993, 0.854993, 0.854993, 1.0),
    "41": (0.745405, 0.023153, 0.022174, 1.0),
    "311": (0.846873, 0.341914, 0.53948, 1.0),
    "113": (0.846873, 0.341914, 0.53948, 1.0),
    "111": (0.846873, 0.341914, 0.53948, 1.0),
    "294": (0.846873, 0.341914, 0.53948, 1.0),
    "43": (0.08022, 0.439657, 0.806952, 1.0),
    "42": (0.846873, 0.341914, 0.53948, 1.0),
    "126": (0.846873, 0.341914, 0.53948, 1.0),
    "48": (0.846873, 0.341914, 0.53948, 1.0),
    "182": (0.846873, 0.341914, 0.53948, 1.0),
    "44": (0.846873, 0.341914, 0.53948, 1.0),
    "47": (0.846873, 0.341914, 0.53948, 1.0),
    "49": (0.846873, 0.341914, 0.53948, 1.0),
    "143": (0.846873, 0.341914, 0.53948, 1.0),
}

IS_TRANSPARENT = "lu_toolbox_is_transparent"

LOD_SUFFIXES = ("LOD_0", "LOD_1", "LOD_2")

class LUTB_PT_process_model(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Process Model"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.box().prop(scene, "lutb_process_use_gpu")
        
        box = layout.box()
        box.prop(scene, "lutb_combine_objects")
        col = box.column()
        col.prop(scene, "lutb_combine_transparent")
        col.enabled = scene.lutb_combine_objects
        
        box = layout.box()
        box.prop(scene, "lutb_correct_colors")
        box.prop(scene, "lutb_use_color_variation")
        col = box.column()
        col.prop(scene, "lutb_color_variation")
        col.enabled = scene.lutb_use_color_variation
        box.prop(scene, "lutb_apply_vertex_colors")

        box = layout.box()
        box.prop(scene, "lutb_setup_bake_mats")
        col = box.column()
        col.prop(scene, "lutb_bake_mat", text="")
        col.enabled = scene.lutb_setup_bake_mats

        box = layout.box()
        box.prop(scene, "lutb_setup_bake_env")
        col = box.column()
        col.prop(scene, "lutb_bake_env", text="")
        col.enabled = scene.lutb_setup_bake_env

        box = layout.box()
        box.prop(scene, "lutb_remove_hidden_faces")
        col = box.column()
        col.prop(scene, "lutb_autoremove_hidden_faces", toggle=1)
        col.prop(scene, "lutb_hidden_surfaces_tris_to_quads", toggle=1)
        col.prop(scene, "lutb_pixels_between_verts", slider=True)
        col.prop(scene, "lutb_hidden_surfaces_samples", slider=True)
        col.enabled = scene.lutb_remove_hidden_faces

        box = layout.box()
        box.prop(scene, "lutb_setup_lod_data")
        col = box.column()
        col.prop(scene, "lutb_lod0")
        col.prop(scene, "lutb_lod1")
        col.prop(scene, "lutb_lod2")
        col.prop(scene, "lutb_cull")
        col.enabled = scene.lutb_setup_lod_data

        layout.operator("lutb.process_model")

class LUTB_OT_process_model(bpy.types.Operator):
    """Process LU model"""
    bl_idname = "lutb.process_model"
    bl_label = "Process Model"  

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        scene = context.scene

        if not scene.lutb_bake_mat:
            scene.lutb_bake_mat = bpy.data.materials.get("VertexColor")
        if not scene.lutb_bake_env:
            world = bpy.data.worlds.new(name="AmbientOcclusion")
            world.use_nodes = True
            world.node_tree.nodes["Background"].inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
            scene.lutb_bake_env = world

        scene.render.engine = "CYCLES"
        scene.cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"

        self.precombine_bricks(context, scene.collection.children)

        for obj in scene.collection.all_objects:
            if not obj.type == "MESH":
                continue

            mat_names = {material.name.split(".")[0] for material in obj.data.materials}
            if mat_names.issubset(MATERIALS_TRANSPARENT):
                obj[IS_TRANSPARENT] = True

        """for obj in scene.collection.all_objects:
            if obj.type != "EMPTY":
                matrix_world = obj.matrix_world.copy()
                obj.parent = None
                obj.matrix_world = matrix_world
        for obj in list(scene.collection.all_objects):
            if obj.type == "EMPTY":
                bpy.data.objects.remove(obj)"""

        if scene.lutb_combine_objects:
            self.combine_objects(context, scene.collection.children)

        context.view_layer.update()

        opaque_objects = []
        transparent_objects = []
        for collection in scene.collection.children:
            if not collection.children:
                self.report({"WARNING"},
                    f"Ignoring \"{collection.name}\": doesn't have any LOD collections"
                )
                continue

            for lod_collection in collection.children:
                if not lod_collection.name[-5:] in LOD_SUFFIXES:
                    self.report({"WARNING"},
                        f"Ignoring \"{lod_collection.name}\": not a LOD collection ({LOD_SUFFIXES})"
                    )
                    continue

                for obj in lod_collection.all_objects:
                    if obj.type == "MESH":
                        if not obj.get(IS_TRANSPARENT):
                            opaque_objects.append(obj)
                        else:
                            transparent_objects.append(obj)
        all_objects = opaque_objects + transparent_objects

        if not all_objects:
            return {"FINISHED"}

        if scene.lutb_correct_colors:
            self.correct_colors(context, all_objects)
                
        if scene.lutb_use_color_variation:
            self.apply_color_variation(context, all_objects)

        if scene.lutb_apply_vertex_colors:
            self.apply_vertex_colors(context, all_objects)

        if scene.lutb_setup_bake_mats:
            self.setup_bake_mats(context, all_objects)

        if scene.lutb_setup_bake_env:
            self.setup_bake_env(context)

        if scene.lutb_remove_hidden_faces:
            for obj in transparent_objects:
                obj.hide_render = True

            self.remove_hidden_faces(context, opaque_objects)

            for obj in transparent_objects:
                obj.hide_render = False

        if scene.lutb_setup_lod_data:
            self.setup_lod_data(context, scene.collection.children)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in all_objects:
            obj.select_set(True)

        return {"FINISHED"}

    def precombine_bricks(self, context, collections):
        bricks = {}
        for collection in collections:
            if not collection.children:
                continue

            for lod_collection in collection.children:
                if not lod_collection.name[-5:] in LOD_SUFFIXES:
                    continue
        
                for obj in lod_collection.all_objects:
                    if not (obj.type == "MESH" and obj.parent):
                        continue

                    if brick := bricks.get(obj.parent):
                        brick.append(obj)
                    else:
                        bricks[obj.parent] = [obj]

        if not bricks:
            return

        for parent_empty, children in bricks.items():
            bm = bmesh.new()
            materials = {}

            for child in children:
                mesh = child.data
                for old_mat_index, material in enumerate(mesh.materials):
                    mat_name = material.name.split(".")[0]
                    if mat := materials.get(mat_name):
                        new_mat_index = mat[1]
                    else:
                        new_mat_index = len(materials)
                        materials[mat_name] = (material, new_mat_index)
                    
                    if old_mat_index != new_mat_index:
                        for polygon in mesh.polygons:
                            if polygon.material_index == old_mat_index:
                                polygon.material_index = new_mat_index

                bm.from_mesh(mesh)

            combined = children[0]
            combined.name = parent_empty.name
            combined.parent = None
            combined.matrix_world = parent_empty.matrix_world.copy()
            bm.to_mesh(combined.data)

            combined.data.materials.clear()
            # dictionaries are guaranteed to be ordered in 3.7+ (see PEP 468)
            for material, _ in materials.values():
                combined.data.materials.append(material)

            bpy.data.objects.remove(parent_empty)
            for obj in children[1:]:
                bpy.data.objects.remove(obj)

        for obj in list(collection.all_objects):
            if obj.type == "EMPTY":
                bpy.data.objects.remove(obj)

    def combine_objects(self, context, collections):
        scene = context.scene

        for collection in collections:
            if not collection.children:
                continue

            for lod_collection in collection.children:
                if not lod_collection.name[-5:] in LOD_SUFFIXES:
                    continue

                objs_opaque = []
                for obj in lod_collection.all_objects:
                    if obj.type == "MESH" and not obj.get(IS_TRANSPARENT):
                        objs_opaque.append(obj)

                if objs_opaque:
                    joined_opaque = self.join_objects(context, objs_opaque)
                    joined_opaque.name = lod_collection.name[:-6]

                objs_transparent = []
                for obj in lod_collection.all_objects:
                    if obj.type == "MESH" and obj.get(IS_TRANSPARENT):
                        objs_transparent.append(obj)

                if scene.lutb_combine_transparent:
                    if objs_transparent:
                        joined_transparent = self.join_objects(context, objs_transparent)
                        joined_transparent.name = lod_collection.name[:-6]
                        joined_transparent[IS_TRANSPARENT] = True

    def join_objects(self, context, objects):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)

        joined = objects[0]
        context.view_layer.objects.active = joined
        bpy.ops.object.join()
        bpy.ops.object.transform_apply()
        return joined

    def correct_colors(self, context, objects):
        for obj in objects:
            for material in obj.data.materials:
                name = material.name.split(".")[0]
                if color := MATERIALS_OPAQUE.get(name):
                    material.diffuse_color = color
                elif color := MATERIALS_TRANSPARENT.get(name):
                    material.diffuse_color = color
    
    def apply_color_variation(self, context, objects):
        variation = context.scene.lutb_color_variation
        for obj in objects:
            for material in obj.data.materials:
                color = Color(material.diffuse_color[:3])
                gamma = color.v ** (1 / 2.224)
                gamma += random.uniform(-variation / 200, variation / 200)
                color.v = min(max(0, gamma), 1) ** 2.224
                material.diffuse_color = (*color, 1.0)

    def apply_vertex_colors(self, context, objects):
        scene = context.scene

        scene.render.engine = "CYCLES"
        scene.cycles.bake_type = "DIFFUSE"
        scene.render.bake.use_pass_direct = False
        scene.render.bake.use_pass_indirect = False
        scene.render.bake.use_pass_color = True
        scene.render.bake.target = "VERTEX_COLORS"

        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)

            mesh = obj.data
            vc_col = mesh.vertex_colors.get("Col")
            if not vc_col:
                vc_col = mesh.vertex_colors.new(name="Col")
            if not obj.get(IS_TRANSPARENT):
                vc_lit = mesh.vertex_colors.get("Lit")
                if not vc_lit:
                    vc_lit = mesh.vertex_colors.new(name="Lit")
            mesh.vertex_colors.active = vc_col

        context.view_layer.objects.active = objects[0]
        bpy.ops.object.bake(type="DIFFUSE")

        shading = context.area.spaces[0].shading
        shading.type = "SOLID"
        shading.light = "FLAT"
        shading.color_type = "VERTEX"

    def setup_bake_mats(self, context, objects):
        for obj in objects:
            mesh = obj.data
            mesh.materials.clear()
            mesh.materials.append(context.scene.lutb_bake_mat)

    def setup_bake_env(self, context):
        scene = context.scene

        if scene.lutb_bake_env:
            scene.world = scene.lutb_bake_env
        
        scene.render.engine = "CYCLES"
        scene.cycles.bake_type = "COMBINED"
        scene.render.bake.use_pass_direct = True
        scene.render.bake.use_pass_indirect = True
        scene.render.bake.use_pass_diffuse = True
        scene.render.bake.use_pass_glossy = False
        scene.render.bake.use_pass_transmission = True
        scene.render.bake.use_pass_emit = True
        scene.render.bake.target = "VERTEX_COLORS"

    def remove_hidden_faces(self, context, objects):
        scene = context.scene

        for obj in objects:
            if obj.get(IS_TRANSPARENT):
                continue

            context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)

            bpy.ops.lutb.remove_hidden_faces(
                autoremove=scene.lutb_autoremove_hidden_faces,
                tris_to_quads=scene.lutb_hidden_surfaces_tris_to_quads,
                pixels_between_verts=scene.lutb_pixels_between_verts,
                samples=scene.lutb_hidden_surfaces_samples,
            )

    def setup_lod_data(self, context, collections):
        scene = context.scene

        for collection in collections:
            if not collection.children:
                continue

            scene_node = bpy.data.objects.new(f"SceneNode_{collection.name}", None)
            collection.objects.link(scene_node)

            coll_opaque = bpy.data.collections.new(f"Opaque_{collection.name}")
            coll_transparent = bpy.data.collections.new(f"Transparent_{collection.name}")

            ni_nodes = {}
            for lod_collection in list(collection.children):
                suffix = lod_collection.name[-5:]
                if not suffix in LOD_SUFFIXES:
                    continue

                for obj in list(lod_collection.all_objects):
                    is_transparent = bool(obj.get(IS_TRANSPARENT))

                    shader_prefix = "S01" if is_transparent else "S01"
                    type_prefix = "Alpha" if is_transparent else "Opaque"
                    obj_name = obj.name[:-4] if obj.name[-4] == "." else obj.name
                    name = f"{shader_prefix}_{type_prefix}_{obj_name}"[:60]

                    if not (node := ni_nodes.get(name)):
                        node = bpy.data.objects.new(name, None)
                        node["type"] = "NiLODNode"
                        node.parent = scene_node
                        ni_nodes[name] = node

                        if is_transparent:
                            coll_transparent.objects.link(node)
                        else:
                            coll_opaque.objects.link(node)

                    lod_obj = bpy.data.objects.new(suffix, None) # f"{suffix}_{name}"
                    lod_obj.parent = node

                    lod_collection.objects.unlink(obj)
                    obj.parent = lod_obj

                    if is_transparent:
                        coll_transparent.objects.link(lod_obj)
                        coll_transparent.objects.link(obj)
                    else:
                        coll_opaque.objects.link(lod_obj)
                        coll_opaque.objects.link(obj)

                    if suffix == LOD_SUFFIXES[0]:
                        lod_obj["near_extent"] = scene.lutb_lod0
                        lod_obj["far_extent"] = scene.lutb_lod1
                    elif suffix == LOD_SUFFIXES[1]:
                        lod_obj["near_extent"] = scene.lutb_lod1
                        lod_obj["far_extent"] = scene.lutb_lod2
                    elif suffix == LOD_SUFFIXES[2]:
                        lod_obj["near_extent"] = scene.lutb_lod2
                        lod_obj["far_extent"] = scene.lutb_cull

                collection.children.unlink(lod_collection)
            
            collection.children.link(coll_opaque)
            collection.children.link(coll_transparent)

def register():
    bpy.utils.register_class(LUTB_OT_process_model)
    bpy.utils.register_class(LUTB_PT_process_model)

    bpy.types.Scene.lutb_process_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_combine_objects = BoolProperty(name="Combine Objects", default=True)
    bpy.types.Scene.lutb_combine_transparent = BoolProperty(name="Combine Transparent", default=False)
    bpy.types.Scene.lutb_correct_colors = BoolProperty(name="Correct Colors", default=True)

    bpy.types.Scene.lutb_use_color_variation = BoolProperty(name="Apply Color Variation", default=True)
    bpy.types.Scene.lutb_color_variation = FloatProperty(name="Color Variation", subtype="PERCENTAGE", min=0.0, soft_max=15.0, max=100.0, default=5.0)
    
    bpy.types.Scene.lutb_apply_vertex_colors = BoolProperty(name="Apply Vertex Colors", default=True)
    
    bpy.types.Scene.lutb_setup_bake_mats = BoolProperty(name="Setup Bake Materials", default=True)
    bpy.types.Scene.lutb_bake_mat= PointerProperty(name="Bake Material", type=bpy.types.Material)
    
    bpy.types.Scene.lutb_setup_bake_env = BoolProperty(name="Setup Bake Environment", default=True)
    bpy.types.Scene.lutb_bake_env = PointerProperty(name="Bake Environment", type=bpy.types.World)
    
    bpy.types.Scene.lutb_remove_hidden_faces = BoolProperty(name="Remove Hidden Faces", default=True,
        description=LUTB_OT_remove_hidden_faces.__doc__)
    bpy.types.Scene.lutb_autoremove_hidden_faces = BoolProperty(name="Autoremove", default=True)
    bpy.types.Scene.lutb_hidden_surfaces_tris_to_quads = BoolProperty(name="Tris to Quads", default=True)
    bpy.types.Scene.lutb_pixels_between_verts = IntProperty(name="Pixels Between Vertices", min=0, default=5, soft_max=15)
    bpy.types.Scene.lutb_hidden_surfaces_samples = IntProperty(name="Samples", min=0, default=8, soft_max=32)

    bpy.types.Scene.lutb_setup_lod_data = BoolProperty(name="Setup LOD Data", default=True)
    bpy.types.Scene.lutb_lod0 = FloatProperty(name="LOD 0", soft_min=0.0, default=0.0, soft_max=25.0)
    bpy.types.Scene.lutb_lod1 = FloatProperty(name="LOD 1", soft_min=0.0, default=25.0, soft_max=50.0)
    bpy.types.Scene.lutb_lod2 = FloatProperty(name="LOD 2", soft_min=0.0, default=50.0, soft_max=500.0)
    bpy.types.Scene.lutb_cull = FloatProperty(name="Cull", soft_min=1000.0, default=10000.0, soft_max=50000.0)

def unregister():
    del bpy.types.Scene.lutb_process_use_gpu
    del bpy.types.Scene.lutb_combine_objects
    del bpy.types.Scene.lutb_correct_colors
    
    del bpy.types.Scene.lutb_use_color_variation
    del bpy.types.Scene.lutb_color_variation
    
    del bpy.types.Scene.lutb_apply_vertex_colors
    
    del bpy.types.Scene.lutb_setup_bake_mats
    del bpy.types.Scene.lutb_bake_mat
    
    del bpy.types.Scene.lutb_remove_hidden_faces
    del bpy.types.Scene.lutb_autoremove_hidden_faces
    del bpy.types.Scene.lutb_hidden_surfaces_tris_to_quads
    del bpy.types.Scene.lutb_pixels_between_verts
    del bpy.types.Scene.lutb_hidden_surfaces_samples
    
    del bpy.types.Scene.lutb_setup_bake_env
    del bpy.types.Scene.lutb_bake_env

    bpy.utils.unregister_class(LUTB_PT_process_model)
    bpy.utils.unregister_class(LUTB_OT_process_model)
