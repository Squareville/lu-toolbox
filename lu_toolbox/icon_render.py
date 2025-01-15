import bpy, bmesh
from bpy.props import BoolProperty
from mathutils import Vector, Matrix

from math import radians
import numpy as np

from .process_model import LOD_SUFFIXES
from .materials import *

class LUTB_OT_setup_icon_render(bpy.types.Operator):
    """Setup Icon Render for LU Model"""
    bl_idname = "lutb.setup_icon_render"
    bl_label = "Setup Icon Render"

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        # we will only increase the sample count for rendering if we need to (currently only if there are any transparent pieces) - jamie
        increase_samples = False
        
        scene = context.scene

        for collection in scene.collection.children:
            for lod_collection in collection.children[:]:
                if lod_collection.name[-5:] in LOD_SUFFIXES[1:]:
                    collection.children.unlink(lod_collection)

        combine_objects_before = scene.lutb_combine_objects
        scene.lutb_combine_objects = False

        apply_vertex_colors_before = scene.lutb_apply_vertex_colors
        scene.lutb_apply_vertex_colors = True

        correct_colors_before = scene.lutb_correct_colors
        scene.lutb_correct_colors = scene.lutb_ir_correct_colors

        color_variation_before = scene.lutb_color_variation
        scene.lutb_color_variation = scene.lutb_ir_color_variation

        setup_bake_mat_before = scene.lutb_setup_bake_mat
        scene.lutb_setup_bake_mat = False

        remove_hidden_faces_before = scene.lutb_remove_hidden_faces
        scene.lutb_remove_hidden_faces = False

        # hacky way to inject modified color corrections
        if scene.lutb_ir_correct_colors:
            color_corrections = (
                [MATERIALS_OPAQUE, ICON_MATERIALS_OPAQUE, None],
                [MATERIALS_TRANSPARENT, ICON_MATERIALS_TRANSPARENT, None],
                [MATERIALS_GLOW, ICON_MATERIALS_GLOW, None],
                [MATERIALS_METALLIC, ICON_MATERIALS_METALLIC, None],
            )
            for color_correction in color_corrections:
                target, updates, _ = color_correction
                color_correction[2] = target.copy()
                target.update(updates)

        bpy.ops.lutb.process_model()

        if scene.lutb_ir_correct_colors:
            for target, _, original in color_corrections:
                target.update(original)

        scene.lutb_combine_objects = combine_objects_before
        scene.lutb_apply_vertex_colors = apply_vertex_colors_before
        scene.lutb_correct_colors = correct_colors_before
        scene.lutb_color_variation = color_variation_before
        scene.lutb_setup_bake_mat = setup_bake_mat_before
        scene.lutb_remove_hidden_faces = remove_hidden_faces_before

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.tris_convert_to_quads(shape_threshold=radians(50))

        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            bm = bmesh.from_edit_mesh(obj.data)
            bevel_weight = bm.edges.layers.bevel_weight.new("Bevel Weight")
            for edge in bm.edges:
                if len(edge.link_faces) == 1:
                    edge[bevel_weight] = 1.0
            bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)

        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode="OBJECT")

        for obj in context.selected_objects:
            if obj.type != "MESH":
                continue
            if scene.lutb_ir_bevel_edges:
                bevel_mod = obj.modifiers.new("Bevel", "BEVEL")
                bevel_mod.width = 0.02
                bevel_mod.segments = 4
                bevel_mod.limit_method = "WEIGHT"
                bevel_mod.harden_normals = True

            if scene.lutb_ir_subdivide:
                brick_id = obj.name.split("brick_")[-1].split("_")[1]
                if not brick_id in ICON_RENDER_DISABLE_SUBDIV:
                    subdiv_mod = obj.modifiers.new("Subdivision", "SUBSURF")
                    subdiv_mod.levels = 1
                    subdiv_mod.render_levels = 2

            mesh = obj.data
            obj.data.use_auto_smooth = True
            obj.data.auto_smooth_angle = radians(180)

            for i, material in enumerate(mesh.materials):
                name = material.name.rsplit(".", 1)[0]
                if name in MATERIALS_OPAQUE:
                    mesh.materials[i] = get_lutb_ir_opaque_mat(self)
                    # another hack to change a material setting, for the same reasons as the comment below...
                    # anyway, it was deemed that having this enabled was making the plastic look too soft and washed-out in many scenarios - jamie
                    if mesh.materials[i].node_tree:
                        for node in mesh.materials[i].node_tree.nodes:
                            if node.type == "BSDF_PRINCIPLED":
                                node.inputs["Subsurface"].default_value = 0
                elif name in MATERIALS_TRANSPARENT:
                    mesh.materials[i] = get_lutb_ir_transparent_mat(self)
                    # next two lines are a silly hacky fix cause i dont wanna mess with the magical mystery box that is resources.blend, and hollis didnt know why it was broken anyway - jamie
                    mesh.materials[i].blend_method = "HASHED"
                    mesh.materials[i].shadow_method = "HASHED"
                    increase_samples = True
                elif name in MATERIALS_METALLIC:
                    mesh.materials[i] = get_lutb_ir_metal_mat(self)

        ir_scene = get_lutb_ir_scene(self)

        for collection in scene.collection.children[:]:
            for obj in collection.objects:
                if obj.type == "EMPTY" and obj.name.startswith("SceneNode_"):
                    break
            else:
                continue

            lod_collection = collection.children[0]
            obj_bounds = np.empty((len(lod_collection.objects) * 2, 3))
            for i, obj in enumerate(lod_collection.objects):
                obj_bounds[i * 2 + 0] = obj.matrix_world @ Vector(obj.bound_box[0])
                obj_bounds[i * 2 + 1] = obj.matrix_world @ Vector(obj.bound_box[6])

            dimensions = obj_bounds.max(0) - obj_bounds.min(0)
            offset = Matrix.Translation(-(obj_bounds.min(0) + dimensions * 0.5))
            scale = Matrix.Scale(1 / np.abs(dimensions).max(), 4)
            for obj in lod_collection.objects:
                obj.matrix_world = scale @ offset @ obj.matrix_world

            scene.collection.children.unlink(collection)
            ir_scene.collection.children.link(collection)

        context.window.scene = ir_scene

        for area in context.screen.areas:
            if area.type == "VIEW_3D":
                area.spaces[0].shading.type = "RENDERED"

        if increase_samples:
            bpy.context.scene.eevee.taa_render_samples = 1024
        
        return {"FINISHED"}

class LUTB_PT_icon_render(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Icon Render"
    bl_label = "Icon Render"

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.operator(LUTB_OT_setup_icon_render.bl_idname)

        layout.separator(factor=0.5)

        layout.prop(scene, "lutb_ir_correct_colors")
        layout.prop(scene, "lutb_ir_color_variation")
        layout.prop(scene, "lutb_ir_bevel_edges")
        layout.prop(scene, "lutb_ir_subdivide")

def register():
    bpy.utils.register_class(LUTB_OT_setup_icon_render)
    bpy.utils.register_class(LUTB_PT_icon_render)

    bpy.types.Scene.lutb_ir_correct_colors = BoolProperty(name="Correct Colors", default=True,
        description=bpy.types.Scene.lutb_correct_colors.keywords["description"])
    bpy.types.Scene.lutb_ir_color_variation = BoolProperty(name="Apply Color Variation", default=False,
        description=bpy.types.Scene.lutb_use_color_variation.keywords["description"])
    bpy.types.Scene.lutb_ir_bevel_edges = BoolProperty(name="Bevel Edges", default=True)
    bpy.types.Scene.lutb_ir_subdivide = BoolProperty(name="Subdivide", default=True)


def unregister():
    del bpy.types.Scene.lutb_ir_correct_colors
    del bpy.types.Scene.lutb_ir_color_variation
    del bpy.types.Scene.lutb_ir_bevel_edges
    del bpy.types.Scene.lutb_ir_subdivide

    bpy.utils.unregister_class(LUTB_PT_icon_render)
    bpy.utils.unregister_class(LUTB_OT_setup_icon_render)
