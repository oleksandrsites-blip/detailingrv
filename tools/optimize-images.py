#!/usr/bin/env python3
"""Готує фото для сайту: AVIF + WebP у кількох ширинах.

    python3 tools/optimize-images.py

1) _src/unsplash/photo-*.jpg  ->  images/photos/photo-…-{480,800,1200,1600,2000}.{avif,webp}
2) images/before-after/<категорія>/before.(jpg|jpeg|png|webp) і after.(…)
   ->  before.webp / after.webp (1600 px по довгій стороні) + before-800.webp / after-800.webp

Потрібен Pillow з підтримкою AVIF:  pip3 install --upgrade pillow
"""
import sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
LADDER = [480, 800, 1200, 1600, 2000]


def save(im, path, fmt):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "webp":
        im.save(path, "WEBP", quality=72, method=6)
    else:
        im.save(path, "AVIF", quality=52, speed=4)


def resize_w(im, w):
    if im.width <= w:
        return im
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def photos():
    src = ROOT / "_src" / "unsplash"
    out = ROOT / "images" / "photos"
    files = sorted(src.glob("photo-*.jpg"))
    if not files:
        print("у _src/unsplash немає фото — спершу запустіть tools/fetch-photos.sh")
    for f in files:
        im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
        for w in LADDER:
            if w > im.width:
                continue
            small = resize_w(im, w)
            for fmt in ("avif", "webp"):
                p = out / f"{f.stem}-{w}.{fmt}"
                if not p.exists() or p.stat().st_mtime < f.stat().st_mtime:
                    save(small, p, fmt)
        print("✓", f.stem)


def pairs():
    base = ROOT / "images" / "before-after"
    for d in sorted(p for p in base.glob("*") if p.is_dir()):
        for side in ("before", "after"):
            srcs = [p for p in d.glob(side + ".*") if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic", ".webp")]
            # беремо оригінал (jpg/png), якщо є; інакше вже готовий webp
            srcs.sort(key=lambda p: p.suffix.lower() == ".webp")
            if not srcs:
                print(f"  {d.name}: немає {side}.jpg")
                continue
            im = ImageOps.exif_transpose(Image.open(srcs[0])).convert("RGB")
            k = min(1, 1600 / max(im.size))
            big = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS) if k < 1 else im
            save(big, d / f"{side}.webp", "webp")
            save(resize_w(big, 800), d / f"{side}-800.webp", "webp")
            for p in srcs:
                if p.suffix.lower() != ".webp":
                    p.unlink()  # оригінал більше не потрібен
        print("✓ до/після:", d.name)


if __name__ == "__main__":
    what = sys.argv[1:] or ["photos", "pairs"]
    if "photos" in what:
        photos()
    if "pairs" in what:
        pairs()
