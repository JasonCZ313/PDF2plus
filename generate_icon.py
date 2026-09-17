# -*- coding: utf-8 -*-
"""
生成 PDF2plus 应用封面图标。

设计：深蓝渐变圆角底 + 中央精致字标「PDF2+」（+ 为琥珀色强调）。
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def _load_font(size: int, bold: bool = True):
    """按优先级加载适合字标的字体。"""
    candidates = []
    if bold:
        candidates.extend([
            "C:/Windows/Fonts/seguisb.ttf",   # Segoe UI Semibold
            "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold
            "C:/Windows/Fonts/msyhbd.ttc",    # 微软雅黑 Bold
            "C:/Windows/Fonts/arialbd.ttf",
        ])
    candidates.extend([
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ])
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_gradient_rounded(size: int) -> Image.Image:
    """绘制深蓝竖直渐变圆角底板。"""
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    top = (15, 39, 68)      # #0F2744
    bottom = (26, 74, 122)  # #1A4A7A
    for row in range(size):
        ratio = row / max(1, size - 1)
        color = (
            int(top[0] + (bottom[0] - top[0]) * ratio),
            int(top[1] + (bottom[1] - top[1]) * ratio),
            int(top[2] + (bottom[2] - top[2]) * ratio),
            255,
        )
        draw.line([(0, row), (size, row)], fill=color)

    # 圆角蒙版
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    radius = max(28, size // 8)
    mask_draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    base.paste(gradient, (0, 0), mask)
    return base


def generate_icon():
    """生成 png 与多尺寸 ico，中央为 PDF2+ 字标。"""
    os.makedirs(ASSETS_DIR, exist_ok=True)
    size = 512
    img = _draw_gradient_rounded(size)
    draw = ImageDraw.Draw(img)

    # 轻微内高光边，增加精致感
    inset = max(8, size // 48)
    draw.rounded_rectangle(
        [inset, inset, size - 1 - inset, size - 1 - inset],
        radius=max(22, size // 9),
        outline=(255, 255, 255, 36),
        width=max(2, size // 180),
    )

    font_main = _load_font(int(size * 0.22), bold=True)
    font_plus = _load_font(int(size * 0.24), bold=True)

    mark_left = "PDF2"
    mark_plus = "+"
    # 先测整段宽度再居中
    left_box = draw.textbbox((0, 0), mark_left, font=font_main)
    plus_box = draw.textbbox((0, 0), mark_plus, font=font_plus)
    left_w = left_box[2] - left_box[0]
    plus_w = plus_box[2] - plus_box[0]
    gap = int(size * 0.01)
    total_w = left_w + gap + plus_w
    start_x = (size - total_w) // 2
    # 垂直居中略偏上，给底线留空
    text_y = int(size * 0.36)

    # 柔和阴影
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text((start_x + 3, text_y + 4), mark_left, font=font_main, fill=(0, 0, 0, 90))
    shadow_draw.text(
        (start_x + left_w + gap + 3, text_y + 2),
        mark_plus,
        font=font_plus,
        fill=(0, 0, 0, 90),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=3))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)

    draw.text((start_x, text_y), mark_left, font=font_main, fill=(248, 250, 252, 255))
    draw.text(
        (start_x + left_w + gap, text_y - int(size * 0.01)),
        mark_plus,
        font=font_plus,
        fill=(244, 185, 66, 255),  # #F4B942
    )

    # 字标下淡金细线
    line_y = text_y + int(size * 0.28)
    line_half = int(size * 0.16)
    draw.line(
        [(size // 2 - line_half, line_y), (size // 2 + line_half, line_y)],
        fill=(244, 185, 66, 160),
        width=max(2, size // 160),
    )

    png_path = os.path.join(ASSETS_DIR, "icon.png")
    ico_path = os.path.join(ASSETS_DIR, "icon.ico")
    # 保存展示用高清 png（窗口图标 / 资源）
    img_256 = img.resize((256, 256), Image.Resampling.LANCZOS)
    img_256.save(png_path, "PNG")
    # 多尺寸 ico：Windows 资源管理器 / 启动器 exe 必须用 .ico 才能正确嵌入
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    ico_frames = [img.resize(frame_size, Image.Resampling.LANCZOS) for frame_size in ico_sizes]
    ico_frames[0].save(
        ico_path,
        format="ICO",
        sizes=ico_sizes,
        append_images=ico_frames[1:],
    )

    print(f"图标已生成: {png_path}")
    print(f"图标已生成: {ico_path}")


if __name__ == "__main__":
    generate_icon()
