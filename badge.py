from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math

def find_font(bold=True, size=40):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
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

def apply_badge(product_img_path, count, out_path, diameter=300, margin_right=-90, margin_top=-60):
    """Overlay a FIXED-size badge at a fixed offset from the top-right corner,
    regardless of the product image's own dimensions.

    diameter:      badge size in pixels (constant across all images)
    margin_right:  horizontal offset of badge's right edge from image's right edge
                   (negative = badge overflows past the right edge, matching reference look)
    margin_top:    vertical offset of badge's top edge from image's top edge
                   (negative = badge overflows above the top edge)
    """
    product = Image.open(product_img_path).convert("RGBA")
    pw, ph = product.size
    badge = make_badge(count, diameter=diameter)

    # extra canvas space so the badge can overflow past the image edges (like reference)
    extra_top = max(0, margin_top * -1) if margin_top < 0 else 0
    extra_right = max(0, margin_right * -1) if margin_right < 0 else 0
    cw, ch = pw + extra_right, ph + extra_top

    # position within the new, larger canvas
    off_x = (cw - diameter) if margin_right < 0 else (pw - diameter - margin_right)
    off_y = 0 if margin_top < 0 else margin_top
    product_pos = (0, extra_top)

    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    canvas.paste(product, product_pos, product)

    shadow = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([off_x + diameter*0.06, off_y + diameter*0.08, off_x + diameter*1.06, off_y + diameter*1.08], fill=(0,0,0,90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(diameter*0.04))
    canvas = Image.alpha_composite(canvas, shadow)

    canvas.paste(badge, (off_x, off_y), badge)

    canvas.convert("RGB").save(out_path, quality=95)

if __name__ == "__main__":
    apply_badge("/mnt/user-data/uploads/1784881159942_image.png", 3, "/home/claude/test_output.png")
