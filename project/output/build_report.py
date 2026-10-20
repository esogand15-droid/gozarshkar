# -*- coding: utf-8 -*-
"""ساخت گزارش نهایی (۴ صفحه A4، راست‌به‌چپ) با قلم Vazirmatn.

اجرا:
    python3 build_report.py            # ساخت PDF
    python3 build_report.py --draft    # گزارش اندازه‌گیری و فضای باقی‌مانده هر صفحه
"""
import json
import os
import sys

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_content as C
import report_photos as P

# ------------------------------------------------------------------ مسیرها
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONTS = os.path.join(ROOT, "assets", "fonts")
OUT = os.path.join(HERE, "final_consultant_report.pdf")

pdfmetrics.registerFont(TTFont("VR", os.path.join(FONTS, "Vazirmatn-Regular.ttf")))
pdfmetrics.registerFont(TTFont("VB", os.path.join(FONTS, "Vazirmatn-Bold.ttf")))
pdfmetrics.registerFont(TTFont("VM", os.path.join(FONTS, "Vazirmatn-Medium.ttf")))
pdfmetrics.registerFont(TTFont("VS", os.path.join(FONTS, "Vazirmatn-SemiBold.ttf")))

# ------------------------------------------------------------------ رنگ‌ها
NAVY = HexColor("#17324D")
STEEL = HexColor("#42657D")
LIGHT = HexColor("#F3F5F7")
GOLD = HexColor("#C29A54")
LINE = HexColor("#D6DDE3")
GREY = HexColor("#5B6470")
MUTED = HexColor("#F8F9FA")

# ------------------------------------------------------------------ صفحه
PW, PH = A4
MX = 40.0                      # حاشیهٔ راست و چپ
TOP = PH - 96.0                # بالای ناحیهٔ محتوا (پایینِ سربرگ)
BOTTOM = 70.0                  # پایین ناحیهٔ محتوا (بالای خط پاصفحه)
CW = PW - 2 * MX

DRAFT = "--draft" in sys.argv
REPORT = []
TABLE_GEOM = []   # هندسهٔ جدول‌ها برای بازبینیِ خودکار (مرزهای واقعی ستون‌ها)
PHOTO_GEOM = []   # هندسهٔ قاب تصاویر پیوست برای بازبینیِ خودکار
TOTAL_PAGES = 7   # ۴ صفحهٔ گزارش + ۳ صفحهٔ پیوست تصویری
PHOTO_ASSETS = os.path.join(ROOT, P.PHOTO_DIR)


def fa_num(n):
    return str(n).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def R(t):
    try:
        return get_display(arabic_reshaper.reshape(t))
    except Exception:
        return t


def W(t, font, size):
    return pdfmetrics.stringWidth(R(str(t)), font, size)


def wrap(text, font, size, maxw):
    """بسته‌بندی روی واژه‌های منطقی؛ هر سطر با بازآرایی/دوجهته‌سازی اندازه‌گیری می‌شود."""
    text = str(text)
    if W(text, font, size) <= maxw:
        return [text]
    words = text.split()
    lines, cur = [], []
    for wd in words:
        trial = cur + [wd]
        if W(" ".join(trial), font, size) <= maxw:
            cur = trial
        else:
            if cur:
                lines.append(" ".join(cur))
            # واژه‌ای بلندتر از عرض ستون: شکست ناگزیر نویسه‌ای
            while W(wd, font, size) > maxw and len(wd) > 1:
                cut = len(wd)
                while cut > 1 and W(wd[:cut], font, size) > maxw:
                    cut -= 1
                lines.append(wd[:cut])
                wd = wd[cut:]
            cur = [wd]
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_str(c, text, x_right, y, font, size, color=None):
    """ترسیم راست‌چین با لنگرِ لبهٔ راست (برای متن بازآرایی‌شده الزامی است)."""
    c.setFont(font, size)
    if color is not None:
        c.setFillColor(color)
    c.drawString(x_right - W(text, font, size), y, R(str(text)))


def draw_str_left(c, text, x_left, y, font, size, color=None):
    """ترسیم با لنگرِ لبهٔ چپ (برای متن‌های چپ‌چینِ سربرگ و پاصفحه)."""
    c.setFont(font, size)
    if color is not None:
        c.setFillColor(color)
    c.drawString(x_left, y, R(str(text)))


def draw_str_center(c, text, cx, y, font, size, color=None):
    c.setFont(font, size)
    if color is not None:
        c.setFillColor(color)
    c.drawString(cx - W(text, font, size) / 2.0, y, R(str(text)))


# ------------------------------------------------------------------ بلوک‌ها
def section_title(c, x_right, y, text, width=CW):
    h = 15.0
    # راست‌چین: نوار تزئینی باید در لبهٔ راستِ کادر و در آغازِ تیتر (سمت شروع
    # خوانش) قرار گیرد، نه در لبهٔ چپ. پهنای نوار ۳/۲ pt است و لبهٔ راستِ آن
    # با x_right منطبق می‌شود؛ متن با ۵/۸ pt فاصله از نوار آغاز می‌گردد.
    c.setFillColor(GOLD)
    c.rect(x_right - 3.2, y - 9.0, 3.2, 11.5, stroke=0, fill=1)
    draw_str(c, text, x_right - 9.0, y - 7.0, "VB", 9.6, NAVY)
    return y - h - 7.0


def para(c, x_right, y, text, font="VR", size=8.6, leading=13.2, width=CW, color=None):
    for ln in wrap(text, font, size, width):
        draw_str(c, ln, x_right, y, font, size, color)
        y -= leading
    return y


def measure_para(text, font="VR", size=8.6, leading=13.2, width=CW):
    return len(wrap(text, font, size, width)) * leading


# ------------------------------------------------------------------ جدول
def _cell_lines(rows, widths, font, size, padx):
    out = []
    for row in rows:
        rl = []
        for i, cell in enumerate(row):
            rl.append(wrap(cell, font, size, widths[i] - 2 * padx))
        out.append(rl)
    return out


def table(c, x_right, y, widths, header, rows, size=7.4, padx=4.0, pady=3.2,
          leading=None, hdr_size=None, status_cols=(), center_cols=(),
          body_font="VR", zebra=True, draw=True):
    """جدول راست‌چین با سطر سرستون تیره. ارتفاع مصرف‌شده برگردانده می‌شود."""
    leading = leading or size * 1.34
    hdr_size = hdr_size or size
    total = sum(widths)
    lines = _cell_lines(rows, widths, body_font, size, padx)
    hlines = [wrap(h, "VB", hdr_size, widths[i] - 2 * padx) for i, h in enumerate(header)]
    hh = max(len(x) for x in hlines) * (hdr_size * 1.34) + 2 * pady
    heights = [max(len(cl) for cl in rl) * leading + 2 * pady for rl in lines]

    if not draw:
        return hh + sum(heights)

    x0 = x_right - total
    # مرزهای مجازِ خطوط عمودی: لبه‌های بیرونیِ جدول + جداکننده‌های ستون‌ها
    bounds = [x0]
    vx = x_right
    for i in range(len(widths) - 1):
        vx -= widths[i]
        bounds.append(vx)
    bounds.append(x_right)
    TABLE_GEOM.append({
        "page": c.getPageNumber(),
        "bounds": [round(b, 2) for b in sorted(bounds)],
        "top": round(y, 2),
        "bottom": round(y - hh - sum(heights), 2),
    })
    # سرستون
    c.setFillColor(NAVY)
    c.rect(x0, y - hh, total, hh, stroke=0, fill=1)
    cx = x_right
    for i, hcell in enumerate(hlines):
        cx -= widths[i]
        base = y - pady - (hdr_size * 1.34) * 0.78
        for k, ln in enumerate(hcell):
            draw_str_center(c, ln, cx + widths[i] / 2.0, base - k * hdr_size * 1.34,
                            "VB", hdr_size, white)
    y -= hh

    for ri, row in enumerate(rows):
        rh = heights[ri]
        if zebra and ri % 2 == 1:
            c.setFillColor(MUTED)
            c.rect(x0, y - rh, total, rh, stroke=0, fill=1)
        cx = x_right
        for i, cell in enumerate(row):
            cx -= widths[i]
            if i in status_cols:
                key = str(cell)
                if key in C.STATUS_LABEL:
                    label = C.STATUS_PILL[key]
                    fs = size - 0.4
                    bw = min(widths[i] - 2 * padx, W(label, "VB", fs) + 11.0)
                    bx = cx + (widths[i] - bw) / 2.0
                    by = y - rh + (rh - 11.5) / 2.0
                    c.setFillColor(HexColor(C.STATUS_COLOR[key]))
                    c.roundRect(bx, by, bw, 11.5, 2.4, stroke=0, fill=1)
                    draw_str_center(c, label, bx + bw / 2.0, by + 3.1, "VB", fs, white)
                    continue
            cl = lines[ri][i]
            base = y - pady - leading * 0.76
            if i in center_cols:
                for k, ln in enumerate(cl):
                    draw_str_center(c, ln, cx + widths[i] / 2.0, base - k * leading,
                                    body_font, size, HexColor("#22303C"))
            else:
                for k, ln in enumerate(cl):
                    draw_str(c, ln, cx + widths[i] - padx, base - k * leading,
                             body_font, size, HexColor("#22303C"))
        # خطوط افقی و عمودی
        # widths به ترتیبِ راست‌به‌چپ است: widths[0] ستونِ اول (راست‌ترین).
        # بنابراین جداکننده‌های عمودی باید با کسرِ پهنای ستون‌ها از راست به چپ
        # و به همان ترتیبِ آرایه (0، 1، 2، ...) به دست آیند.
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(x0, y - rh, x0 + total, y - rh)
        vx = x_right
        for i in range(len(widths) - 1):
            vx -= widths[i]
            c.line(vx, y, vx, y - rh)
        y -= rh
    c.setStrokeColor(STEEL)
    c.setLineWidth(0.7)
    c.rect(x0, y, total, hh + sum(heights), stroke=1, fill=0)
    return y


def note_box(c, x_right, y, text, width=CW, size=7.8, pad=7.0):
    lines = wrap(text, "VR", size, width - 2 * pad - 10)
    lh = size * 1.36
    h = len(lines) * lh + 2 * pad
    c.setFillColor(LIGHT)
    c.rect(x_right - width, y - h, width, h, stroke=0, fill=1)
    # نوار تزئینی کادر یادداشت نیز باید در لبهٔ راست باشد (راست‌چین)
    c.setFillColor(GOLD)
    c.rect(x_right - 3.2, y - h, 3.2, h, stroke=0, fill=1)
    yy = y - pad - lh * 0.76
    for ln in lines:
        draw_str(c, ln, x_right - pad - 3.2, yy, "VR", size, HexColor("#2B3A47"))
        yy -= lh
    return y - h


def multi_col_list(c, x_right, y, items, ncols=2, width=CW, size=7.6, gap=16.0, lh=None):
    """فهرست نشانه‌دار چندستونه (راست‌به‌چپ) با نشانه در ابتدای هر ستون."""
    lh = lh or size * 1.45
    colw = (width - gap * (ncols - 1)) / ncols
    per_col = -(-len(items) // ncols)
    y0 = y
    for ci in range(ncols):
        chunk = items[ci * per_col:(ci + 1) * per_col]
        x_col = x_right - ci * (colw + gap)      # لبهٔ راستِ این ستون
        yy = y0
        for it in chunk:
            draw_str(c, "•", x_col - 1.5, yy, "VB", size, GOLD)
            for ln in wrap(it, "VR", size, colw - 12):
                draw_str(c, ln, x_col - 11.0, yy, "VR", size, HexColor("#22303C"))
                yy -= lh
            yy -= 3.2
    # ارتفاع بلندترین ستون
    heights = []
    for ci in range(ncols):
        chunk = items[ci * per_col:(ci + 1) * per_col]
        h = sum(len(wrap(it, "VR", size, colw - 12)) * lh + 3.2 for it in chunk)
        heights.append(h)
    return y0 - max(heights) + 3.2 if heights else y0


def status_legend(c, x_right, y, width=CW):
    """راهنمای برچسب‌های وضعیت (همان رنگ‌های به‌کاررفته در جدول‌ها)."""
    keys = ["A", "C", "E", "D", "B", "F"]
    gap = 6.0
    n = len(keys)
    item_w = (width - gap * (n - 1)) / n
    x = x_right
    for k in keys:
        label = C.STATUS_PILL[k]
        x0 = x - item_w
        c.setFillColor(HexColor(C.STATUS_COLOR[k]))
        c.roundRect(x0, y - 12.6, item_w, 12.6, 2.2, stroke=0, fill=1)
        draw_str_center(c, label, x0 + item_w / 2.0, y - 9.0, "VB", 6.9, white)
        x -= item_w + gap
    return y - 12.6


def bullets(c, x_right, y, items, size=8.2, lh=12.6, width=CW, color=GOLD):
    for it in items:
        lines = wrap(it, "VR", size, width - 14)
        draw_str(c, "•", x_right - 2, y, "VB", size, color)
        yy = y
        for ln in lines:
            draw_str(c, ln, x_right - 14, yy, "VR", size, HexColor("#22303C"))
            yy -= lh
        y = yy - 2.2
    return y


def measure_bullets(items, size=8.2, lh=12.6, width=CW):
    tot = 0.0
    for it in items:
        tot += len(wrap(it, "VR", size, width - 14)) * lh + 2.2
    return tot


def cards(c, x_right, y, items, width=CW, gap=8.0, h=44.0, vsize=13.0, lsize=7.0, ncols=None):
    ncols = ncols or len(items)
    colw = (width - gap * (ncols - 1)) / ncols
    cx = x_right
    for value, label in items:
        x0 = cx - colw
        c.setFillColor(LIGHT)
        c.roundRect(x0, y - h, colw, h, 3, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(x0, y - h, colw, 2.2, stroke=0, fill=1)
        draw_str_center(c, value, x0 + colw / 2.0, y - 17.5, "VB", vsize, NAVY)
        draw_str_center(c, label, x0 + colw / 2.0, y - 31.0, "VR", lsize, STEEL)
        cx -= colw + gap
    return y - h


# ------------------------------------------------------------------ سربرگ/پاصفحه
def header(c, page_no, total=TOTAL_PAGES):
    c.setFillColor(NAVY)
    c.rect(0, PH - 72, PW, 72, stroke=0, fill=1)
    c.setFillColor(GOLD)
    c.rect(0, PH - 75.4, PW, 3.4, stroke=0, fill=1)
    draw_str(c, C.COMPANY, PW - MX, PH - 27, "VB", 12.2, white)
    draw_str(c, C.UNITS + " — " + C.SUBTITLE, PW - MX, PH - 41.5, "VR", 8.4, HexColor("#C9D6E0"))
    draw_str(c, "مشاور: " + C.CONSULTANT + "    |    دوره: " + C.PERIOD,
             PW - MX, PH - 55.5, "VR", 7.8, HexColor("#AFC0CE"))
    draw_str_left(c, C.PAGE_TITLES[page_no], MX, PH - 27, "VS", 9.0, HexColor("#E7EEF3"))
    draw_str_left(c, "تاریخ تنظیم: " + C.REPORT_DATE, MX, PH - 41.5, "VR", 7.8, HexColor("#AFC0CE"))


def footer(c, page_no, total=TOTAL_PAGES):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MX, 58.0, PW - MX, 58.0)
    draw_str(c, C.TITLE + " — " + C.UNITS + " — " + C.COMPANY,
             PW - MX, 44.0, "VR", 7.4, GREY)
    draw_str_left(c, "صفحه " + fa_num(page_no) + " از " + fa_num(total), MX, 44.0, "VB", 7.4, NAVY)


def page_frame(c, page_no, total=TOTAL_PAGES, title=None):
    header(c, page_no, total)
    footer(c, page_no, total)
    y = TOP
    if title:
        y = section_title(c, PW - MX, y, title)
    return y


# ------------------------------------------------------------------ ساخت صفحات
def page1(c):
    y = page_frame(c, 1, title="بخش یک — نظارت، کنترل کیفیت و اقدامات اصلاحی")
    y = para(c, PW - MX, y, C.INTRO, size=8.8, leading=13.6)
    y -= 4
    y = section_title(c, PW - MX, y, "خلاصه بازدیدها و دستورهای ابلاغی دوره")
    y = table(c, PW - MX, y, C.VISITS_WIDTHS, C.VISITS_HEADER, C.VISITS,
              size=7.4, padx=3.7, pady=3.2, leading=9.9, hdr_size=7.5,
              center_cols=(0, 1))
    y -= 7
    y = cards(c, PW - MX, y, C.CARDS_P1, h=50.0, vsize=13.4, lsize=6.9)
    REPORT.append(("صفحه ۱", y))
    return y


def page2(c):
    y = page_frame(c, 2, title="بخش دو — مدیریت مصرف، آمار عملکرد و کنترل هزینه")
    y = section_title(c, PW - MX, y, "آمار روزانه پخت و توزیع غذا")
    y = table(c, PW - MX, y, C.STATS_WIDTHS, C.STATS_HEADER, C.STATS,
              size=7.0, padx=3.1, pady=1.5, leading=7.8, hdr_size=7.1,
              center_cols=(0, 1, 3, 5))
    y -= 5
    y = section_title(c, PW - MX, y, "سهمیه مصرف به ازای هر نفر")
    y = table(c, PW - MX, y, C.STANDARDS_WIDTHS, C.STANDARDS_HEADER, C.STANDARDS,
              size=7.3, padx=3.3, pady=1.9, leading=8.7, hdr_size=7.3,
              center_cols=())
    y -= 5
    y = section_title(c, PW - MX, y, "اقدامات کنترل مصرف و پیشگیری از هزینه اضافی")
    y = table(c, PW - MX, y, C.COST_WIDTHS, C.COST_HEADER, C.COST,
              size=7.4, padx=3.5, pady=2.1, leading=9.0, hdr_size=7.4,
              center_cols=(2,))
    y -= 8
    y = note_box(c, PW - MX, y, C.COST_NOTE, size=7.5, pad=6.0)
    REPORT.append(("صفحه ۲", y))
    return y


def page3(c):
    y = page_frame(c, 3, title="بخش سه — تعمیرات، تجهیزات و کنترل کیفیت")
    y = section_title(c, PW - MX, y, "اقدامات تعمیراتی و تجهیزاتی انجام‌شده")
    y = table(c, PW - MX, y, C.REPAIRS_WIDTHS, C.REPAIRS_HEADER, C.REPAIRS,
              size=7.8, padx=3.7, pady=3.3, leading=9.9, hdr_size=7.8,
              status_cols=(3,), center_cols=(0, 2))
    y -= 6
    y = section_title(c, PW - MX, y, "موارد عدم انطباق ثبت‌شده در ارزیابی کنترل کیفیت")
    y = table(c, PW - MX, y, C.NC_WIDTHS, C.NC_HEADER, C.NC,
              size=7.8, padx=3.5, pady=3.1, leading=9.7, hdr_size=7.8,
              status_cols=(3,), center_cols=(0, 2))
    y -= 6
    y = section_title(c, PW - MX, y, "خلاصه وضعیت اقدامات")
    y = table(c, PW - MX, y, C.STATUS_SUMMARY_WIDTHS, C.STATUS_SUMMARY_HEADER,
              C.STATUS_SUMMARY, size=7.8, padx=3.7, pady=3.1, leading=9.7,
              hdr_size=7.8, status_cols=(0,), center_cols=(1,))
    y -= 6
    y = section_title(c, PW - MX, y, "راهنمای برچسب‌های وضعیت")
    y = status_legend(c, PW - MX, y)
    y -= 10
    y = section_title(c, PW - MX, y, "اقدامات انجام‌شده در دوره")
    y = multi_col_list(c, PW - MX, y, C.ACHIEVEMENTS, ncols=3, size=7.7,
                       gap=16.0, lh=12.4)
    REPORT.append(("صفحه ۳", y))
    return y


def page4(c):
    y = page_frame(c, 4, title="بخش چهار — چکیده مدیریتی و جمع‌بندی نهایی عملکرد")
    y = para(c, PW - MX, y, C.SUMMARY_TEXT, size=9.2, leading=14.7)
    y -= 10
    y = cards(c, PW - MX, y, C.CARDS_P4, h=54.0, vsize=13.0, lsize=7.0,
              ncols=len(C.CARDS_P4))
    y -= 12
    y = section_title(c, PW - MX, y, "دستاوردهای شاخص دوره")
    y = bullets(c, PW - MX, y, C.ACHIEVEMENTS_SHORT, size=8.7, lh=13.9)
    y -= 7
    y = section_title(c, PW - MX, y, "اولویت‌های آتی")
    y = bullets(c, PW - MX, y, C.PRIORITIES, size=8.7, lh=13.9)
    y -= 8
    y = section_title(c, PW - MX, y, "محدودیت داده و مبنای گزارش")
    y = note_box(c, PW - MX, y, C.DATA_NOTE, size=7.8, pad=6.8)
    y -= 8
    y = section_title(c, PW - MX, y, "جمع‌بندی نهایی")
    y = para(c, PW - MX, y, C.CLOSING, size=8.9, leading=13.8)
    y -= 8
    y = section_title(c, PW - MX, y, "پیوست تصویری گزارش (صفحه‌های ۵ تا ۷)")
    y = appendix_index(c, PW - MX, y)
    REPORT.append(("صفحه ۴", y))
    return y


def appendix_index(c, x_right, y, h=62.0, gap=8.0):
    """سه کارت فهرست پیوست: عنوان، تعداد تصویر و بازهٔ تاریخ ثبت."""
    counts = P.counts()
    ncols = len(P.CATEGORIES)
    colw = (CW - gap * (ncols - 1)) / ncols
    cx = x_right
    for idx in sorted(P.CATEGORIES):
        d1, d2 = P.date_range(idx)
        x0 = cx - colw
        c.setFillColor(LIGHT)
        c.roundRect(x0, y - h, colw, h, 3, stroke=0, fill=1)
        c.setFillColor(GOLD)
        c.rect(x0, y - h, colw, 2.2, stroke=0, fill=1)
        draw_str_center(c, "پیوست " + fa_num(idx) + " — " + C.APPENDIX_TITLES[idx],
                        x0 + colw / 2.0, y - 18.0, "VM", 7.7, NAVY)
        draw_str_center(c, fa_num(counts[idx]) + " تصویر  |  صفحه " + fa_num(4 + idx),
                        x0 + colw / 2.0, y - 34.0, "VR", 7.1, STEEL)
        draw_str_center(c, d1 + " تا " + d2, x0 + colw / 2.0, y - 48.0, "VR", 6.7, GREY)
        cx -= colw + gap
    return y - h


# ------------------------------------------------------------------ پیوست تصویری
def photo_card(c, x0, y_top, box_w, box_h, path, title, date, number):
    """یک قاب تصویر: کادر عکس، نشان شماره، شرح و تاریخ. ارتفاع مصرف‌شده برگردانده می‌شود."""
    iw, ih = ImageReader(path).getSize()
    pad = 2.4
    aw, ah = box_w - 2 * pad, box_h - 2 * pad
    sc = min(aw / float(iw), ah / float(ih))
    w, h = iw * sc, ih * sc
    ix = x0 + (box_w - w) / 2.0
    iy = y_top - pad - (ah - h) / 2.0 - h
    c.setFillColor(HexColor("#E9EDF1"))
    c.rect(x0 + 0.8, y_top - box_h - 0.8, box_w, box_h, stroke=0, fill=1)
    c.drawImage(path, ix, iy, w, h, mask=None)
    c.setStrokeColor(HexColor("#C9D2D9"))
    c.setLineWidth(0.5)
    c.rect(ix, iy, w, h, stroke=1, fill=0)

    # نشان شمارهٔ تصویر (گوشهٔ بالا-راستِ کادر)
    bw = 12.5
    c.setFillColor(NAVY)
    c.roundRect(x0 + box_w - bw - 1.6, y_top - bw - 1.6, bw, bw, 2.2, stroke=0, fill=1)
    draw_str_center(c, fa_num(number), x0 + box_w - bw / 2.0 - 1.6, y_top - bw + 2.9,
                    "VB", 6.4, white)

    # شرح و تاریخ زیر تصویر (همیشه دو سطر برای شرح رزرو می‌شود تا تاریخ‌ها هم‌تراز شوند)
    ty = y_top - box_h - 9.2
    lines = wrap(title, "VM", 6.3, box_w - 2)[:2]
    for k in range(2):
        if k < len(lines):
            draw_str_center(c, lines[k], x0 + box_w / 2.0, ty, "VM", 6.3, HexColor("#22303C"))
        ty -= 7.4
    draw_str_center(c, date, x0 + box_w / 2.0, ty + 1.2, "VR", 5.7, STEEL)
    return box_h + 24.6


def photo_grid(c, x_right, y_top, entries, ncols=None, gap=5.0, max_bottom=BOTTOM,
               reserve_bottom=0.0):
    """چیدمان جدولی تصاویر با وسط‌چین کردن ردیف آخر. بازگشت: y پایانی."""
    n = len(entries)
    if ncols is None:
        rows0 = (n + 5) // 6                 # حداکثر ۶ ستون
        ncols = max(4, -(-n // rows0))       # ستون‌ها را متوازن کن
    rows = (n + ncols - 1) // ncols
    cell_w = (CW - gap * (ncols - 1)) / ncols
    avail = y_top - max_bottom - reserve_bottom - 8.0
    row_h = avail / rows
    box_h = max(46.0, row_h - 26.0)

    y = y_top
    for r in range(rows):
        row = entries[r * ncols:(r + 1) * ncols]
        if not row:
            break
        used = len(row) * cell_w + (len(row) - 1) * gap
        x = x_right - (CW - used) / 2.0
        for number, name, title, date in row:
            x0 = x - cell_w
            path = os.path.join(PHOTO_ASSETS, name)
            photo_card(c, x0, y, cell_w, box_h, path, title, date, number)
            PHOTO_GEOM.append({
                "page": c.getPageNumber(),
                "number": number,
                "x0": round(x0, 2), "x1": round(x0 + cell_w, 2),
                "top": round(y, 2), "bottom": round(y - box_h, 2),
            })
            x -= cell_w + gap
        y -= row_h
    return y


def appendix(c, idx):
    cat = P.CATEGORIES[idx]
    items = P.by_category(idx)
    first = sum(len(P.by_category(k)) for k in range(1, idx)) + 1
    y = page_frame(c, 4 + idx,
                   title="پیوست تصویری {} — {}".format(fa_num(idx), cat["title"]))
    y = para(c, PW - MX, y + 2.0, cat["desc"], size=7.9, leading=11.6,
             color=HexColor("#2B3A47"))
    y -= 2.0
    d1, d2 = P.date_range(idx)
    draw_str(c, "{} تصویر  |  بازهٔ ثبت: {} تا {}".format(
        fa_num(len(items)), d1, d2), PW - MX, y, "VB", 7.2, STEEL)
    y -= 9.0
    entries = [(first + i, it[1], it[2], it[3]) for i, it in enumerate(items)]
    # ستون‌ها متوازن می‌شوند تا ردیف آخر پر و صفحه بدون فضای خالی بماند
    y = photo_grid(c, PW - MX, y, entries, ncols=None, gap=5.0, max_bottom=BOTTOM)
    REPORT.append(("پیوست {}".format(fa_num(idx)), y))


def page5(c):
    appendix(c, 1)


def page6(c):
    appendix(c, 2)


def page7(c):
    appendix(c, 3)


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle(C.TITLE + " — " + C.UNITS + " — " + C.COMPANY)
    c.setAuthor(C.CONSULTANT)
    c.setSubject(C.SUBTITLE + " — " + C.PERIOD)
    c.setCreator(C.COMPANY)
    for fn in (page1, page2, page3, page4, page5, page6, page7):
        fn(c)
        c.showPage()
    c.save()

    with open(OUT + ".tables.json", "w", encoding="utf-8") as fh:
        json.dump(TABLE_GEOM, fh, ensure_ascii=False, indent=1)
    with open(OUT + ".photos.json", "w", encoding="utf-8") as fh:
        json.dump(PHOTO_GEOM, fh, ensure_ascii=False, indent=1)

    print("PDF ساخته شد: " + OUT)
    for name, y in REPORT:
        status = "OK " if y >= BOTTOM else "سرریز!"
        print("  {}: y پایانی = {:7.1f} pt | محدوده مجاز تا {:7.1f} | {}".format(
            name, y, BOTTOM, status))


if __name__ == "__main__":
    main()
