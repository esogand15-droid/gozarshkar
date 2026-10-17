#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""استخراج تصویرِ تمام‌وضوحِ هر صفحه از PDF منبع و ساخت نمایهٔ تصاویر.

خروجی:
  processing/normalized_images/page_01.png … page_32.png
  analysis/image_index.json
"""
import json, os

try:
    import pymupdf
except ImportError:  # سازگاری با نسخه‌های قدیمی‌تر
    import fitz as pymupdf

ROOT = os.environ.get("PROJECT_ROOT", "/home/user/project")
SRC = os.path.join(ROOT, "source", "extracted", "CamScanner 10-17-26 20.43.pdf")
IMGDIR = os.path.join(ROOT, "processing", "normalized_images")
INDEX = os.path.join(ROOT, "analysis", "image_index.json")


def main():
    os.makedirs(IMGDIR, exist_ok=True)
    doc = pymupdf.open(SRC)
    index = []
    for i, page in enumerate(doc, start=1):
        imgs = page.get_images(full=True)
        # بزرگ‌ترین تصویرِ صفحه = اسکن اصلی (تصویر دوم معمولاً نشان CamScanner است)
        best, bestarea = None, 0
        for im in imgs:
            info = doc.extract_image(im[0])
            area = info["width"] * info["height"]
            if area > bestarea:
                bestarea, best = area, im[0]
        out = os.path.join(IMGDIR, f"page_{i:02d}.png")
        if best is not None:
            pix = pymupdf.Pixmap(doc, best)
            if pix.n > 4:  # حذف کانال آلفا در صورت وجود
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            pix.save(out)
            info = doc.extract_image(best)
            w, h = info["width"], info["height"]
        else:
            pix = page.get_pixmap(dpi=300)
            pix.save(out)
            w, h = pix.width, pix.height
        index.append({
            "page": i,
            "xref": best,
            "width": w,
            "height": h,
            "png": out,
            "png_bytes": os.path.getsize(out),
            "image_count": len(imgs),
        })
        print(f"page {i:02d}: {w}x{h} -> {out}")
    with open(INDEX, "w") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"wrote {INDEX} ({len(index)} pages)")


if __name__ == "__main__":
    main()
