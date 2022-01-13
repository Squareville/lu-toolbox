import bpy
from bpy.props import BoolProperty, IntProperty
from .process_model import IS_TRANSPARENT
from timeit import default_timer as timer

WHITE_AMBIENT = "LUTB_WHITE_AMBIENT"

class LUTB_PT_bake_lighting(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Bake Lighting"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        box = layout.box()
        box.prop(scene, "lutb_bake_use_gpu")
        box.prop(scene, "lutb_bake_use_white_ambient")
        box.prop(scene, "lutb_bake_smooth_lit")
        box.prop(scene, "lutb_bake_samples")

        layout.operator("lutb.bake_lighting")

class LUTB_OT_bake_lighting(bpy.types.Operator):
    """Bake scene lighting to vertex color layer named \"Lit\" on all selected objects"""
    bl_idname = "lutb.bake_lighting"
    bl_label = "Bake Lighting"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        start = timer()

        scene = context.scene

        old_world = scene.world
        if scene.lutb_bake_use_white_ambient:
            if not (world := bpy.data.worlds.get(WHITE_AMBIENT)):
                world = bpy.data.worlds.new(WHITE_AMBIENT)
                world.color = (1.0, 1.0, 1.0)
            scene.world = world

        scene.render.engine = "CYCLES"
        scene.cycles.bake_type = "COMBINED"
        scene.cycles.caustics_reflective = False
        scene.cycles.caustics_refractive = False
        scene.render.bake.use_pass_direct = True
        scene.render.bake.use_pass_indirect = True
        scene.render.bake.use_pass_diffuse = True
        scene.render.bake.use_pass_glossy = False
        scene.render.bake.use_pass_transmission = True
        scene.render.bake.use_pass_emit = True
        scene.render.bake.target = "VERTEX_COLORS"

        scene.cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"

        old_samples = scene.cycles.samples
        scene.cycles.samples = scene.lutb_bake_samples

        old_active_obj = bpy.context.object
        
        hidden_objects = []
        for obj in list(scene.collection.all_objects):
            if obj.type == "MESH" and obj.get(IS_TRANSPARENT) and not obj.hide_render:
                obj.hide_render = True
                hidden_objects.append(obj)

        for obj in (selected := list(context.selected_objects)):
            if obj.type != "MESH":
                self.report({"WARNING"}, f"Ignoring \"{obj.name}\". (not a mesh)")
                continue

            if obj.get(IS_TRANSPARENT):
                self.report({"WARNING"}, f"Ignoring \"{obj.name}\". (transparent)")
                continue

            mesh = obj.data
            vc_lit = mesh.vertex_colors.get("Lit")
            if vc_lit:
                mesh.vertex_colors.active = vc_lit

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj
        
            bpy.ops.object.bake()

            has_edge_split_modifier = "EDGE_SPLIT" in {mod.type for mod in obj.modifiers}
            if scene.lutb_bake_smooth_lit and not has_edge_split_modifier:
                bpy.ops.object.mode_set(mode="VERTEX_PAINT")
                bpy.ops.paint.vertex_color_smooth()
                bpy.ops.object.mode_set(mode="OBJECT")

        for obj in selected:
            obj.select_set(True)

        for obj in hidden_objects:
            obj.hide_render = False

        context.view_layer.objects.active = old_active_obj
        scene.cycles.samples = old_samples
        scene.world = old_world

        end = timer()
        print(f"finished bake lighthing in {end - start:.2f}s")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(LUTB_OT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_bake_lighting)

    bpy.types.Scene.lutb_bake_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_bake_smooth_lit = BoolProperty(name="Smooth Vertex Colors", default=True)
    bpy.types.Scene.lutb_bake_samples = IntProperty(name="Samples", default=256,
        description="Number of samples to render for each vertex.")
    bpy.types.Scene.lutb_bake_use_white_ambient = BoolProperty(name="White Ambient", default=True,
        description="Sets ambient light to pure white while baking.")

def unregister():
    del bpy.types.Scene.lutb_bake_use_gpu
    del bpy.types.Scene.lutb_bake_smooth_lit
    del bpy.types.Scene.lutb_bake_samples
    del bpy.types.Scene.lutb_bake_use_white_ambient

    bpy.utils.unregister_class(LUTB_PT_bake_lighting)
    bpy.utils.unregister_class(LUTB_OT_bake_lighting)
