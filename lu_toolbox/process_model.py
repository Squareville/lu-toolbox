import bpy, bmesh
from bpy.props import *
from mathutils import Color, Matrix
from math import radians
import random
import numpy as np
from timeit import default_timer as timer

from .remove_hidden_faces import LUTB_OT_remove_hidden_faces
from .materials import *
from .divide_mesh import divide_mesh

IS_TRANSPARENT = "lu_toolbox_is_transparent"

LOD_SUFFIXES = ("LOD_0", "LOD_1", "LOD_2")

class LUTB_OT_process_model(bpy.types.Operator):
    """Process LU model"""
    bl_idname = "lutb.process_model"
    bl_label = "Process Model"  

    @classmethod
    def poll(cls, context):
        return context.mode == "OBJECT"

    def execute(self, context):
        start = timer()

        scene = context.scene

        scene.render.engine = "CYCLES"
        scene.cycles.device = "GPU" if scene.lutb_process_use_gpu else "CPU"

        self.precombine_bricks(context, scene.collection.children)

        for obj in scene.collection.all_objects:
            if not obj.type == "MESH":
                continue

            mat_names = {material.name.rsplit(".", 1)[0] for material in obj.data.materials}
            if mat_names.issubset(MATERIALS_TRANSPARENT):
                obj[IS_TRANSPARENT] = True

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

        if not scene.lutb_keep_uvs:
            self.clear_uvs(all_objects)

        if scene.lutb_apply_vertex_colors:
            if scene.lutb_correct_colors:
                self.correct_colors(context, all_objects)

            if scene.lutb_use_color_variation:
                self.apply_color_variation(context, all_objects)

            self.apply_vertex_colors(context, all_objects)

        if scene.lutb_setup_bake_mat:
            self.setup_bake_mat(context, all_objects)

        if scene.lutb_remove_hidden_faces:
            for obj in transparent_objects:
                obj.hide_render = True

            self.remove_hidden_faces(context, opaque_objects)

            for obj in transparent_objects:
                obj.hide_render = False

        self.split_objects(context, scene.collection.children)

        if scene.lutb_setup_lod_data:
            self.setup_lod_data(context, scene.collection.children)

        bpy.ops.object.select_all(action="DESELECT")
        for obj in all_objects:
            obj.select_set(True)

        end = timer()
        print(f"finished process model in {end - start:.2f}s")

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

        combined_bricks = {}
        for parent_empty, children in bricks.items():
            bm = bmesh.new()
            materials = {}

            for child in children:
                mesh = child.data
                for old_mat_index, material in enumerate(mesh.materials):
                    mat_name = material.name.rsplit(".", 1)[0]
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

            combined_bricks[combined.name] = combined

        brick_base_mats = {}
        for name, obj in combined_bricks.items():
            if name[-4:-3] == ".":
                base_name = name.rsplit(".", 1)[0]
                if not (base_mats := brick_base_mats.get(base_name)):
                    if not (obj_base := combined_bricks.get(base_name)):
                        continue

                    mats = obj_base.data.materials.values()
                    base_mats = {mat.name.rsplit(".", 1)[0]: mat for mat in mats}
                    brick_base_mats[base_name] = base_mats

                for i, mat in enumerate(obj.data.materials):
                    if (base_mat := base_mats.get(mat.name.rsplit(".", 1)[0])):
                        obj.data.materials[i] = base_mat

        for obj in list(collection.all_objects):
            if obj.type == "EMPTY":
                bpy.data.objects.remove(obj)

    def clear_uvs(self, objects):
        for obj in objects:
            for uv_layer in reversed(obj.data.uv_layers):
                obj.data.uv_layers.remove(uv_layer)

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
                name = material.name.rsplit(".", 1)[0]
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

        for obj in objects:
            is_transparent = obj.get(IS_TRANSPARENT)
            mesh = obj.data
            n_loops = len(mesh.loops)

            if not is_transparent:
                if not (vc_lit := mesh.vertex_colors.get("Lit")):
                    vc_lit = mesh.vertex_colors.new(name="Lit")
                lit_data = np.tile((0.0, 0.0, 0.0, 1.0), n_loops)
                vc_lit.data.foreach_set("color", lit_data)

            if not (vc_col := mesh.vertex_colors.get("Col")):
                vc_col = mesh.vertex_colors.new(name="Col")

            materials = mesh.materials
            n_materials = len(materials)
            if n_materials < 2:
                color = materials[0].diffuse_color if materials else (0.8, 0.8, 0.8, 1.0)
                if is_transparent:
                    color[3] = scene.lutb_transparent_opacity / 100.0
                color_data = np.tile(color, n_loops)
            else:
                colors = np.zeros((n_materials, 4))
                for i, material in enumerate(materials):
                    colors[i] = lin2srgb(material.diffuse_color)

                if is_transparent:
                    colors[:, 3] = scene.lutb_transparent_opacity / 100.0

                color_indices = np.zeros(len(mesh.loops), dtype=int)
                for poly in mesh.polygons:
                    poly_loop_end = poly.loop_start + poly.loop_total
                    color_indices[poly.loop_start:poly_loop_end] = poly.material_index

                color_data = colors[color_indices].flatten()

            vc_col.data.foreach_set("color", color_data)

            if not is_transparent:
                if not (vc_alpha := mesh.vertex_colors.get("Alpha")):
                    vc_alpha = mesh.vertex_colors.new(name="Alpha")
                alpha_data = np.tile((1.0, 1.0, 1.0, 1.0), n_loops)
                vc_alpha.data.foreach_set("color", alpha_data)

                if not (vc_glow := mesh.vertex_colors.get("Glow")):
                    vc_glow = mesh.vertex_colors.new(name="Glow")

                mat_names = [mat.name.rsplit(".", 1)[0] for mat in mesh.materials]
                if set(mat_names) & set(MATERIALS_GLOW):
                    colors = np.zeros((n_materials, 4))
                    for i, (name, material) in enumerate(zip(mat_names, materials)):
                        color = MATERIALS_GLOW.get(name)
                        colors[i] = lin2srgb(color) if color else (0.0, 0.0, 0.0, 1.0)

                    color_indices = np.zeros(len(mesh.loops), dtype=int)
                    for poly in mesh.polygons:
                        poly_loop_end = poly.loop_start + poly.loop_total
                        color_indices[poly.loop_start:poly_loop_end] = poly.material_index

                    glow_data = colors[color_indices].flatten()
                else:
                    glow_data = np.tile((0.0, 0.0, 0.0, 1.0), n_loops)

                vc_glow.data.foreach_set("color", glow_data)

            # no clue why setting .active doesn't work ...
            mesh.vertex_colors.active_index = mesh.vertex_colors.keys().index("Col")

        shading = context.area.spaces[0].shading
        shading.type = "SOLID"
        shading.light = "FLAT"
        shading.color_type = "VERTEX"

    def setup_bake_mat(self, context, objects):
        if not (bake_mat := context.scene.lutb_bake_mat):
            bake_mat = context.scene.lutb_bake_mat = get_lutb_bake_mat(self)
        
        mat_transparent = get_lutb_transparent_mat(self)

        for obj in objects:
            mesh = obj.data
            mesh.materials.clear()
            if obj.get(IS_TRANSPARENT):
                mesh.materials.append(mat_transparent)
            else:
                mesh.materials.append(bake_mat)

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
                use_ground_plane=scene.lutb_use_ground_plane,
            )

    def split_objects(self, context, collections):
        for collection in collections:
            for lod_collection in collection.children:
                for obj in list(lod_collection.objects):
                    if obj.type == "MESH":
                        for new_obj in divide_mesh(context, obj):
                            lod_collection.objects.link(new_obj)

    def setup_lod_data(self, context, collections):
        scene = context.scene

        for collection in collections:
            if not collection.children:
                continue

            scene_node = bpy.data.objects.new(f"SceneNode_{collection.name}", None)
            collection.objects.link(scene_node)

            if scene.lutb_correct_orientation:
                rotation = Matrix.Rotation(radians(90), 4, "X")
                scene_node.matrix_world = rotation @ scene_node.matrix_world

            ni_nodes = {}
            for lod_collection in list(collection.children):
                suffix = lod_collection.name[-5:]
                if not suffix in LOD_SUFFIXES:
                    continue

                for obj in list(lod_collection.all_objects):
                    is_transparent = bool(obj.get(IS_TRANSPARENT))

                    shader_prefix = "S01" if is_transparent else scene.lutb_shader_prefix
                    type_prefix = "Alpha" if is_transparent else "Opaque"
                    obj_name = obj.name.rsplit(".", 1)[0]
                    name = f"{shader_prefix}_{type_prefix}_{obj_name}"[:60]
                    obj.name = name

                    if (node := ni_nodes.get(name)):
                        node_obj, node_lods = node
                    else:
                        node_obj = bpy.data.objects.new(name, None)
                        node_obj["type"] = "NiLODNode"
                        matrix_before = node_obj.matrix_world.copy()
                        node_obj.parent = scene_node
                        node_obj.matrix_world = matrix_before
                        collection.objects.link(node_obj)

                        node_lods = {}
                        node = (node_obj, node_lods)
                        ni_nodes[name] = node

                    if not (lod_obj := node_lods.get(suffix)):
                        lod_obj = bpy.data.objects.new(suffix, None)
                        lod_obj.parent = node_obj
                        collection.objects.link(lod_obj)

                        if suffix == LOD_SUFFIXES[0]:
                            lod_obj["near_extent"] = scene.lutb_lod0
                            lod_obj["far_extent"] = scene.lutb_lod1
                        elif suffix == LOD_SUFFIXES[1]:
                            lod_obj["near_extent"] = scene.lutb_lod1
                            lod_obj["far_extent"] = scene.lutb_lod2
                        elif suffix == LOD_SUFFIXES[2]:
                            lod_obj["near_extent"] = scene.lutb_lod2
                            lod_obj["far_extent"] = scene.lutb_cull

                        node_lods[suffix] = lod_obj

                    obj.parent = lod_obj

class LUToolboxPanel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "LU Toolbox"

class LUTB_PT_process_model(LUToolboxPanel, bpy.types.Panel):
    bl_label = "Process Model"

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.operator("lutb.process_model")

        layout.separator(factor=0.5)

        layout.prop(scene, "lutb_process_use_gpu")
        
        layout.prop(scene, "lutb_combine_objects")
        col = layout.column()
        col.prop(scene, "lutb_combine_transparent")
        col.enabled = scene.lutb_combine_objects

        layout.prop(scene, "lutb_keep_uvs")

class LUTB_PT_apply_vertex_colors(LUToolboxPanel, bpy.types.Panel):
    bl_label = "Apply Vertex Colors"
    bl_parent_id = "LUTB_PT_process_model"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_apply_vertex_colors", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_apply_vertex_colors

        layout.prop(scene, "lutb_correct_colors")

        layout.prop(scene, "lutb_use_color_variation")
        col = layout.column()
        col.prop(scene, "lutb_color_variation")
        col.enabled = scene.lutb_use_color_variation

        layout.prop(scene, "lutb_transparent_opacity")

class LUTB_PT_setup_bake_mat(LUToolboxPanel, bpy.types.Panel):
    bl_label = "Setup Bake Material"
    bl_parent_id = "LUTB_PT_process_model"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_setup_bake_mat", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_setup_bake_mat

        layout.prop(scene, "lutb_bake_mat", text="")

class LUTB_PT_remove_hidden_faces(LUToolboxPanel, bpy.types.Panel):
    bl_label = "Remove Hidden Faces"
    bl_parent_id = "LUTB_PT_process_model"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_remove_hidden_faces", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_remove_hidden_faces

        layout.prop(scene, "lutb_autoremove_hidden_faces")
        layout.prop(scene, "lutb_hidden_surfaces_tris_to_quads")
        layout.prop(scene, "lutb_use_ground_plane")
        layout.prop(scene, "lutb_pixels_between_verts", slider=True)
        layout.prop(scene, "lutb_hidden_surfaces_samples", slider=True)

class LUTB_PT_setup_lod_data(LUToolboxPanel, bpy.types.Panel):
    bl_label = "Setup LOD Data"
    bl_parent_id = "LUTB_PT_process_model"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        self.layout.prop(context.scene, "lutb_setup_lod_data", text="")

    def draw(self, context):
        scene = context.scene

        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False
        layout.active = scene.lutb_setup_lod_data

        layout.prop(scene, "lutb_correct_orientation")
        layout.prop(scene, "lutb_shader_prefix")
        layout.prop(scene, "lutb_lod0")
        layout.prop(scene, "lutb_lod1")
        layout.prop(scene, "lutb_lod2")
        layout.prop(scene, "lutb_cull")

def register():
    bpy.utils.register_class(LUTB_OT_process_model)
    bpy.utils.register_class(LUTB_PT_process_model)
    bpy.utils.register_class(LUTB_PT_apply_vertex_colors)
    bpy.utils.register_class(LUTB_PT_setup_bake_mat)
    bpy.utils.register_class(LUTB_PT_remove_hidden_faces)
    bpy.utils.register_class(LUTB_PT_setup_lod_data)

    bpy.types.Scene.lutb_process_use_gpu = BoolProperty(name="Use GPU", default=True)
    bpy.types.Scene.lutb_combine_objects = BoolProperty(name="Combine Objects", default=True)
    bpy.types.Scene.lutb_combine_transparent = BoolProperty(name="Combine Transparent", default=False)
    bpy.types.Scene.lutb_keep_uvs = BoolProperty(name="Keep UVs", default=False)

    bpy.types.Scene.lutb_correct_colors = BoolProperty(name="Correct Colors", default=True)
    bpy.types.Scene.lutb_use_color_variation = BoolProperty(name="Apply Color Variation", default=True)
    bpy.types.Scene.lutb_color_variation = FloatProperty(name="Color Variation", subtype="PERCENTAGE", min=0.0, soft_max=15.0, max=100.0, default=5.0)
    
    bpy.types.Scene.lutb_transparent_opacity = FloatProperty(name="Transparent Opacity", subtype="PERCENTAGE", min=0.0, max=100.0, default=70.0)
    bpy.types.Scene.lutb_apply_vertex_colors = BoolProperty(name="Apply Vertex Colors", default=True)
    
    bpy.types.Scene.lutb_setup_bake_mat = BoolProperty(name="Setup Bake Material", default=True)
    bpy.types.Scene.lutb_bake_mat = PointerProperty(name="Bake Material", type=bpy.types.Material)
    
    bpy.types.Scene.lutb_remove_hidden_faces = BoolProperty(name="Remove Hidden Faces", default=True,
        description=LUTB_OT_remove_hidden_faces.__doc__)
    bpy.types.Scene.lutb_autoremove_hidden_faces = BoolProperty(name="Autoremove", default=True)
    bpy.types.Scene.lutb_hidden_surfaces_tris_to_quads = BoolProperty(name="Tris to Quads", default=True)
    bpy.types.Scene.lutb_pixels_between_verts = IntProperty(name="Pixels Between Vertices", min=0, default=5, soft_max=15)
    bpy.types.Scene.lutb_hidden_surfaces_samples = IntProperty(name="Samples", min=0, default=8, soft_max=32)
    bpy.types.Scene.lutb_use_ground_plane = BoolProperty(name="Use Ground Plane", default=False,
        description=LUTB_OT_remove_hidden_faces.__annotations__["use_ground_plane"].keywords["description"])

    bpy.types.Scene.lutb_setup_lod_data = BoolProperty(name="Setup LOD Data", default=True)
    bpy.types.Scene.lutb_correct_orientation = BoolProperty(name="Correct Orientation", default=True)
    bpy.types.Scene.lutb_shader_prefix = StringProperty(name="Shader Prefix", default="S01")
    bpy.types.Scene.lutb_lod0 = FloatProperty(name="LOD 0", soft_min=0.0, default=0.0, soft_max=25.0)
    bpy.types.Scene.lutb_lod1 = FloatProperty(name="LOD 1", soft_min=0.0, default=25.0, soft_max=50.0)
    bpy.types.Scene.lutb_lod2 = FloatProperty(name="LOD 2", soft_min=0.0, default=50.0, soft_max=500.0)
    bpy.types.Scene.lutb_cull = FloatProperty(name="Cull", soft_min=1000.0, default=10000.0, soft_max=50000.0)

def unregister():
    del bpy.types.Scene.lutb_process_use_gpu
    del bpy.types.Scene.lutb_combine_objects
    del bpy.types.Scene.lutb_combine_transparent
    del bpy.types.Scene.lutb_keep_uvs
    
    del bpy.types.Scene.lutb_correct_colors
    del bpy.types.Scene.lutb_use_color_variation
    del bpy.types.Scene.lutb_color_variation
    
    del bpy.types.Scene.lutb_transparent_opacity
    del bpy.types.Scene.lutb_apply_vertex_colors
    
    del bpy.types.Scene.lutb_setup_bake_mat
    del bpy.types.Scene.lutb_bake_mat
    
    del bpy.types.Scene.lutb_remove_hidden_faces
    del bpy.types.Scene.lutb_autoremove_hidden_faces
    del bpy.types.Scene.lutb_hidden_surfaces_tris_to_quads
    del bpy.types.Scene.lutb_pixels_between_verts
    del bpy.types.Scene.lutb_hidden_surfaces_samples
    del bpy.types.Scene.lutb_use_ground_plane

    del bpy.types.Scene.lutb_setup_lod_data
    del bpy.types.Scene.lutb_correct_orientation
    del bpy.types.Scene.lutb_shader_prefix
    del bpy.types.Scene.lutb_lod0
    del bpy.types.Scene.lutb_lod1
    del bpy.types.Scene.lutb_lod2
    del bpy.types.Scene.lutb_cull

    bpy.utils.unregister_class(LUTB_PT_setup_lod_data)
    bpy.utils.unregister_class(LUTB_PT_remove_hidden_faces)
    bpy.utils.unregister_class(LUTB_PT_setup_bake_mat)
    bpy.utils.unregister_class(LUTB_PT_apply_vertex_colors)
    bpy.utils.unregister_class(LUTB_PT_process_model)
    bpy.utils.unregister_class(LUTB_OT_process_model)
