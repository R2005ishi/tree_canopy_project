"""Drawing helpers: bounding-box overlay, KML outline overlay, crown-size histogram."""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Amber rather than red: it stays legible against green canopy and, unlike a
# red/green pairing, survives the common forms of colour-vision deficiency.
BOX_COLOR = (255, 176, 32)
OUTLINE_COLOR = (94, 234, 212)

# Chart palette, matched to the app's dark theme (see ui/theme.py)
_INK = "#E8EFEA"
_MUTED = "#93A49B"
_ACCENT = "#3FD98C"
_GRID = "#2A3A33"


def _scale_for(image: Image.Image) -> float:
    """Stroke/type scale so overlays stay visible on large orthomosaics."""
    return max(1.0, min(image.width, image.height) / 700.0)


def draw_boxes(image: Image.Image, df, box_color=BOX_COLOR, line_width=None) -> Image.Image:
    """Return a copy of `image` with bounding boxes and a tree-count label drawn on it."""
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img, "RGBA")

    scale = _scale_for(img)
    width = line_width if line_width is not None else max(2, round(2 * scale))

    for _, row in df.iterrows():
        draw.rectangle(
            [row["xmin"], row["ymin"], row["xmax"], row["ymax"]],
            outline=box_color + (235,),
            width=width,
        )

    _draw_count_badge(img, draw, f"Trees detected: {len(df)}", scale)
    return img


def _draw_count_badge(img: Image.Image, draw: ImageDraw.ImageDraw, label: str, scale: float) -> None:
    size = max(14, round(19 * scale))
    font = _load_font(size)

    pad_x, pad_y, margin = round(14 * scale), round(9 * scale), round(14 * scale)
    box = draw.textbbox((0, 0), label, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]

    x0, y0 = margin, margin
    x1, y1 = x0 + tw + pad_x * 2, y0 + th + pad_y * 2

    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=round(10 * scale),
        fill=(7, 11, 13, 205),
        outline=(255, 255, 255, 38),
        width=max(1, round(scale)),
    )
    draw.text((x0 + pad_x - box[0], y0 + pad_y - box[1]), label, fill=_INK, font=font)


def _load_font(size: int):
    for name in ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def draw_polygon_outline(image: Image.Image, pixel_coords, color=OUTLINE_COLOR, line_width=None) -> Image.Image:
    """Draw a closed polygon outline (list of (x, y) pixel coordinates) on the image."""
    img = image.convert("RGB").copy()
    draw = ImageDraw.Draw(img)
    width = line_width if line_width is not None else max(3, round(3 * _scale_for(img)))

    coords = list(pixel_coords)
    if coords and coords[0] != coords[-1]:
        coords.append(coords[0])
    draw.line(coords, fill=color, width=width, joint="curve")
    return img


def crown_size_histogram(areas_m2, bins=30):
    """Return a matplotlib Figure histogramming per-crown area (m2)."""
    fig, ax = plt.subplots(figsize=(5.0, 3.9))
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")

    if len(areas_m2) == 0:
        ax.text(
            0.5, 0.5, "No detections above\nthe current threshold",
            ha="center", va="center", color=_MUTED, fontsize=10,
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    else:
        ax.hist(areas_m2, bins=bins, color=_ACCENT, edgecolor="none", alpha=0.85)
        ax.set_xlabel("Crown bounding-box area (m²)", color=_MUTED, fontsize=11, labelpad=9)
        ax.set_ylabel("Number of trees", color=_MUTED, fontsize=11, labelpad=9)
        ax.tick_params(colors=_MUTED, labelsize=10, length=0)
        ax.grid(axis="y", color=_GRID, linewidth=0.8, alpha=0.9)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(_GRID)

    fig.tight_layout()
    return fig
