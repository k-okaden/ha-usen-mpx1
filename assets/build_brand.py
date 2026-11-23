"""Render assets/icon.svg to custom_components/usen_mpx1/brand/*.png.

    pip install cairosvg pillow
    python assets/build_brand.py
"""

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SVG = (ROOT / "assets" / "icon.svg").read_text(encoding="utf-8")
OUT = ROOT / "custom_components" / "usen_mpx1" / "brand"

# The dark variant lifts the body so it does not disappear on a dark background.
DARK = {"#1f2937": "#334155", "#111827": "#475569", "#4b5563": "#64748b"}


def render(svg: str, size: int) -> Image.Image:
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=size, output_height=size)
    image = Image.open(BytesIO(png)).convert("RGBA")
    # Trim to the artwork and re-center it on a square canvas.
    box = image.getbbox()
    art = image.crop(box)
    side = max(art.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(art, ((side - art.width) // 2, (side - art.height) // 2))
    return canvas.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    dark_svg = SVG
    for light, dark in DARK.items():
        dark_svg = dark_svg.replace(light, dark)
    for prefix, svg in (("", SVG), ("dark_", dark_svg)):
        for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
            render(svg, size * 2).resize((size, size), Image.LANCZOS).save(
                OUT / f"{prefix}{name}", optimize=True
            )
            print(OUT / f"{prefix}{name}")


if __name__ == "__main__":
    main()
