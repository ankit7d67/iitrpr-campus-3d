"""Render PNG previews of the Blender campus scene into build/preview/.

Run:  blender -b build/campus.blend -P blender/scripts/render_preview.py -- --views main
"""

import bpy


def main() -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = "/Users/mundr/iitrpr-campus-3d/build/preview/main.png"
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
