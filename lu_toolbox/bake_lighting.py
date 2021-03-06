import bpy
from bpy.props import *
import numpy as np
from timeit import default_timer as timer

from .process_model import IS_TRANSPARENT
from .materials import get_lutb_force_white_mat

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

        layout.prop(scene, "lutb_bake_use_gpu")
        layout.prop(scene, "lutb_bake_selected_only")
        col = layout.column()
        col.prop(scene, "lutb_bake_use_white_ambient")
        col.active = not scene.lutb_bake_ao_only
        layout.prop(scene, "lutb_bake_smooth_lit")
        col = layout.column()
        col.prop(scene, "lutb_bake_force_to_white")
        col.active = not scene.lutb_bake_use_mat_override

        layout.prop(scene, "lutb_bake_samples")
        layout.prop(scene, "lutb_bake_fast_gi_bounces")
        layout.prop(scene, "lutb_bake_glow_strength")

class LUTB_PT_bake_ao_only(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"
    bl_label = "AO Only"
    bl_parent_id = "LUTB_PT_bake_lighting"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_bake_ao_only", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_bake_ao_only

        layout.prop(scene, "lutb_bake_glow_multiplier")
        layout.prop(scene, "lutb_bake_ao_samples")

class LUTB_PT_bake_mat_override(bpy.types.Panel):
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
        scene_override = scene.copy()

        render = scene_override.render
        cycles = scene_override.cycles
        render.engine = "CYCLES"
        cycles.use_denoising = False
        cycles.bake_type = "COMBINED"
        cycles.caustics_reflective = False
        cycles.caustics_refractive = False
        render.bake.use_pass_direct = True
        render.bake.use_pass_indirect = True
        render.bake.use_pass_diffuse = True
        render.bake.use_pass_glossy = False
        render.bake.use_pass_transmission = True
        render.bake.use_pass_emit = True
        render.bake.target = "VERTEX_COLORS"

        cycles.use_fast_gi = True
        cycles.ao_bounces_render = scene.lutb_bake_fast_gi_bounces

        cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"
        cycles.samples = scene.lutb_bake_samples

        if scene.lutb_bake_use_white_ambient:
            if not (world := bpy.data.worlds.get(WHITE_AMBIENT)):
                world = bpy.data.worlds.new(WHITE_AMBIENT)
                world.color = (1.0, 1.0, 1.0)
            scene_override.world = world

        emission_strength = scene.lutb_bake_glow_strength

        ao_only_world_override = None
        if scene.lutb_bake_ao_only:
            cycles.max_bounces = 0
            cycles.fast_gi_method = "ADD"
            cycles.samples = scene.lutb_bake_ao_samples

            ao_only_world_override = bpy.data.worlds.new("AO_ONLY")
            ao_only_world_override.color = (0.0, 0.0, 0.0)
            ao_only_world_override.light_settings.ao_factor = 1.0
            ao_only_world_override.light_settings.distance = 5.0
            scene_override.world = ao_only_world_override

            emission_strength *= scene.lutb_bake_glow_multiplier

        hidden_objects = []
        for obj in list(scene.collection.all_objects):
            if obj.type == "MESH" and obj.get(IS_TRANSPARENT) and not obj.hide_render:
                obj.hide_render = True
                hidden_objects.append(obj)

        target_objects = scene.collection.all_objects
        if scene.lutb_bake_selected_only:
            target_objects = context.selected_objects

        old_active_obj = context.object
        old_selected_objects = context.selected_objects
        for obj in list(target_objects):
            if obj.type != "MESH" or obj.get(IS_TRANSPARENT):
                continue
            if not obj.name in context.view_layer.objects:
                self.report({"WARNING"}, f"Skipping \"{obj.name}\". (not in viewlayer)")
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

            other_lod_colls = set()
            for lod_collection in obj.users_collection:
                for collection in bpy.data.collections:
                    if lod_collection.name in collection.children:
                        other_lod_colls |= set(collection.children) - {lod_collection,}

            for other_lod_coll in list(other_lod_colls):
                if other_lod_coll.hide_render:
                    other_lod_colls.remove(other_lod_coll)
                else:
                    other_lod_coll.hide_render = True

            old_material = mesh.materials[0]
            if scene.lutb_bake_use_mat_override:
                mesh.materials[0] = scene.lutb_bake_mat_override
            elif scene.lutb_bake_force_to_white:
                if material := get_lutb_force_white_mat(self):
                    mesh.materials[0] = material

            if mesh.materials[0].use_nodes:
                for node in mesh.materials[0].node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        node.inputs['Emission Strength'].default_value = emission_strength

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            context.view_layer.objects.active = obj

            context_override = context.copy()
            context_override["scene"] = scene_override
            try:
                bpy.ops.object.bake(context_override)
            except RuntimeError as e:
                if "is not enabled for rendering" in str(e):
                    self.report({"WARNING"}, f"Skipping \"{obj.name}\". (not enabled for rendering)")
                    continue
                else:
                    raise
            finally:
                mesh.materials[0] = old_material

                for other_lod_coll in other_lod_colls:
                    other_lod_coll.hide_render = False

            has_edge_split_modifier = "EDGE_SPLIT" in {mod.type for mod in obj.modifiers}
            if scene.lutb_bake_smooth_lit and not has_edge_split_modifier:
                bpy.ops.object.mode_set(mode="VERTEX_PAINT")
                if mesh.use_paint_mask or mesh.use_paint_mask_vertex:
                    bpy.ops.paint.vert_select_all(action="SELECT")
                bpy.ops.paint.vertex_color_smooth()
                bpy.ops.object.mode_set(mode="OBJECT")

            if vc_lit and (vc_alpha := mesh.vertex_colors.get("Alpha")):
                n_loops = len(mesh.loops)

                lit_data = np.empty(n_loops * 4)
                alpha_data = np.empty(n_loops * 4)

                vc_lit.data.foreach_get("color", lit_data)
                vc_alpha.data.foreach_get("color", alpha_data)
                lit_data = lit_data.reshape((n_loops, 4))
                lit_data[:, 3] = alpha_data.reshape((n_loops, 4))[:, 0]
                vc_lit.data.foreach_set("color", lit_data.flatten())

        bpy.data.scenes.remove(scene_override)

        if ao_only_world_override:
            bpy.data.worlds.remove(ao_only_world_override)

        for obj in hidden_objects:
            obj.hide_render = False

        bpy.ops.object.select_all(action="DESELECT")
        for obj in old_selected_objects:
            obj.select_set(True)
        context.view_layer.objects.active = old_active_obj

        end = timer()
        print(f"finished bake lighting in {end - start:.2f}s")

        return {"FINISHED"}

def register():
    bpy.utils.register_class(LUTB_OT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_bake_lighting)
    bpy.utils.register_class(LUTB_PT_bake_ao_only)
    bpy.utils.register_class(LUTB_PT_bake_mat_override)

    bpy.types.Scene.lutb_bake_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_bake_selected_only = BoolProperty(name="Selected Only")
    bpy.types.Scene.lutb_bake_smooth_lit = BoolProperty(name="Smooth Vertex Colors", default=True)
    bpy.types.Scene.lutb_bake_samples = IntProperty(name="Samples", default=256, min=1, description=""\
        "Number of samples to render for each vertex")
    bpy.types.Scene.lutb_bake_fast_gi_bounces = IntProperty(name="Fast GI Bounces", default=3, min=0)
    bpy.types.Scene.lutb_bake_glow_strength = FloatProperty(name="Glow Strength Global", default=3.0, min=0, soft_min=0.5, soft_max=5.0)
    bpy.types.Scene.lutb_bake_use_white_ambient = BoolProperty(name="White Ambient", default=True, description=""\
        "Sets ambient light to pure white while baking")
    bpy.types.Scene.lutb_bake_ao_only = BoolProperty(name="AO Only", default=True)
    bpy.types.Scene.lutb_bake_glow_multiplier = FloatProperty(name="Glow Multiplier Global", default=2.0, min=0, soft_min=0.5, soft_max=5.0)
    bpy.types.Scene.lutb_bake_ao_samples = IntProperty(name="AO Samples", default=64, min=1)
    bpy.types.Scene.lutb_bake_use_mat_override = BoolProperty(name="Material Override")
    bpy.types.Scene.lutb_bake_force_to_white = BoolProperty(name="Force to White")
    bpy.types.Scene.lutb_bake_mat_override = PointerProperty(name="Override Material", type=bpy.types.Material)

def unregister():
    del bpy.types.Scene.lutb_bake_use_gpu
    del bpy.types.Scene.lutb_bake_selected_only
    del bpy.types.Scene.lutb_bake_smooth_lit
    del bpy.types.Scene.lutb_bake_samples
    del bpy.types.Scene.lutb_bake_fast_gi_bounces
    del bpy.types.Scene.lutb_bake_glow_strength
    del bpy.types.Scene.lutb_bake_use_white_ambient
    del bpy.types.Scene.lutb_bake_ao_only
    del bpy.types.Scene.lutb_bake_force_to_white
    del bpy.types.Scene.lutb_bake_glow_multiplier
    del bpy.types.Scene.lutb_bake_ao_samples
    del bpy.types.Scene.lutb_bake_use_mat_override
    del bpy.types.Scene.lutb_bake_mat_override

    bpy.utils.unregister_class(LUTB_PT_bake_mat_override)
    bpy.utils.unregister_class(LUTB_PT_bake_ao_only)
    bpy.utils.unregister_class(LUTB_PT_bake_lighting)
    bpy.utils.unregister_class(LUTB_OT_bake_lighting)
