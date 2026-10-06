"""Prepare a portrait photo for ASCII conversion.

1. Remove the background with rembg so only the subject is left.
2. Boost local contrast with CLAHE so a flatly lit face gets real highlights and shadows.
3. Composite onto pure white (alpha kept) so the background maps to the blank end of the ASCII ramp.

Usage: python scripts/prep_photo.py source-photo.jpg [--out source-prepped.png] [--crop-bottom 0.75]
"""
import argparse
import io

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo")
    ap.add_argument("--out", default="source-prepped.png")
    ap.add_argument("--crop-bottom", type=float, default=0.75,
                    help="keep this fraction of the image height, from the top (head-to-torso framing)")
    ap.add_argument("--upscale", type=int, default=3,
                    help="upscale small photos before segmentation for cleaner edges")
    args = ap.parse_args()

    img = Image.open(args.photo).convert("RGB")
    w, h = img.size
    img = img.crop((0, 0, w, int(h * args.crop_bottom)))
    if args.upscale > 1:
        img = img.resize((img.width * args.upscale, img.height * args.upscale), Image.LANCZOS)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    cut = Image.open(io.BytesIO(remove(buf.getvalue(), session=new_session("u2net_human_seg")))).convert("RGBA")

    rgba = np.array(cut)
    gray = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)
    alpha = rgba[..., 3].astype(np.float32) / 255.0

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # stretch the subject's own tonal range so it uses the whole ramp
    subject = gray[alpha > 0.5]
    lo, hi = np.percentile(subject, 2), np.percentile(subject, 98)
    gray = np.clip((gray.astype(np.float32) - lo) / max(hi - lo, 1) * 255, 0, 255)

    # gray composited on white, with the cutout mask kept as alpha so the
    # ASCII step can tell background from bright skin
    out = gray * alpha + 255 * (1 - alpha)
    la = np.dstack([out, alpha * 255]).astype(np.uint8)
    Image.fromarray(la, "LA").save(args.out)
    print(f"wrote {args.out} ({out.shape[1]}x{out.shape[0]})")


if __name__ == "__main__":
    main()
