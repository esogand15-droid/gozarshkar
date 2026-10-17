# -*- coding: utf-8 -*-
"""ساخت گزارش نهایی (۴ صفحه A4، راست‌به‌چپ) با قلم Vazirmatn.

اجرا:
    python3 build_report.py            # ساخت PDF
    python3 build_report.py --draft    # گزارش اندازه‌گیری و فضای باقی‌مانده هر صفحه
"""
import os
import sys

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import report_content as C

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
    c.setFillColor(GOLD)
    c.rect(x_right - width, y - 9.0, 3.2, 11.5, stroke=0, fill=1)
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
                    label = C.STATUS_SHORT[key]
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
        c.setStrokeColor(LINE)
        c.setLineWidth(0.4)
        c.line(x0, y - rh, x0 + total, y - rh)
        vx = x_right
        for i in range(len(widths) - 1, 0, -1):
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
    c.setFillColor(GOLD)
    c.rect(x_right - width, y - h, 3.2, h, stroke=0, fill=1)
    yy = y - pad - lh * 0.76
    for ln in lines:
        draw_str(c, ln, x_right - pad, yy, "VR", size, HexColor("#2B3A47"))
        yy -= lh
    return y - h


def two_col_list(c, x_right, y, items, width=CW, size=7.4, gap=16.0, lh=None):
    lh = lh or size * 1.42
    colw = (width - gap) / 2.0
    n = (len(items) + 1) // 2
    rows = []
    for i in range(n):
        left = items[i]
        right = items[i + n] if i + n < len(items) else ""
        wrapped_l = wrap(left, "VR", size, colw - 13)
        wrapped_r = wrap(right, "VR", size, colw - 13) if right else []
        rows.append((items[i], wrapped_l, items[i + n] if i + n < len(items) else None, wrapped_r))
    for idx, wl, _, wr in rows:
        draw_str(c, "•", x_right - 2, y, "VB", size, GOLD)
        yy = y
        for k, ln in enumerate(wl):
            draw_str(c, ln, x_right - 13, yy, "VR", size, HexColor("#22303C"))
            yy -= lh
        yy2 = y
        for k, ln in enumerate(wr):
            draw_str(c, ln, x_right - width + colw + gap - 13, yy2, "VR", size, HexColor("#22303C"))
            yy2 -= lh
        y -= max(len(wl), len(wr)) * lh + 2.4
    return y


def measure_two_col_list(items, width=CW, size=7.4, gap=16.0, lh=None):
    lh = lh or size * 1.42
    colw = (width - gap) / 2.0
    n = (len(items) + 1) // 2
    tot = 0.0
    for i in range(n):
        wl = len(wrap(items[i], "VR", size, colw - 13))
        wr = len(wrap(items[i + n], "VR", size, colw - 13)) if i + n < len(items) else 0
        tot += max(wl, wr) * lh + 2.4
    return tot


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
def header(c, page_no, total=4):
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


def footer(c, page_no, total=4):
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MX, 58.0, PW - MX, 58.0)
    draw_str(c, C.TITLE + " — " + C.UNITS + " — " + C.COMPANY,
             PW - MX, 44.0, "VR", 7.4, GREY)
    draw_str_left(c, "صفحه " + fa_num(page_no) + " از " + fa_num(total), MX, 44.0, "VB", 7.4, NAVY)


def page_frame(c, page_no, total=4, title=None):
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
              size=7.3, padx=3.6, pady=2.9, leading=9.6, hdr_size=7.5,
              center_cols=(0, 1))
    y -= 7
    y = cards(c, PW - MX, y, C.CARDS_P1, h=44.0, vsize=13.0, lsize=6.9)
    REPORT.append(("صفحه ۱", y))
    return y


def page2(c):
    y = page_frame(c, 2, title="بخش دو — مدیریت مصرف، آمار عملکرد و کنترل هزینه")
    y = section_title(c, PW - MX, y, "آمار روزانه پخت و توزیع غذا")
    y = table(c, PW - MX, y, C.STATS_WIDTHS, C.STATS_HEADER, C.STATS,
              size=7.0, padx=3.0, pady=1.4, leading=7.6, hdr_size=7.1,
              center_cols=(0, 1, 3, 5))
    y -= 5
    y = section_title(c, PW - MX, y, "سهمیه مصرف به ازای هر نفر")
    y = table(c, PW - MX, y, C.STANDARDS_WIDTHS, C.STANDARDS_HEADER, C.STANDARDS,
              size=7.0, padx=3.2, pady=1.7, leading=8.5, hdr_size=7.1,
              center_cols=())
    y -= 5
    y = section_title(c, PW - MX, y, "اقدامات کنترل مصرف و پیشگیری از هزینه اضافی")
    y = table(c, PW - MX, y, C.COST_WIDTHS, C.COST_HEADER, C.COST,
              size=7.2, padx=3.4, pady=1.9, leading=8.6, hdr_size=7.2,
              center_cols=(2,))
    y -= 5
    y = note_box(c, PW - MX, y, C.COST_NOTE, size=7.0, pad=5.5)
    REPORT.append(("صفحه ۲", y))
    return y


def page3(c):
    y = page_frame(c, 3, title="بخش سه — قراردادها، تعمیرات و خلاصه وضعیت اقدامات")
    y = section_title(c, PW - MX, y, "قرارداد خرید خدمات سپتیک و فاضلاب")
    y = table(c, PW - MX, y, C.CONTRACT_WIDTHS, C.CONTRACT_HEADER, C.CONTRACT,
              size=7.0, padx=3.4, pady=2.1, leading=8.5, hdr_size=7.2)
    y -= 5
    y = note_box(c, PW - MX, y, C.CONTRACT_NOTE, size=7.0, pad=5.5)
    y -= 5
    y = section_title(c, PW - MX, y, "اقدامات تعمیراتی و تجهیزاتی")
    y = table(c, PW - MX, y, C.REPAIRS_WIDTHS, C.REPAIRS_HEADER, C.REPAIRS,
              size=7.2, padx=3.4, pady=2.2, leading=8.8, hdr_size=7.3,
              status_cols=(3,), center_cols=(0, 2))
    y -= 5
    y = section_title(c, PW - MX, y, "موارد عدم انطباق ثبت‌شده در ارزیابی کنترل کیفیت")
    y = table(c, PW - MX, y, C.NC_WIDTHS, C.NC_HEADER, C.NC,
              size=7.1, padx=3.2, pady=2.0, leading=8.6, hdr_size=7.2,
              status_cols=(3,), center_cols=(0, 2))
    y -= 5
    y = section_title(c, PW - MX, y, "خلاصه وضعیت اقدامات")
    y = table(c, PW - MX, y, C.STATUS_SUMMARY_WIDTHS, C.STATUS_SUMMARY_HEADER,
              C.STATUS_SUMMARY, size=7.2, padx=3.4, pady=2.2, leading=8.8,
              hdr_size=7.3, status_cols=(0,), center_cols=(1,))
    REPORT.append(("صفحه ۳", y))
    return y


def page4(c):
    y = page_frame(c, 4, title="بخش چهار — چکیده مدیریتی و جمع‌بندی نهایی عملکرد")
    y = para(c, PW - MX, y, C.SUMMARY_TEXT, size=9.0, leading=13.9)
    y -= 10
    y = cards(c, PW - MX, y, C.CARDS_P4[:3], h=47.0, vsize=12.2, lsize=6.8, ncols=3)
    y -= 6
    y = cards(c, PW - MX, y, C.CARDS_P4[3:], h=47.0, vsize=12.2, lsize=6.8, ncols=3)
    y -= 10
    y = section_title(c, PW - MX, y, "دستاوردهای شاخص دوره")
    y = bullets(c, PW - MX, y, C.ACHIEVEMENTS_SHORT, size=8.4, lh=12.9)
    y -= 6
    y = section_title(c, PW - MX, y, "الزامات ایمنی، بهداشت و محیط زیست ابلاغی به پیمانکار")
    y = note_box(c, PW - MX, y, C.HSE_NOTE, size=7.8, pad=7.0)
    y -= 8
    y = section_title(c, PW - MX, y, "اولویت‌های آتی")
    y = bullets(c, PW - MX, y, C.PRIORITIES, size=8.4, lh=12.9)
    y -= 6
    y = section_title(c, PW - MX, y, "جمع‌بندی نهایی")
    y = para(c, PW - MX, y, C.CLOSING, size=8.8, leading=13.6)
    REPORT.append(("صفحه ۴", y))
    return y


def main():
    c = canvas.Canvas(OUT, pagesize=A4)
    c.setTitle(C.TITLE + " — " + C.UNITS + " — " + C.COMPANY)
    c.setAuthor(C.CONSULTANT)
    c.setSubject(C.SUBTITLE + " — " + C.PERIOD)
    c.setCreator(C.COMPANY)
    for fn in (page1, page2, page3, page4):
        fn(c)
        c.showPage()
    c.save()

    print("PDF ساخته شد: " + OUT)
    for name, y in REPORT:
        status = "OK " if y >= BOTTOM else "سرریز!"
        print("  {}: y پایانی = {:7.1f} pt | محدوده مجاز تا {:7.1f} | {}".format(
            name, y, BOTTOM, status))


if __name__ == "__main__":
    main()
