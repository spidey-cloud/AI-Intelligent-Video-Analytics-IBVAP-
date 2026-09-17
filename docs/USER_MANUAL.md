# IBVAP User Manual — BOP Operators

*For personnel operating the IBVAP console from a BOP, check post, or command
centre. Reading time: ~10 minutes.*

---

## 1. Getting in

1. Open the console URL in any browser (desktop, tablet or phone).
2. Sign in with the username/password issued by your sector IT.
   (Demo accounts: `admin / admin123`, `operator / operator123`, `viewer / viewer123`.)
3. Your role decides what you can do:

| Role | Can do |
|---|---|
| **viewer** | Watch live cameras, read alerts & events, open evidence |
| **operator** | Everything above + acknowledge alerts, create/delete zones, register cameras |
| **admin** | Everything above + user management, delete cameras |

Your session lasts 12 hours; sign out when you leave the console.

## 2. Live View (your home screen)

* **Camera wall** — every camera you are cleared to see, with server-side
  detection boxes (person / car / truck / bus / motorcycle + confidence +
  track ID). Green polygons are the configured **zones**; they flash red for
  4 seconds after a breach.
* **Status dots** — green = streaming, red = offline. If a camera goes red,
  it is trying to reconnect by itself; do nothing unless it stays red > 5 min
  (then report to IT — see Admin Guide §7).
* **Live Alerts panel** (right) — newest first, red border = high severity
  (person intrusion), amber = medium (vehicle intrusion / loitering).
  Each alert shows camera, class, zone and time.
* **Alert sound** — new high-severity alerts play a two-tone chime, medium
  a single tone. Toggle with the 🔔/🔕 button in the header (default on;
  your choice is remembered on this computer). Browsers require one click
  (e.g. the login) before audio is allowed — that happens automatically.
* **Acknowledge** — click *Acknowledge* on an active alert so the next officer
  knows it is being handled. Acknowledgement is recorded with your name.

**Typical response flow (drill this):**
alert sounds/visible → read camera + zone → verify on live view →
ACK → if real breach, initiate the BOP SOP (lights, challenge, report) →
attach evidence later from the Events tab.

## 3. Events tab (the searchable record)

Every analytics event is stored permanently with its evidence:

* **Filters** — camera, type (intrusion / loitering), free-text search
  (class, camera name, type).
* **Columns** — time (UTC), camera, type, class, severity, confidence,
  status, zone, and two evidence links:
  * **snap** — annotated frame at the moment of breach (opens in new tab)
  * **clip** — 20-second MP4 (10 s before the breach + after). Available once
    the event closes (a few seconds after the intruder leaves the zone).
* **Statuses** — `active` (in progress) → `acknowledged` (someone handled it)
  → `closed` (auto, when the track left / was lost).
* Events cannot be edited or deleted (tamper-evidence); only status changes,
  which are audit-logged.

## 4. Zone Editor (operator+)

Configure *where* the platform should watch:

1. Pick a camera → **Load latest frame**.
2. Click on the frame to drop the polygon corners (minimum 3). Click the
   *kind*:
   * `perimeter` — boundary line/strip (fence, gate approach),
   * `restricted` — no-entry area (gate interior, restricted strip),
   * `area` — open area for loitering detection.
3. Name it (e.g. *"Perimeter fence line"*) → **Save zone**.
4. The zone appears green on the live view immediately (≤ 3 s).
   *Clear sketch* resets your drawing without touching saved zones.
   The ✕ next to a zone deletes it (confirm with the officer-in-charge).

Zones are stored as resolution-independent coordinates, so a camera change
does not lose your drawings.

## 5. Cameras tab (operator+)

* **Registered cameras** table — name, BOP, source, live status.
* **Register camera** — pick BOP, name it, choose source:
  * *RTSP* — paste the IP camera's RTSP URL (over the SSB VPN). The camera
    appears on the wall within ~10 s. **This is the whole onboarding —
    no hardware, no site visit.**
  * *Video file* / *Synthetic scene* — for training/demo use.
* Admins can additionally ✕-delete cameras.

## 6. Reading a detection box

`person 0.88 #14` = class **person**, confidence **0.88** (0–1),
**track #14** (stable while the same person stays in view). Confidence below
~0.5 is treated as unreliable by the rule engine — don't chase it.

## 7. Quick reference

| I want to… | Go to |
|---|---|
| See what's happening now | Live View |
| Handle an alert | Live View → alert → Acknowledge |
| Get proof of an incident | Events → filter → snap / clip |
| Add a watched area | Zone Editor |
| Add a new camera | Cameras → Register camera |
| Camera shows red | wait 5 min → report to IT (Admin Guide §7) |

*Training video (Hindi/English) and this manual are delivered with the pilot
deployment; 2-hour hands-on session per BOP.*
