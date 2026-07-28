#!/usr/bin/env python3
"""HYBRID DDQN-ALNS — presentation deck. Chronographic Cartography."""
import cairo, math, random, os
from deckkit import *

OUT = os.path.dirname(os.path.abspath(__file__))

XL = M + 54          # 122  content left
XR = W - M - 54      # 1478 content right
IW = XR - XL         # 1356


# ═══════════════════════════════════════════════════════════════════════════
# shared apparatus
# ═══════════════════════════════════════════════════════════════════════════
def header(c, eb, vn, en, size=44):
    eyebrow(c, XL, 158, eb)
    heading(c, XL, 214, vn, size, INK, 0.6)
    txt(c, XL, 244, en, BODY, 14.5, SLATE, sl="i")
    line(c, XL, 276, XR, 276, HAIR, 0.9)


def verdict(c, bottom, vn_lines, en_lines, hcol=INK, tagcol=VERM,
            tag=None, right=None, size=30):
    """Bottom-anchored statement band. Never clips."""
    lv, le = size * 1.16, 19.0
    hh = 30 + (34 if tag else 0) + lv * len(vn_lines) \
         + ((14 + le * len(en_lines)) if en_lines else 0) + 20
    y = bottom - hh
    rect(c, XL, y, IW, hh, PARCH_D, fill=True, alpha=0.66)
    rect(c, XL, y, IW, hh, hcol, lw=1.1)
    rect(c, XL, y, 5, hh, tagcol, fill=True)
    yy = y + 30
    if tag:
        txt(c, XL + 32, yy, tag, MONO, 9.5, tagcol, track=2.6)
        yy += 34
    for i, ln in enumerate(vn_lines):
        txt(c, XL + 32, yy + lv * (i + 0.78), ln, DISP, size, INK, w="b", track=0.5)
    yy += lv * len(vn_lines) + 14
    for i, ln in enumerate(en_lines):
        txt(c, XL + 32, yy + le * (i + 0.72), ln, BODY, 12.6, SLATE, sl="i")
    if right:
        txt(c, XR - 32, y + hh / 2 + 5, right, MONO, 13.5, tagcol,
            track=1.2, align="r")
    return y


def routing_chart(c, cx, cy, R, seed=11, alpha=1.0, n_nodes=22, labels=True):
    rnd = random.Random(seed)
    for i, r in enumerate([R * 0.34, R * 0.58, R * 0.82, R * 1.0]):
        arc(c, cx, cy, r, 0, 360, HAIR, 0.7, alpha * 0.9,
            dash=[1.6, 4.4] if i % 2 else None)
    line(c, cx - R * 1.1, cy, cx + R * 1.1, cy, HAIR, 0.6, alpha * 0.7)
    line(c, cx, cy - R * 1.1, cx, cy + R * 1.1, HAIR, 0.6, alpha * 0.7)
    for a in range(0, 360, 15):
        rr = R * (1.06 if a % 45 == 0 else 1.02)
        line(c, cx + math.cos(math.radians(a)) * R,
             cy + math.sin(math.radians(a)) * R,
             cx + math.cos(math.radians(a)) * rr,
             cy + math.sin(math.radians(a)) * rr, HAIR, 0.7, alpha)

    cols = [INK_S, SLATE, VERM]
    spans = [(96, 214), (222, 336), (344, 448)]
    for k in range(3):
        a0, a1 = spans[k]
        m = 5
        pts = [(cx, cy)]
        for j in range(m):
            a = math.radians(a0 + (a1 - a0) * (j + 0.5) / m + rnd.uniform(-7, 7))
            rr = R * (0.42 + 0.5 * math.sin(math.pi * (j + 0.5) / m)) * rnd.uniform(0.9, 1.06)
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        pts.append((cx, cy))
        smooth(c, pts, cols[k], 1.2 if k == 2 else 0.95, alpha * 0.92, t=0.22)
        for p in pts[1:-1]:
            circ(c, p[0], p[1], 3.4, PARCH, fill=True, alpha=alpha)
            circ(c, p[0], p[1], 3.4, cols[k], 0.95, alpha=alpha)

    for _ in range(n_nodes):
        a = rnd.uniform(0, 2 * math.pi)
        rr = R * math.sqrt(rnd.uniform(0.06, 0.98))
        circ(c, cx + math.cos(a) * rr, cy + math.sin(a) * rr, 1.5,
             SLATE_L, fill=True, alpha=alpha * 0.6)

    rect(c, cx - 5.5, cy - 5.5, 11, 11, PARCH, fill=True, alpha=alpha)
    rect(c, cx - 5.5, cy - 5.5, 11, 11, INK, lw=1.5, alpha=alpha)
    rect(c, cx - 2, cy - 2, 4, 4, INK, fill=True, alpha=alpha)
    if labels:
        line(c, cx + 8, cy - 8, cx + 26, cy - 26, HAIR, 0.7, alpha)
        txt(c, cx + 30, cy - 26, "KHO / DEPOT", MONO, 7.5, SLATE, track=1.6,
            alpha=alpha)


def module(c, x, y, w, h, no, name, io1, io2, col=INK, accent=None):
    rect(c, x, y, w, h, PARCH, fill=True)
    rect(c, x, y, w, h, HAIR, lw=0.8)
    rect(c, x, y, 3, h, accent or col, fill=True)
    txt(c, x + 16, y + 22, no, MONO, 7.5, SLATE_L, track=1.8)
    txt(c, x + 16, y + 42, name, BODY, 14.2, INK, w="b")
    txt(c, x + 16, y + 62, io1, MONO, 8.6, SLATE, track=0.9)
    txt(c, x + 16, y + 76, io2, MONO, 8.6, SLATE, track=0.9)


def chip(c, x, y, w, h, no, vn, en, col=INK):
    rect(c, x, y, w, h, PARCH, fill=True)
    rect(c, x, y, w, h, HAIR, lw=0.8)
    txt(c, x + 12, y + 20, no, MONO, 8, col, track=1.6)
    txt(c, x + 12, y + 40, vn, BODY, 13.4, INK, w="b")
    txt(c, x + 12, y + 57, en, MONO, 7.6, SLATE_L, track=1.2)


def hbar(c, x, y, w, frac, col, h=15.0, ghost=True):
    if ghost:
        rect(c, x, y, w, h, PARCH_D, fill=True, alpha=0.8)
        rect(c, x, y, w, h, HAIR, lw=0.6)
    rect(c, x, y, max(w * frac, 1.2), h, col, fill=True)


# ═══════════════════════════════════════════════════════════════════════════
# 01 — TITLE
# ═══════════════════════════════════════════════════════════════════════════
def page_title(c):
    ground(c, seed=3)
    frame(c, folio="PL. I", cat="TDTU · FACULTY OF INFORMATION TECHNOLOGY")

    routing_chart(c, 1178, 442, 208, seed=29)
    tickfield(c, 964, 712, 428, 40, 4, HAIR, 0.7, every=5, hl=8)
    txt(c, 964, 730, "0", MONO, 7.5, SLATE_L, track=1.4)
    txt(c, 1178, 730, "TRƯỜNG TOẠ ĐỘ  ·  n = 100 … 1000", MONO, 7.5,
        SLATE_L, track=1.6, align="c")
    txt(c, 1392, 730, "1", MONO, 7.5, SLATE_L, track=1.4, align="r")

    x = XL
    eyebrow(c, x, 206, "NGHIÊN CỨU KHOA HỌC SINH VIÊN — 2026")

    for i, ln in enumerate(["TỐI ƯU ĐỊNH TUYẾN", "VẬN TẢI CÓ", "KHUNG THỜI GIAN"]):
        heading(c, x, 320 + i * 86, ln, 74, INK, track=0.5)

    line(c, x, 528, x + 470, 528, HAIR, 0.9)
    txt(c, x, 558, "Optimizing Operator Selection in ALNS", BODY, 15.5, SLATE, sl="i")
    txt(c, x, 581, "using Double DQN for the VRPTW", BODY, 15.5, SLATE, sl="i")
    label_box(c, x, 638, "HYBRID  DDQN – ALNS", VERM, pad=9, size=11, track=3.2)

    yb = 716
    line(c, x, yb - 26, x + 470, yb - 26, HAIR, 0.7)
    kicker(c, x, yb, "SINH VIÊN THỰC HIỆN / AUTHORS", SLATE_L, 8.0, 1.9)
    para(c, x, yb + 22, ["Nguyễn Thị Bảo Trân · Huỳnh Nhật Huy",
                         "Nguyễn Nhật Huy"], 14, 21, INK_S)
    kicker(c, x + 336, yb, "GVHD / ADVISOR", SLATE_L, 8.0, 1.9)
    txt(c, x + 336, yb + 22, "TS. Hồ Thị Linh", BODY, 14, INK_S)

    footer(c, "CHRONOGRAPHIC CARTOGRAPHY  ·  PLATE 01 OF 11",
           "TON DUC THANG UNIVERSITY  ·  HO CHI MINH CITY")


# ═══════════════════════════════════════════════════════════════════════════
# 02 — BIG PICTURE
# ═══════════════════════════════════════════════════════════════════════════
def page_bigpicture(c):
    ground(c, seed=11)
    frame(c, folio="PL. II", cat="02  ·  BỨC TRANH LỚN / THE BIG PICTURE")
    header(c, "DÀNH CHO MỌI NGƯỜI / IN PLAIN TERMS",
           "MỘT ĐỘI XE. MỘT NGÀY. HÀNG NGHÌN LỜI HỨA.",
           "One fleet, one day, a thousand promises to keep.", 46)

    colw, gap = 412, 60
    xs = [XL, XL + colw + gap, XL + 2 * (colw + gap)]
    yt = 316

    blocks = [
        ("01", "VẤN ĐỀ", "THE PROBLEM", VERM,
         ["Một kho hàng phải giao cho hàng trăm",
          "khách. Mỗi khách chỉ nhận hàng trong",
          "một khung giờ hẹp. Cần bao nhiêu xe,",
          "và mỗi xe đi theo lộ trình nào?"],
         ["Hundreds of customers, each with a narrow delivery",
          "window. How many vehicles — and in what order?"]),
        ("02", "ĐÓNG GÓP", "OUR CONTRIBUTION", INK,
         ["Thuật toán cũ chọn nước đi bằng “bốc",
          "thăm có trọng số”. Chúng tôi thay bằng",
          "một tác nhân học tăng cường, biết chọn",
          "nước đi theo tình huống đang gặp."],
         ["We replace ALNS's roulette-wheel operator choice",
          "with a hierarchical Double-DQN agent."]),
        ("03", "KẾT QUẢ", "THE RESULT", TEAL,
         ["Trên bộ chuẩn Solomon, số xe dư so với",
          "mức tối ưu chỉ còn 0.089 — bằng 1/6 của",
          "Google OR-Tools. Khi cùng số xe, độ lệch",
          "quãng đường giảm 65%."],
         ["Vehicle inflation 0.089 vs 0.536 for OR-Tools; at",
          "matched fleet size, 65% lower distance gap."]),
    ]

    for i, (no, vn, en, col, lines, eng) in enumerate(blocks):
        bx = xs[i]
        line(c, bx, yt - 22, bx + colw, yt - 22, col, 1.9)
        txt(c, bx, yt + 46, no, DISP, 66, col, w="b", track=-0.5)
        txt(c, bx + 76, yt + 22, vn, DISP, 30, INK, w="b", track=0.6)
        txt(c, bx + 76, yt + 44, en, MONO, 8.5, SLATE_L, track=2.0)
        para(c, bx, yt + 96, lines, 15.2, 23.5, INK_S)
        line(c, bx, yt + 178, bx + colw * 0.4, yt + 178, HAIR, 0.7)
        para(c, bx, yt + 198, eng, 11.6, 16, SLATE_L, sl="i")

    # measurement strip: the six-fold difference, drawn
    line(c, XL, 554, XR, 554, HAIR, 0.9)
    sy = 576
    txt(c, XL, sy, "SỐ XE DƯ SO VỚI TỐI ƯU  ·  VEHICLE INFLATION ABOVE OPTIMUM",
        MONO, 8.2, SLATE_L, track=2.0)
    bw = 560
    rows = [("GOOGLE OR-TOOLS", 0.536, SLATE), ("ALNS CỔ ĐIỂN", 0.258, INK_S),
            ("HYBRID DDQN-ALNS", 0.089, VERM)]
    for i, (nm, v, col) in enumerate(rows):
        yy = sy + 14 + i * 25
        txt(c, XL, yy + 11, nm, MONO, 9, INK_S if col is not VERM else VERM,
            track=1.6)
        hbar(c, XL + 220, yy, bw, v / 0.60, col, 13)
        txt(c, XL + 220 + bw + 14, yy + 11, f"+{v:.3f}", MONO, 11,
            col if col is VERM else INK_S, track=1.0)
    fx = XL + 220 + bw + 108
    line(c, fx - 24, sy + 6, fx - 24, sy + 82, HAIR, 0.8)
    txt(c, fx, sy + 52, "1/6", DISP, 50, VERM, w="b")
    txt(c, fx + 80, sy + 36, "SỐ XE DƯ CỦA CHÚNG TÔI", MONO, 7.8, SLATE_L, track=1.7)
    txt(c, fx + 80, sy + 52, "SO VỚI GOOGLE OR-TOOLS", MONO, 7.8, SLATE_L, track=1.7)
    txt(c, fx + 80, sy + 72, "one sixth the inflation", BODY, 10.6, SLATE_L, sl="i")

    verdict(c, 804, ["MỘT XE CẮT ĐƯỢC = HÀNG CHỤC TRIỆU ĐỒNG TIẾT KIỆM MỖI THÁNG"],
            ["Fleet size is minimised first, distance second — the lexicographic order real logistics economics demands."],
            right="min ( NV » TD )", size=29)

    footer(c, "PLATE 02  ·  BỨC TRANH LỚN", "45 GIÂY / 45 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 03 — PROBLEM & CONSTRAINTS
# ═══════════════════════════════════════════════════════════════════════════
def page_problem(c):
    ground(c, seed=17)
    frame(c, folio="PL. III", cat="03  ·  BÀI TOÁN & RÀNG BUỘC / PROBLEM & CONSTRAINTS")
    header(c, "ĐỊNH NGHĨA BÀI TOÁN / FORMAL STATEMENT",
           "BA RÀNG BUỘC CỨNG, MỘT THỨ TỰ ƯU TIÊN",
           "Three hard constraints and one strict priority order.")

    # ── left column : formal object
    x = XL
    txt(c, x, 326, "G = ( V , A )", MONO, 21, INK, track=1.8)
    txt(c, x, 352, "V = { 0 }  U  N ,   | N | = n", MONO, 11.5, SLATE, track=0.8)
    para(c, x, 392, ["Đỉnh 0 là kho tổng. Mỗi khách hàng i có",
                     "nhu cầu q_i , thời gian phục vụ s_i và một",
                     "khung giờ [ e_i , l_i ]. Đội xe đồng nhất,",
                     "tải trọng Q."], 14.6, 23, INK_S)
    txt(c, x, 500, "Vertex 0 is the depot; every customer carries a demand,", BODY,
        11.4, SLATE_L, sl="i")
    txt(c, x, 516, "a service time and a hard window. Homogeneous fleet.", BODY,
        11.4, SLATE_L, sl="i")

    # small schematic: one route, one window bar
    line(c, x, 552, x + 400, 552, HAIR, 0.7)
    txt(c, x, 578, "MINH HOẠ MỘT KHUNG GIỜ / ONE WINDOW", MONO, 8, SLATE_L, track=1.9)
    ay, aw = 616, 400
    line(c, x, ay, x + aw, ay, SLATE_L, 0.9)
    for i in range(9):
        line(c, x + aw * i / 8, ay, x + aw * i / 8, ay - 5, HAIR, 0.7)
    rect(c, x + aw * 0.32, ay - 21, aw * 0.30, 21, TEAL_L, fill=True, alpha=0.5)
    rect(c, x + aw * 0.32, ay - 21, aw * 0.30, 21, TEAL, lw=0.9)
    txt(c, x + aw * 0.32, ay - 28, "e_i", MONO, 9, TEAL, track=1.0)
    txt(c, x + aw * 0.62, ay - 28, "l_i", MONO, 9, TEAL, track=1.0, align="r")
    txt(c, x + aw * 0.47, ay + 16, "ĐƯỢC PHÉP GIAO", MONO, 8, TEAL, track=1.6, align="c")
    circ(c, x + aw * 0.47, ay, 4.2, PARCH, fill=True)
    circ(c, x + aw * 0.47, ay, 4.2, TEAL, 1.2)
    txt(c, x + aw * 0.12, ay + 16, "ĐẾN SỚM → CHỜ", MONO, 8, SLATE, track=1.4, align="c")
    txt(c, x + aw * 0.83, ay + 16, "ĐẾN MUỘN → MẤT ĐƠN", MONO, 8, VERM, track=1.4, align="c")

    # capacity schematic
    line(c, x, 662, x + 400, 662, HAIR, 0.7)
    txt(c, x, 688, "MINH HOẠ TẢI TRỌNG MỘT TUYẾN / ONE ROUTE LOAD", MONO, 8,
        SLATE_L, track=1.9)
    ly2, seg = 706, 400 / 12.0
    for i in range(12):
        filled = i < 8
        rect(c, x + i * seg + 1, ly2, seg - 2, 22,
             INK_S if filled else PARCH_D, fill=True, alpha=1.0 if filled else 0.9)
        if not filled:
            rect(c, x + i * seg + 1, ly2, seg - 2, 22, HAIR, lw=0.6)
    line(c, x + 400, ly2 - 8, x + 400, ly2 + 30, VERM, 1.6)
    txt(c, x + 400, ly2 - 14, "Q", MONO, 10, VERM, track=1.0, align="c")
    txt(c, x, ly2 + 42, "sum d_i", MONO, 9, INK_S, track=1.0)
    txt(c, x + 400, ly2 + 42, "còn chỗ / slack", MONO, 8, SLATE_L, track=1.4,
        align="r")

    # ── right column : three constraint cards
    cx0, cw, chh = XL + 470, IW - 470, 118
    cards = [
        ("C1", "KHUNG THỜI GIAN", "TIME WINDOW", "e_i  <=  t_i  <=  l_i",
         "Đến sớm phải chờ; đến muộn là mất đơn.", VERM),
        ("C2", "SỨC CHỨA XE", "CAPACITY", "sum d_i  <=  Q",
         "Tổng hàng trên một tuyến không vượt tải trọng.", INK_S),
        ("C3", "GIỜ ĐÓNG KHO", "DEPOT CLOSING", "t_cuối + s + dist  <=  l₀",
         "Mọi tuyến phải kết thúc trước khi kho đóng cửa.", INK_S),
    ]
    for i, (tag, vn, en, f, d, col) in enumerate(cards):
        by = 312 + i * (chh + 18)
        rect(c, cx0, by, cw, chh, PARCH_D, fill=True, alpha=0.5)
        rect(c, cx0, by, cw, chh, HAIR, lw=0.8)
        rect(c, cx0, by, 3, chh, col, fill=True)
        txt(c, cx0 + 22, by + 26, tag, MONO, 8.6, SLATE_L, track=2.2)
        txt(c, cx0 + 22, by + 58, vn, DISP, 30, INK, w="b", track=0.6)
        txt(c, cx0 + 22, by + 78, en, MONO, 8.2, SLATE_L, track=2.0)
        txt(c, cx0 + 22, by + 104, d, BODY, 13, INK_S)
        fw = tw(c, f, MONO, 14, track=1.0)
        rect(c, cx0 + cw - fw - 48, by + 40, fw + 26, 34, PARCH, fill=True)
        rect(c, cx0 + cw - fw - 48, by + 40, fw + 26, 34, INK_S, lw=0.8)
        txt(c, cx0 + cw - fw - 35, by + 62, f, MONO, 14, INK, track=1.0)

    # ── objective
    oy = 726
    rect(c, cx0, oy, cw, 78, INK, fill=True)
    txt(c, cx0 + 24, oy + 26, "HÀM MỤC TIÊU / OBJECTIVE — LEXICOGRAPHIC", MONO,
        8.6, VERM_L, track=2.4)
    txt(c, cx0 + 24, oy + 62, "min ( NV  »  TD )", MONO, 25, PARCH, track=1.4)
    txt(c, cx0 + 330, oy + 40, "1.  SỐ XE  ( NV )   — chi phí cố định", MONO, 10,
        VERM_L, track=1.4)
    txt(c, cx0 + 330, oy + 62, "2.  QUÃNG ĐƯỜNG  ( TD )   — chi phí biến đổi",
        MONO, 10, TEAL_L, track=1.4)

    footer(c, "PLATE 03  ·  BÀI TOÁN & RÀNG BUỘC", "35 GIÂY / 35 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 04 — RESEARCH GAP
# ═══════════════════════════════════════════════════════════════════════════
def page_gap(c):
    ground(c, seed=23)
    frame(c, folio="PL. IV", cat="04  ·  KHOẢNG TRỐNG NGHIÊN CỨU / RESEARCH GAP")
    header(c, "TỔNG QUAN / RELATED WORK", "HAI HƯỚNG TIẾP CẬN, HAI ĐIỂM MÙ",
           "Two established families, two blind spots.")

    colw, gap = 640, 76
    xs = [XL, XL + colw + gap]
    data = [
        ("A", "ALNS CỔ ĐIỂN", "Classical metaheuristic  ·  Ropke & Pisinger, 2006",
         ["Chọn toán tử phá huỷ / khôi phục bằng bánh xe roulette,",
          "trọng số cập nhật theo hiệu suất gần đây."],
         "Đảm bảo khả thi cứng; mọi nước đi đều có tên, dễ kiểm toán.",
         ["Cận thị — không đọc trạng thái tìm kiếm hiện tại.",
          "Mắc bẫy plateau khi giảm số xe đòi hỏi tạm xấu đi.",
          "Nhiệt độ SA đặt toàn cục, không theo từng pha."]),
        ("B", "MẠNG NƠ-RON ĐẦU-CUỐI", "End-to-end neural  ·  Pointer Nets, Attention Models",
         ["Sinh lộ trình trực tiếp từ policy học được, tối ưu một",
          "hàm mục tiêu có trọng số."],
         "Suy luận cực nhanh; học được cấu trúc chung của bài toán.",
         ["Không cưỡng chế thứ tự từ điển NV » TD.",
          "Khó giữ khả thi cứng dưới khung giờ khắt khe.",
          "Hộp đen — điều phối viên không thể kiểm tra, ghi đè."]),
    ]

    for i, (tag, vn, en, desc, pro, cons) in enumerate(data):
        bx = xs[i]
        line(c, bx, 306, bx + colw, 306, INK, 1.9)
        txt(c, bx, 354, tag, DISP, 48, SLATE_L, w="b")
        txt(c, bx + 50, 346, vn, DISP, 32, INK, w="b", track=0.6)
        txt(c, bx + 50, 368, en, MONO, 8.2, SLATE_L, track=1.7)
        para(c, bx, 408, desc, 14.2, 21, INK_S)
        line(c, bx, 448, bx + colw, 448, HAIR, 0.7)
        circ(c, bx + 4, 470, 4, TEAL, fill=True)
        txt(c, bx + 22, 474, pro, BODY, 13.2, INK_S)
        for j, cn in enumerate(cons):
            yy = 504 + j * 26
            line(c, bx, yy - 4, bx + 8, yy - 4, VERM, 1.8)
            txt(c, bx + 22, yy, cn, BODY, 13.2, INK_S)

    # bridge rule between the two blind spots
    my = 604
    line(c, XL, my, XR, my, HAIR, 0.7)
    for i in range(0, 46):
        tx = XL + IW * i / 45
        line(c, tx, my, tx, my - (8 if i % 5 == 0 else 4), HAIR, 0.7)
    txt(c, XL, my + 19, "KHẢ THI CỨNG + KIỂM TOÁN ĐƯỢC", MONO, 8, SLATE_L, track=1.8)
    txt(c, XR, my + 19, "THÍCH ỨNG + HỌC ĐƯỢC", MONO, 8, SLATE_L, track=1.8, align="r")
    circ(c, XL + IW / 2, my, 6.5, PARCH, fill=True)
    circ(c, XL + IW / 2, my, 6.5, VERM, 1.6)
    txt(c, XL + IW / 2, my + 21, "CHÚNG TÔI Ở ĐÂY", MONO, 8.4, VERM, track=1.9,
        align="c")

    verdict(c, 804, ["NHÚNG POLICY HỌC ĐƯỢC VÀO TRONG VÒNG LẶP ALNS, KHÔNG THAY THẾ NÓ."],
            ["Embed the learned policy inside ALNS rather than replacing it: keep hard feasibility and named, auditable operators, gain a",
             "state-conditioned selection policy. Every move remains a destroy/repair operator a dispatcher can inspect and override."],
            tag="KHOẢNG TRỐNG / THE GAP", size=31)

    footer(c, "PLATE 04  ·  KHOẢNG TRỐNG NGHIÊN CỨU", "25 GIÂY / 25 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 05 — ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════
def page_arch(c):
    ground(c, seed=31)
    frame(c, folio="PL. V", cat="05  ·  KIẾN TRÚC / ARCHITECTURE")
    header(c, "PHƯƠNG PHÁP ĐỀ XUẤT / PROPOSED METHOD",
           "BA KHỐI, MỘT VÒNG LẶP KHÉP KÍN",
           "Three blocks, one closed loop: decide, search, learn.")

    pg = 96
    pw = (IW - 2 * pg) / 3
    xs = [XL, XL + pw + pg, XL + 2 * (pw + pg)]
    py, ph = 320, 386

    panels = [
        ("BỘ NÃO QUYẾT ĐỊNH", "DECISION BRAIN", "DRL CONTROL", VERM,
         [("01", "Stagnation Monitor", "In   success, NV", "Out  no_imp, trigger"),
          ("02", "Plateau Controller", "In   state s_c in R¹²", "Out  mode m, (d,r)"),
          ("03", "Operator Controller", "In   state s_o, goal", "Out  action a = (d,r)")]),
        ("CƠ BẮP TÌM KIẾM", "SEARCH MUSCLE", "ALNS + MIP", INK,
         [("04", "ALNS Core Engine", "In   action (d,r), x_t", "Out  candidate x'"),
          ("05", "Learned Accept (LAC)", "In   delta-c, T_t in R⁹", "Out  accept bit b_t"),
          ("06", "MIP Recombination", "In   accepted x', columns", "Out  incumbent x*")]),
        ("VÒNG HỌC", "LEARNING LOOP", "FEEDBACK", TEAL,
         [("07", "Route Pool", "In   valid routes", "Out  columns for MIP"),
          ("08", "Replay Buffer (PER)", "In   (s, a, r, s')", "Out  training batches"),
          ("09", "Welford Normalizer", "In   raw reward r_t", "Out  z_t in [-8, 8]")]),
    ]

    for i, (vn, en, tag, col, mods) in enumerate(panels):
        bx = xs[i]
        rect(c, bx, py, pw, ph, PARCH_D, fill=True, alpha=0.42)
        rect(c, bx, py, pw, ph, col, lw=1.1)
        rect(c, bx, py, pw, 4, col, fill=True)
        txt(c, bx + 20, py + 40, vn, DISP, 30, INK, w="b", track=0.6)
        txt(c, bx + 20, py + 60, en, MONO, 8.2, SLATE_L, track=2.0)
        txt(c, bx + pw - 20, py + 40, tag, MONO, 8.2, col, track=2.0, align="r")
        for j, (no, nm, a, b) in enumerate(mods):
            module(c, bx + 20, py + 82 + j * 100, pw - 40, 88, no, nm, a, b, col)

    # inter-panel arrows
    for i in range(2):
        ax = xs[i] + pw
        ay = py + 200
        line(c, ax + 8, ay, ax + pg - 14, ay, INK, 1.2)
        arrowhead(c, ax + pg - 8, ay, 0, 7, INK)
        lbl = ["mode m | goal", "candidate x'"][i]
        txt(c, ax + pg / 2, ay - 12, lbl, MONO, 8, SLATE, track=1.2, align="c")

    # feedback arc
    fy = py + ph + 34
    line(c, xs[2] + pw / 2, py + ph + 4, xs[2] + pw / 2, fy, TEAL, 1.2)
    line(c, xs[2] + pw / 2, fy, xs[0] + pw / 2, fy, TEAL, 1.2, dash=[5, 4])
    line(c, xs[0] + pw / 2, fy, xs[0] + pw / 2, py + ph + 10, TEAL, 1.2)
    arrowhead(c, xs[0] + pw / 2, py + ph + 4, -math.pi / 2, 7, TEAL)
    txt(c, XL + IW / 2, fy - 10, "reward z_t  ·  cập nhật policy / policy update",
        MONO, 8.4, TEAL, track=1.6, align="c")

    txt(c, XL, 792, "Hierarchical MDP: một tác nhân macro chọn CHẾ ĐỘ tìm kiếm, một tác nhân micro chọn CẶP TOÁN TỬ trong chế độ đó.",
        BODY, 13, INK_S)
    txt(c, XR, 792, "Hierarchical MDP — macro picks the regime, micro picks the operator pair.",
        BODY, 11.6, SLATE_L, sl="i", align="r")

    footer(c, "PLATE 05  ·  KIẾN TRÚC", "45 GIÂY / 45 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 06 — THREE LAYERS
# ═══════════════════════════════════════════════════════════════════════════
def page_layers(c):
    ground(c, seed=37)
    frame(c, folio="PL. VI", cat="06  ·  BA TẦNG ĐIỀU KHIỂN / THE THREE LAYERS")
    header(c, "CƠ CHẾ THEN CHỐT / KEY MECHANISMS",
           "L1 CHỌN CHẾ ĐỘ · L2 CHỌN TOÁN TỬ · L3 PHÁ BẾ TẮC",
           "Regime selection, operator selection, and deadlock breaking.", 40)

    # L1
    y1 = 312
    txt(c, XL, y1, "L1", DISP, 42, VERM, w="b")
    txt(c, XL + 52, y1 - 4, "PLATEAU CONTROLLER", DISP, 28, INK, w="b", track=0.6)
    txt(c, XL + 52, y1 + 16, "SÁU CHẾ ĐỘ TÌM KIẾM / SIX SEARCH REGIMES", MONO, 8.2,
        SLATE_L, track=2.0)
    modes = [("1", "Intensify", "khai thác sâu lời giải tốt"),
             ("2", "Diversify", "phá huỷ diện rộng"),
             ("3", "Route-Reduce", "tập trung triệt tiêu xe"),
             ("4", "Pool-Recombine", "tái hợp từ Route Pool"),
             ("5", "TW-Rescue", "sửa vi phạm khung giờ"),
             ("6", "Capacity-Fix", "cân bằng lại tải trọng")]
    cwd = (IW - 5 * 14) / 6
    for i, (n, nm, d) in enumerate(modes):
        chip(c, XL + i * (cwd + 14), y1 + 34, cwd, 76, n, nm, d.upper(), VERM)
    line(c, XL, y1 + 132, XR, y1 + 132, HAIR, 0.8)

    # L2 / L3 columns
    y2 = 486
    colw, gap = 660, 36
    xs = [XL, XL + colw + gap]

    txt(c, xs[0], y2, "L2", DISP, 42, INK, w="b")
    txt(c, xs[0] + 52, y2 - 4, "OPERATOR CONTROLLER + LAC", DISP, 26, INK, w="b", track=0.6)
    txt(c, xs[0] + 52, y2 + 16, "KHÔNG GIAN HÀNH ĐỘNG & NGƯỠNG CHẤP NHẬN HỌC ĐƯỢC",
        MONO, 8.2, SLATE_L, track=1.9)
    txt(c, xs[0], y2 + 54, "13", DISP, 34, VERM, w="b")
    txt(c, xs[0] + 34, y2 + 54, "toán tử phá huỷ", BODY, 13.6, INK_S)
    txt(c, xs[0] + 168, y2 + 54, "×", MONO, 13, SLATE, track=0)
    txt(c, xs[0] + 190, y2 + 54, "5", DISP, 34, VERM, w="b")
    txt(c, xs[0] + 210, y2 + 54, "toán tử khôi phục", BODY, 13.6, INK_S)
    txt(c, xs[0] + 352, y2 + 54, "=", MONO, 13, SLATE, track=0)
    txt(c, xs[0] + 374, y2 + 54, "65", DISP, 34, INK, w="b")
    txt(c, xs[0] + 414, y2 + 54, "cặp hành động", BODY, 13.6, INK_S)
    para(c, xs[0], y2 + 92, ["Mạng LAC học ngưỡng chấp nhận lời giải tệ hơn,",
                             "thay cho lịch làm nguội Simulated Annealing tĩnh."],
         13.6, 21, INK_S)
    fw = tw(c, "P_acc = σ ( W · [ Δf , T , iter ] + b )".replace("σ", "s").replace("Δ", "d"),
            MONO, 14, track=1.0)
    txt(c, xs[0], y2 + 158, "P_acc  =  sigmoid ( W · [ delta-f , T , iter ] + b )",
        MONO, 13.4, INK, track=0.9)
    rect(c, xs[0] - 10, y2 + 138, tw(c, "P_acc  =  sigmoid ( W · [ delta-f , T , iter ] + b )", MONO, 13.4, track=0.9) + 20, 28, INK_S, lw=0.8)

    txt(c, xs[1], y2, "L3", DISP, 42, TEAL, w="b")
    txt(c, xs[1] + 52, y2 - 4, "PHÁ BẾ TẮC KHẢ THI", DISP, 26, INK, w="b", track=0.6)
    txt(c, xs[1] + 52, y2 + 16, "GENERALIZED EJECTION CHAINS + GNN EDGE HEATMAP",
        MONO, 8.2, SLATE_L, track=1.9)
    para(c, xs[1], y2 + 54, ["Chuỗi đẩy liên hoàn: đẩy khách u_1 sang tuyến R_2, ép",
                             "R_2 đẩy u_2 sang R_3 … nhằm xoá hẳn một tuyến xe.",
                             "Vượt được rào cản khung giờ mà Relocate / Swap đơn lẻ",
                             "không thể vượt."], 13.6, 21, INK_S)
    # ejection chain diagram
    ey = y2 + 150
    labs = ["R_A", "R_B", "R_C", "∅".replace("∅", "0")]
    for i in range(3):
        cxp = xs[1] + 26 + i * 150
        circ(c, cxp, ey, 15, PARCH, fill=True)
        circ(c, cxp, ey, 15, INK_S, 1.0)
        txt(c, cxp, ey + 4, ["R_A", "R_B", "R_C"][i], MONO, 9.5, INK, track=0.6,
            align="c")
        if i < 2:
            line(c, cxp + 18, ey, cxp + 128, ey, VERM, 1.2)
            arrowhead(c, cxp + 132, ey, 0, 6.5, VERM)
            txt(c, cxp + 73, ey - 10, f"eject u_{i+1}", MONO, 8, VERM, track=1.0,
                align="c")
    cxp = xs[1] + 26 + 3 * 150
    circ(c, cxp, ey, 15, VERM, fill=True, alpha=0.14)
    circ(c, cxp, ey, 15, VERM, 1.4)
    txt(c, cxp, ey + 4, "NV−1", MONO, 8.6, VERM, track=0.4, align="c")
    line(c, xs[1] + 26 + 2 * 150 + 18, ey, cxp - 18, ey, VERM, 1.2)
    arrowhead(c, cxp - 18, ey, 0, 6.5, VERM)

    # GNN edge predictor — scalability, stated honestly
    gy = 700
    line(c, XL, gy, XR, gy, HAIR, 0.8)
    txt(c, XL, gy + 24, "GNN EDGE PREDICTOR  ·  ĐÓNG GÓP LÀ KHẢ NĂNG MỞ RỘNG, KHÔNG PHẢI CHẤT LƯỢNG",
        MONO, 8.4, SLATE_L, track=2.0)
    figs = [("1160×", "bộ nhớ giảm ở n = 1000", "1517 MB → 1.3 MB", TEAL),
            ("81×", "suy luận nhanh hơn", "3.96 s → 0.049 s", TEAL),
            ("p = 0.683", "không cải thiện chất lượng", "kết quả âm, báo cáo thẳng", SLATE)]
    for i, (v, k, sub, col) in enumerate(figs):
        bx = XL + i * 452
        txt(c, bx, gy + 68, v, DISP, 40, col, w="b")
        off = 214 if i == 2 else 152
        txt(c, bx + off, gy + 56, k, BODY, 13.2, INK_S)
        txt(c, bx + off, gy + 74, sub, MONO, 8.2, SLATE_L, track=1.4)

    footer(c, "PLATE 06  ·  BA TẦNG ĐIỀU KHIỂN", "35 GIÂY / 35 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 07 — ZERO-SHOT TRAINING
# ═══════════════════════════════════════════════════════════════════════════
def page_training(c):
    ground(c, seed=41)
    frame(c, folio="PL. VII", cat="07  ·  HUẤN LUYỆN / TRAINING PROTOCOL")
    header(c, "TÍNH TỔNG QUÁT HOÁ / GENERALISATION",
           "HỌC TRÊN DỮ LIỆU GIẢ LẬP, THI TRÊN BỘ CHUẨN",
           "Trained only on synthetic graphs; evaluated zero-shot on the standard suites.")

    sy, sh = 330, 176
    stages = [
        ("01", "SINH DỮ LIỆU GIẢ LẬP", "DOMAIN RANDOMIZATION",
         ["n = 20 … 120 khách hàng", "3 dạng địa hình: Clustered,", "Uniform, Mixed"], VERM),
        ("02", "GIÁO TRÌNH BA GIAI ĐOẠN", "3-STAGE CURRICULUM",
         ["Welford chuẩn hoá reward", "trực tuyến, chặn ở ±8 sigma", "→ huấn luyện ổn định"], INK_S),
        ("03", "CHUYỂN GIAO ZERO-SHOT", "ZERO-SHOT TRANSFER",
         ["Không fine-tune, không xem", "trước bất kỳ instance nào", "của bộ chuẩn"], INK),
        ("04", "ĐÁNH GIÁ TRÊN BỘ CHUẨN", "BENCHMARK EVALUATION",
         ["Solomon 56 instance (100)", "Gehring–Homberger 200 …", "1000 khách hàng"], TEAL),
    ]
    pw = (IW - 3 * 44) / 4
    for i, (no, vn, en, lines, col) in enumerate(stages):
        bx = XL + i * (pw + 44)
        rect(c, bx, sy, pw, sh, PARCH_D, fill=True, alpha=0.45)
        rect(c, bx, sy, pw, sh, HAIR, lw=0.8)
        rect(c, bx, sy, pw, 3, col, fill=True)
        txt(c, bx + 18, sy + 30, no, DISP, 30, col, w="b")
        txt(c, bx + 18, sy + 58, vn, BODY, 13.4, INK, w="b")
        txt(c, bx + 18, sy + 76, en, MONO, 7.8, SLATE_L, track=1.6)
        para(c, bx + 18, sy + 106, lines, 12.6, 19, INK_S)
        if i < 3:
            ax = bx + pw
            line(c, ax + 10, sy + sh / 2, ax + 32, sy + sh / 2, INK, 1.2)
            arrowhead(c, ax + 38, sy + sh / 2, 0, 7, INK)

    # gate: no leakage
    gy = 548
    line(c, XL, gy, XR, gy, HAIR, 0.8)
    txt(c, XL, gy + 26, "RÀO CHẮN DỮ LIỆU / DATA FIREWALL", MONO, 8.4, VERM, track=2.2)
    para(c, XL, gy + 54, ["Trọng số mạng không bao giờ được tinh chỉnh trên Solomon hay Gehring–Homberger.",
                          "Mỗi thuật toán chạy khởi động lạnh độc lập — archive xoá sạch, cache rỗng — nên",
                          "không có hiện tượng nhiễm chéo kết quả giữa các thuật toán."], 14, 22, INK_S)
    txt(c, XR, gy + 54, "Weights are never tuned on the benchmark suites.", BODY,
        11.8, SLATE_L, sl="i", align="r")
    txt(c, XR, gy + 76, "Strict per-algorithm cold-start isolation: cleared archive,", BODY,
        11.8, SLATE_L, sl="i", align="r")
    txt(c, XR, gy + 98, "empty cache — no cross-algorithm contamination.", BODY,
        11.8, SLATE_L, sl="i", align="r")

    verdict(c, 804, ["164 INSTANCE CHUẨN · 100 → 1000 KHÁCH HÀNG · KHÔNG MỘT LẦN FINE-TUNE"],
            ["Zero-shot transfer across 164 standard instances is the decisive evidence that the learned policy generalises."],
            right="ZERO – SHOT", size=26)

    footer(c, "PLATE 07  ·  HUẤN LUYỆN", "20 GIÂY / 20 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 08 — RESULTS
# ═══════════════════════════════════════════════════════════════════════════
def page_results(c):
    ground(c, seed=47)
    frame(c, folio="PL. VIII", cat="08  ·  KẾT QUẢ / RESULTS — SOLOMON, 56 INSTANCES")
    header(c, "ĐÁNH GIÁ THỰC NGHIỆM / EMPIRICAL EVALUATION",
           "ÍT XE HƠN — VÀ KHI CÙNG SỐ XE, ĐƯỜNG NGẮN HƠN",
           "Fewer vehicles; and at matched fleet size, shorter routes.")

    colw, gap = 660, 36
    xs = [XL, XL + colw + gap]

    # panel 1: NV
    txt(c, xs[0], 314, "A", DISP, 34, SLATE_L, w="b")
    txt(c, xs[0] + 30, 312, "SỐ XE DƯ SO VỚI TỐI ƯU", DISP, 26, INK, w="b", track=0.6)
    txt(c, xs[0] + 30, 332, "MEAN VEHICLE INFLATION ABOVE BKS  ·  LOWER IS BETTER",
        MONO, 8, SLATE_L, track=1.8)
    rows = [("OR-Tools (iso-time)", 0.536, SLATE),
            ("ALNS cổ điển", 0.258, INK_S),
            ("Hybrid-Fixed", 0.097, SLATE_L),
            ("HYBRID-DDQN", 0.089, VERM)]
    bw = 340
    for i, (nm, v, col) in enumerate(rows):
        yy = 360 + i * 34
        txt(c, xs[0], yy + 12, nm, MONO, 9.2, VERM if col is VERM else INK_S,
            track=1.3)
        hbar(c, xs[0] + 196, yy, bw, v / 0.58, col, 15)
        txt(c, xs[0] + 196 + bw + 12, yy + 12, f"+{v:.3f}", MONO, 11,
            VERM if col is VERM else INK_S, track=0.9)
    line(c, xs[0], 504, xs[0] + colw, 504, HAIR, 0.7)
    txt(c, xs[0], 526, "GIẢM 65.3% so với ALNS  ·  83.3% so với OR-Tools", MONO,
        9.4, VERM, track=1.5)

    # panel 2: TD at matched fleet
    txt(c, xs[1], 314, "B", DISP, 34, SLATE_L, w="b")
    txt(c, xs[1] + 30, 312, "ĐỘ LỆCH QUÃNG ĐƯỜNG, CÙNG SỐ XE", DISP, 26, INK,
        w="b", track=0.6)
    txt(c, xs[1] + 30, 332, "TD GAP AT MATCHED FLEET SIZE  ·  STRICT FAIR SUBSET, N = 40",
        MONO, 8, SLATE_L, track=1.8)
    rows2 = [("ALNS cổ điển", 1.642, INK_S), ("Hybrid-Rule", 0.734, SLATE_L),
             ("Hybrid-Fixed", 0.707, SLATE_L), ("HYBRID-DDQN", 0.575, TEAL)]
    for i, (nm, v, col) in enumerate(rows2):
        yy = 360 + i * 34
        txt(c, xs[1], yy + 12, nm, MONO, 9.2, TEAL if col is TEAL else INK_S,
            track=1.3)
        hbar(c, xs[1] + 196, yy, bw, v / 1.80, col, 15)
        txt(c, xs[1] + 196 + bw + 12, yy + 12, f"+{v:.3f}%", MONO, 11,
            TEAL if col is TEAL else INK_S, track=0.9)
    line(c, xs[1], 504, xs[1] + colw, 504, HAIR, 0.7)
    txt(c, xs[1], 526, "GIẢM 65% độ lệch  ·  họ R2/RC2 khó nhất: 2.593% → 1.364%",
        MONO, 9.4, TEAL, track=1.5)

    # statistical band
    sy = 566
    txt(c, XL, sy, "KIỂM ĐỊNH WILCOXON SIGNED-RANK  ·  PAIRED, 56 SOLOMON INSTANCES",
        MONO, 8.4, SLATE_L, track=2.0)
    tests = [("Số xe vs OR-Tools", "p = 2.96e-05", "RẤT CÓ Ý NGHĨA", VERM),
             ("Số xe vs ALNS cổ điển", "p = 1.78e-03", "CÓ Ý NGHĨA", VERM),
             ("Quãng đường vs Hybrid-Rule", "p = 0.064", "NHẤT QUÁN, CHƯA QUYẾT ĐỊNH", SLATE)]
    tw_ = (IW - 2 * 24) / 3
    for i, (nm, p, verdict_, col) in enumerate(tests):
        bx = XL + i * (tw_ + 24)
        rect(c, bx, sy + 14, tw_, 92, PARCH_D, fill=True, alpha=0.5)
        rect(c, bx, sy + 14, tw_, 92, HAIR, lw=0.8)
        rect(c, bx, sy + 14, 3, 92, col, fill=True)
        txt(c, bx + 18, sy + 40, nm, BODY, 13, INK, w="b")
        txt(c, bx + 18, sy + 72, p, MONO, 17, col, track=0.8)
        txt(c, bx + 18, sy + 94, verdict_, MONO, 7.8, SLATE_L, track=1.7)

    verdict(c, 804, ["R101: ĐẠT ĐÚNG CẢ SỐ XE (19) VÀ QUÃNG ĐƯỜNG TỐI ƯU (1650.80)"],
            ["On RC101 it also reaches the BKS fleet of 14 where classical ALNS stalls at 15 and OR-Tools at 16 — the lexicographic trade, paid deliberately."],
            right="BKS  MATCHED", size=26, tagcol=TEAL)

    footer(c, "PLATE 08  ·  KẾT QUẢ", "45 GIÂY / 45 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 09 — SCALE & HONEST LIMITS
# ═══════════════════════════════════════════════════════════════════════════
def page_scale(c):
    ground(c, seed=53)
    frame(c, folio="PL. IX", cat="09  ·  KHẢ NĂNG MỞ RỘNG & GIỚI HẠN / SCALE & LIMITS")
    header(c, "MỞ RỘNG QUY MÔ / SCALABILITY",
           "CÀNG LỚN, KHOẢNG CÁCH CÀNG RỘNG",
           "The advantage over OR-Tools grows monotonically with problem size.")

    # chart
    gx, gy, gw, gh = XL, 330, 760, 300
    rect(c, gx, gy, gw, gh, PARCH_D, fill=True, alpha=0.36)
    rect(c, gx, gy, gw, gh, HAIR, lw=0.8)
    ns = [400, 600, 800, 1000]
    vals = [1.34, 4.92, 8.50, 9.45]
    dist = [7.86, 9.50, 12.51, 14.42]
    vmax = 10.0
    for i in range(6):
        yy = gy + gh - gh * i / 5
        line(c, gx, yy, gx + gw, yy, HAIR, 0.6, 0.8, dash=[2, 5] if i else None)
        txt(c, gx - 10, yy + 4, f"{vmax*i/5:.0f}", MONO, 8, SLATE_L, track=0.8,
            align="r")
    pts = []
    for i, n in enumerate(ns):
        px = gx + gw * (i + 0.5) / 4
        py = gy + gh - gh * vals[i] / vmax
        pts.append((px, py))
        txt(c, px, gy + gh + 22, f"n = {n}", MONO, 9, INK_S, track=1.2, align="c")
    smooth(c, pts, VERM, 2.0, t=0.2)
    for i, (px, py) in enumerate(pts):
        circ(c, px, py, 5.5, PARCH, fill=True)
        circ(c, px, py, 5.5, VERM, 1.6)
        ly_ = py - 16 if py - 16 > gy + 20 else py + 24
        txt(c, px, ly_, f"+{vals[i]:.2f}", MONO, 10.5, VERM, track=0.8,
            align="c")
    txt(c, gx + 14, gy + 26, "SỐ XE TIẾT KIỆM ĐƯỢC SO VỚI OR-TOOLS", MONO, 8.4,
        VERM, track=2.0)
    txt(c, gx + 14, gy + 44, "vehicles saved vs OR-Tools at equal wall-clock time",
        BODY, 11.4, SLATE_L, sl="i")
    txt(c, gx + gw - 14, gy + gh - 14, "TRỤC Y: SỐ XE", MONO, 7.6, SLATE_L,
        track=1.6, align="r")

    # right column: distance + honest limits
    rx = XL + 800
    rw = XR - rx
    txt(c, rx, 344, "QUÃNG ĐƯỜNG, CÙNG SỐ XE", DISP, 26, INK, w="b", track=0.6)
    txt(c, rx, 364, "MATCHED-FLEET DISTANCE IMPROVEMENT vs ALNS", MONO, 8,
        SLATE_L, track=1.7)
    for i, n in enumerate(ns):
        yy = 392 + i * 30
        txt(c, rx, yy + 11, f"n = {n}", MONO, 9.2, INK_S, track=1.2)
        hbar(c, rx + 76, yy, 330, dist[i] / 16.0, TEAL, 14)
        txt(c, rx + 76 + 330 + 12, yy + 11, f"−{dist[i]:.2f}%", MONO, 10.5, TEAL,
            track=0.8)
    line(c, rx, 528, XR, 528, HAIR, 0.7)
    txt(c, rx, 552, "n = 1000:  60.55 xe  ·  OR-Tools 70.00 xe", MONO, 10, INK,
        track=1.1)
    txt(c, rx, 574, "cùng ngân sách ~400 s wall-clock", MONO, 8.6, SLATE_L, track=1.5)
    txt(c, rx, 608, "GH-200, cùng số xe: quãng đường giảm 4.32%", MONO, 9.4, TEAL,
        track=1.2)

    # honest limits
    ly = 664
    rect(c, XL, ly, IW, 140, PARCH_D, fill=True, alpha=0.6)
    rect(c, XL, ly, IW, 140, INK_S, lw=1.0)
    rect(c, XL, ly, 5, 140, SLATE, fill=True)
    txt(c, XL + 30, ly + 30, "GIỚI HẠN — NÓI THẲNG / STATED LIMITATIONS", MONO,
        9.2, SLATE, track=2.4)
    lims = [["Từ 400 khách trở lên, cả hai thuật toán",
             "đều còn xa BKS — đóng góp ở quy mô này",
             "là tương đối, không phải tuyệt đối."],
            ["Chậm hơn ALNS cổ điển 2–100× trên các",
             "instance mà ALNS dừng sớm: đó là giá",
             "phải trả cho việc triệt tiêu thêm xe."],
            ["GNN heatmap không cải thiện chất lượng",
             "(p = 0.683) — nên mọi kết quả ở trên",
             "đều KHÔNG dùng GNN guidance."]]
    cwx = (IW - 60 - 2 * 34) / 3
    for i, block in enumerate(lims):
        bx = XL + 30 + i * (cwx + 34)
        line(c, bx, ly + 50, bx + 22, ly + 50, VERM, 1.8)
        para(c, bx, ly + 74, block, 12.4, 18, INK_S)

    footer(c, "PLATE 09  ·  KHẢ NĂNG MỞ RỘNG & GIỚI HẠN", "30 GIÂY / 30 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 10 — DEMO
# ═══════════════════════════════════════════════════════════════════════════
def page_demo(c):
    ground(c, seed=59)
    frame(c, folio="PL. X", cat="10  ·  DEMO TRỰC TIẾP / LIVE DEMONSTRATION")

    eyebrow(c, XL, 158, "80 GIÂY / 80 SECONDS  —  DISPATCH PORTAL")
    heading(c, XL, 240, "DEMO TRỰC TIẾP", 62, INK, 1.0)
    txt(c, XL, 268, "Cổng điều phối web · FastAPI + PyTorch + HiGHS MILP  —  load instance, solve, watch the fleet shrink.",
        BODY, 14, SLATE, sl="i")
    line(c, XL, 294, XR, 294, HAIR, 0.9)

    # left: script
    steps = [
        ("01", "NẠP INSTANCE", "Chọn R101 (100 khách) từ bộ Solomon.", "15 s"),
        ("02", "CHẠY SOLVER", "Bấm Solve — theo dõi số xe tụt dần theo thời gian thực.", "25 s"),
        ("03", "SO SÁNH", "Bật lớp ALNS cổ điển: 15 xe, so với 14 xe của chúng tôi.", "25 s"),
        ("04", "KIỂM TOÁN", "Mở một tuyến: từng khung giờ, tải trọng, thứ tự phục vụ.", "15 s"),
    ]
    for i, (no, vn, d, t) in enumerate(steps):
        yy = 322 + i * 88
        txt(c, XL, yy + 30, no, DISP, 40, VERM if i == 1 else SLATE_L, w="b")
        txt(c, XL + 58, yy + 22, vn, DISP, 27, INK, w="b", track=0.6)
        txt(c, XL + 58, yy + 46, d, BODY, 13.4, INK_S)
        txt(c, XL + 640, yy + 24, t, MONO, 11, VERM if i == 1 else SLATE, track=1.4,
            align="r")
        line(c, XL, yy + 66, XL + 640, yy + 66, HAIR, 0.7)

    # right: screen plate
    px, py, pw, ph = XL + 704, 318, IW - 704, 340
    rect(c, px, py, pw, ph, PARCH, fill=True)
    rect(c, px, py, pw, ph, INK, lw=1.1)
    rect(c, px, py, pw, 26, INK, fill=True)
    txt(c, px + 12, py + 18, "DISPATCH PORTAL  ·  localhost:8000", MONO, 8, PARCH,
        track=1.6)
    routing_chart(c, px + pw * 0.42, py + 190, 118, seed=71, labels=False,
                  n_nodes=30)
    # side readout
    rxx = px + pw - 176
    line(c, rxx - 18, py + 46, rxx - 18, py + ph - 30, HAIR, 0.7)
    reads = [("SỐ XE / NV", "14", VERM), ("QUÃNG ĐƯỜNG / TD", "1699.1", INK),
             ("KHẢ THI / FEASIBLE", "100%", TEAL), ("THỜI GIAN / TIME", "97.4 s", INK_S)]
    for i, (k, v, col) in enumerate(reads):
        yy = py + 74 + i * 62
        txt(c, rxx, yy, k, MONO, 7.6, SLATE_L, track=1.6)
        txt(c, rxx, yy + 30, v, DISP, 34, col, w="b")
    tickfield(c, px + 20, py + ph - 18, pw - 40, 40, 3, HAIR, 0.7, every=5, hl=7)

    verdict(c, 804, ["NẾU DEMO LỖI: MỞ SẴN VIDEO 40 GIÂY VÀ BẢNG KẾT QUẢ TĨNH"],
            ["Fallback rehearsed: a 40-second screen recording plus the static results table, already open in tab two."],
            right="PLAN  B", size=26)

    footer(c, "PLATE 10  ·  DEMO", "80 GIÂY / 80 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
# 11 — CONCLUSION
# ═══════════════════════════════════════════════════════════════════════════
def page_conclusion(c):
    ground(c, seed=61)
    frame(c, folio="PL. XI", cat="11  ·  KẾT LUẬN & ĐÓNG GÓP / CONCLUSION")
    header(c, "TỔNG KẾT / IN CLOSING", "BỐN ĐÓNG GÓP, MỘT KẾT LUẬN",
           "Four contributions and one conclusion.")

    conts = [
        ("01", "MDP PHÂN CẤP", "HIERARCHICAL MDP",
         ["Plateau Controller (macro) và Operator", "Controller (micro) phối hợp như hai", "tác nhân Dueling Double DQN."]),
        ("02", "NGƯỠNG CHẤP NHẬN HỌC ĐƯỢC", "LEARNED ACCEPTANCE",
         ["Bộ phân loại gán nhãn hồi tố thay cho", "lịch làm nguội Simulated Annealing", "tĩnh của ALNS truyền thống."]),
        ("03", "PHÁ BẾ TẮC KHẢ THI", "FEASIBILITY ENTRAPMENT",
         ["Tìm kiếm qua trạng thái tạm bất khả thi", "+ ejection chains + tail-swap: thoát", "khỏi mức số xe cao hơn BKS."]),
        ("04", "THỰC NGHIỆM NGHIÊM NGẶT", "RIGOROUS EVALUATION",
         ["164 instance, khởi động lạnh độc lập,", "ablation 5 điều kiện, kiểm định Wilcoxon,", "báo cáo cả kết quả âm."]),
    ]
    pw = (IW - 3 * 34) / 4
    for i, (no, vn, en, lines) in enumerate(conts):
        bx = XL + i * (pw + 34)
        line(c, bx, 306, bx + pw, 306, INK if i < 3 else TEAL, 1.9)
        txt(c, bx, 352, no, DISP, 44, VERM if i == 0 else SLATE_L, w="b")
        txt(c, bx, 386, vn, DISP, 25, INK, w="b", track=0.5)
        txt(c, bx, 404, en, MONO, 7.8, SLATE_L, track=1.7)
        para(c, bx, 434, lines, 12.8, 19, INK_S)

    line(c, XL, 512, XR, 512, HAIR, 0.8)

    # closing statement + future
    txt(c, XL, 552, "HƯỚNG PHÁT TRIỂN / FUTURE WORK", MONO, 8.6, SLATE_L, track=2.2)
    fw = [("Thay đặc trưng trạng thái thủ công bằng bộ mã hoá đồ thị dựa attention.",),
          ("Ablation cho N-step returns, HER relabelling, giáo trình thích ứng.",),
          ("Mở rộng sang định tuyến động, thời gian thực: giao thông, đơn phát sinh.",)]
    for i, (t,) in enumerate(fw):
        yy = 582 + i * 24
        line(c, XL, yy - 4, XL + 12, yy - 4, TEAL, 1.6)
        txt(c, XL + 24, yy, t, BODY, 13.2, INK_S)

    rxx = XL + 760
    txt(c, rxx, 552, "SỐ LIỆU CHÍNH / HEADLINE FIGURES", MONO, 8.6, SLATE_L, track=2.2)
    figs = [("+0.089", "số xe dư trên Solomon", VERM),
            ("+0.575%", "độ lệch đường, cùng số xe", TEAL),
            ("9.45", "xe tiết kiệm ở n = 1000", INK)]
    for i, (v, k, col) in enumerate(figs):
        bx = rxx + i * 214
        txt(c, bx, 604, v, DISP, 44, col, w="b")
        txt(c, bx, 626, k, MONO, 8, SLATE_L, track=1.4)

    verdict(c, 804, ["GIỮ NGUYÊN TÍNH KIỂM TOÁN CỦA OR — THÊM VÀO TÍNH THÍCH ỨNG CỦA RL."],
            ["Hybrid DDQN-ALNS keeps every move a named, inspectable operator while learning when to play it. Fleet discipline first, distance second.",
             "Cảm ơn TS. Hồ Thị Linh đã hướng dẫn.   ·   Xin mời câu hỏi / Questions welcome."],
            right="Q & A", size=28)

    footer(c, "PLATE 11  ·  KẾT LUẬN & ĐÓNG GÓP", "30 GIÂY / 30 SECONDS")


# ═══════════════════════════════════════════════════════════════════════════
PAGES = [page_title, page_bigpicture, page_problem, page_gap, page_arch,
         page_layers, page_training, page_results, page_scale, page_demo,
         page_conclusion]


def render(pngs=True):
    pdf = os.path.join(OUT, "deck.pdf")
    s = cairo.PDFSurface(pdf, W, H)
    c = cairo.Context(s)
    for p in PAGES:
        p(c)
        c.show_page()
    s.finish()
    if pngs:
        for i, p in enumerate(PAGES):
            sc = 2.0
            ps = cairo.ImageSurface(cairo.FORMAT_RGB24, int(W * sc), int(H * sc))
            pc = cairo.Context(ps)
            pc.scale(sc, sc)
            p(pc)
            ps.write_to_png(os.path.join(OUT, f"p{i+1:02d}.png"))
    print("ok", len(PAGES))


if __name__ == "__main__":
    render()
