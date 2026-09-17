#!/usr/bin/env python3
"""Generate docs/EXECUTIVE_SUMMARY.docx (printable, 1-page-per-section style).

Usage:  python3 scripts/make_exec_docx.py
Output: docs/EXECUTIVE_SUMMARY.docx
"""
import os

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "docs", "EXECUTIVE_SUMMARY.docx")

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
TEAL = RGBColor(0x0E, 0x74, 0x90)
GREY = RGBColor(0x55, 0x5F, 0x6B)


def h(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for r in p.runs:
        r.font.color.rgb = NAVY if level == 1 else TEAL
    return p


def para(doc, text, size=10.5, bold=False, color=None, space_after=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    if color:
        r.font.color.rgb = color
    return p


def bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(it)
        r.font.size = Pt(10.5)


def table(doc, headers, rows, widths=None):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = t.rows[0].cells
    for i, htxt in enumerate(headers):
        hdr[i].text = ""
        r = hdr[i].paragraphs[0].add_run(htxt)
        r.font.bold = True
        r.font.size = Pt(10)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(val))
            r.font.size = Pt(10)
    if widths:
        for i, w in enumerate(widths):
            for row in t.rows:
                row.cells[i].width = Cm(w)
    return t


def main():
    doc = Document()
    for section in doc.sections:
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(2.0)
        section.top_margin = Cm(1.8)
        section.bottom_margin = Cm(1.8)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    # ---- title block -------------------------------------------------
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("IBVAP")
    r.font.size = Pt(30)
    r.font.bold = True
    r.font.color.rgb = NAVY
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("AI-Based Intelligent Video Analytics Platform for Border Surveillance")
    r.font.size = Pt(14)
    r.font.bold = True
    r.font.color.rgb = TEAL
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(
        "Executive Summary  ·  Problem Statement ID 26187  ·  SSB / MHA  ·  "
        "Reference architecture + working prototype  ·  September 2026"
    )
    r.font.size = Pt(9.5)
    r.font.color.rgb = GREY
    doc.add_paragraph()

    # ---- 1. what & why ------------------------------------------------
    h(doc, "1. What and Why", 1)
    para(doc,
         "IBVAP turns SSB's existing border video surveillance — RTSP cameras already "
         "installed at Border Outposts (BOPs) and connected over the existing SSB VPN — "
         "into an intelligent, 24×7 surveillance system. Deep-learning analytics "
         "(YOLOv8, CPU-only) detect person/vehicle intrusions across virtual fences and "
         "loitering in restricted areas, and raise an alert on the watch-room console in "
         "under 3 seconds, with automatic evidence (snapshot + 20-second clip) for every "
         "event. The system needs zero new hardware at the BOP: it is software that runs on "
         "a central SSB server (16–32 cores, 64 GB+, 5–10 TB, 1 Gbps) and reuses the "
         "existing camera/VPN estate.")
    para(doc,
         "A complete, working reference prototype is delivered with this summary: live "
         "multi-camera wall, real AI inference on video, virtual-fence editor, real-time "
         "WebSocket alerts, searchable event database with evidence, role-based access "
         "(admin/operator/viewer), reports & analytics, and an offline BOP deployment map — "
         "all deployable via Docker.")

    # ---- 2. headline numbers ------------------------------------------
    h(doc, "2. Headline Numbers — proposal target vs prototype evidence", 1)
    table(doc,
          ["Metric (proposal §7)", "Target", "Prototype evidence"],
          [
              ["Alert latency (fence crossing → alert)", "< 3 s", "p50 2 ms · p95 3 ms · max 4 ms — measured end-to-end via real WebSocket (KPI report)"],
              ["Detection accuracy", "> 85%", "Event precision/recall 100% on ground-truth scene; YOLOv8n person-conf p50 0.81, 31% of detections ≥ 0.85; annotated-set eval in Phase 1"],
              ["Frames per camera (CPU, 640×360)", "3–5 fps", "16 fps single-stream measured on 2-core VM (YOLOv8n); scales 10 → 1000+ cams via workers/GPU option"],
              ["New BOP hardware", "None", "None — RTSP + VPN reuse only"],
              ["Event storage", "Event-only ≈ 100 GB/mo per 100 cams", "Snapshots + 10 s pre-roll clips only; no continuous recording"],
              ["Evidence per event", "Snapshot + 10–20 s clip", "JPG snapshot + 20 s MP4 (10 s before / 10 s after)"],
              ["Deployment", "Docker, PostgreSQL production", "Dockerfile + docker-compose; SQLite in prototype, Postgres swap is config-level"],
              ["Access control", "RBAC + audit", "3 roles enforced (401/403 verified) + audit log table"],
          ],
          widths=[5.6, 4.0, 7.0])

    # ---- 3. architecture in one breath --------------------------------
    h(doc, "3. Architecture in One Breath", 1)
    bullets(doc, [
        "Capture: existing RTSP cameras (H.264) over the existing SSB VPN; 640×360 analytics resolution; motion-triggered frame sampling to cut CPU.",
        "Analytics: FastAPI service with per-camera worker threads → YOLOv8n (INT8-capable, CPU) person/vehicle detection → IoU tracker → rule engine (intrusion line / loitering area, per-zone cooldown, dropout tolerance, and track handoff — a tracker ID reset can't fake a re-intrusion).",
        "Alerting: in-process alert hub → WebSocket push to consoles (< 1 s fan-out) with polling fallback; severity = high (intrusion) / medium (loitering).",
        "Evidence: ring buffer of 10 s pre-roll per camera → JPG snapshot + 20 s MP4 clip auto-attached to every event.",
        "Data: events, alerts, cameras, zones, BOPs, users, audit — SQLite in the prototype, PostgreSQL in production (identical schema, config-level swap).",
        "Console: single-page web console (no build step) — live wall with drawn boxes, alert feed, event timeline with search, fence editor, camera registration, reports & analytics, BOP map, admin users.",
        "Scale-out: stateless analytics workers behind a queue; horizontal scale from 10 to 1000+ cameras; GPU option later (OpenVINO/TensorRT); multi-tenant BOP scoping and C2 API are designed-in.",
    ])

    # ---- 4. what's in the delivery ------------------------------------
    h(doc, "4. What Is Delivered", 1)
    table(doc,
          ["Deliverable", "Status"],
          [
              ["Working prototype (4 demo cameras incl. real-AI video, RBAC, zones, events, evidence, alerts)", "Built & verified live"],
              ["System architecture document (17 sections) + 5 diagrams (logical, deployment, pipeline, sequence, ER)", "Delivered"],
              ["User manual, admin guide, API reference, training script (2-hr bilingual BOP session)", "Delivered"],
              ["Automated test suite — 27 tests (geometry, tracker, event engine, full API incl. WebSocket, latency)", "All passing (18.7 s)"],
              ["KPI verification report — measured alert latency, event precision/recall, YOLO inference audit", "Delivered (docs/KPI_VERIFICATION.md)"],
              ["Docker + docker-compose deployment, .env config, demo asset fetcher", "Delivered"],
              ["Reports & analytics endpoint + console (daily trend, type/severity mix, per-camera load)", "Built & verified live"],
              ["BOP deployment map (offline schematic, GPS-plotted, status-coloured cameras)", "Built in console"],
              ["Budget workbook (6 sheets, ₹) + 14-slide proposal deck (PPTX)", "Delivered"],
          ],
          widths=[11.6, 5.0])

    # ---- 5. roadmap ----------------------------------------------------
    h(doc, "5. Phased Roadmap", 1)
    table(doc,
          ["Phase", "Scope", "Exit criteria"],
          [
              ["Phase 0 — Pilot (2–3 BOPs, 10–20 cams)", "Deploy on existing SSB server; operator training (script provided); weekly tuning of zones", "Alert latency < 3 s in field; operator acceptance"],
              ["Phase 1 — Hardening (1–3 months)", "PostgreSQL, Nginx TLS, MFA, HA pair, ONNX-INT8 inference, load test to 100 cams", "4-week soak, < 2% false positives per shift after tuning"],
              ["Phase 2 — Scale (3–9 months)", "Queue-based workers to 1000+ cams, multi-tenant BOP scoping, GIS map with real basemap, C2 API", "Design capacity demonstrated at 500 cams"],
              ["Phase 3 — Advanced analytics (optional)", "ANPR, face watchlist, abandoned-object, multi-frame behaviour rules", "Feature-by-feature, funded separately"],
          ],
          widths=[4.4, 6.4, 5.8])

    # ---- 6. budget at a glance -----------------------------------------
    h(doc, "6. Budget at a Glance (₹, indicative)", 1)
    para(doc,
         "Full workbook: docs/budget/IBVAP-Budget.xlsx (6 sheets: pilot, scaling, hardware, "
         "software/licensing, manpower, summary).", size=9.5, color=GREY)
    table(doc,
          ["Head", "Pilot (2–3 BOPs)", "Full build-out (1000+ cams)"],
          [
              ["Software development & integration", "₹ 12–18 L", "₹ 60–90 L (incl. scale-out engineering)"],
              ["Central server (existing SSB estate — uplift only)", "₹ 4–8 L", "₹ 25–40 L (2 nodes HA + storage)"],
              ["Deployment, training, pilot ops (3 months)", "₹ 3–6 L", "₹ 12–20 L"],
              ["Indicative total", "₹ 19–32 L", "₹ 97–150 L"],
          ],
          widths=[7.2, 4.6, 5.8])
    para(doc,
         "Consistent with the proposal's pilot band (₹ 2–4 L per BOP for 10–20 cameras) when "
         "central costs are amortised across the BOP estate.", size=9.5, color=GREY)

    # ---- 7. risks -------------------------------------------------------
    h(doc, "7. Key Risks and Mitigations", 1)
    table(doc,
          ["Risk", "Mitigation (already in design)"],
          [
              ["VPN bandwidth saturation from 1000+ cam streams", "640×360 analytics resolution + motion-triggered sampling; per-BOP ingest caps; edge pre-filter option in Phase 2"],
              ["False alarms eroding operator trust", "Per-zone cooldown, dropout-tolerant tracker, operator acknowledgement loop; tuning SOP in training script"],
              ["CPU inference not keeping up at scale", "INT8/ONNX, worker pool scale-out, GPU option; capacity test at Phase 1 exit"],
              ["Evidence retention & legal chain", "Event-only storage, tamper-evident DB records, audit log of every user action"],
              ["Vendor lock-in", "100% open-source stack (PyTorch/Ultralytics, FastAPI, PostgreSQL, FFmpeg, Docker)"],
          ],
          widths=[6.2, 10.4])

    # ---- 8. next steps ---------------------------------------------------
    h(doc, "8. Immediate Next Steps", 1)
    bullets(doc, [
        "Stakeholder review of this summary + live prototype walkthrough (30 min, demo logins provided).",
        "Confirm pilot BOP shortlist (2–3) and central server allocation (16–32 cores / 64 GB / 5 TB minimum).",
        "Sign off Phase 0 scope; 6-week pilot mobilisation using the delivered deployment package.",
    ])

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(
        "Prepared for SSB / MHA  ·  IBVAP working prototype + reference architecture  ·  "
        "See ARCHITECTURE.md for the full 17-section design  ·  September 2026"
    )
    r.font.size = Pt(8.5)
    r.font.color.rgb = GREY

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print(f"wrote {os.path.abspath(OUT)} ({os.path.getsize(OUT)} bytes)")


if __name__ == "__main__":
    main()
