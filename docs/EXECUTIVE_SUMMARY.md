# IBVAP — Executive Summary (1-pager)

**Problem.** SSB runs thousands of CCTV cameras at BOPs, check posts and
border roads, but they *only record*: 24/7 human watching (a person can
actually supervise 4–6 screens), 30–40% of intrusions caught, incidents
found hours later, and every commercial upgrade (smart cameras, edge AI,
VMS licences) costs ₹50 lakhs–₹10+ crores at scale.

**Solution.** **IBVAP — Intelligent Border Video Analytics Platform:** a
100% software, 100% open-source platform that runs on SSB's *existing*
servers and turns the *existing* IP cameras into an AI surveillance network
through the *existing* VPN. **Zero new hardware at BOPs. No camera
replacement. No per-camera or annual fees.**

**How it works.** Camera RTSP → central CPU workers (YOLO nano, INT8,
3–5 fps, motion-gated) → person/vehicle tracking → virtual-fence intrusion
& loitering rules → event database with **snapshot + 20-second evidence
clip** → sub-3-second alerts to dashboard, mobile and command centre.
Everything is managed from a web console: draw zones remotely, search
events, review evidence, manage users (RBAC + audit).

**Why it costs almost nothing.**

| | Conventional (100 cams, 5 yrs) | IBVAP |
|---|---|---|
| One-time | ₹50L – ₹1.8 Cr (smart cams) | **₹2–6 lakhs** (software + optional server) |
| Annual | ₹19L – ₹1.05 Cr (licences, maintenance, power) | **₹30k – 1.1L** |
| 5-year TCO | ₹50L – ₹3.2 Cr | **₹3.2 – 10.4L** → **80–95% savings** |

One 32-core server sustains **100–200 cameras**; cost grows sub-linearly
(1000 cameras ≈ ₹10–12L total).

**Proven, not promised.** A working reference platform is demonstrated:
4-camera live wall (incl. **real CNN detection on live footage**),
virtual-fence events firing in < 3 s, evidence clips, RBAC, REST/C2 API —
running on a 2-core laptop-class VM at ~8 FPS/camera (proposal §14 MVP
targets met).

**The ask.** Approve a **₹2–4 lakh, 3-month pilot**: 2–3 BOPs, 10–20
cameras on an existing server, full analytics, operator training, and a
go/no-go performance report (accuracy > 85%, latency < 3 s, false alarms
< 5%) — after which border-wide rollout costs < 10% of any alternative.
