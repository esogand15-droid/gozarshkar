#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""آماده‌سازی تصاویر پیوست: تغییر اندازه، یکسان‌سازی چرخش و ذخیره در assets/photos.

ورودی: پوشهٔ حاوی ۶۳ فایل JPG استخراج‌شده از آرشیو «عکس های گزارش».
خروجی:
  project/assets/photos/<original-name>.jpg   (حداکثر ۱۴۰۰ پیکسل در ضلع بزرگ)
  project/analysis/photo_index.csv            (سیاههٔ تصاویر)

اجرا:
  python3 project/scripts/prepare_photos.py [مسیر پوشهٔ تصاویر خام]
"""

import csv
import os
import sys

from PIL import Image, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "assets", "photos")
CSV_PATH = os.path.join(ROOT, "analysis", "photo_index.csv")
DEFAULT_SRC = os.path.join(ROOT, "source", "photos_original", "عکس های گزارش")

MAX_EDGE = 1200      # بلندترین ضلع (کافی برای چاپ در پیوست A4)
QUALITY = 82


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    if not os.path.isdir(src):
        sys.exit("پوشهٔ تصاویر یافت نشد: " + src)
    os.makedirs(OUT_DIR, exist_ok=True)

    names = sorted(f for f in os.listdir(src) if f.lower().endswith(".jpg"))
    rows = []
    for name in names:
        im = Image.open(os.path.join(src, name))
        im = ImageOps.exif_transpose(im).convert("RGB")
        w, h = im.size
        scale = MAX_EDGE / float(max(w, h))
        if scale < 1:
            im = im.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
        out = os.path.join(OUT_DIR, name)
        im.save(out, "JPEG", quality=QUALITY, optimize=True, progressive=True)
        rows.append([name, im.size[0], im.size[1], os.path.getsize(out)])
        print("{} → {}×{}  {:.0f} KB".format(name, im.size[0], im.size[1],
                                             os.path.getsize(out) / 1024.0))

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as fh:
        wr = csv.writer(fh)
        wr.writerow(["فایل", "عرض", "ارتفاع", "بایت"])
        wr.writerows(rows)
    print("{} تصویر در {} ذخیره شد؛ سیاهه: {}".format(len(rows), OUT_DIR, CSV_PATH))


if __name__ == "__main__":
    main()
