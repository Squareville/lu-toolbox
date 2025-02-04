bl_info = {
	"name": "LU Toolbox",
	"author": "Bobbe",
	"version": (2, 4, 0),
	"blender": (2, 93, 0),
	"location": "3D View -> Sidebar -> LU Toolbox",
	"category": "Import-Export",
	"support": "COMMUNITY",
}

import importlib

module_names = (
    "process_model",
    "icon_render",
    "bake_lighting",
    "remove_hidden_faces",
    "importldd"
)

modules = []
for module_name in module_names:
    if module_name in locals():
        modules.append(importlib.reload(locals()[module_name]))
    else:
        modules.append(importlib.import_module("." + module_name, package=__package__))

def register():
    for module in modules:
        module.register()


def unregister():
    for module in modules:
        module.unregister()
