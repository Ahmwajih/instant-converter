from pathlib import Path
from PIL import Image, ImageDraw


def generate_icons() -> None:
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Render at 512x512 and downsample to 256x256 for smooth anti-aliasing
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Outer dark badge background
    draw.ellipse((16, 16, size - 16, size - 16), fill=(24, 24, 27, 255), outline=(63, 63, 70, 255), width=8)

    # 4 Radial format slices (Blue, Cyan, Emerald, Violet)
    slice_bbox = (48, 48, size - 48, size - 48)
    slices = [
        (-82, -8, (59, 130, 246, 255)),    # Top-Right: Blue
        (8, 82, (6, 182, 212, 255)),       # Bottom-Right: Cyan
        (98, 172, (16, 185, 129, 255)),    # Bottom-Left: Emerald
        (188, 262, (139, 92, 246, 255)),   # Top-Left: Violet
    ]
    for start_deg, end_deg, color in slices:
        draw.pieslice(slice_bbox, start=start_deg, end=end_deg, fill=color)

    # Inner hub cutout
    hub_margin = 148
    draw.ellipse(
        (hub_margin, hub_margin, size - hub_margin, size - hub_margin),
        fill=(24, 24, 27, 255),
        outline=(96, 165, 250, 255),
        width=8,
    )

    # Center conversion arrows (top arrow -> right, bottom arrow -> left)
    white = (255, 255, 255, 255)
    # Top arrow shaft & head (pointing right)
    draw.rounded_rectangle((195, 222, 285, 242), radius=8, fill=white)
    draw.polygon([(275, 204), (322, 232), (275, 260)], fill=white)

    # Bottom arrow shaft & head (pointing left)
    draw.rounded_rectangle((227, 270, 317, 290), radius=8, fill=white)
    draw.polygon([(237, 252), (190, 280), (237, 308)], fill=white)

    icon_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"

    icon_256.save(png_path, format="PNG")
    img.save(
        ico_path,
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
    )
    print(f"Generated icons: {png_path} and {ico_path}")


if __name__ == "__main__":
    generate_icons()
