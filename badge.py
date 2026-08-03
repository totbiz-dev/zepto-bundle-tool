from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def find_font(bold=True, size=40):
    candidates = [
        os.path.join(_SCRIPT_DIR, "fonts", "DejaVuSans-Bold.ttf"),  # bundled, always present
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()

def make_badge(count, diameter=300):
    """Creates a purple gradient circle badge with number + 'Pieces' text, RGBA, transparent bg."""
    scale = 4  # supersample for smooth edges/text
    d = diameter * scale
    img = Image.new("RGBA", (d, d), (0, 0, 0, 0))

    # Radial-ish gradient purple circle (lighter upper-left -> darker lower-right)
    grad = Image.new("L", (d, d), 0)
    gpix = grad.load()
    cx, cy = d * 0.35, d * 0.30
    max_dist = math.hypot(d - cx, d - cy)
    for y in range(0, d, 2):
        for x in range(0, d, 2):
            dist = math.hypot(x - cx, y - cy) / max_dist
            val = int(max(0, min(255, 255 - dist * 180)))
            gpix[x, y] = val
            if x + 1 < d: gpix[x+1, y] = val
            if y + 1 < d: gpix[x, y+1] = val
            if x + 1 < d and y + 1 < d: gpix[x+1, y+1] = val

    light = (124, 58, 180, 255)   # lighter violet
    dark = (46, 15, 84, 255)      # deep purple
    circle_grad = Image.new("RGBA", (d, d))
    cg = circle_grad.load()
    gp = grad.load()
    for y in range(d):
        for x in range(d):
            t = gp[x, y] / 255.0
            r = int(dark[0] + (light[0] - dark[0]) * t)
            g = int(dark[1] + (light[1] - dark[1]) * t)
            b = int(dark[2] + (light[2] - dark[2]) * t)
            cg[x, y] = (r, g, b, 255)

    mask = Image.new("L", (d, d), 0)
    mdraw = ImageDraw.Draw(mask)
    pad = int(d * 0.02)
    mdraw.ellipse([pad, pad, d - pad, d - pad], fill=255)

    img.paste(circle_grad, (0, 0), mask)

    # subtle highlight (glossy) top-left
    highlight = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    hdraw = ImageDraw.Draw(highlight)
    hdraw.ellipse([d*0.15, d*0.08, d*0.75, d*0.45], fill=(255, 255, 255, 40))
    highlight = highlight.filter(ImageFilter.GaussianBlur(d * 0.03))
    img = Image.alpha_composite(img, highlight)

    # subtle rim
    rim = Image.new("RGBA", (d, d), (0, 0, 0, 0))
    rdraw = ImageDraw.Draw(rim)
    rdraw.ellipse([pad, pad, d - pad, d - pad], outline=(200, 170, 230, 120), width=int(d*0.006))
    img = Image.alpha_composite(img, rim)

    draw = ImageDraw.Draw(img)
    num_str = str(count)
    num_font_size = int(d * (0.34 if len(num_str) == 1 else 0.28))
    num_font = find_font(size=num_font_size)
    label_font = find_font(size=int(d * 0.11))

    bbox = draw.textbbox((0, 0), num_str, font=num_font)
    nw, nh = bbox[2]-bbox[0], bbox[3]-bbox[1]
    lbox = draw.textbbox((0, 0), "Pieces", font=label_font)
    lw, lh = lbox[2]-lbox[0], lbox[3]-lbox[1]

    total_h = nh + int(d*0.03) + lh
    start_y = (d - total_h) / 2 - d*0.03

    draw.text(((d - nw) / 2 - bbox[0], start_y - bbox[1]), num_str, font=num_font, fill="white")
    ly = start_y + nh + int(d*0.03)
    draw.text(((d - lw) / 2 - lbox[0], ly - lbox[1]), "Pieces", font=label_font, fill="white")

    img = img.resize((diameter, diameter), Image.LANCZOS)
    return img

def apply_badge(product_img_path, count, out_path, badge_scale=0.34, overlap_x=0.55, overlap_y=0.32):
    """Overlay badge sized proportionally to the product image (scales with each image),
    positioned overlapping the top-right corner, matching the reference look.

    badge_scale: badge diameter as a fraction of the product image's width
    overlap_x:   fraction of badge diameter that sits PAST the right edge of the image
    overlap_y:   fraction of badge diameter that sits ABOVE the top edge of the image
    """
    product = Image.open(product_img_path).convert("RGBA")
    pw, ph = product.size
    diameter = int(pw * badge_scale)
    badge = make_badge(count, diameter=diameter)

    extra_right = int(diameter * overlap_x)
    extra_top = int(diameter * overlap_y)
    cw, ch = pw + extra_right, ph + extra_top

    off_x = cw - diameter
    off_y = 0
    product_pos = (0, extra_top)

    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    canvas.paste(product, product_pos, product)

    # subtle drop shadow — small offset, low opacity, soft blur (not a visible second circle)
    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    so = diameter * 0.02
    sdraw.ellipse([off_x + so, off_y + so * 2, off_x + diameter + so, off_y + diameter + so * 2],
                  fill=(0, 0, 0, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(diameter * 0.05))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(badge, (off_x, off_y), badge)

    if out_path.lower().endswith((".jpg", ".jpeg")):
        flat = Image.new("RGB", canvas.size, (255, 255, 255))
        flat.paste(canvas, (0, 0), canvas)
        flat.save(out_path, quality=95)
    else:
        canvas.save(out_path)  # PNG keeps transparency intact

if __name__ == "__main__":
    apply_badge("/mnt/user-data/uploads/1784881159942_image.png", 3, "/home/claude/test_output.png")
