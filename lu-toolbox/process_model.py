import bpy
from bpy.props import BoolProperty, FloatProperty, PointerProperty, IntProperty
from mathutils import Color
import random

color_correction = {
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

class LUTB_PT_process_model(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Process Model"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "lutb_process_use_gpu")
        layout.prop(scene, "lutb_combine_objects")
        layout.prop(scene, "lutb_correct_colors")

        layout.prop(scene, "lutb_use_color_variation")
        col = layout.column()
        col.prop(scene, "lutb_color_variation")
        col.enabled = scene.lutb_use_color_variation

        layout.prop(scene, "lutb_apply_vertex_colors")

        layout.prop(scene, "lutb_setup_bake_mats")
        col = layout.column()
        col.prop(scene, "lutb_bake_mat", text="")
        col.enabled = scene.lutb_setup_bake_mats

        layout.prop(scene, "lutb_setup_bake_env")
        col = layout.column()
        col.prop(scene, "lutb_bake_env", text="")
        col.enabled = scene.lutb_setup_bake_env

        layout.prop(scene, "lutb_remove_hidden_faces")
        col = layout.column()
        col.prop(scene, "lutb_autoremove_hidden_faces", toggle=1)
        col.prop(scene, "lutb_hidden_surfaces_tris_to_quads", toggle=1)
        col.prop(scene, "lutb_pixels_between_verts", slider=True)
        col.prop(scene, "lutb_hidden_surfaces_samples", slider=True)
        col.enabled = scene.lutb_remove_hidden_faces

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

        if scene.lutb_combine_objects:
            for collection in scene.collection.children:
                if len(collection.all_objects) > 1:
                    bpy.ops.object.select_all(action="DESELECT")
                    for obj in collection.all_objects:
                        if obj.type == "MESH":
                            obj.select_set(True)

                    context.view_layer.objects.active = obj

                    bpy.ops.object.join()

                    matrix_world = context.object.matrix_world.copy()
                    context.object.parent = None
                    context.object.matrix_world = matrix_world
                    bpy.ops.object.transform_apply()

                    for obj in collection.all_objects:
                        if obj.type == "EMPTY":
                            bpy.data.objects.remove(obj)

                if len(collection.objects) > 0:
                    obj = collection.objects[0]
                    obj.name = f"{collection.name}_LOD_0"
                    obj.data.name = obj.name
                else:
                    self.report({"WARNING"}, f"Collection \"{collection.name}\" is empty.")
        
        context.view_layer.update()
        objects = list(filter(lambda obj: obj.type == "MESH", scene.collection.all_objects))

        for obj in objects:
            for material in obj.data.materials:
                if scene.lutb_correct_colors:
                    name = material.name if not "." in material.name else material.name.split(".")[0]
                    if name in color_correction:
                        material.diffuse_color = color_correction[name]
                
                if scene.lutb_use_color_variation:
                    color = Color(material.diffuse_color[:3])
                    gamma = color.v ** (1 / 2.224)
                    gamma += random.uniform(-scene.lutb_color_variation / 200, scene.lutb_color_variation / 200)
                    color.v = min(max(0, gamma), 1) ** 2.224
                    material.diffuse_color = (*color, 1.0)

        if scene.lutb_apply_vertex_colors:
            scene.render.engine = "CYCLES"
            scene.cycles.bake_type = "DIFFUSE"
            scene.render.bake.use_pass_direct = False
            scene.render.bake.use_pass_indirect = False
            scene.render.bake.use_pass_color = True
            scene.render.bake.target = "VERTEX_COLORS"

            for obj in objects:
                mesh = obj.data

                vc_lit = mesh.vertex_colors.get("Lit")
                if not vc_lit:
                    vc_lit = mesh.vertex_colors.new(name="Lit")
                vc_col = mesh.vertex_colors.get("Col")
                if not vc_col:
                    vc_col = mesh.vertex_colors.new(name="Col")

                mesh.vertex_colors.active = vc_col

                context.view_layer.objects.active = obj
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)

                bpy.ops.object.bake(type="DIFFUSE")

            context.area.spaces[0].shading.type = "SOLID"
            context.area.spaces[0].shading.light = "FLAT"
            context.area.spaces[0].shading.color_type = "VERTEX"

        if scene.lutb_setup_bake_mats:
            for obj in objects:
                mesh = obj.data
                mesh.materials.clear()
                
                if scene.lutb_bake_mat:
                    mesh.materials.append(scene.lutb_bake_mat)

        if scene.lutb_setup_bake_env:
            if scene.lutb_bake_env:
                scene.world = scene.lutb_bake_env
            
            scene.render.engine = "CYCLES"
            scene.cycles.bake_type = "COMBINED"
            scene.render.bake.use_pass_direct = True
            scene.render.bake.use_pass_indirect = True
            scene.render.bake.use_pass_diffuse = True
            scene.render.bake.use_pass_glossy = False
            scene.render.bake.use_pass_transmission = True
            scene.render.bake.use_pass_ambient_occlusion = True
            scene.render.bake.use_pass_emit = True
            scene.render.bake.target = "VERTEX_COLORS"

        if scene.lutb_remove_hidden_faces:
            for obj in objects:
                context.view_layer.objects.active = obj
                bpy.ops.object.select_all(action="DESELECT")
                obj.select_set(True)

                bpy.ops.lutb.remove_hidden_faces(
                    autoremove=scene.lutb_autoremove_hidden_faces,
                    tris_to_quads=scene.lutb_hidden_surfaces_tris_to_quads,
                    pixels_between_verts=scene.lutb_pixels_between_verts,
                    samples=scene.lutb_hidden_surfaces_samples,
                )

        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)

        return {"FINISHED"}


def register():
    bpy.utils.register_class(LUTB_OT_process_model)
    bpy.utils.register_class(LUTB_PT_process_model)

    bpy.types.Scene.lutb_process_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_combine_objects = BoolProperty(name="Combine Objects", default=True)
    bpy.types.Scene.lutb_correct_colors = BoolProperty(name="Correct Colors", default=True)

    bpy.types.Scene.lutb_use_color_variation = BoolProperty(name="Apply Color Variation", default=True)
    bpy.types.Scene.lutb_color_variation = FloatProperty(name="Color Variation", subtype="PERCENTAGE", min=0.0, soft_max=15.0, max=100.0, default=5.0)
    
    bpy.types.Scene.lutb_apply_vertex_colors = BoolProperty(name="Apply Vertex Colors", default=True)
    
    bpy.types.Scene.lutb_setup_bake_mats = BoolProperty(name="Setup Bake Materials", default=True)
    bpy.types.Scene.lutb_bake_mat= PointerProperty(name="Bake Material", type=bpy.types.Material)
    
    bpy.types.Scene.lutb_remove_hidden_faces = BoolProperty(name="Remove Hidden Faces", default=True)
    bpy.types.Scene.lutb_autoremove_hidden_faces = BoolProperty(name="Autoremove", default=True)
    bpy.types.Scene.lutb_hidden_surfaces_tris_to_quads = BoolProperty(name="Tris to Quads", default=True)
    bpy.types.Scene.lutb_pixels_between_verts = IntProperty(name="Pixels Between Vertices", min=0, default=5, soft_max=15)
    bpy.types.Scene.lutb_hidden_surfaces_samples = IntProperty(name="Samples", min=0, default=8, soft_max=32)
    
    bpy.types.Scene.lutb_setup_bake_env = BoolProperty(name="Setup Bake Environment", default=True)
    bpy.types.Scene.lutb_bake_env = PointerProperty(name="Bake Environment", type=bpy.types.World)

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
