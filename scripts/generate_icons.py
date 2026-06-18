"""Generate PWA icon files for MeowDB. Run once and commit the outputs."""

from pathlib import Path

from PIL import Image, ImageDraw

BG = (10, 10, 10)
CORAL = (255, 107, 107)

OUT = Path("src/meowdb/static/icons")


def _make_icon(size: int, safe_zone: float = 1.0) -> Image.Image:
    """Draw a simple cat face icon. safe_zone < 1 pads content for maskable icons."""
    img = Image.new("RGBA", (size, size), (*BG, 255))
    draw = ImageDraw.Draw(img)

    # Scaled dimensions within safe zone
    pad = int(size * (1 - safe_zone) / 2)
    inner = size - 2 * pad

    # Circle face
    margin = int(inner * 0.1)
    face_box = (pad + margin, pad + margin, pad + inner - margin, pad + inner - margin)
    draw.ellipse(face_box, fill=CORAL)

    # Ear triangles (top-left and top-right)
    cx = pad + inner // 2
    top = pad + margin
    ear_h = int(inner * 0.22)
    # Left ear
    draw.polygon(
        [
            (cx - int(inner * 0.28), top + ear_h),
            (cx - int(inner * 0.10), top - ear_h // 2),
            (cx - int(inner * 0.05), top + ear_h // 2),
        ],
        fill=CORAL,
    )
    # Right ear
    draw.polygon(
        [
            (cx + int(inner * 0.28), top + ear_h),
            (cx + int(inner * 0.10), top - ear_h // 2),
            (cx + int(inner * 0.05), top + ear_h // 2),
        ],
        fill=CORAL,
    )

    # Eyes
    eye_y = pad + margin + int(inner * 0.35)
    eye_r = max(int(inner * 0.06), 2)
    draw.ellipse(
        (
            cx - int(inner * 0.22) - eye_r,
            eye_y - eye_r,
            cx - int(inner * 0.22) + eye_r,
            eye_y + eye_r,
        ),
        fill=(*BG, 255),
    )
    draw.ellipse(
        (
            cx + int(inner * 0.22) - eye_r,
            eye_y - eye_r,
            cx + int(inner * 0.22) + eye_r,
            eye_y + eye_r,
        ),
        fill=(*BG, 255),
    )

    # Nose
    nose_y = pad + margin + int(inner * 0.54)
    nose_r = max(int(inner * 0.04), 1)
    draw.ellipse(
        (cx - nose_r, nose_y - nose_r, cx + nose_r, nose_y + nose_r),
        fill=(*BG, 255),
    )

    return img


def _favicon_svg() -> str:
    return """\
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" fill="#0a0a0a"/>
  <!-- cat face -->
  <circle cx="16" cy="17" r="11" fill="#ff6b6b"/>
  <!-- ears -->
  <polygon points="7,10 10,4 13,10" fill="#ff6b6b"/>
  <polygon points="19,10 22,4 25,10" fill="#ff6b6b"/>
  <!-- eyes -->
  <circle cx="12" cy="15" r="2" fill="#0a0a0a"/>
  <circle cx="20" cy="15" r="2" fill="#0a0a0a"/>
  <!-- nose -->
  <circle cx="16" cy="20" r="1.2" fill="#0a0a0a"/>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    sizes = [
        ("icon-192.png", 192, 1.0),
        ("icon-512.png", 512, 1.0),
        ("icon-maskable-192.png", 192, 0.8),
        ("icon-maskable-512.png", 512, 0.8),
        ("apple-touch-icon.png", 180, 1.0),
        ("favicon-32.png", 32, 1.0),
    ]

    for filename, size, safe in sizes:
        img = _make_icon(size, safe)
        out_path = OUT / filename
        img.save(out_path, "PNG", optimize=True)
        print(f"  {out_path}")

    svg_path = OUT / "favicon.svg"
    svg_path.write_text(_favicon_svg())
    print(f"  {svg_path}")

    print(f"generate_icons.py: wrote {len(sizes) + 1} icon files to {OUT}/")


if __name__ == "__main__":
    main()
