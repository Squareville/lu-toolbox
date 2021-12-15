import bpy, bmesh
from mathutils import Vector
from bpy.props import IntProperty, FloatProperty, BoolProperty
import math
import numpy as np

class LUTB_OT_remove_hidden_faces(bpy.types.Operator):
    """Remove faces hidden inside the model (using Cycles baking)"""
    bl_idname = "lutb.remove_hidden_faces"
    bl_label = "Remove Hidden Faces"

    autoremove : BoolProperty(default=True)
    tris_to_quads : BoolProperty(default=True)
    pixels_between_verts : IntProperty(min=0, default=5)
    samples : IntProperty(min=0, default=8)
    threshold : FloatProperty(min=0, default=0.01, max=1)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == "MESH" and context.mode == "OBJECT" and context.scene.render.engine == "CYCLES"

    def execute(self, context):
        scene = context.scene
        obj = context.object
        mesh = obj.data

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

        size = math.ceil(math.sqrt(faceCount))
        quadrant_size = 2 + self.pixels_between_verts
        size_pixels = size * quadrant_size

        imageName = "LUTB_OVEREXPOSED_TARGET"
        image = bpy.data.images.get(imageName)
        if image and (image.size[0] != size_pixels or image.size[1] != size_pixels):
            bpy.data.images.remove(image)
            image = None
        if not image:
            image = bpy.data.images.new(imageName, size_pixels, size_pixels, alpha=False, float_buffer=False)

        uvlayer = bm.loops.layers.uv.active
        if not uvlayer:
            uvlayer = bm.loops.layers.uv.new()

        pixelSize = 1 / size_pixels
        pbv_p_1 = self.pixels_between_verts + 1
        offsets = (
            pixelSize * Vector((0 - 0.01 * pbv_p_1, 0 + 0.00 * pbv_p_1)),
            pixelSize * Vector((1 + 1.00 * pbv_p_1, 0 + 0.00 * pbv_p_1)),
            pixelSize * Vector((1 + 1.00 * pbv_p_1, 1 + 1.01 * pbv_p_1)),
            pixelSize * Vector((0 - 0.01 * pbv_p_1, 1 + 1.01 * pbv_p_1)),
        )
        
        bm.faces.ensure_lookup_table()
        for i, face in enumerate(bm.faces):
            target = Vector((i % size, i // size)) * quadrant_size / size_pixels
            for j, loop in enumerate(face.loops):
                loop[uvlayer].uv = target + offsets[j]

        bm.to_mesh(mesh)

        # baking

        originalMaterials = []
        for i, material_slot in enumerate(obj.material_slots):
            originalMaterials.append(material_slot.material)
            obj.material_slots[i].material = getOverexposedMaterial(obj, image)

        originalWorld = scene.world
        scene.world = getOverexposedWorld()

        originalSamples = scene.cycles.samples
        scene.cycles.samples = self.samples

        originalTarget = scene.render.bake.target
        scene.render.bake.target = "IMAGE_TEXTURES"

        passes = ("use_pass_direct", "use_pass_indirect", "use_pass_diffuse")
        originalPasses = []
        for p in passes:
            originalPasses.append(getattr(scene.render.bake, p))
            setattr(scene.render.bake, p, True)

        context.view_layer.update()
        bpy.ops.object.bake(type="DIFFUSE", margin=0, use_clear=True)
        
        for i, material in enumerate(originalMaterials):
            obj.material_slots[i].material = material

        scene.world = originalWorld
        scene.cycles.samples = originalSamples
        scene.render.bake.target = originalTarget

        for p, originalValue in zip(passes, originalPasses):
            setattr(scene.render.bake, p, originalValue)

        bm = bmesh.new(use_operators=False)
        bm.from_mesh(mesh)

        pixels = np.array(image.pixels)

        size_sq = size ** 2
        size_pixels_sq = size_pixels ** 2

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
        sum_per_face = np.reshape(sum_per_face, (1, size_sq))[0][:len(bm.faces)]
        
        pixels_per_quad = quadrant_size ** 2
        pixels_per_tri  = (pixels_per_quad + quadrant_size) / 2

        average_per_face = np.zeros(sum_per_face.shape)
        for i, face in enumerate(bm.faces):
            if len(face.verts) == 4:
                average_per_face[i] = sum_per_face[i] / pixels_per_quad
            else:
                average_per_face[i] = sum_per_face[i] / pixels_per_tri

        average_per_face = average_per_face / 3

        if self.autoremove:
            for face, value in reversed(list(zip(bm.faces, average_per_face))):
                if value < self.threshold:
                    bm.faces.remove(face)

            bm.to_mesh(mesh)
            bm.free()

            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)
            bpy.ops.object.mode_set(mode="OBJECT")
        
        else:
            bpy.ops.object.mode_set(mode="EDIT")
            context.tool_settings.mesh_select_mode = (False, False, True)
            bpy.ops.mesh.select_all(action="DESELECT")
            bpy.ops.object.mode_set(mode="OBJECT")

            for polygon, value in zip(mesh.polygons, average_per_face):
                polygon.select = value < self.threshold
        
        return {"FINISHED"}

def getOverexposedMaterial(obj, image):
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
