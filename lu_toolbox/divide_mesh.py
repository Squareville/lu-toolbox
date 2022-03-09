import bpy, bmesh
import numpy as np

def divide_mesh(context, mesh_obj, max_verts=65536, min_div_rate=0.1):
    def divide_rec(obj):
        mesh = obj.data
        n_verts = len(mesh.vertices)

        if n_verts < max_verts:
            return []

        buffer_co = np.empty(n_verts * 3)
        mesh.vertices.foreach_get("co", buffer_co)
        vecs = buffer_co.reshape((n_verts, 3))
        mean = np.sum(vecs, axis=0) / n_verts

        bound_box = np.array(obj.bound_box)
        target_axis = np.argmax((bound_box[0] - bound_box[6]) ** 2)
        select = vecs[:,target_axis] < mean[target_axis]

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        context.view_layer.objects.active = obj

        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")

        bm = bmesh.from_edit_mesh(mesh)
        for vert, v_select in zip(bm.verts, select):
            vert.select = v_select
        bm.select_mode = {"VERT"}
        bm.select_flush_mode()
        bmesh.update_edit_mesh(mesh)
        bm.free()

        bpy.ops.mesh.select_linked()
        bpy.ops.mesh.separate()
        bpy.ops.object.mode_set(mode="OBJECT")

        new_obj = (set(context.selected_objects) - set((obj,))).pop()

        div_rate = len(new_obj.data.vertices) / n_verts
        div_rate = min(div_rate, 1 - div_rate)

        if div_rate < min_div_rate:
            raise Exception(f"fatal: failed to divide mesh: {div_rate} < {min_div_rate} (div_rate < min_div_rate)")

        return divide_rec(obj) + divide_rec(new_obj) + [new_obj]

    new_objects = divide_rec(mesh_obj)
    return new_objects
