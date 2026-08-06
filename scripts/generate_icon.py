"""Generate the AIMux application icon for Windows and macOS packages."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ICON_DIR = ROOT / "assets" / "icons"


def generate_icon(size: int = 1024) -> Image.Image:
    """绘制无文字的 AIMux 图标，保证小尺寸下仍能识别主图形。"""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    padding = size // 16
    radius = size // 5
    draw.rounded_rectangle(
        (padding, padding, size - padding, size - padding), radius=radius, fill="#172033"
    )
    # A 形主路径与两侧分流节点，表达多账号 API 汇聚与分发。
    stroke = size // 20
    points = [(size * 0.31, size * 0.72), (size * 0.50, size * 0.27), (size * 0.69, size * 0.72)]
    draw.line(points, fill="#55D6BE", width=stroke, joint="curve")
    draw.line((size * 0.39, size * 0.55, size * 0.61, size * 0.55), fill="#55D6BE", width=stroke)
    node_radius = size // 24
    for x, y, color in (
        (size * 0.23, size * 0.31, "#5CA9FF"),
        (size * 0.77, size * 0.31, "#5CA9FF"),
        (size * 0.50, size * 0.80, "#F5C46B"),
    ):
        draw.ellipse((x - node_radius, y - node_radius, x + node_radius, y + node_radius), fill=color)
    draw.line((size * 0.27, size * 0.34, size * 0.40, size * 0.43), fill="#5CA9FF", width=size // 40)
    draw.line((size * 0.73, size * 0.34, size * 0.60, size * 0.43), fill="#5CA9FF", width=size // 40)
    draw.line((size * 0.50, size * 0.72, size * 0.50, size * 0.76), fill="#F5C46B", width=size // 40)
    return image


def main() -> None:
    """输出 PNG、ICO、ICNS 三种图标格式，供运行时和平台打包器使用。"""
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    icon = generate_icon()
    icon.save(ICON_DIR / "aimux.png")
    icon.save(ICON_DIR / "aimux.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    icon.save(ICON_DIR / "aimux.icns")
    print(f"Generated icons in {ICON_DIR}")


if __name__ == "__main__":
    main()
