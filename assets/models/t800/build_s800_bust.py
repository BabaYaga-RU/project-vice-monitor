"""Create the editable, leg-free S-800 source and its web GLB.

Run with Blender opened on the original asset.  The original is only read;
the trimmed source and runtime model are written beside this script.
"""
import bpy
import os

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_NAME = "S-800-bust.blend"
MODEL_NAME = "S-800-bust.glb"
KEEP_MESHES = {"T800Endo-Head", "T800Endo-Body", "T800Endo-Arms"}

for obj in list(bpy.data.objects):
    keep = obj.type == "ARMATURE" or (obj.type == "MESH" and obj.name in KEEP_MESHES)
    if not keep:
        bpy.data.objects.remove(obj, do_unlink=True)

# Keep just the runtime collection and remove all empty authoring collections.
for collection in list(bpy.data.collections):
    if collection.name != "Endo" and collection.users == 0:
        bpy.data.collections.remove(collection)

for obj in bpy.context.scene.objects:
    obj.hide_viewport = False
    obj.hide_render = False
    obj.hide_set(False)
    if "T800" in obj.name:
        obj.name = obj.name.replace("T800", "S800")
    if obj.data and "T800" in obj.data.name:
        obj.data.name = obj.data.name.replace("T800", "S800")

for mesh in bpy.data.meshes:
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for material in bpy.data.materials:
    if material.users == 0:
        bpy.data.materials.remove(material)

source_path = os.path.join(OUTPUT_DIR, SOURCE_NAME)
model_path = os.path.join(OUTPUT_DIR, MODEL_NAME)
bpy.ops.wm.save_as_mainfile(filepath=source_path)

bpy.ops.object.select_all(action="DESELECT")
armature = next((obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"), None)
if armature is None:
    raise RuntimeError("S-800 armature was not found.")
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE" or (obj.type == "MESH" and obj.name in {"S800Endo-Head", "S800Endo-Body", "S800Endo-Arms"}):
        obj.select_set(True)
bpy.context.view_layer.objects.active = armature

bpy.ops.export_scene.gltf(
    filepath=model_path,
    export_format="GLB",
    use_selection=True,
    export_apply=False,
    export_animations=False,
    export_skins=True,
    export_morph=True,
    export_materials="EXPORT",
    export_image_format="WEBP",
    export_image_quality=72,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=8,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=10,
    export_draco_texcoord_quantization=12,
    export_draco_color_quantization=10,
    export_draco_generic_quantization=12,
    export_cameras=False,
    export_lights=False,
)
print("S-800 editable source:", source_path)
print("S-800 web model:", model_path)
