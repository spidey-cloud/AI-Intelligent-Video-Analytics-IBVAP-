#!/usr/bin/env python3
"""Generate IBVAP-Budget.xlsx from the proposal's cost model (§4, §6, §7).
All amounts in ₹ lakhs unless stated."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

NAVY = "0B1220"
AMBER = "F5A524"
LIGHT = "EEF2FF"
GREY = "64748B"
GREEN = "16A34A"

thin = Side(style="thin", color="CBD5E1")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
hfont = Font(bold=True, color="FFFFFF", size=11)
hfill = PatternFill("solid", fgColor=NAVY)
sfont = Font(bold=True, size=14, color=NAVY)
tfont = Font(bold=True, size=11, color="FFFFFF")
tfill = PatternFill("solid", fgColor=AMBER)
gfill = PatternFill("solid", fgColor="DCFCE7")
bfill = PatternFill("solid", fgColor=LIGHT)


def sheet_title(ws, text, note="All amounts in ₹ lakhs"):
    ws["A1"] = text
    ws["A1"].font = sfont
    ws["A2"] = note
    ws["A2"].font = Font(italic=True, size=9, color=GREY)


def table(ws, row, headers, rows, widths=None, money_cols=(), total_row=False):
    for j, h in enumerate(headers, 1):
        c = ws.cell(row=row, column=j, value=h)
        c.font = hfont; c.fill = hfill; c.border = border
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for i, r in enumerate(rows, 1):
        for j, v in enumerate(r, 1):
            c = ws.cell(row=row + i, column=j, value=v)
            c.border = border
            if i % 2 == 0:
                c.fill = bfill
            if j in money_cols and isinstance(v, (int, float)):
                c.number_format = "#,##0.00"
            if total_row and i == len(rows):
                c.font = Font(bold=True); c.fill = gfill
    if widths:
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w
    return row + len(rows) + 2


wb = Workbook()

# ------------------------------------------------------------- Overview
ws = wb.active
ws.title = "Overview"
sheet_title(ws, "IBVAP — Budget Overview (Problem Statement 26187)")
rows = [
    ["Scenario", "Value", "Notes"],
    ["Deployment size", "100 cameras / 20 BOPs (pilot → rollout)", "Base case for all comparisons"],
    ["One-time investment (IBVAP)", "2.0 – 6.0", "Software dev + optional server"],
    ["Annual operating (IBVAP)", "0.30 – 1.10", "Power + spares + optional support"],
    ["5-year TCO (IBVAP)", "3.2 – 10.4", "Vs 50 – 180 for smart cameras"],
    ["5-year savings vs smart cameras", "80 – 95%", "₹47L – ₹1.7Cr avoided"],
    ["Pilot ask (3 months)", "2.0 – 4.0", "2–3 BOPs, 10–20 cameras, existing server"],
    ["Payback", "Immediate", "Cost avoidance vs any alternative"],
]
table(ws, 4, rows[0], rows[1:], widths=[38, 42, 46], money_cols=(2,), total_row=True)
ws["A13"] = "Sensitivity: per-camera cost falls sub-linearly — see 'Scaling' sheet."
ws["A13"].font = Font(italic=True, size=9, color=GREY)

# --------------------------------------------------------- One-time costs
ws = wb.create_sheet("One-Time Costs")
sheet_title(ws, "One-Time Costs (3 options — proposal §4.1, §6.1)")
ws["A4"] = "Option A — reuse existing SSB server (most common)"
ws["A4"].font = Font(bold=True, color=NAVY)
rows = [
    ["Item", "Low", "High", "Notes"],
    ["Hardware (new)", 0.0, 0.0, "Existing data-centre server"],
    ["Software development", 2.0, 3.0, "10–16 weeks: ingestion, AI, events, dashboard, API, testing"],
    ["Initial setup & configuration", 0.2, 0.5, "Install, 10–20 pilot cameras, 2-day training, docs"],
    ["Total (Option A)", 2.2, 3.5, ""],
]
r = table(ws, 5, rows[0], rows[1:], widths=[40, 10, 10, 58], money_cols=(2, 3), total_row=True)
ws.cell(row=4 + 6, column=1, value="Option B — minor server upgrade (add RAM/storage/NIC)")
ws.cell(row=4 + 6, column=1).font = Font(bold=True, color=NAVY)
rows = [
    ["Item", "Low", "High", "Notes"],
    ["RAM 64GB DDR4", 0.15, 0.25, ""],
    ["Storage 10TB HDD", 0.20, 0.30, "Or reuse NAS/SAN"],
    ["1Gbps NIC", 0.05, 0.10, ""],
    ["Software development", 2.0, 3.0, ""],
    ["Total (Option B)", 2.4, 3.65, ""],
]
r = table(ws, 4 + 7, rows[0], rows[1:], widths=[40, 10, 10, 58], money_cols=(2, 3), total_row=True)
ws.cell(row=4 + 14, column=1, value="Option C — refurbished server (worst case)")
ws.cell(row=4 + 14, column=1).font = Font(bold=True, color=NAVY)
rows = [
    ["Item", "Low", "High", "Notes"],
    ["Refurbished 2×Xeon / 128GB / 10TB", 1.5, 3.0, "e.g. Dell PowerEdge R740"],
    ["Software development", 2.0, 3.0, ""],
    ["Total (Option C)", 3.5, 6.0, "Handles 100–200 cameras"],
]
table(ws, 4 + 15, rows[0], rows[1:], widths=[40, 10, 10, 58], money_cols=(2, 3), total_row=True)

# --------------------------------------------------------------- Scaling
ws = wb.create_sheet("Scaling")
sheet_title(ws, "Scaling Cost (proposal §4.2) — sub-linear growth")
rows = [
    ["Cameras", "Servers needed", "Hardware cost", "Software cost", "Total (one-time)", "Per-camera total"],
    ["1 – 100", "1 (existing / refurb)", "0 – 3.0", "2 – 3.0 (one-time)", "2 – 6.0", "20 – 60k"],
    ["101 – 200", "1 (same server)", "0", "0 (already built)", "0", "0"],
    ["201 – 500", "2", "0 – 3.0", "0", "0 – 3.0", "6 – 15k"],
    ["501 – 1000", "3 – 4", "0 – 6.0", "0", "0 – 6.0", "6 – 12k"],
]
table(ws, 4, rows[0], rows[1:], widths=[16, 24, 16, 22, 20, 18], money_cols=(3, 4, 5))
ws["A11"] = "Key point: 1000 cameras ≈ ₹10–12L total (not ₹3–10Cr like smart cameras)."
ws["A11"].font = Font(bold=True, color=GREEN)

# --------------------------------------------------------- Annual operating
ws = wb.create_sheet("Annual Operating")
sheet_title(ws, "Annual Operating Cost (proposal §4.3)")
rows = [
    ["Item", "Traditional", "IBVAP", "Notes"],
    ["License renewal", "5 – 50", "0", "Open source, forever"],
    ["Hardware maintenance", "2 – 10", "0.10 – 0.20", "1–2 central servers vs 100 BOP edge boxes"],
    ["Support contract", "5 – 20", "0 – 0.5", "Optional"],
    ["Software updates", "2 – 10", "0", "Automated"],
    ["Network connectivity", "(already paid)", "0", "Existing SSB VPN/WAN"],
    ["Power (24/7)", "5 – 15", "0.20 – 0.40", "Central servers only"],
    ["Total annual", "19 – 105", "0.30 – 1.10", "Savings: ₹18–104L per year"],
]
table(ws, 4, rows[0], rows[1:], widths=[26, 16, 16, 52], money_cols=(2, 3), total_row=True)

# ------------------------------------------------------------ 5-yr TCO
ws = wb.create_sheet("5-Year TCO")
sheet_title(ws, "5-Year Total Cost of Ownership — 100 cameras (proposal §4.4, §7)")
rows = [
    ["Solution", "Year 1", "Years 2–5 (each)", "5-Year Total", "Savings vs IBVAP"],
    ["Smart cameras", "30 – 100", "5 – 20", "50 – 180", "95%"],
    ["Edge AI servers at BOPs", "50 – 200", "10 – 30", "90 – 320", "97%"],
    ["Commercial VMS", "10 – 50", "10 – 50", "50 – 250", "96%"],
    ["IBVAP (this proposal)", "2 – 6", "0.3 – 1.1", "3.2 – 10.4", "—"],
]
table(ws, 4, rows[0], rows[1:], widths=[30, 16, 20, 18, 20], money_cols=(2, 3, 4), total_row=True)
ws["A11"] = "Per-camera economics (5-yr TCO):"
ws["A11"].font = Font(bold=True, color=NAVY)
rows = [
    ["Solution", "Initial /cam", "Annual /cam", "5-yr TCO /cam"],
    ["Smart cameras", "30k – 1L", "5 – 10k", "55k – 1.5L"],
    ["Edge AI", "15 – 40k", "3 – 8k", "27 – 72k"],
    ["Commercial VMS", "10 – 50k", "5 – 20k", "35k – 1.5L"],
    ["IBVAP (100 cams)", "2 – 6k", "300 – 1k", "3.5 – 11k"],
    ["IBVAP (500 cams)", "400 – 1.2k", "60 – 220", "700 – 2.3k"],
]
table(ws, 12, rows[0], rows[1:], widths=[30, 16, 16, 18])
ws["A19"] = "At scale, IBVAP costs 95–98% less per camera."
ws["A19"].font = Font(bold=True, color=GREEN)

# ----------------------------------------------------------------- ROI
ws = wb.create_sheet("ROI")
sheet_title(ws, "ROI — 100-camera deployment (proposal §12)")
rows = [
    ["Metric", "Value", "Notes"],
    ["Investment (one-time)", "6.0", "Option C worst case"],
    ["Alternative cost (smart cameras)", "30 – 100", "Immediate cost avoidance"],
    ["Savings (year 1)", "24 – 94", ""],
    ["5-year savings", "50 – 180", ""],
    ["ROI", "400 – 3000%", "On avoided spend"],
    ["Alert latency", "< 3 s (was 5–60 min)", "100–1200× faster"],
    ["Intrusion detection rate", "> 90% (was 30–40%)", ""],
    ["Cameras per operator", "20–30 (was 4–6)", "4–5× productivity"],
    ["False alarms", "< 5% (was high)", "90%+ reduction"],
]
table(ws, 4, rows[0], rows[1:], widths=[34, 26, 40], money_cols=(2,))

out = "docs/budget/IBVAP-Budget.xlsx"
import os
os.makedirs("docs/budget", exist_ok=True)
wb.save(out)
print("wrote", out)
