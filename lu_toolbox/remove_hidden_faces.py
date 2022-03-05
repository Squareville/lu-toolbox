import bpy, bmesh
from mathutils import Vector
from bpy.props import IntProperty, FloatProperty, BoolProperty
import math
import numpy as np

LUTB_HSR_ID = "LUTB_HSR"

class LUTB_OT_remove_hidden_faces(bpy.types.Operator):
    """Remove hidden interior geometry from the model."""
    bl_idname = "lutb.remove_hidden_faces"
    bl_label = "Remove Hidden Faces"

    autoremove:           BoolProperty(default=True, description=""\
        "Automatically remove hidden polygons. "\
        "Disabling this results in hidden polygons being assigned to the objects Face Maps"
    )
    tris_to_quads:        BoolProperty(default=True, description=""\
        "Convert models triangles to quads for faster, more efficient HSR. "\
        "Quads are then converted back to tris afterwards. "\
        "Disabling this may result in slower HSR processing")
    pixels_between_verts: IntProperty(min=0, default=5, description="")
    samples:              IntProperty(min=0, default=8, description=""\
        "Number of samples to render for HSR")
    threshold:            FloatProperty(min=0, default=0.01, max=1)
    use_ground_plane:     BoolProperty(default=False, description=""\
        "Add a ground plane that contributes occlusion to the model during HSR so that "\
        "the underside of the model gets removed. Before enabling this option, make "\
        "sure your model does not extend below the default ground plane in LDD")

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == "MESH" and context.mode == "OBJECT" and context.scene.render.engine == "CYCLES"

    def execute(self, context):
        scene = context.scene
        target_obj = context.object
        mesh = target_obj.data

        if self.tris_to_quads:
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.tris_convert_to_quads()
            bpy.ops.object.mode_set(mode="OBJECT")

        bm = bmesh.new(use_operators=False)
        bm.from_mesh(mesh)

        faceCount = len(bm.faces)

        for face in bm.faces:
            if len(face.verts) > 4:
                self.report({"ERROR"}, "Mesh needs to consist of tris or quads only!")
                return {"CANCELLED"}

        ground_plane = None
        if self.use_ground_plane:
            ground_plane = self.add_ground_plane(context)

        size = math.ceil(math.sqrt(faceCount))
        quadrant_size = 2 + self.pixels_between_verts
        size_pixels = size * quadrant_size

        image = bpy.data.images.get(LUTB_HSR_ID)
        if image and tuple(image.size) != (size_pixels, size_pixels):
            bpy.data.images.remove(image)
            image = None
        if not image:
            image = bpy.data.images.new(LUTB_HSR_ID, size_pixels, size_pixels)

        bm.faces.ensure_lookup_table()
        uv_layer = self.setup_uv_layer(context, bm, bm.faces, size, size_pixels)
        bm.to_mesh(mesh)
        mesh.uv_layers[uv_layer.name].active = True

        self.bake_to_image(context, image, target_obj, ground_plane)

        bm.loops.layers.uv.remove(bm.loops.layers.uv["LUTB_HSR"])

        hidden_indices = self.get_hidden_faces(image, bm.faces, size, size_pixels, quadrant_size)

        if self.autoremove:
            hidden_faces = [bm.faces[index] for index in hidden_indices]
            for face in reversed(hidden_faces):
                bm.faces.remove(face)

            bm.to_mesh(mesh)

            bpy.ops.object.mode_set(mode="EDIT")
            context.tool_settings.mesh_select_mode = (True, False, False)
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        else:
            bpy.ops.object.mode_set(mode="EDIT")
            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT")

            for index in hidden_indices:
                mesh.polygons[index].select = True

        bm.free()

        if ground_plane:
            bpy.data.objects.remove(ground_plane)

        return {"FINISHED"}

    def add_ground_plane(self, context):
        old_active_obj = context.object

        bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, -50), scale=(1000, 1000, 100))
        bpy.ops.object.transform_apply()
        ground_plane = context.object

        bpy.ops.object.select_all(action="DESELECT")
        old_active_obj.select_set(True)
        context.view_layer.objects.active = old_active_obj

        if not (material := bpy.data.materials.get("LUTB_GROUND_PLANE")):
            material = bpy.data.materials.new("LUTB_GROUND_PLANE")
            material.use_nodes = True
            nodes = material.node_tree.nodes
            nodes.clear()
            node_diffuse = nodes.new("ShaderNodeBsdfDiffuse")
            node_diffuse.inputs["Color"].default_value = (0, 0, 0, 1)
            node_output = nodes.new("ShaderNodeOutputMaterial")
            material.node_tree.links.new(node_diffuse.outputs[0], node_output.inputs[0])
        
        ground_plane.data.materials.append(material)

        return ground_plane

    def setup_uv_layer(self, context, bm, faces, size, size_pixels):
        uvlayer = bm.loops.layers.uv.new(LUTB_HSR_ID)

        size_pixels_inv = 1 / size_pixels
        pbv_p_1 = self.pixels_between_verts + 1
        offsets = (
            size_pixels_inv * Vector((0 - 0.01 * pbv_p_1, 0 + 0.00 * pbv_p_1)),
            size_pixels_inv * Vector((1 + 1.00 * pbv_p_1, 0 + 0.00 * pbv_p_1)),
            size_pixels_inv * Vector((1 + 1.00 * pbv_p_1, 1 + 1.01 * pbv_p_1)),
            size_pixels_inv * Vector((0 - 0.01 * pbv_p_1, 1 + 1.01 * pbv_p_1)),
        )
        
        size_inv = 1 / size
        for i, face in enumerate(faces):
            target = Vector((i % size, i // size)) * size_inv
            for j, loop in enumerate(face.loops):
                loop[uvlayer].uv = target + offsets[j]

        return uvlayer

    def bake_to_image(self, context, image, target_obj, ground_plane):
        scene = context.scene
        scene_override = scene.copy()

        hidden_objects = []
        for obj in list(scene.collection.all_objects):
            if obj not in {target_obj, ground_plane} and not obj.hide_render:
                obj.hide_render = True
                hidden_objects.append(obj)

        originalMaterials = []
        for i, material_slot in enumerate(target_obj.material_slots):
            originalMaterials.append(material_slot.material)
            target_obj.material_slots[i].material = getOverexposedMaterial(image)

        scene_override.world = getOverexposedWorld()
        cycles = scene_override.cycles
        cycles.samples = self.samples
        cycles.use_denoising = False
        cycles.use_fast_gi = False
        cycles.max_bounces = 8
        cycles.diffuse_bounces = 8
        cycles.sample_clamp_direct = 0.0
        cycles.sample_clamp_indirect = 0.0

        bake_settings = scene_override.render.bake
        bake_settings.target = "IMAGE_TEXTURES"
        bake_settings.use_pass_direct = True
        bake_settings.use_pass_indirect = True
        bake_settings.use_pass_diffuse = True

        context_override = context.copy()
        context_override["scene"] = scene_override
        bpy.ops.object.bake(context_override, type="DIFFUSE", margin=0, use_clear=True)
        bpy.data.scenes.remove(scene_override)

        for obj in hidden_objects:
            obj.hide_render = False

        for i, material in enumerate(originalMaterials):
            target_obj.material_slots[i].material = material

    def get_hidden_faces(self, image, faces, size, size_pixels, quadrant_size):
        size_sq = size ** 2
        size_pixels_sq = size_pixels ** 2

        pixels = np.empty(size_pixels_sq * 4, dtype=np.float32)
        image.pixels.foreach_get(pixels)

        sum_per_face = pixels.copy()
        sum_per_face = np.reshape(sum_per_face, (size_pixels_sq, 4))
        sum_per_face = np.delete(sum_per_face, 3, 1)
        sum_per_face = np.reshape(sum_per_face, (size_pixels_sq // quadrant_size, quadrant_size * 3))
        sum_per_face = np.sum(sum_per_face, axis=1)
        sum_per_face = np.reshape(sum_per_face, (size_pixels, size))
        sum_per_face = np.swapaxes(sum_per_face, 0, 1)
        sum_per_face = np.reshape(sum_per_face, (size_sq, quadrant_size))
        sum_per_face = np.sum(sum_per_face, axis=1)
        sum_per_face = np.reshape(sum_per_face, (size, size))
        sum_per_face = np.swapaxes(sum_per_face, 0, 1)
        sum_per_face = np.reshape(sum_per_face, (1, size_sq))[0][:len(faces)]

        pixels_per_quad = quadrant_size ** 2
        pixels_per_tri  = (pixels_per_quad + quadrant_size) / 2
        pixels_per_face = [pixels_per_quad if len(face.verts) == 4 else pixels_per_tri for face in faces]

        average_per_face = sum_per_face / pixels_per_face / 3

        indices = np.where(average_per_face < self.threshold)[0]

        return indices

def getOverexposedMaterial(image):
    name = "LUTB_overexposed"

    material = bpy.data.materials.get(name)
    if not material:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes

        node_texture = nodes.new("ShaderNodeTexImage")
        node_texture.name = "LUTB_TARGET"

    nodes = material.node_tree.nodes
    node_texture = nodes["LUTB_TARGET"]
    node_texture.image = image

    return material

def getOverexposedWorld():
    name = "LUTB_overexposed"

    world = bpy.data.worlds.get(name)
    if not world:
        world = bpy.data.worlds.new(name)
        world.use_nodes = True
        nodes = world.node_tree.nodes

        node_background = nodes["Background"]
        node_background.inputs["Color"].default_value = (1, 1, 1, 1)
        node_background.inputs["Strength"].default_value = 100000

    return world

def register():
    bpy.utils.register_class(LUTB_OT_remove_hidden_faces)
    
def unregister():
    bpy.utils.unregister_class(LUTB_OT_remove_hidden_faces)
