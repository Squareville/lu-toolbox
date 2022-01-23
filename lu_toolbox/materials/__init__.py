from pathlib import Path
import bpy

LUTB_BAKE_MAT = "VertexColor"
LUTB_TRANSPARENT_MAT = "VertexColorTransparent"
LUTB_AO_ONLY_MAT = "VertexColor"
LUTB_OTHER_MATS = ["VertexColorAO"]

MATERIALS_OPAQUE = {
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

MATERIALS_TRANSPARENT = {
    "40": (0.854993, 0.854993, 0.854993, 1.0),
    "41": (0.745405, 0.023153, 0.022174, 1.0),
    "311": (0.42869, 0.64448, 0.061246, 1.0),
    "113": (0.854993, 0.337164, 0.545725, 1.0),
    "111": (0.496933, 0.445201, 0.341914, 1.0),
    "294": (0.846873, 0.341914, 0.53948, 1.0),
    "43": (0.08022, 0.439657, 0.806952, 1.0),
    "42": (0.467784, 0.745404, 0.863157, 1.0),
    "126": (0.332452, 0.296138, 0.571125, 1.0),
    "48": (0.119539, 0.450786, 0.155927, 1.0),
    "182": (0.8388, 0.181164, 0.004391, 1.0),
    "44": (0.947307, 0.863157, 0.141263, 1.0),
    "47": (0.791298, 0.132868, 0.059511, 1.0),
    "49": (0.930111, 0.83077, 0.099899, 1.0),
    "143": (0.623961, 0.760525, 0.930111, 1.0),
    "20": (0.930111, 0.672443, 0.250158, 1.0),
}

MATERIALS_GLOW = {
    "50": (1.0, 1.0, 1.0, 1.0),
    "329": MATERIALS_OPAQUE["329"],
}

CUSTOM_VARIATION = {
    "140": 1.0,
    "194": 1.0,
}

def get_lutb_bake_mat(parent_op=None):
    if not LUTB_BAKE_MAT in bpy.data.materials:
        append_resources(parent_op)
    return bpy.data.materials.get(LUTB_BAKE_MAT)

def get_lutb_transparent_mat(parent_op=None):
    if not LUTB_TRANSPARENT_MAT in bpy.data.materials:
        append_resources(parent_op)
    return bpy.data.materials.get(LUTB_TRANSPARENT_MAT)

def get_lutb_ao_only_mat(parent_op=None):
    if not LUTB_AO_ONLY_MAT in bpy.data.materials:
        append_resources(parent_op)
    return bpy.data.materials.get(LUTB_AO_ONLY_MAT)

def append_resources(parent_op=None):
    blend_file = Path(__file__).parent / "resources.blend"

    for mat_name in (LUTB_BAKE_MAT, LUTB_AO_ONLY_MAT, LUTB_TRANSPARENT_MAT, *LUTB_OTHER_MATS):
        if not mat_name in bpy.data.materials:
            bpy.ops.wm.append(directory=str(blend_file / "Material"), filename=mat_name)

            if not mat_name in bpy.data.materials and parent_op:
                self.report({"WARNING"},
                    f"Failed to append \"{mat_name}\" from \"{blend_file}\"."
                )

def srgb2lin(color):
    result = []
    for srgb in color:
        if srgb <= 0.0404482362771082:
            lin = srgb / 12.92
        else:
            lin = pow(((srgb + 0.055) / 1.055), 2.4)
        result.append(lin)
    return result


def lin2srgb(color):
    result = []
    for lin in color:
        if lin > 0.0031308:
            srgb = 1.055 * (pow(lin, (1.0 / 2.4))) - 0.055
        else:
            srgb = 12.92 * lin
        result.append(srgb)
    return result
