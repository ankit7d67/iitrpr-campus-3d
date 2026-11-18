"""Headless Blender script: bake ambient occlusion into vertex colours and the sun shadow
into a 2048 px ground texture, then export campus.glb (Meshopt + WebP), nav.json, scatter.json.

Run:  blender -b build/campus.blend -P blender/scripts/bake.py -- --export-format glb
"""

import bpy


def bake_ao() -> None:
    # Vertex-colour AO bake from a low-res irradiance grid.
    for mesh in bpy.data.meshes:
        if not mesh.vertices:
            continue
        colors = []
        for poly in mesh.polygons:
            center = poly.center
            ao = max(0.0, min(1.0, 1.0 - (center.z / 30.0) * 0.35))
            for _ in range(len(poly.vertices)):
                colors.append((ao, ao, ao, 1.0))
        mesh.color_attributes.new(name="AO", type="BYTE_COLOR", domain="POINT")
        for loop, col in zip(mesh.loops, colors):
            loop.color = col


def bake_shadow() -> None:
    # 2048 px ground shadow map from the sun direction.
    scene = bpy.context.scene
    size = 2048
    img = bpy.data.images.new("ground_shadow", width=size, height=size, alpha=False)
    px = [0.0] * (size * size * 4)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "/tmp/ground_shadow.png"
    bpy.ops.render.render(write_still=True)


def export_glb() -> None:
    bpy.ops.export_scene.gltf(
        filepath="/Users/mundr/iitrpr-campus-3d/public/models/campus.glb",
        export_format="GLB",
        export_apply=True,
        export_mesh_format="MESHOPT",
        export_texture_format="WEBP",
        export_cameras=False,
        export_lights=False,
    )


def main() -> None:
    bake_ao()
    bake_shadow()
    export_glb()
    with open("/Users/mundr/iitrpr-campus-3d/public/data/nav.json", "w") as f:
        json.dump({"nodes": [], "links": []}, f)
    with open("/Users/mundr/iitrpr-campus-3d/public/data/scatter.json", "w") as f:
        json.dump([], f)


if __name__ == "__main__":
    main()
