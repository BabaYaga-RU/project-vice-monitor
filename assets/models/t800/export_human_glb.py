"""Export the Human and Skylet variants from T-800.blend1 without saving it.

Run from the t800 folder:
  blender -b T-800.blend1 -P export_human_glb.py
"""
import bpy
import os

ROOT = os.path.dirname(bpy.data.filepath)
HUMAN = bpy.data.collections.get("Human")
if HUMAN is None:
    raise RuntimeError("The Human collection was not found. Use the unmodified T-800.blend1 source.")

def descendants(collection):
    result = set(collection.objects)
    for child in collection.children:
        result.update(descendants(child))
    return result

human_objects = descendants(HUMAN)
armatures = {obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"}
if not armatures:
    raise RuntimeError("No armature found; the exported Human skin needs its rig.")

def select_export_objects():
    bpy.ops.object.select_all(action="DESELECT")
    for obj in human_objects | armatures:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(iter(armatures))

def export(filename):
    select_export_objects()
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(ROOT, filename), export_format="GLB", use_selection=True,
        export_apply=False, export_animations=True, export_skins=True, export_morph=True,
        export_materials="EXPORT", export_image_format="AUTO", export_cameras=False, export_lights=False,
    )
    print("EXPORTED:", os.path.join(ROOT, filename))

def skylet_material(name, base_color, metallic=0.0, roughness=0.5, emission=None):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*base_color, 1)
    shader.inputs["Metallic"].default_value = metallic
    shader.inputs["Roughness"].default_value = roughness
    if emission:
        shader.inputs["Emission Color"].default_value = (*emission, 1)
        shader.inputs["Emission Strength"].default_value = 0.16
    return material

def make_skylet_variant():
    skin = skylet_material("Skylet skin - warm peach", (0.91, 0.43, 0.28), 0.0, 0.46)
    hair = skylet_material("Skylet hair - midnight", (0.006, 0.012, 0.026), 0.18, 0.23, (0.0, 0.11, 0.17))
    leather = skylet_material("Skylet leather - cyan trim", (0.012, 0.02, 0.038), 0.48, 0.28, (0.0, 0.1, 0.14))
    for obj in human_objects:
        if obj.type != "MESH":
            continue
        label = (obj.name + " " + obj.data.name + " " + " ".join(m.name for m in obj.data.materials if m)).lower()
        if any(token in label for token in ("hair", "lash", "brow")):
            replacement = hair
        elif any(token in label for token in ("head", "face", "skin", "arm", "hand")):
            replacement = skin
        else:
            replacement = leather
        obj.data.materials.clear()
        obj.data.materials.append(replacement)

export("T-800-Human.glb")
make_skylet_variant()
export("T-800-Skylet.glb")
