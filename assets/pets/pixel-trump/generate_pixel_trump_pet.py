#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parent
CELL_W = 192
CELL_H = 208
COLS = 8
ROWS = 9
ROW_SPECS = [
    ("idle", 6),
    ("running-right", 8),
    ("running-left", 8),
    ("waving", 4),
    ("jumping", 5),
    ("failed", 8),
    ("waiting", 6),
    ("running", 6),
    ("review", 6),
]


COLORS = {
    "outline": (29, 28, 36, 255),
    "skin": (239, 178, 126, 255),
    "skin_dark": (200, 125, 84, 255),
    "hair": (245, 204, 60, 255),
    "hair_dark": (190, 134, 31, 255),
    "suit": (17, 43, 83, 255),
    "suit_light": (35, 75, 133, 255),
    "shirt": (242, 244, 250, 255),
    "tie": (190, 30, 45, 255),
    "shoe": (18, 18, 24, 255),
    "mouth": (120, 42, 36, 255),
    "blue": (64, 120, 205, 255),
    "sad": (105, 150, 230, 255),
}


def rect(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: str) -> None:
    draw.rectangle((x, y, x + w - 1, y + h - 1), fill=COLORS[color])


def block(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: str, scale: int = 4) -> None:
    rect(draw, x * scale, y * scale, w * scale, h * scale, color)


def draw_pet(
    cell: Image.Image,
    *,
    pose: str,
    phase: int,
    total: int,
    direction: int = 1,
    y_offset: int = 0,
) -> None:
    draw = ImageDraw.Draw(cell)
    s = 4
    cx = CELL_W // 2
    base_x = cx - 24 * s
    base_y = 42 + y_offset

    bob = 0
    if pose == "idle":
        bob = [0, -1, -2, -1, 0, 1][phase % 6] * 2
    elif pose in {"running-right", "running-left"}:
        bob = [-3, -1, 1, 3, 1, -1, -3, -1][phase % 8]
    elif pose == "waving":
        bob = [-1, -2, -1, 0][phase % 4]
    elif pose == "jumping":
        bob = [8, -4, -18, -6, 8][phase % 5]
    elif pose == "failed":
        bob = [2, 4, 6, 7, 6, 5, 4, 3][phase % 8]
    elif pose == "waiting":
        bob = [0, -1, -2, -1, 0, 1][phase % 6]
    elif pose == "running":
        bob = [-1, -2, -1, 0, -1, -2][phase % 6]
    elif pose == "review":
        bob = [0, 0, -1, -1, 0, 1][phase % 6]

    x = base_x
    y = base_y + bob
    if direction < 0:
        x += 4 * s

    stride = phase % 2
    leg_a = -2 if stride == 0 else 2
    leg_b = 2 if stride == 0 else -2
    if pose not in {"running-right", "running-left"}:
        leg_a = leg_b = 0
    if pose == "jumping":
        leg_a = -2
        leg_b = 2
    if pose == "failed":
        leg_a = 2
        leg_b = -1

    # Shoes and legs.
    block(draw, x // s + 14 + leg_a * direction, y // s + 34, 8, 4, "shoe")
    block(draw, x // s + 29 + leg_b * direction, y // s + 34, 8, 4, "shoe")
    block(draw, x // s + 17 + leg_a * direction, y // s + 26, 5, 9, "suit")
    block(draw, x // s + 29 + leg_b * direction, y // s + 26, 5, 9, "suit")

    # Body outline and suit.
    block(draw, x // s + 11, y // s + 14, 30, 20, "outline")
    block(draw, x // s + 13, y // s + 15, 26, 18, "suit")
    block(draw, x // s + 21, y // s + 15, 8, 17, "shirt")
    block(draw, x // s + 24, y // s + 17, 3, 13, "tie")
    block(draw, x // s + 14, y // s + 16, 6, 4, "suit_light")
    block(draw, x // s + 32, y // s + 16, 5, 4, "suit_light")

    # Arms.
    left_arm_y = y // s + 17
    right_arm_y = y // s + 17
    if pose == "waving":
        right_arm_y = y // s + [6, 4, 7, 10][phase % 4]
    elif pose == "waiting":
        left_arm_y = y // s + 13
        right_arm_y = y // s + 13
    elif pose == "review":
        right_arm_y = y // s + 12
    elif pose in {"running-right", "running-left"}:
        left_arm_y += 2 if stride else -2
        right_arm_y += -2 if stride else 2
    elif pose == "failed":
        left_arm_y += 7
        right_arm_y += 8
    block(draw, x // s + 7, left_arm_y, 6, 14, "outline")
    block(draw, x // s + 8, left_arm_y + 1, 4, 12, "suit")
    block(draw, x // s + 39, right_arm_y, 6, 14, "outline")
    block(draw, x // s + 40, right_arm_y + 1, 4, 12, "suit")
    block(draw, x // s + 7, left_arm_y + 12, 5, 4, "skin")
    block(draw, x // s + 40, right_arm_y + 12, 5, 4, "skin")

    # Head outline, face, ears.
    block(draw, x // s + 14, y // s - 5, 25, 20, "outline")
    block(draw, x // s + 16, y // s - 3, 21, 17, "skin")
    block(draw, x // s + 12, y // s + 2, 4, 7, "skin_dark")
    block(draw, x // s + 37, y // s + 2, 4, 7, "skin_dark")

    # Hair cap and swept front.
    block(draw, x // s + 13, y // s - 8, 25, 6, "outline")
    block(draw, x // s + 15, y // s - 9, 22, 5, "hair")
    block(draw, x // s + 17, y // s - 11, 17, 4, "hair")
    block(draw, x // s + 24, y // s - 13, 12, 4, "hair")
    block(draw, x // s + 15, y // s - 4, 7, 3, "hair_dark")
    block(draw, x // s + 31, y // s - 5, 6, 3, "hair_dark")

    # Face.
    if pose == "failed":
        block(draw, x // s + 21, y // s + 3, 2, 2, "outline")
        block(draw, x // s + 30, y // s + 3, 2, 2, "outline")
        block(draw, x // s + 24, y // s + 10, 6, 2, "mouth")
        block(draw, x // s + 19, y // s + 6, 2, 4, "sad")
        block(draw, x // s + 32, y // s + 6, 2, 4, "sad")
    elif pose == "review":
        block(draw, x // s + 20, y // s + 4, 4, 2, "outline")
        block(draw, x // s + 29, y // s + 4, 4, 2, "outline")
        block(draw, x // s + 25, y // s + 10, 5, 1, "mouth")
    else:
        block(draw, x // s + 21, y // s + 4, 3, 2, "outline")
        block(draw, x // s + 30, y // s + 4, 3, 2, "outline")
        block(draw, x // s + 24, y // s + 10, 7, 2, "mouth")
        block(draw, x // s + 25, y // s + 9, 5, 1, "skin_dark")

    if pose == "running":
        # Attached thinking/working cue: small blue folder-like rectangle held close.
        block(draw, x // s + 42, y // s + 17, 5, 7, "blue")


def make_frame(state: str, phase: int, count: int) -> Image.Image:
    cell = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    direction = -1 if state == "running-left" else 1
    y_offset = 0
    draw_pet(cell, pose=state, phase=phase, total=count, direction=direction, y_offset=y_offset)
    if state == "running-left":
        cell = cell.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return cell


def main() -> None:
    atlas = Image.new("RGBA", (CELL_W * COLS, CELL_H * ROWS), (0, 0, 0, 0))
    frames_root = ROOT / "frames"
    frames_root.mkdir(parents=True, exist_ok=True)

    for row, (state, count) in enumerate(ROW_SPECS):
        state_dir = frames_root / state
        state_dir.mkdir(parents=True, exist_ok=True)
        for col in range(count):
            frame = make_frame(state, col, count)
            frame.save(state_dir / f"{col:02d}.png")
            atlas.alpha_composite(frame, (col * CELL_W, row * CELL_H))

    out_png = ROOT / "spritesheet.png"
    out_webp = ROOT / "spritesheet.webp"
    atlas.save(out_png)
    atlas.save(out_webp, format="WEBP", lossless=True, quality=100, method=6, exact=True)

    pet = {
        "id": "pixel-trump",
        "displayName": "Pixel Trump",
        "description": "A compact pixel-art political-character pet with blond hair, navy suit, and red tie.",
        "spritesheetPath": "spritesheet.webp",
    }
    (ROOT / "pet.json").write_text(json.dumps(pet, indent=2) + "\n", encoding="utf-8")

    codex_pet_dir = Path.home() / ".codex" / "pets" / "pixel-trump"
    codex_pet_dir.mkdir(parents=True, exist_ok=True)
    out_webp.replace(codex_pet_dir / "spritesheet.webp")
    (codex_pet_dir / "pet.json").write_text(json.dumps(pet, indent=2) + "\n", encoding="utf-8")
    atlas.save(out_webp, format="WEBP", lossless=True, quality=100, method=6, exact=True)
    print(f"wrote {out_png}")
    print(f"wrote {out_webp}")
    print(f"installed {codex_pet_dir / 'pet.json'}")


if __name__ == "__main__":
    main()
