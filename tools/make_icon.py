"""Gera o ícone do Praxis (assets/icon.ico) com Pillow.

Ícone flat moderno: quadrado arredondado com gradiente indigo->violeta e um "P"
estilizado com barras de cadência. Exporta múltiplas resoluções num único .ico.

Uso:
    python tools/make_icon.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "icon.ico"

BG_TOP = (99, 60, 255)     # indigo
BG_BOTTOM = (158, 60, 255)  # violeta
FG = (255, 255, 255)

SIZES = [16, 32, 48, 64, 128, 256]
BASE = 256


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def _gradient(size: int) -> Image.Image:
    grad = Image.new("RGB", (size, size), BG_TOP)
    px = grad.load()
    for y in range(size):
        t = y / max(1, size - 1)
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        for x in range(size):
            px[x, y] = (r, g, b)
    return grad


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build_base() -> Image.Image:
    img = Image.new("RGBA", (BASE, BASE), (0, 0, 0, 0))
    grad = _gradient(BASE).convert("RGBA")
    img.paste(grad, (0, 0), _rounded_mask(BASE, radius=56))

    d = ImageDraw.Draw(img)

    # Barras de "cadência" à direita, semitransparentes.
    bar_w = 14
    xs = [150, 178, 206]
    heights = [70, 120, 95]
    for x, h in zip(xs, heights):
        top = (BASE - h) // 2
        d.rounded_rectangle(
            [x, top, x + bar_w, top + h], radius=6, fill=(255, 255, 255, 90)
        )

    # "P" central.
    font = _font(170)
    text = "P"
    box = d.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    d.text(
        ((BASE - tw) / 2 - box[0] - 18, (BASE - th) / 2 - box[1] - 6),
        text, font=font, fill=FG,
    )
    return img


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base = build_base()
    base.save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"Ícone gerado: {OUT}")


if __name__ == "__main__":
    main()
