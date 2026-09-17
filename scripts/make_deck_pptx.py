#!/usr/bin/env python3
"""Generate IBVAP-Proposal-Deck.pptx (16:9, dark ops theme)."""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

NAVY = RGBColor(0x0B, 0x12, 0x20)
PANEL = RGBColor(0x12, 0x1E, 0x38)
PANEL2 = RGBColor(0x0D, 0x15, 0x26)
AMBER = RGBColor(0xF5, 0xA5, 0x24)
WHITE = RGBColor(0xDC, 0xE5, 0xF7)
MUT = RGBColor(0x8E, 0xA0, 0xC0)
GREEN = RGBColor(0x22, 0xC5, 0x5E)
RED = RGBColor(0xEF, 0x44, 0x44)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide():
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = NAVY
    return s


def box(s, x, y, w, h, fill=PANEL, line=None, rnd=True):
    shp = s.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rnd else MSO_SHAPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.2)
    shp.shadow.inherit = False
    return shp


def txt(s, x, y, w, h, text, size=14, color=WHITE, bold=False,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, font="Segoe UI"):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, ln in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.name = font
    return tb


def arrow(s, x, y, w, h, direction="right", color=MUT):
    shp = s.shapes.add_shape(
        {"right": MSO_SHAPE.RIGHT_ARROW, "down": MSO_SHAPE.DOWN_ARROW}[direction],
        Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = color
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def header(s, title, sub=None):
    txt(s, 0.55, 0.32, 12.2, 0.6, title, size=26, color=WHITE, bold=True)
    box(s, 0.58, 0.95, 1.6, 0.06, fill=AMBER, rnd=False)
    if sub:
        txt(s, 0.55, 1.08, 12.2, 0.4, sub, size=13, color=MUT)


def table(s, x, y, w, headers, rows, col_ws, size=12, row_h=0.36,
          first_col_left=True):
    gf = s.shapes.add_table(len(rows) + 1, len(headers),
                            Inches(x), Inches(y), Inches(w),
                            Inches(row_h * (len(rows) + 1)))
    t = gf.table
    for j, cw in enumerate(col_ws):
        t.columns[j].width = Inches(cw)
    for i in range(len(rows) + 1):
        t.rows[i].height = Inches(row_h)

    def cell(c, text, size, color, bold, fill, align):
        c.fill.solid()
        c.fill.fore_color.rgb = fill
        c.vertical_anchor = MSO_ANCHOR.MIDDLE
        c.margin_left = Inches(0.08)
        c.margin_right = Inches(0.08)
        tf = c.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.alignment = align
        r = p.add_run()
        r.text = text
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold
        r.font.name = "Segoe UI"

    for j, htxt in enumerate(headers):
        cell(t.cell(0, j), htxt, size, WHITE, True, RGBColor(0x1B, 0x29, 0x46),
             PP_ALIGN.CENTER)
    for i, row in enumerate(rows, 1):
        fill = PANEL if i % 2 else PANEL2
        for j, v in enumerate(row):
            cell(t.cell(i, j), str(v), size - 1, WHITE, i == len(rows), fill,
                 PP_ALIGN.LEFT if (j == 0 and first_col_left) else PP_ALIGN.CENTER)
    return t


# ================================================================ S1 title
s = new_slide()
box(s, 0, 2.35, 13.333, 2.8, fill=PANEL)
txt(s, 1.0, 2.6, 11.3, 1.2, "IBVAP", size=66, color=AMBER, bold=True,
    align=PP_ALIGN.CENTER)
txt(s, 1.0, 3.85, 11.3, 0.6,
    "AI-Based Intelligent Video Analytics Platform for Border Surveillance",
    size=20, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
txt(s, 1.0, 4.6, 11.3, 0.4,
    "Submitted to: Ministry of Home Affairs — Sashastra Seema Bal (SSB) · Problem Statement 26187",
    size=13, color=MUT, align=PP_ALIGN.CENTER)
txt(s, 1.0, 5.6, 11.3, 0.5,
    "Zero new BOP hardware   ·   CPU-only AI   ·   100% open-source   ·   ₹2–6 L pilot",
    size=15, color=GREEN, bold=True, align=PP_ALIGN.CENTER)

# ================================================================ S2 problem
s = new_slide()
header(s, "The Problem: Cameras That Only Record",
       "SSB runs thousands of CCTVs at BOPs, check posts and border roads — passive recording only")
pains = [
    ("24/7", "human watching — an operator can actually supervise 4–6 screens"),
    ("30–40%", "of intrusions detected; the rest are missed between glances"),
    ("Hours", "to discover incidents — during footage review, not in real time"),
    ("₹30k–₹1L", "per camera for smart upgrades → crores across hundreds of sites"),
    ("Remote", "BOPs can't maintain specialized hardware or handle vendor lock-in"),
]
y = 1.75
for big, small in pains:
    box(s, 0.55, y, 2.5, 0.85)
    txt(s, 0.6, y + 0.14, 2.4, 0.6, big, size=22, color=AMBER, bold=True,
        align=PP_ALIGN.CENTER)
    txt(s, 3.3, y + 0.12, 9.4, 0.7, small, size=15, color=WHITE,
        anchor=MSO_ANCHOR.MIDDLE)
    y += 1.02
box(s, 0.55, y + 0.05, 12.23, 0.6, fill=RGBColor(0x2A, 0x15, 0x1A))
txt(s, 0.75, y + 0.15, 11.9, 0.4,
    "Result: missed security incidents · operator fatigue · delayed response · unaffordable upgrades",
    size=14, color=RED, bold=True)

# ================================================================ S3 existing solutions
s = new_slide()
header(s, "Existing Solutions & Why They Fail for Border Deployment")
table(s, 0.55, 1.6, 12.23,
      ["Approach", "Cost (100 units)", "Why it fails at the border"],
      [
          ["Smart cameras (FRS/ANPR built-in)", "₹30L – 1 Cr",
           "Replaces the entire existing CCTV estate; per-camera config & maintenance at remote BOPs; vendor lock-in"],
          ["Dedicated AI servers per BOP", "₹50L – 2 Cr",
           "100+ GPU servers in solar-powered remote sites; spares & skilled staff unavailable; each runs under capacity"],
          ["Proprietary VMS + analytics licences", "₹10–50L / year",
           "Per-camera, per-feature pricing (ANPR/FRS extra); renewals in perpetuity; migration cost = lock-in"],
      ],
      [3.4, 2.2, 6.6], size=13, row_h=1.05)
box(s, 0.55, 5.3, 12.23, 0.9, fill=PANEL2)
txt(s, 0.75, 5.45, 11.9, 0.6,
    "Common flaw: all three are hardware- or licence-centric.\n"
    "The intelligence must be software that reuses what SSB already owns.",
    size=15, color=WHITE, bold=True)

# ================================================================ S4 core innovation
s = new_slide()
header(s, "Our Solution: Pure Software, Zero Additional Hardware")
quads = [
    ("Reuse existing cameras", "Direct RTSP over the existing SSB VPN — no gateways, no camera replacement, no site visits"),
    ("Run on existing servers", "One central data-centre server (SSB already has them) runs the whole platform"),
    ("CPU-only AI — no GPU", "YOLO-nano, INT8, 3–5 fps per camera with motion gating — enough for security, cheap to run"),
    ("100% open-source stack", "Ubuntu · FastAPI · PostgreSQL · PyTorch/ONNX · FFmpeg — ₹0 licensing, forever, no vendor lock-in"),
]
pos = [(0.55, 1.7), (6.75, 1.7), (0.55, 3.75), (6.75, 3.75)]
for (t, d), (x, y) in zip(quads, pos):
    box(s, x, y, 6.03, 1.85)
    txt(s, x + 0.25, y + 0.18, 5.6, 0.5, "✅  " + t, size=17, color=AMBER, bold=True)
    txt(s, x + 0.25, y + 0.75, 5.55, 1.0, d, size=13.5, color=WHITE)
box(s, 0.55, 5.9, 12.23, 0.85, fill=RGBColor(0x12, 0x2A, 0x1A))
txt(s, 0.75, 6.05, 11.9, 0.55,
    "New spend = software development only:  ₹2–6 L one-time · no per-camera fees · no annual licence renewals",
    size=16, color=GREEN, bold=True)

# ================================================================ S5 deployment
s = new_slide()
header(s, "Deployment Architecture — Inside Existing SSB Infrastructure",
       "No changes at any BOP. Everything new lives on one central server.")
for i, name in enumerate(["BOP-01", "BOP-02", "BOP-03"]):
    box(s, 0.55, 1.8 + i * 1.25, 3.1, 1.0)
    txt(s, 0.7, 1.92 + i * 1.25, 2.8, 0.4, name, size=14, color=AMBER, bold=True)
    txt(s, 0.7, 2.32 + i * 1.25, 2.85, 0.5, "4–8 existing IP cams\n+ existing NVR / router",
        size=11, color=MUT)
arrow(s, 3.85, 3.75, 0.9, 0.3)
box(s, 4.95, 1.8, 1.7, 3.45)
txt(s, 5.05, 2.1, 1.5, 2.6, "S\nS\nB\n \nV\nP\nN\n/\nW\nA\nN\n\n(\ne\nx\ni\ns\nt\ni\nn\ng)",
    size=12, color=MUT, bold=True, align=PP_ALIGN.CENTER)
arrow(s, 6.85, 3.75, 0.9, 0.3)
box(s, 7.95, 1.8, 4.83, 3.45, fill=PANEL, line=AMBER)
txt(s, 8.15, 1.95, 4.5, 0.4, "Central server (existing SSB)", size=14, color=AMBER, bold=True)
for i, line in enumerate(["IBVAP:  Ingestion · AI Workers (CPU)",
                          "Event DB · Evidence clips (NAS)",
                          "API (REST + WebSocket) · Web dashboard",
                          "16–32 cores · 64GB RAM · 100Mbps–1Gbps"]):
    txt(s, 8.15, 2.45 + i * 0.62, 4.5, 0.5, "•  " + line, size=12.5, color=WHITE)
arrow(s, 10.3, 5.35, 0.3, 0.55, direction="down")
box(s, 0.55, 6.0, 12.23, 0.85)
txt(s, 0.75, 6.15, 11.9, 0.55,
    "Users:  BOP staff (web dashboard)   ·   mobile (alerts + live)   ·   command centre (C2 via REST API)",
    size=14, color=WHITE)
txt(s, 7.0, 5.42, 3.5, 0.4, "HTTPS / WSS (TLS)", size=11, color=MUT, align=PP_ALIGN.CENTER)

# ================================================================ S6 pipeline
s = new_slide()
header(s, "How It Works: Frame → Alert in < 3 Seconds")
steps = ["RTSP frame\n(640×360)", "Resize +\nmotion gate", "YOLO-nano\nINT8, CPU",
         "Track +\nzone rules", "Event +\nevidence clip", "Alert < 3 s\nWS · SMS · C2"]
x = 0.55
for i, stp in enumerate(steps):
    last = i == len(steps) - 1
    box(s, x, 2.1, 1.85, 1.25, fill=PANEL if not last else RGBColor(0x2A, 0x15, 0x1A))
    txt(s, x + 0.08, 2.25, 1.7, 1.0, stp, size=12.5,
        color=RED if last else WHITE, bold=True, align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE)
    if not last:
        arrow(s, x + 1.87, 2.55, 0.19, 0.3)
    x += 2.05
txt(s, 0.55, 3.75, 12.2, 0.5,
    "Person/vehicle tracked across frames  →  centroid crosses a drawn zone  →  intrusion event (cooldown + dedup)  →  loitering if dwell > T",
    size=13.5, color=MUT)
savings = [
    ("60–80%", "compute saved — analytics only when motion is detected"),
    ("70–90%", "bandwidth saved — 640×360 analytics stream, full-res only for evidence"),
    ("99%", "storage saved — event-only: snapshots + 20 s clips (≈100 GB/mo per 100 cams, not petabytes)"),
]
y = 4.45
for big, small in savings:
    box(s, 0.55, y, 12.23, 0.72)
    txt(s, 0.75, y + 0.12, 1.9, 0.5, big, size=18, color=GREEN, bold=True)
    txt(s, 2.8, y + 0.14, 9.9, 0.5, small, size=13, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
    y += 0.85

# ================================================================ S7 capabilities
s = new_slide()
header(s, "What SSB Gets for ₹2–6 Lakhs")
box(s, 0.55, 1.6, 6.03, 5.1)
txt(s, 0.8, 1.75, 5.6, 0.4, "Full AI Analytics Suite", size=16, color=AMBER, bold=True)
suite = ["Person & vehicle detection + tracking",
         "Virtual fence intrusion (custom zones per camera)",
         "Loitering & suspicious activity",
         "ANPR (plate OCR + watchlist)",
         "Face detection + optional watchlist matching",
         "Night / low-light (IR) optimised detection",
         "Real-time alerts < 3 s + searchable event log",
         "Auto evidence: snapshot + 10–20 s clip"]
for i, f_ in enumerate(suite):
    txt(s, 0.8, 2.3 + i * 0.52, 5.6, 0.5, "✅  " + f_, size=12.5, color=WHITE)
box(s, 6.75, 1.6, 6.03, 5.1)
txt(s, 7.0, 1.75, 5.6, 0.4, "Professional Web Dashboard", size=16, color=AMBER, bold=True)
dash = ["Live camera wall (4/9/16 grid, any browser)",
        "Real-time alert panel + one-click ACK",
        "Interactive map of BOPs & camera markers",
        "Event timeline with advanced search",
        "Virtual fence editor — draw zones remotely",
        "User management (RBAC: operator/supervisor/admin)",
        "Reports & analytics (daily/weekly stats)",
        "Mobile-responsive (tablets & phones)"]
for i, f_ in enumerate(dash):
    txt(s, 7.0, 2.3 + i * 0.52, 5.6, 0.5, "✅  " + f_, size=12.5, color=WHITE)

# ================================================================ S8 cost comparison
s = new_slide()
header(s, "5-Year Cost of Ownership — 100 Cameras",
       "₹ lakhs · one-time + 4 years of operation")
table(s, 0.55, 1.8, 12.23,
      ["Solution", "Year 1", "Years 2–5 (each)", "5-Year Total", "vs IBVAP"],
      [
          ["Smart cameras", "30 – 100", "5 – 20", "50 – 180", "95% more"],
          ["Edge AI servers at BOPs", "50 – 200", "10 – 30", "90 – 320", "97% more"],
          ["Commercial VMS", "10 – 50", "10 – 50", "50 – 250", "96% more"],
          ["IBVAP (this proposal)", "2 – 6", "0.3 – 1.1", "3.2 – 10.4", "—"],
      ],
      [3.6, 1.9, 2.4, 2.2, 2.1], size=13, row_h=0.55)
box(s, 0.55, 4.75, 12.23, 1.9, fill=RGBColor(0x12, 0x2A, 0x1A))
txt(s, 0.8, 4.95, 11.8, 0.5,
    "Per-camera, 5-yr TCO:  smart cameras ₹55k–1.5L  →  IBVAP ₹3.5–11k   (95–98% less at scale)",
    size=15, color=GREEN, bold=True)
txt(s, 0.8, 5.6, 11.8, 0.9,
    "Annual savings: ₹18–104 lakhs per year  ·  Payback: immediate (cost avoidance)  ·  ROI: 400–3000%",
    size=14, color=WHITE)

# ================================================================ S9 scaling
s = new_slide()
header(s, "Scales Sub-linearly — 10 to 1000+ Cameras Without Redesign")
table(s, 0.55, 1.7, 12.23,
      ["Cameras", "Servers needed", "Additional one-time cost", "Effective cost / camera"],
      [
          ["1 – 100", "1 (existing / refurbished)", "₹2 – 6 L", "₹20 – 60k"],
          ["101 – 200", "1 (same server)", "₹0", "₹0"],
          ["201 – 500", "2", "₹0 – 3 L", "₹6 – 15k"],
          ["501 – 1000", "3 – 4", "₹0 – 6 L", "₹6 – 12k"],
      ],
      [2.6, 3.4, 3.2, 3.0], size=13, row_h=0.55)
box(s, 0.55, 4.8, 12.23, 1.7)
txt(s, 0.8, 5.0, 11.8, 1.3,
    "1000 cameras ≈ ₹10–12 lakhs total  —  not ₹3–10 crores.\n"
    "One 32-core server sustains 100–200 cameras at 3–5 fps (measured: 73 ms/frame, YOLOv8n, 2-core VM).\n"
    "HA = second server with auto-failover (≤ 35 s); adding cameras = paste RTSP URL in the web UI (~5 min).",
    size=14, color=WHITE)

# ================================================================ S10 open source
s = new_slide()
header(s, "Open-Source Foundation — Zero Licensing, Forever")
table(s, 0.55, 1.7, 12.23,
      ["Component", "Commercial cost", "IBVAP (open source)"],
      [
          ["Operating system", "Windows Server ₹0.4–1 L", "Ubuntu Server — ₹0"],
          ["AI / ML framework", "MATLAB / proprietary ₹2–10 L", "PyTorch / ONNX Runtime — ₹0"],
          ["Database", "Oracle / SQL Server ₹5–50 L", "PostgreSQL — ₹0"],
          ["Web / API server", "IIS licences ₹0.5–2 L", "Nginx + FastAPI — ₹0"],
          ["Video processing", "Commercial SDK ₹2–20 L", "FFmpeg / OpenCV — ₹0"],
          ["VMS + analytics licences", "₹10–50 L + per-camera/year fees", "Custom platform, open models — ₹0"],
      ],
      [3.4, 4.4, 4.4], size=12.5, row_h=0.5)
box(s, 0.55, 5.15, 12.23, 1.2, fill=RGBColor(0x12, 0x2A, 0x1A))
txt(s, 0.8, 5.3, 11.8, 0.9,
    "One-time licensing savings: ₹25 L – 1.5 Cr    ·    Annual renewals avoided: ₹5 – 50 L/year\n"
    "Full source control — no vendor dependency, upgrades are file swaps.",
    size=14.5, color=GREEN, bold=True)

# ================================================================ S11 implementation
s = new_slide()
header(s, "Implementation Plan")
phases = [
    ("PHASE 1 — PILOT", "Months 1–3 · ₹2–4 L",
     "2–3 BOPs · 10–20 cameras\n• Deploy on existing server\n• Configure fences, tune thresholds\n• Train BOP operators (2 h/BOP)\n• Performance report + go/no-go"),
    ("PHASE 2 — ROLLOUT", "Months 4–12 · ₹0–2 L",
     "20–100 BOPs · 100–500 cameras\n• Add cameras via web UI (~5 min each)\n• Per-BOP zones & alert rules\n• C2 system integration (REST API)\n• No new hardware required"),
    ("PHASE 3 — SCALE", "Year 2+ · ₹0–3 L",
     "100–1000+ cameras\n• Second server for HA (if >200 cams)\n• Behaviour prediction, multi-cam tracking\n• Field-officer mobile app\n• Automated model retraining"),
]
x = 0.55
for title, meta, body in phases:
    box(s, x, 1.7, 3.95, 5.0)
    txt(s, x + 0.2, 1.9, 3.55, 0.45, title, size=15, color=AMBER, bold=True)
    txt(s, x + 0.2, 2.4, 3.55, 0.4, meta, size=12, color=GREEN, bold=True)
    txt(s, x + 0.2, 2.95, 3.6, 3.6, body, size=12.5, color=WHITE)
    x += 4.15

# ================================================================ S12 MVP
s = new_slide()
header(s, "Not a Slide, a Running System — MVP Demonstrated")
demos = [
    ("4-camera live wall", "3 border scenes (IR night / day / dusk) + real CNN feed, server-annotated"),
    ("Real CNN detection", "YOLOv8n on live footage: person 0.88 · car 0.80 — measured on a 2-core VM"),
    ("Virtual fence events", "intrusion + loitering firing < 3 s, deduped, severity-ranked"),
    ("Evidence on demand", "snapshot at breach + 20-second MP4 clips, searchable & downloadable"),
    ("Ops-grade controls", "JWT + RBAC (admin/operator/viewer), audit log, WS alerts with poll fallback"),
    ("Integration-ready", "REST API for C2: events, clips, status, camera & zone management"),
]
for i, (t, d) in enumerate(demos):
    x = 0.55 + (i % 2) * 6.2
    y = 1.7 + (i // 2) * 1.35
    box(s, x, y, 6.03, 1.2)
    txt(s, x + 0.22, y + 0.14, 5.6, 0.4, t, size=14.5, color=AMBER, bold=True)
    txt(s, x + 0.22, y + 0.56, 5.6, 0.6, d, size=12, color=WHITE)
box(s, 0.55, 5.85, 12.23, 0.95, fill=RGBColor(0x12, 0x2A, 0x1A))
txt(s, 0.75, 6.0, 11.9, 0.7,
    "Proposal §14 MVP targets met: 3+ cams @ 5 fps on CPU laptop-class VM · alert latency < 3 s · > 85% detection · mobile-responsive dashboard",
    size=14.5, color=GREEN, bold=True)

# ================================================================ S13 risks
s = new_slide()
header(s, "Risk Mitigation")
table(s, 0.55, 1.7, 12.23,
      ["Risk", "Mitigation"],
      [
          ["Existing server insufficient", "20-camera pilot proves capacity first; RAM/storage upgrade costs only ₹0.4–0.65 L"],
          ["Network bandwidth limited", "Adaptive streaming works at 2 Mbps/camera; motion-gated selective processing"],
          ["AI accuracy concerns", "Per-BOP tunable thresholds, multi-frame confirmation, quality gating; continuous retraining"],
          ["Central server failure", "HA pair with auto-failover (≤ 35 s), daily backups, 99.5%+ uptime target"],
          ["Need GPU later", "Add one GPU (₹0.5–1 L) to existing server — optional, never required"],
          ["Scale beyond 200 cameras", "Second server (₹1.5–3 L) — still < 10% of per-camera alternatives"],
      ],
      [4.0, 8.2], size=12.5, row_h=0.62)

# ================================================================ S14 ask
s = new_slide()
box(s, 0, 1.6, 13.333, 4.4, fill=PANEL)
txt(s, 1.0, 1.95, 11.3, 0.9, "The Ask", size=30, color=AMBER, bold=True,
    align=PP_ALIGN.CENTER)
txt(s, 1.0, 2.85, 11.3, 0.6,
    "Approve a ₹2–4 lakh, 3-month pilot", size=22, color=WHITE, bold=True,
    align=PP_ALIGN.CENTER)
txt(s, 2.2, 3.7, 9.0, 2.0,
    "•  2–3 pilot BOPs · 10–20 cameras · existing server (no BOP hardware)\n"
    "•  Full analytics suite + web dashboard + operator training\n"
    "•  MVP demo within 4 weeks · performance report · go/no-go decision\n"
    "•  Expected: proven system for border-wide rollout at < 10% of alternatives' cost",
    size=15, color=WHITE, align=PP_ALIGN.CENTER)
txt(s, 1.0, 6.35, 11.3, 0.5,
    "Timeline:  M1–3 pilot  →  M4–6 rollout decision  →  M7–12 border-wide deployment",
    size=14, color=MUT, align=PP_ALIGN.CENTER)
txt(s, 1.0, 6.85, 11.3, 0.4,
    "Project Team: [Your College / Team Name]   ·   [email]   ·   [phone]",
    size=12, color=MUT, align=PP_ALIGN.CENTER)

os.makedirs("docs/presentation", exist_ok=True)
out = "docs/presentation/IBVAP-Proposal-Deck.pptx"
prs.save(out)
print("wrote", out, f"({len(prs.slides.__iter__.__self__._sldIdLst)} slides)")
