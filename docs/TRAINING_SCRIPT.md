# IBVAP — BOP Training Script (Trainer Edition)
### AI-Based Intelligent Video Analytics Platform · Border Post Operators
**Duration:** 2 hours (120 min) · **Audience:** BOP command staff + video-post operators (4–8 pax) · **Language:** Bilingual — Hindi/English (हिंदी/अंग्रेज़ी)
**Language of delivery:** Hindi first, English technical terms kept (Devanagari translation in *(कॉंसोल)*). All dashboard labels stay in English — trainees will use the console exactly as it is shown here.

> **Trainer notes:** This script is line-by-line. Text in **bold** is spoken. The *(Hindi: …)* lines are the Devanagari version — deliver in whichever order your audience prefers (recommended: Hindi sentence, then English). Demo commands assume the live prototype is running on the training laptop.

---

## 0 · Session setup (before trainees arrive)

| # | Item | Check |
|---|------|-------|
| 1 | Training laptop / SSB server VM with IBVAP running | `curl -s localhost:8000/api/system/status` returns `"cameras_online": 4` |
| 2 | Projector showing browser at `http://<server>:8000/` (login screen visible) | ✓ |
| 3 | Seeded demo cameras: CAM-01 North Gate (IR), CAM-02 West Approach, CAM-03 Checkpost, CAM-04 live-crosswalk (real AI) | Events flowing (~1 event / 15–30 s) |
| 4 | Printed handouts: this script's quick-reference cards (Section 8) | 1 per trainee |
| 5 | Spare demo logins: `admin/admin123`, `operator/operator123`, `viewer/viewer123` | ✓ |

---

## 1 · Opening & objectives (0:00 – 0:10)

**Good morning/afternoon. Aaj hum aapko IBVAP — hamara naya AI-based video analytics system — seekhaayenge.**
*(Hindi: "सुप्रभात। आज हम आपको IBVAP — हमारा नया AI-आधारित वीडियो एनालिटिक्स सिस्टम — सिखाएँगे।")*

**Bold, then Hindi:**
- **This system watches your existing cameras — it does not need any new hardware at the BOP.**
  *(Hindi: "यह सिस्टम आपकी मौजूदा कैमरों पर नज़र रखता है — BOP पर कोई नया हार्डवेयर ज़रूरी नहीं।")*
- **It calls out intrusions and loitering on your screen in under 3 seconds — 24×7, so your men can sleep.**
  *(Hindi: "यह intrusion और loitering को 3 सेकंड के अंदर स्क्रीन पर दिखाता है — 24×7, ताकि आपका जवान आराम कर सके।")*
- **Today's three promises: (1) log in and see the live wall, (2) draw a virtual fence yourself, (3) close an event with evidence.**

**House rules:**
- Phones on silent; ask questions any time *(सवाल कभी भी पूछ सकते हैं)*.
- The console is a **web page** — same on any computer with a browser.

---

## 2 · System overview — what it is and is not (0:10 – 0:25)

**Key message: software only, on what you already have.**
*(Hindi: "बस सॉफ्टवेयर — आपके जो है उसी पर चलता है।")*

| What trainees should understand | Spoken version (English) | Hindi gloss |
|---|---|---|
| No new sensors, no new cables | "Same RTSP cameras you use today, same VPN link to the centre." | "आज जो RTSP कैमरा है वही, वही VPN लींक।" |
| Where the AI runs | "All processing on the central server — the BOP sends only video, never analysis." | "सारा processing सेंट्रल सर्वर पर — BOP सिर्फ वीडियो भेजता है।" |
| What it detects | "Person or vehicle crossing a line you drew, or standing too long where they shouldn't." | "जो लीन बनाई है उस पर person/vehicle का पार करना, या ज़रूरी नहीं वहाँ खड़े रहना।" |
| What happens on an event | "Alert on screen + a photo snapshot + a 20-second clip saved as evidence." | "स्क्रीन पर alert + photo + 20 सेकंड का clip — सब सबूत के तौर पर सहेजा जाता है।" |
| What it is NOT | "It does not replace you. It tells you **where to look**." | "यह आपकी जगह नहीं लेता। यह बताता है **कहाँ देखें**।" |

**Demo (2 min):** open browser → show login screen. Point out the name: *IBVAP — Border Surveillance Console*.

---

## 3 · Login & roles (RBAC) (0:25 – 0:35)

**Explain the three roles — then prove it:**

1. **Viewer (देखने वाला)** — can see live wall, events, reports. Cannot change anything.
2. **Operator (संचालक)** — can also draw fences, add cameras, acknowledge events.
3. **Admin (प्रशासक)** — everything, including user accounts.

**Live demo:**
```
Log in as viewer/viewer123  → try "Zone Editor" tab → button disabled
Log in as operator/operator123 → same tab → now editable
Log in as admin/admin123 → "Admin" tab → user list visible
```
**Said:** *"(1) दर्ज किया viewer से — Zone Editor बंद। (2) operator से — खुल गया। (3) admin — सब कुछ।"*
**Said:** "Every action is logged in an audit trail — who changed what, when. SSB compliance."
*(Hindi: "हर काम का रिकॉर्ड रहता है — कब, किसने, क्या बदला।")*

---

## 4 · Live wall (0:35 – 0:50)

**Navigate: `Live Wall` tab.**

**Walk through, one camera at a time (30 s each):**
- **CAM-01 · North Gate (IR night):** "Black-and-white night vision. Watch the detection box — a **green/yellow box** follows a person. The box is the AI's 'I see this'."
  *(Hindi: "लाल/पीली बॉक्स = AI उस person को देख रहा है।")*
- **CAM-02 · West Approach:** "See the **red fence line**? That is a virtual boundary drawn on the video. Cross it → alert."
- **CAM-03 · Checkpost (dusk):** "Vehicle class as well as person — *vehicle* is labelled in the box."
- **CAM-04 · Live crosswalk (real AI):** "This one runs real deep-learning on a real video — you can see person and car boxes moving."

**Key words to hammer:**
| Term | Meaning | Hindi gloss |
|---|---|---|
| Detection box | AI sees an object | "AI को दिखा" |
| Virtual fence / zone | Line/area you drew on video | "आपकी बनी लीन" |
| Event | Fence crossed or loiter detected | "घटना" |
| Evidence | Snapshot + clip auto-saved | "सबूत" |

**Q&A checkpoint** (60 s): "Which box colour means vehicle?" *(जब vehicle दिखे तो बॉक्स में क्या लिखा होता है?)*

---

## 5 · Alerts & event timeline (0:50 – 1:05)

**Alerts tab (live):**
- "Every 15–30 seconds during this demo you will see a **red banner** pop up: `INTRUSION — CAM-02 · West Approach — confidence 0.87`."
- **Sound + colour + text** — designed for a dark watch room.
- **Latency promise:** from the moment the person crosses, to the alert: **under 3 seconds.** *(Hindi: "लीन पार होते ही 3 सेकंड में alert।")*

**Events tab (searchable history):**
```
Filter by: camera ▸  CAM-02        Type ▸  all        Status ▸  closed
Search box: type "north"           → only North Gate events
```
**Click one event row → detail panel shows:**
1. **Snapshot** — the exact frame at the moment of the event (zoomable).
2. **Clip** — 10 seconds *before* + 10 seconds after (you see **why** it happened).
3. **Confidence** — 0.0–1.0, how sure the AI is (0.85+ = high trust).
4. **Status**: `active → acked → closed`.
5. **Acknowledge button** (operator+) — marks "I have seen this". **Close** marks handled.

**Said:** "Acknowledge is your diary. If an event sits *active* for 30 minutes, your commander will ask why."
*(Hindi: "Acknowledge आपका डायरी है। 30 मिनट तक active रहने पर command पूछेगा।")*

**Hands-on (5 min):** give each trainee the **operator** account on a split screen (or one laptop, one trainee at a time):
1. Find the latest intrusion event.
2. Open it, watch the clip.
3. **Acknowledge** it, then **close** it.
4. Check it moved to `closed` in the list.

---

## 6 · Virtual fence editor (1:05 – 1:20)  ← *the core skill*

**Navigate: `Zone Editor` tab (operator/admin only).**

**Step-by-step, trainer demonstrates on CAM-01 while trainees follow on their screen:**

| Step | Action on console | Spoken script |
|---|---|---|
| 1 | Select camera **CAM-01** | "Pehle camera chunein." *(पहले कैमरा चुनें।)* |
| 2 | Click **Add zone**, pick type **Intrusion line** | "Line ke liye 'Intrusion' — vehicle/person is līn ko pāre toh alert." |
| 3 | Click **3–5 points** across the road, from left edge to right edge; click *Finish* | "Raste ko daakhe kaat-ti hui line banaiye. 3 se 5 points." |
| 4 | Pick type **Loitering area**: drag a **rectangle** where a person should not stand (e.g., 10 m before the gate) | "Jahan koi khada nahi hona chahiye — wahan box banao. 15 second se zyada khada raha toh alert." |
| 5 | **Save** | "Save dabao. Ab line laal dikhegi live wall par." |

**Rule of thumb (write on whiteboard):**
- **Intrusion line** = across the thing you guard (road, gate, wire). *Ek line.*
- **Loitering area** = the spot people loiter at (bus stop, wall corner). *Ek box.*
- Zone too big → false alarms. Keep it **tight but forgiving** — 2–3 m margin on the line. *(Hindi: "Zone tight rakho — false alert kam honge.")*

**Hands-on (5 min):** each trainee draws one intrusion line on CAM-03, saves it, and goes to Live Wall to see it appear in red.
**Troubleshooting tip:** "If your line does not appear: you are logged in as **viewer** — viewers cannot edit. Log in as operator."

---

## 7 · Camera registration & adding sources (1:20 – 1:30)

**Navigate: `Cameras` tab (operator+).**

**Demonstrate adding a real RTSP camera:**
```
POST /api/cameras (via UI "Add camera"):
  Name:      BOP-01 · South Perimeter
  Source:    rtsp://10.20.30.40:554/stream1
  Resolution: 640x360 (analytics) — leave as suggested
```
**Said:** "It connects within ~10 seconds. When its tile says **ONLINE**, register it in the paper logbook too."
*(Hindi: "~10 सेकंड में जोड़ जाएगा। Tile 'ONLINE' kahe toh paper logbook mein bhi likh dein.")*

**Video file / trial source (for training rooms):**
```
Type: video file, Path: data/videos/crosswalk.mp4
```

**Delete (admin only):** select → **Delete**. "Deleting a camera keeps its event history — the database is the record." *(Hindi: "Camera hata diye, events rahe — database hi record hai।")*

**Hands-on (3 min):** one trainee adds CAM-05 (video file), watches it come online, then an admin deletes it.

---

## 8 · Reports & BOP map (1:30 – 1:40)

**Reports tab:**
- **5 stat cards** — Total / Active / Acked / Closed / Avg confidence.
- **Daily bar chart** (7/30/90-day window, selectable) — "This is your **situation trend** for the weekly report. A rising bar = more activity; investigate before the commander asks."
- **Mix bars** — intrusion vs loitering; **per-camera table** — which camera sees the most.

**Map tab:**
- Schematic **BOP deployment map** — each BOP plotted from its GPS (lat/long); cameras shown as dots, **coloured by status** (green online / red offline).
- **Click a BOP → camera list on the right.** *(Hindi: "BOP par click — saamne uske cameras.")*
- "In production this is a real GIS map with the full BOP chain; the layout is identical."

**Said:** "Your daily/weekly report now takes **2 minutes** instead of 2 hours — export what you see here."
*(Hindi: "Daily report ab 2 minute ka kaam — 2 ghante ka nahi.")*

---

## 9 · Operations SOP & maintenance (1:40 – 1:55)

### 9.1 Event handling SOP (print & pin)

```
ALERT SEEN
  ├─ 1. Look at the live wall tile (already red-bordered)
  ├─ 2. Confirm: real incursion OR false alarm (animal, shadow, vehicle of own men)
  ├─ 3a. REAL  → acknowledge → follow BOP standing orders (fire control,
  │          communication with next BOP) → close after situation stable
  └─ 3b. FALSE → acknowledge → close, note "false" in remarks if repeated
        → repeated false alarms? → tell admin to tighten the zone
```

### 9.2 Daily checklist (operator, 5 min each shift)
- [ ] All camera tiles **ONLINE** (check Live Wall + Map tab)
- [ ] No event stuck in **active** > 30 min
- [ ] Audio test: play a test alert once per shift
- [ ] Snapshot + clip spot-check: open yesterday's first event, play clip
- [ ] Network: VPN link status (existing SSB link) — same as today

### 9.3 Common faults & first response

| Symptom | First response | Escalate to |
|---|---|---|
| Camera tile **OFFLINE** | Tile auto-reconnects (10 s). If > 5 min: check camera power/PTZ | Camera vendor (existing contract) |
| No alerts for 24 h but cameras online | System may be blind — verify with video file test camera | IBVAP helpdesk (central) |
| Many false alarms, one zone | Zone too big / near road edge | Admin → Zone Editor → tighten |
| Alert late (> 3 s) | VPN congestion | Network/VPN team |
| Console unreachable | Try `http://<server>:8000` from BOP LAN PC | Central IT |

### 9.4 What the trainee must never do
- **Never** delete the central server's event database — it is the legal record.
- **Never** disable a zone "because of false alarms" — tighten it instead; disablement needs officer's written OK.
- **Never** share admin credentials — one user per person (audit trail).

---

## 10 · Wrap-up & assessment (1:55 – 2:00)

**Recap (say once, fast):**
1. Software only — your cameras, your VPN. *(सॉफ्टवेयर बस — आपका कैमरा, आपकी VPN।)*
2. AI draws the box, **you make the decision.**
3. Line = intrusion, Box = loitering. Tight zones = fewer false alarms.
4. Acknowledge → every event, no exceptions.

**5-question assessment (verbal, 60 s):**
1. What do the two zone types mean? *(दो zone types क्या हैं?)*
2. A person crosses the line — how fast is the alert? *(कितने सेकंड में alert?)*
3. What evidence is saved with every event? *(हर event के साथ क्या-क्या save होता है?)*
4. Which role can draw a fence? *(कौन role fence बना सकता है?)*
5. An event has been *active* for 40 minutes. What do you do? *(40 मिनट active event — क्या करेंगे?)*

**Close:**
**"Aaj se aapke watch room mein AI saathi hai. Wo nind nahi gata — lekin faisla aapka hi hoga."**
*(Hindi: "आज से आपके watch room में AI साथी है। वह नींद नहीं गता — लेकिन फैसला आपका ही होगा।")*

---

## Appendix A · Quick-reference cards (print, 1 page)

```
┌─ ROLES ─────────────────────────────────────────────┐
│ viewer    : see live wall, events, reports          │
│ operator  : + zones, cameras, ack/close events      │
│ admin     : + users, delete cameras                 │
│ logins: admin/admin123 · operator/operator123       │
│         viewer/viewer123                            │
└──────────────────────────────────────────────────────┘
┌─ ZONES ─────────────────────────────────────────────┐
│ Intrusion LINE  → across road/gate/wire (3–5 pts)   │
│ Loitering AREA  → box; alert if >15 s inside        │
│ Tight but forgiving: 2–3 m margin                   │
└──────────────────────────────────────────────────────┘
┌─ EVENT SOP ─────────────────────────────────────────┐
│ see → confirm (real/false) → ACK → act/close        │
│ active > 30 min = investigate                       │
│ evidence: snapshot + 20 s clip, auto-saved          │
└──────────────────────────────────────────────────────┘
┌─ TROUBLE ───────────────────────────────────────────┐
│ offline > 5 min      → camera vendor                │
│ no alerts 24 h       → IBVAP helpdesk               │
│ false alarms         → admin tightens zone          │
│ console unreachable  → central IT                   │
└──────────────────────────────────────────────────────┘
```

## Appendix B · Glossary (EN ↔ HI)

| English | Hindi | Note |
|---|---|---|
| Border Outpost (BOP) | सीमा भवन (BOP) | As per SSB nomenclature |
| Intrusion | प्रवेश (अनुन्यक्त) | Fence/line crossing |
| Loitering | घूमना-घूमना / ठहरना | Standing > 15 s in a zone |
| Detection box | डिटेक्शन बॉक्स | AI's object box |
| Virtual fence | वर्चुअल फ़ेंस | Zone on video |
| Snapshot | स्नैपशॉट / तस्वीर | Event frame |
| Evidence clip | सबूत क्लिप | 10 s before + 10 s after |
| Confidence | विश्वसनीयता (0–1) | 0.85+ = high |
| Acknowledge | पहचानना / दर्ज करना | "Seen" mark |
| False alarm | ग़लत अलर्ट | Animal/shadow/own vehicle |
| Live wall | लाइव वॉल | Multi-camera grid |
| RBAC | भूमिका-आधारित पहुँच | Role-based access |
