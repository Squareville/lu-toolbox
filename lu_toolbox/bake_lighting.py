import bpy
from bpy.props import *
import numpy as np
from timeit import default_timer as timer

from .process_model import IS_TRANSPARENT
from .materials import get_lutb_ao_only_mat

WHITE_AMBIENT = "LUTB_WHITE_AMBIENT"

class LUTB_PT_bake_lighting(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Bake Lighting"

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.operator("lutb.bake_lighting")

        layout.separator()

        layout.prop(scene, "lutb_bake_samples")
        layout.prop(scene, "lutb_bake_use_gpu")
        layout.prop(scene, "lutb_bake_use_white_ambient")
        layout.prop(scene, "lutb_bake_smooth_lit")
        col = layout.column()
        col.prop(scene, "lutb_bake_ao_only")
        col.active = not scene.lutb_bake_use_mat_override

class LUTB_PT_mat_override(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "Material Override"
    bl_parent_id = "LUTB_PT_bake_lighting"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_bake_use_mat_override", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_bake_use_mat_override

        layout.prop(scene, "lutb_bake_mat_override", text="")

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

        scene.cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"

        old_samples = scene.cycles.samples
        scene.cycles.samples = scene.lutb_bake_samples

        old_max_bounces = scene.cycles.max_bounces
        if scene.lutb_bake_ao_only:
            scene.cycles.max_bounces = 0

        old_active_obj = bpy.context.object
        
        hidden_objects = []
        for obj in list(scene.collection.all_objects):
            if obj.type == "MESH" and obj.get(IS_TRANSPARENT) and not obj.hide_render:
                obj.hide_render = True
                hidden_objects.append(obj)

        for obj in (selected := list(context.selected_objects)):
            if obj.type != "MESH" or obj.get(IS_TRANSPARENT):
                continue

            mesh = obj.data

            if not mesh.materials:
                self.report({"WARNING"}, f"Skipping \"{obj.name}\". (has no materials)")
                continue

            triangulate_mods = [mod for mod in obj.modifiers if mod.type == "TRIANGULATE"]
            for modifier in triangulate_mods:
                modifier.show_render = False
            if not triangulate_mods or not obj.modifiers[-1] in triangulate_mods:
                modifier = obj.modifiers.new("Triangulate", "TRIANGULATE")
                modifier.show_render = False
            
            if vc_lit := mesh.vertex_colors.get("Lit"):
                mesh.vertex_colors.active_index = mesh.vertex_colors.keys().index(vc_lit.name)

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj

            old_material = mesh.materials[0]

            if scene.lutb_bake_ao_only and not scene.lutb_bake_use_mat_override:
                if material := get_lutb_ao_only_mat(self):
                    mesh.materials[0] = material

            if scene.lutb_bake_use_mat_override:
                mesh.materials[0] = scene.lutb_bake_mat_override
        
            bpy.ops.object.bake(target="VERTEX_COLORS")

            mesh.materials[0] = old_material

            has_edge_split_modifier = "EDGE_SPLIT" in {mod.type for mod in obj.modifiers}
            if scene.lutb_bake_smooth_lit and not has_edge_split_modifier:
                bpy.ops.object.mode_set(mode="VERTEX_PAINT")
                bpy.ops.paint.vertex_color_smooth()
                bpy.ops.object.mode_set(mode="OBJECT")

            if vc_lit and (vc_alpha := mesh.vertex_colors.get("Alpha")):
                n_loops = len(mesh.loops)

                lit_data = np.zeros(n_loops * 4)
                alpha_data = np.zeros(n_loops * 4)

                vc_lit.data.foreach_get("color", lit_data)
                vc_alpha.data.foreach_get("color", alpha_data)
                lit_data = lit_data.reshape((n_loops, 4))
                lit_data[:, 3] = alpha_data.reshape((n_loops, 4))[:, 0]
                vc_lit.data.foreach_set("color", lit_data.flatten())

        for obj in selected:
            obj.select_set(True)

        for obj in hidden_objects:
            obj.hide_render = False

        context.view_layer.objects.active = old_active_obj
        scene.cycles.samples = old_samples
        scene.cycles.max_bounces = old_max_bounces
        scene.world = old_world

        end = timer()
        print(f"finished bake lighthing in {end - start:.2f}s")

        return {"FINISHED"}


def register():
    bpy.utils.register_class(LUTB_OT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_mat_override)

    bpy.types.Scene.lutb_bake_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_bake_smooth_lit = BoolProperty(name="Smooth Vertex Colors", default=True)
    bpy.types.Scene.lutb_bake_samples = IntProperty(name="Samples", default=256,
        description="Number of samples to render for each vertex.")
    bpy.types.Scene.lutb_bake_use_white_ambient = BoolProperty(name="White Ambient", default=True,
        description="Sets ambient light to pure white while baking.")
    bpy.types.Scene.lutb_bake_ao_only = BoolProperty(name="AO Only", default=False)
    bpy.types.Scene.lutb_bake_use_mat_override = BoolProperty(name="Material Override")
    bpy.types.Scene.lutb_bake_mat_override = PointerProperty(name="Override Material", type=bpy.types.Material)

def unregister():
    del bpy.types.Scene.lutb_bake_use_gpu
    del bpy.types.Scene.lutb_bake_smooth_lit
    del bpy.types.Scene.lutb_bake_samples
    del bpy.types.Scene.lutb_bake_use_white_ambient
    del bpy.types.Scene.lutb_bake_ao_only
    del bpy.types.Scene.lutb_bake_use_mat_override
    del bpy.types.Scene.lutb_bake_mat_override

    bpy.utils.unregister_class(LUTB_PT_mat_override)
    bpy.utils.unregister_class(LUTB_PT_bake_lighting)
    bpy.utils.unregister_class(LUTB_OT_bake_lighting)
