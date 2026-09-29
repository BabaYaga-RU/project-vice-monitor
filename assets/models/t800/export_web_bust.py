"""Build the lightweight runtime model from the source blend without saving it.

Keeps only endoskeleton head, upper torso and shoulder/upper-arm mesh. The
full-body source .blend is never modified. Output: T-800-bust.glb.
"""
import bpy
import os

OUTPUT = os.path.join(os.path.dirname(bpy.data.filepath), "T-800-bust.glb")
KEEP_MESHES = {"T800Endo-Head", "T800Endo-Body", "T800Endo-Arms"}

bpy.ops.object.select_all(action="DESELECT")
armature = None
for obj in bpy.context.scene.objects:
    keep = obj.type == "ARMATURE" or (obj.type == "MESH" and obj.name in KEEP_MESHES)
    obj.hide_viewport = not keep
    obj.hide_render = not keep
    obj.select_set(keep)
    if obj.type == "ARMATURE":
        armature = obj

if armature is None:
    raise RuntimeError("Terminator armature was not found.")
bpy.context.view_layer.objects.active = armature

bpy.ops.export_scene.gltf(
    filepath=OUTPUT,
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
print("EXPORTED:", os.path.abspath(OUTPUT))
