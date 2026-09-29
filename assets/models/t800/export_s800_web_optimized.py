"""Export the S-800 bust for the portfolio without authoring data.

The source .blend stays untouched. The generated GLB contains only the three
visible endoskeleton meshes, retains only the runtime armature needed for
eyes/head/jaw, has no animation clips, and downsizes the embedded 2K textures
to 1K WebP for the web scene.
"""
import bpy
import os
import sys

OUTPUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.join(
    os.path.dirname(bpy.data.filepath), "S-800-web.glb"
)
KEEP = {"S800Endo-Head", "S800Endo-Body", "S800Endo-Arms"}

for image in bpy.data.images:
    if image.size[0] > 1024 or image.size[1] > 1024:
        image.scale(min(1024, image.size[0]), min(1024, image.size[1]))

bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.context.scene.objects:
    if obj.type == "ARMATURE" or (obj.type == "MESH" and obj.name in KEEP):
        obj.select_set(True)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
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
    export_image_quality=62,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=8,
    export_draco_position_quantization=13,
    export_draco_normal_quantization=9,
    export_draco_texcoord_quantization=11,
    export_cameras=False,
    export_lights=False,
)
print("S-800 web GLB:", OUTPUT)
