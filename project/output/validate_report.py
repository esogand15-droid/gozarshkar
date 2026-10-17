# -*- coding: utf-8 -*-
"""بازبینی خودکار خروجی: سرریز، خروج از حاشیه، تداخل نوشتار، قلم، واژگان کلیدی.

اجرا:  python3 validate_report.py
کد خروجی ۰ = بدون نقص.
"""
import os
import sys
import unicodedata

import numpy
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
PDF = os.path.join(HERE, "final_consultant_report.pdf")

MX = 40.0
PW, PH = 595.276, 841.89
# ناحیهٔ محتوای مجاز (مختصات PDF با مبدأ پایین-چپ)
CONTENT_TOP = PH - 76.0      # 765.9 : زیرِ نوارِ سربرگ
CONTENT_BOTTOM = 66.0        # بالای خط پاصفحه

problems = []


def norm(s):
    s = unicodedata.normalize("NFKC", s)
    return s.replace("\u200c", "").replace("\u200d", "").replace("\u200e", "").replace("\u200f", "")


def to_r(pdf_y0, pdf_y1):
    """تبدیل بازهٔ mupdf (مبدأ بالا-چپ) به بازهٔ PDF (مبدأ پایین-چپ)."""
    return (PH - pdf_y1, PH - pdf_y0)


def area(r):
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def inter(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0, 0.0, 0.0
    return (x1 - x0) * (y1 - y0), (x1 - x0), (y1 - y0)


def main():
    doc = pymupdf.open(PDF)
    if doc.page_count != 4:
        problems.append("تعداد صفحات {} است (باید ۴ باشد)".format(doc.page_count))

    full = []
    for pno in range(doc.page_count):
        page = doc[pno]
        raw = page.get_text()
        full.append(norm(raw))
        if len(raw.strip()) < 200:
            problems.append("صفحه {}: متن بسیار کم است".format(pno + 1))
        if not any("Vazirmatn" in f[3] for f in page.get_fonts(full=True)):
            problems.append("صفحه {}: قلم Vazirmatn درون‌نشانی نشده".format(pno + 1))

        spans = []
        for blk in page.get_text("dict")["blocks"]:
            for line in blk.get("lines", []):
                for sp in line.get("spans", []):
                    if not sp["text"].strip():
                        continue
                    b = sp["bbox"]
                    y0, y1 = to_r(b[1], b[3])
                    # سربرگ و پاصفحه از بازبینیِ حاشیه مستثنی هستند
                    if y1 > CONTENT_TOP or y0 < CONTENT_BOTTOM:
                        continue
                    spans.append({"t": sp["text"], "r": (b[0], y0, b[2], y1)})

        for sp in spans:
            x0, y0, x1, y1 = sp["r"]
            if x0 < MX - 0.8 or x1 > PW - MX + 0.8:
                problems.append("صفحه {} خروج افقی: x=[{:.1f},{:.1f}] «{}»".format(
                    pno + 1, x0, x1, sp["t"][:40]))
            if y0 < CONTENT_BOTTOM - 0.8 or y1 > CONTENT_TOP + 0.8:
                problems.append("صفحه {} خروج عمودی: y=[{:.1f},{:.1f}] «{}»".format(
                    pno + 1, y0, y1, sp["t"][:40]))

        for i in range(len(spans)):
            a = spans[i]["r"]
            for j in range(i + 1, len(spans)):
                b = spans[j]["r"]
                ov, ow, oh = inter(a, b)
                if ov < 3.0 or ow < 1.0 or oh < 1.0:
                    continue
                vr = oh / min(a[3] - a[1], b[3] - b[1])
                hr = ow / min(a[2] - a[0], b[2] - b[0])
                if vr > 0.50 and hr > 0.15:
                    problems.append("صفحه {} تداخل «{}» با «{}» (عمودی {:.0%})".format(
                        pno + 1, spans[i]["t"][:26], spans[j]["t"][:26], vr))

        # ۵) آزمونِ «متنِ ناخوانا»: متن سفید خارج از نوار سربرگ باید روی زمینهٔ تیره باشد
        pix = page.get_pixmap(dpi=150)
        n = pix.width / PW
        for blk in page.get_text("dict")["blocks"]:
            for line in blk.get("lines", []):
                for sp in line.get("spans", []):
                    if not sp["text"].strip():
                        continue
                    col = sp.get("color")
                    if col is None:
                        continue
                    try:
                        r, g, bl = int(col) >> 16 & 255, int(col) >> 8 & 255, int(col) & 255
                    except Exception:
                        continue
                    if not (r > 235 and g > 235 and bl > 235):
                        continue
                    bb = sp["bbox"]
                    y0, y1 = to_r(bb[1], bb[3])
                    if y1 > CONTENT_TOP:
                        continue                      # متنِ نوار سربرگ
                    x0 = max(0, int(bb[0] * n)); x1 = min(pix.width, int(bb[2] * n))
                    ya = max(0, int(bb[1] * n)); yb = min(pix.height, int(bb[3] * n))
                    if x1 <= x0 or yb <= ya:
                        continue
                    tot = dark = 0
                    for yy in range(ya, yb, 2):
                        for xx in range(x0, x1, 2):
                            i = (yy * pix.width + xx) * pix.n
                            pr, pg, pb = pix.samples[i], pix.samples[i + 1], pix.samples[i + 2]
                            tot += 1
                            if not (pr > 225 and pg > 225 and pb > 225):
                                dark += 1
                    if tot and dark / float(tot) < 0.25:
                        problems.append(
                            "صفحه {} متن روشن روی زمینهٔ روشن (ناخوانا): «{}»".format(
                                pno + 1, sp["text"][:30]))

        # ۶) نبودِ جوهر در نوارهای حاشیهٔ کناریِ ناحیهٔ محتوا
        pix = page.get_pixmap(dpi=150)
        arr = numpy.frombuffer(pix.samples, dtype=numpy.uint8).reshape(
            pix.height, pix.width, pix.n)[:, :, :3].astype(numpy.int16)
        n = pix.width / PW
        y_top_px = int((PH - CONTENT_TOP) * n)
        y_bot_px = min(int((PH - CONTENT_BOTTOM) * n), pix.height)
        band = arr[y_top_px:y_bot_px]
        if band.size:
            left = band[:, :max(1, int((MX - 2.5) * n))]
            right = band[:, max(1, int((PW - MX + 2.5) * n)):]
            ink = int(((left < 232).any(axis=2)).sum() + ((right < 232).any(axis=2)).sum())
            if ink > 400:
                problems.append("صفحه {}: {} پیکسلِ جوهر در حاشیهٔ کناری (نشت به بیرون از ستون‌ها)".format(
                    pno + 1, ink))

    text = "\n".join(full)
    # بررسیِ واژگانیِ مقاوم در برابر بازآراییِ دوجهته (همهٔ واژه‌های هر گروه باید حاضر باشند)
    must = [
        ["علی", "بهمنزاده"],
        ["مادکوش", "سهامی", "خاص"],
        ["صفحه", "۱", "از", "۴"],
        ["۶,۶۰۰,۰۰۰,۰۰۰"],
        ["۲۲,۰۰۰,۰۰۰"],
        ["SKS-F4420007"],
        ["۱۴۰۵/۱۲/۲۹"],
        ["۲۵۰", "گرم"],
        ["۲۰۰", "گرم"],
        ["غربت", "بستانی"],
        ["چکیده", "مدیریتی"],
        ["کباب", "کوبیده"],
        ["انبارگردانی"],
        ["تاریخ", "تنظیم", "مهر"],
        ["اردیبهشت", "پایان", "مهر"],
        ["حراست", "پیمانکاران"],
        ["استانبولی", "زرشک", "قیمه"],
        ["MKO-FR-MD-IS-23"],
        ["کشک", "بادمجان"],
    ]
    for group in must:
        missing = [w for w in group if w not in text]
        if missing:
            problems.append("واژگان کلیدی در متن یافت نشد: «{}» (غایب: {})".format(
                " ".join(group), "، ".join(missing)))

    bad = ["OCR", "ocr", "Tesseract", "tesseract", "هوش مصنوعی", "ایجنت",
           "Agent", "agent", "confidence", "مستندات", "بازشناسی", "ناخوانا",
           "گزارش خودکار", "ReportLab", "لایه متن", "traineddata", "نیازمند تأیید"]
    for b in bad:
        if b in text:
            problems.append("نشانهٔ نامطلوب در متن: «{}»".format(b))

    print("تعداد نویسهٔ متنِ استخراج‌شده: {}".format(len(text)))
    if problems:
        seen, uniq = set(), []
        for p in problems:
            if p not in seen:
                seen.add(p)
                uniq.append(p)
        print("\n{} مورد نقص:".format(len(uniq)))
        for p in uniq:
            print(" - " + p)
        return 1
    print("\nبدون نقص: ۴ صفحه | بدون خروج از حاشیه | بدون تداخل نوشتار | "
          "قلم درون‌نشانی‌شده | واژگان کلیدی حاضر")
    return 0


if __name__ == "__main__":
    sys.exit(main())
