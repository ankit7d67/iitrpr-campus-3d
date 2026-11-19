"""Headless Blender script: export the built campus scene to public/models/campus.glb.

Run:  blender -b build/campus.blend -P blender/scripts/bake.py

No textures and no lightmaps are baked: the campus.glb stays a low-poly mesh with four
materials, and lighting/shadows are computed at runtime by React Three Fiber (the app's
SunPanel changes the sun direction, so a baked shadow map would be wrong). Vertex-colour
AO, if added later, must keep the GLB under the material/texture budgets.
"""

import os

import bpy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MODEL = os.path.join(ROOT, "public", "models", "campus.glb")


def export_glb() -> None:
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=MODEL,
        export_format="GLB",
        export_apply=True,
        export_extras=True,
        export_cameras=False,
        export_lights=False,
        export_yup=True,
    )


def main() -> None:
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    tris = sum(len(o.data.loop_triangles) if o.data.loop_triangles else 0 for o in objects)
    if not tris:
        for o in objects:
            o.data.calc_loop_triangles()
        tris = sum(len(o.data.loop_triangles) for o in objects)
    export_glb()
    size = os.path.getsize(MODEL)
    print(f"GLB_OK objects={len(objects)} meshes={len(bpy.data.meshes)} tris={tris} "
          f"materials={len(bpy.data.materials)} size={size} bytes -> public/models/campus.glb")


if __name__ == "__main__":
    main()
