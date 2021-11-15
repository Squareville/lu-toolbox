import bpy
from bpy.props import BoolProperty, IntProperty

class LUTB_PT_bake_lighting(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Bake Lighting"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "lutb_bake_use_gpu")
        layout.prop(scene, "lutb_smooth_lit")
        layout.prop(scene, "lutb_bake_samples")
        layout.operator("lutb.bake_lighting")

class LUTB_OT_bake_lighting(bpy.types.Operator):
    """Bake lighting"""
    bl_idname = "lutb.bake_lighting"
    bl_label = "Bake Lighting"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        scene = context.scene

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

        
        scene.cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"

        previous_samples = scene.cycles.samples
        scene.cycles.samples = scene.lutb_bake_samples

        for obj in context.selected_objects:
            if obj.type == "MESH":
                mesh = obj.data
                vc_lit = mesh.vertex_colors.get("Lit")
                if vc_lit:
                    mesh.vertex_colors.active = vc_lit

            context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
        
            bpy.ops.object.bake()

            if scene.lutb_smooth_lit:
                bpy.ops.object.mode_set(mode="VERTEX_PAINT")
                bpy.ops.paint.vertex_color_smooth()
                bpy.ops.object.mode_set(mode="OBJECT")
        
        scene.cycles.samples = previous_samples

        return {"FINISHED"}


def register():
    bpy.utils.register_class(LUTB_OT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_bake_lighting)

    bpy.types.Scene.lutb_bake_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_smooth_lit = BoolProperty(name="Smooth Vertex Colors", default=True)
    bpy.types.Scene.lutb_bake_samples = IntProperty(name="Samples", default=256)

def unregister():
    del bpy.types.Scene.lutb_bake_use_gpu
    del bpy.types.Scene.lutb_smooth_lit
    del bpy.types.Scene.lutb_bake_samples

    bpy.utils.unregister_class(LUTB_PT_bake_lighting)
    bpy.utils.unregister_class(LUTB_OT_bake_lighting)
