from pathlib import Path
import bpy

from .color_conversions import *

LUTB_BAKE_MAT = "VertexColor"
LUTB_TRANSPARENT_MAT = "VertexColorTransparent"
LUTB_FORCE_WHITE_MAT = "ForceWhite"
LUTB_OTHER_MATS = ["VertexColorAO"]
LUTB_BAKE_MATS = (LUTB_BAKE_MAT, LUTB_TRANSPARENT_MAT, LUTB_FORCE_WHITE_MAT, *LUTB_OTHER_MATS)

LUTB_IR_OPAQUE_MAT = "ItemRender_Opaque"
LUTB_IR_TRANSPARENT_MAT = "ItemRender_Transparent"
LUTB_IR_METAL_MAT = "ItemRender_Metal"
LUTB_IR_MATS = (LUTB_IR_OPAQUE_MAT, LUTB_IR_TRANSPARENT_MAT, LUTB_IR_METAL_MAT)

LUTB_IR_SCENE = "ItemRender"

# Solid/Opaque
MATERIALS_OPAQUE = {
    "1"     : (0.904661,    0.904661,   0.904661,   1.0),
    "5"     : (0.693872,    0.491021,   0.194618,   1.0),
    "18"    : (0.672443,    0.168269,   0.051269,   1.0),
    "21"    : (0.730461,    0.0,        0.004025,   1.0),
    "23"    : (0.0,         0.095307,   0.391572,   1.0),
    "24"    : (0.991102,    0.552011,   0.0,        1.0),
    "26"    : (0.006,       0.006,      0.006,      1.0),
    "28"    : (0.0,         0.198069,   0.021219,   1.0),
    "37"    : (0.0,         0.304987,   0.017642,   1.0),
    "38"    : (0.391572,    0.046665,   0.007499,   1.0),
    "50"    : (0.7399,      0.7399,     0.7399,     1.0),
    "102"   : (0.06301,     0.262251,   0.564712,   1.0),
    "106"   : (0.799103,    0.124772,   0.009134,   1.0),
    "107"   : (0.002732,    0.462077,   0.462077,   1.0),
    "119"   : (0.296138,    0.47932,    0.003035,   1.0),
    "120"   : (0.672444,    0.768151,   0.262251,   1.0),
    "124"   : (0.332452,    0.0,        0.147027,   1.0),
    "135"   : (0.111932,    0.174647,   0.262251,   1.0),
    "138"   : (0.262251,    0.177888,   0.084376,   1.0),
    "140"   : (0.0,         0.0185,     0.052861,   1.0),
    "141"   : (0.0,         0.03434,    0.008023,   1.0),
    "151"   : (0.114435,    0.223228,   0.130137,   1.0),
    "154"   : (0.215861,    0.002428,   0.01096,    1.0),
    "191"   : (0.887923,    0.318547,   0.0,        1.0),
    "192"   : (0.104617,    0.011612,   0.003677,   1.0),
    "194"   : (0.332452,    0.283149,   0.283149,   1.0),
    "199"   : (0.072272,    0.082283,   0.093059,   1.0),
    "208"   : (0.768151,    0.768151,   0.693872,   1.0),
    "212"   : (0.242281,    0.520996,   0.83077,    1.0),
    "221"   : (0.730461,    0.038204,   0.258183,   1.0),
    "222"   : (0.846873,    0.341914,   0.53948,    1.0),
    "226"   : (1.0,         0.768151,   0.141263,   1.0),
    "268"   : (0.066626,    0.011612,   0.341914,   1.0),
    "283"   : (0.913099,    0.533276,   0.250158,   1.0),
    "294"   : (0.991102,    0.973445,   0.665388,   1.0),
    "308"   : (0.03434,     0.015209,   0.0,        1.0),
    "329"   : (1.0,         1.0,        1.0,        1.0),
    "330"   : (0.184475,    0.184475,   0.076185,   1.0),
    "9013"  : (1.0,         0.009721,   0.020289,   1.0),
    "9014"  : (0.799103,    0.088655,   0.0,        1.0),
    "9015"  : (1.0,         0.630757,   0.033105,   1.0),
    "9016"  : (0.012983,    1.0,        0.090842,   1.0),
    "9017"  : (0.059511,    0.768152,   0.913099,   1.0),
    "9018"  : (0.0,         0.226966,   1.0,        1.0),
    "9019"  : (0.40724,     0.012983,   1.0,        1.0),
    "9020"  : (0.686686,    0.000303,   1.0,        1.0),
}

# Duplicate Solid/Opaque
MATERIALS_OPAQUE["0"]   = MATERIALS_OPAQUE["26"]
MATERIALS_OPAQUE["2"]   = MATERIALS_OPAQUE["194"]
MATERIALS_OPAQUE["3"]   = MATERIALS_OPAQUE["5"]
MATERIALS_OPAQUE["4"]   = MATERIALS_OPAQUE["106"]
MATERIALS_OPAQUE["6"]   = MATERIALS_OPAQUE["119"]
MATERIALS_OPAQUE["9"]   = MATERIALS_OPAQUE["222"]
MATERIALS_OPAQUE["11"]  = MATERIALS_OPAQUE["212"]
MATERIALS_OPAQUE["12"]  = MATERIALS_OPAQUE["106"]
MATERIALS_OPAQUE["13"]  = MATERIALS_OPAQUE["191"]
MATERIALS_OPAQUE["19"]  = MATERIALS_OPAQUE["191"]
MATERIALS_OPAQUE["22"]  = MATERIALS_OPAQUE["221"]
MATERIALS_OPAQUE["25"]  = MATERIALS_OPAQUE["192"]
MATERIALS_OPAQUE["27"]  = MATERIALS_OPAQUE["199"]
MATERIALS_OPAQUE["29"]  = MATERIALS_OPAQUE["151"]
MATERIALS_OPAQUE["36"]  = MATERIALS_OPAQUE["283"]
MATERIALS_OPAQUE["39"]  = MATERIALS_OPAQUE["194"]
MATERIALS_OPAQUE["45"]  = MATERIALS_OPAQUE["212"]
MATERIALS_OPAQUE["100"] = MATERIALS_OPAQUE["283"]
MATERIALS_OPAQUE["101"] = MATERIALS_OPAQUE["106"]
MATERIALS_OPAQUE["103"] = MATERIALS_OPAQUE["194"]
MATERIALS_OPAQUE["104"] = MATERIALS_OPAQUE["268"]
MATERIALS_OPAQUE["105"] = MATERIALS_OPAQUE["191"]
MATERIALS_OPAQUE["110"] = MATERIALS_OPAQUE["23"]
MATERIALS_OPAQUE["112"] = MATERIALS_OPAQUE["23"]
MATERIALS_OPAQUE["115"] = MATERIALS_OPAQUE["119"]
MATERIALS_OPAQUE["116"] = MATERIALS_OPAQUE["107"]
MATERIALS_OPAQUE["118"] = MATERIALS_OPAQUE["212"]
MATERIALS_OPAQUE["326"] = MATERIALS_OPAQUE["120"]
MATERIALS_OPAQUE["125"] = MATERIALS_OPAQUE["283"]
MATERIALS_OPAQUE["128"] = MATERIALS_OPAQUE["38"]
MATERIALS_OPAQUE["133"] = MATERIALS_OPAQUE["106"]
MATERIALS_OPAQUE["134"] = MATERIALS_OPAQUE["119"]
MATERIALS_OPAQUE["136"] = MATERIALS_OPAQUE["135"]
MATERIALS_OPAQUE["153"] = MATERIALS_OPAQUE["138"]
MATERIALS_OPAQUE["180"] = MATERIALS_OPAQUE["191"]
MATERIALS_OPAQUE["195"] = MATERIALS_OPAQUE["23"]
MATERIALS_OPAQUE["196"] = MATERIALS_OPAQUE["23"]
MATERIALS_OPAQUE["198"] = MATERIALS_OPAQUE["124"]
MATERIALS_OPAQUE["216"] = MATERIALS_OPAQUE["154"]
MATERIALS_OPAQUE["217"] = MATERIALS_OPAQUE["138"]
MATERIALS_OPAQUE["218"] = MATERIALS_OPAQUE["124"]
MATERIALS_OPAQUE["219"] = MATERIALS_OPAQUE["268"]
MATERIALS_OPAQUE["223"] = MATERIALS_OPAQUE["222"]
MATERIALS_OPAQUE["232"] = MATERIALS_OPAQUE["212"]
MATERIALS_OPAQUE["233"] = MATERIALS_OPAQUE["37"]
MATERIALS_OPAQUE["295"] = MATERIALS_OPAQUE["222"]
MATERIALS_OPAQUE["312"] = MATERIALS_OPAQUE["138"]
MATERIALS_OPAQUE["321"] = MATERIALS_OPAQUE["102"]
MATERIALS_OPAQUE["322"] = MATERIALS_OPAQUE["212"]
MATERIALS_OPAQUE["323"] = MATERIALS_OPAQUE["208"]
MATERIALS_OPAQUE["324"] = MATERIALS_OPAQUE["124"]
MATERIALS_OPAQUE["325"] = MATERIALS_OPAQUE["222"]

# Transparent
MATERIALS_TRANSPARENT = {
    "20"    : (0.930111,    0.672443,   0.250158,   1.0),
    "40"    : (0.854993,    0.854993,   0.854993,   1.0),
    "41"    : (0.745405,    0.023153,   0.022174,   1.0),
    "42"    : (0.467784,    0.745404,   0.863157,   1.0),
    "43"    : (0.08022,     0.439657,   0.806952,   1.0),
    "44"    : (0.947307,    0.863157,   0.141263,   1.0),
    "47"    : (0.791298,    0.132868,   0.059511,   1.0),
    "48"    : (0.119539,    0.450786,   0.155927,   1.0),
    "49"    : (0.930111,    0.83077,    0.099899,   1.0),
    "111"   : (0.496933,    0.445201,   0.341914,   1.0),
    "113"   : (0.854993,    0.337164,   0.545725,   1.0),
    "126"   : (0.332452,    0.296138,   0.571125,   1.0),
    "143"   : (0.623961,    0.760525,   0.930111,   1.0),
    "182"   : (0.8388,      0.181164,   0.004391,   1.0),
    "311"   : (0.42869,     0.64448,    0.061246,   1.0),
}

# Duplicate Transparent
MATERIALS_TRANSPARENT["157"] = MATERIALS_TRANSPARENT["44"]
MATERIALS_TRANSPARENT["230"] = MATERIALS_TRANSPARENT["113"]
MATERIALS_TRANSPARENT["231"] = MATERIALS_TRANSPARENT["182"]
MATERIALS_TRANSPARENT["234"] = MATERIALS_TRANSPARENT["44"]
MATERIALS_TRANSPARENT["284"] = MATERIALS_TRANSPARENT["126"]
MATERIALS_TRANSPARENT["285"] = MATERIALS_TRANSPARENT["111"]
MATERIALS_TRANSPARENT["293"] = MATERIALS_TRANSPARENT["43"]

# Glow
MATERIALS_GLOW = {
    "50"    : (0.401978, 0.401978, 0.401978, 1.0),
    "329"   : MATERIALS_OPAQUE["329"],
    "294"   : MATERIALS_OPAQUE["294"],
    "9013"  : MATERIALS_OPAQUE["9013"],
    "9014"  : MATERIALS_OPAQUE["9014"],
    "9015"  : MATERIALS_OPAQUE["9015"],
    "9016"  : MATERIALS_OPAQUE["9016"],
    "9017"  : MATERIALS_OPAQUE["9017"],
    "9018"  : MATERIALS_OPAQUE["9018"],
    "9019"  : MATERIALS_OPAQUE["9019"],
    "9020"  : MATERIALS_OPAQUE["9020"],
}

# Duplicate Glow
MATERIALS_GLOW["9000"] = MATERIALS_GLOW["9020"]
MATERIALS_GLOW["9002"] = MATERIALS_GLOW["9016"]
MATERIALS_GLOW["9004"] = MATERIALS_GLOW["9018"]
MATERIALS_GLOW["9008"] = MATERIALS_GLOW["9013"]
MATERIALS_GLOW["9009"] = MATERIALS_GLOW["9014"]
MATERIALS_GLOW["9010"] = MATERIALS_GLOW["9016"]
MATERIALS_GLOW["9011"] = MATERIALS_GLOW["9017"]
MATERIALS_GLOW["9012"] = MATERIALS_GLOW["9019"]
MATERIALS_GLOW["9021"] = MATERIALS_GLOW["329"]
MATERIALS_GLOW["9022"] = MATERIALS_GLOW["50"]
MATERIALS_GLOW["9023"] = MATERIALS_GLOW["9013"]
MATERIALS_GLOW["9024"] = MATERIALS_GLOW["9014"]
MATERIALS_GLOW["9025"] = MATERIALS_GLOW["9016"]
MATERIALS_GLOW["9026"] = MATERIALS_GLOW["9018"]
MATERIALS_GLOW["9027"] = MATERIALS_GLOW["329"]

# Metallic
MATERIALS_METALLIC = {
    ("131", "150", "179", "298", "315")  : (0.262251, 0.296138, 0.296138, 1.0),
    ("139", "187", "300")                : (0.174648, 0.066626, 0.029557, 1.0),
    "148"                                : (0.06301,  0.051269, 0.043735, 1.0),
    "149"                                : (0.006,    0.006,    0.006,    1.0),
    "184"                                : (0.238095, 0.00907,  0.00907,  1.0),
    ("186", "200")                       : (0.081104, 0.252379, 0.045668, 1.0),
    ("145", "185")                       : (0.104617, 0.177888, 0.278894, 1.0),
    ("309", "183")                       : (0.617207, 0.617207, 0.617207, 1.0),
    ("297", "147", "189")                : (0.401978, 0.212231, 0.027321, 1.0),
    ("310", "127", )                     : (0.737911, 0.533276, 0.181164, 1.0),
}

CUSTOM_VARIATION = {
    "1"     : 1.3,
    "21"    : 1.4,
    "23"    : 1.25,
    "24"    : 1.5,
    "26"    : 0.4,
    "28"    : 0.8,
    "37"    : 0.8,
    "135"   : 0.85,
    "141"   : 0.7,
    "199"   : 0.7,
    "192"   : 0.75,
    "212"   : 1.25,
    "222"   : 1.05,
    "226"   : 1.75,
    "283"   : 1.15,
    "308"   : 0.85,
    "323"   : 1.4,
    "326"   : 1.75,
}

ICON_MATERIALS_OPAQUE = {
    "1"     : srgb2lin((0.7,    0.7,   0.7,   1.0)),
    "26"    : srgb2lin((0.01,    0.01,   0.01,   1.0)),    
}

ICON_MATERIALS_TRANSPARENT = {
    
}

ICON_MATERIALS_GLOW = {
    
}

ICON_MATERIALS_METALLIC = {
    
}

ICON_RENDER_DISABLE_SUBDIV = {
    
}

dicts = (
    MATERIALS_OPAQUE, MATERIALS_TRANSPARENT, MATERIALS_GLOW, MATERIALS_METALLIC,
    ICON_MATERIALS_OPAQUE, ICON_MATERIALS_TRANSPARENT, ICON_MATERIALS_GLOW,
    ICON_MATERIALS_METALLIC, CUSTOM_VARIATION,
)
for dictionary in dicts:
    for keys, value in list(dictionary.items()):
        if not type(keys) == str:
            dictionary.pop(keys)
            for key in keys:
                dictionary[key] = value

def get_lutb_bake_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_BAKE_MAT)

def get_lutb_transparent_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_TRANSPARENT_MAT)

def get_lutb_force_white_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_FORCE_WHITE_MAT)

def get_lutb_ir_opaque_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_IR_OPAQUE_MAT)

def get_lutb_ir_transparent_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_IR_TRANSPARENT_MAT)

def get_lutb_ir_metal_mat(parent_op=None):
    append_resources(parent_op)
    return bpy.data.materials.get(LUTB_IR_METAL_MAT)

def get_lutb_ir_scene(parent_op=None, copy=True):
    append_resources(parent_op)
    return bpy.data.scenes.get(LUTB_IR_SCENE).copy()

def append_resources(parent_op=None):
    blend_file = Path(__file__).parent / "resources.blend"

    for mat_name in (*LUTB_BAKE_MATS, *LUTB_IR_MATS):
        if not mat_name in bpy.data.materials:
            bpy.ops.wm.append(directory=str(blend_file / "Material"), filename=mat_name)
            if not mat_name in bpy.data.materials and parent_op:
                parent_op.report({"WARNING"},
                    f"Failed to append \"{mat_name}\" from \"{blend_file}\"."
                )

    scene_name = LUTB_IR_SCENE
    if not scene_name in bpy.data.scenes:
        bpy.ops.wm.append(directory=str(blend_file / "Scene"), filename=scene_name)
        if not scene_name in bpy.data.scenes and parent_op:
                parent_op.report({"WARNING"},
                    f"Failed to append \"{scene_name}\" from \"{blend_file}\"."
                )
