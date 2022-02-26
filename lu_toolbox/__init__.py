bl_info = {
	"name": "LU Toolbox",
	"author": "Bobbe",
	"version": (1, 7, 0),
	"blender": (2, 93, 0),
	"location": "3D View -> Sidebar -> LU Toolbox",
	"category": "Import-Export",
	"support": "COMMUNITY",
}

import bpy
import importlib

module_names = ("process_model", "bake_lighting", "remove_hidden_faces")
modules = []

for module_name in module_names:
	if module_name in locals():
		modules.append(importlib.reload(locals()[module_name]))
	else:
		modules.append(importlib.import_module("." + module_name, package=__package__))

def register():
	for module in modules:
		module.register()
	bpy.utils.register_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
	for module in modules:
		module.unregister()
	bpy.utils.unregister_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
