"""Leitura da barra de vida na tela para a regra de auto-poção.

Captura uma região retangular e calcula a fração de pixels cuja cor está
próxima da cor-alvo (a cor da vida cheia). Vida cheia => fração alta;
ao tomar dano, a parte vazia da barra muda de cor e a fração cai.
"""

from __future__ import annotations

from PIL import ImageGrab


def _close(c: tuple[int, int, int], target: list[int], tol: int) -> bool:
    return (
        abs(c[0] - target[0]) <= tol
        and abs(c[1] - target[1]) <= tol
        and abs(c[2] - target[2]) <= tol
    )


def health_fraction(region: list[int], color: list[int], tolerance: int) -> float:
    """Retorna a fração [0..1] de pixels da região próximos da cor da vida.

    Faz subamostragem para ser barata o suficiente para rodar várias vezes
    por segundo sem pesar.
    """
    x1, y1, x2, y2 = region
    if x2 <= x1 or y2 <= y1:
        return 1.0  # região inválida => assume vida cheia (não dispara poção)

    img = ImageGrab.grab(bbox=(x1, y1, x2, y2)).convert("RGB")
    w, h = img.size
    px = img.load()

    step_x = max(1, w // 60)
    step_y = max(1, h // 20)

    total = 0
    hits = 0
    for yy in range(0, h, step_y):
        for xx in range(0, w, step_x):
            total += 1
            if _close(px[xx, yy], color, tolerance):
                hits += 1

    if total == 0:
        return 1.0
    return hits / total


def sample_color(x: int, y: int) -> tuple[int, int, int]:
    """Cor RGB de um único pixel — útil para calibrar a cor-alvo da vida."""
    img = ImageGrab.grab(bbox=(x, y, x + 1, y + 1)).convert("RGB")
    return img.getpixel((0, 0))
