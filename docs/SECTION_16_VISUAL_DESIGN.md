# SESHADRIPURAM COLLEGE – SMART ACADEMIC MANAGEMENT SYSTEM
## SECTION 16: Master Visual Design, Interactive Rocket Cursor & Particle Engine Specification

---

### 1. Executive Overview & Architecture

The visual architecture for the **Seshadripuram College Smart Academic Management System** bridges futuristic cosmic glassmorphism with institutional academic workflows across both the web application (Django) and the desktop client (PySide6).

#### Primary Visual Design References
1. **Web Dashboard Reference:** *Sapphire - Dashboard LMS* (Aditya Anugrah for Emura on Dribbble)
2. **Desktop Application Reference:** *Student Portal Dashboard* (SaulDesign on Dribbble)

```
+-----------------------------------------------------------------------------------------+
|                                     VIEWPORT ARCHITECTURE                               |
+-----------------------------------------------------------------------------------------+
| [Layer 0] Cosmic Background: Radial Nebulae (#080816, #101B63, #7900FF, #00E5FF)        |
| [Layer 1] HTML5 Particle FX Canvas (#fx-canvas): Stars, Volumetric Smoke, Fireworks     |
| [Layer 2] Screen Shake Wrapper (#shake-wrapper): Exponential / Delta-Time Decay         |
| [Layer 3] Institutional Web UI: Hero Banner, KPI Cards, Academic Modules, Live Tables   |
| [Layer 4] Event Isolation Boundary: Pointer Events Pass-Through (pointer-events: none)  |
| [Layer 5] Floating Controls Dock (#cosmic-dock): Smoke, Shake, Cursor, Quality Controls |
+-----------------------------------------------------------------------------------------+
```

---

### 2. Verified Technical Implementation

#### A. Rocket Cursor & Aerodynamic Physics
- **Displacement Clamping:** `ROCKET_SPEED` is enforced as an authentic physical displacement clamp per frame:
  $$\Delta x_{\text{step}} = \min\left(\|\Delta \vec{x}\|,\, \text{ROCKET\_SPEED} \times \Delta t \times 60\right) \times \frac{\Delta x}{\|\Delta \vec{x}\|}$$
- **Shortest-Arc Angular Interpolation:** To eliminate $\pm 180^\circ$ rotational flips when crossing angular boundaries, angular distance is wrapped within $(-\pi, \pi]$:
  $$\Delta \theta = ((\theta_{\text{target}} - \theta_{\text{current}} + \pi) \pmod{2\pi}) - \pi$$
  $$\theta_{\text{next}} = \theta_{\text{current}} + \Delta \theta \times \min(1.0, \text{ROTATION\_SMOOTHING} \times \Delta t \times 60)$$
- **Resting Orientation:** When velocity drops below $2\,\text{px}$ for `RESTING_TIMEOUT` ($550\,\text{ms}$), target angle smoothly returns to `RESTING_ANGLE` ($0\,\text{rad}$, pointing upright).
- **Lateral Roll / Banking:** The spacecraft dynamically compresses width during sharp turns to simulate aerodynamic roll:
  $$\text{Scale}_x = \max(0.68,\, 1 - |\omega_{\text{roll}}| \times \text{BANKING\_FACTOR})$$
- **Engine Glow Scaling:** `ENGINE_GLOW` directly scales the flame length, nozzle bloom radius, and radial gradient alpha compositing in `drawRocket()`.

#### B. True Particle Object Pooling & Single Global Ceiling
- **Pre-Allocated Pool:** Memory churn and GC stalls are eliminated by pre-allocating an array of `MAX_PARTICLES` (1,200) reusable particle structs.
- **Single Global Ceiling:** All particle systems—smoke puffs, explosion sparks, central flash flares, and shockwave rings—draw from the same unified pool.
- **$O(1)$ Deallocation:** Active particles are managed in a contiguous active list. When a particle expires, it is deactivated and swapped with the last active element (`swap-and-pop`), avoiding array reallocation or memory leaks.
- **Secondary Bursts:** Delayed micro-sparks strictly request slots from the shared pool; if the pool is saturated, bursts are safely dropped to protect framerate.

#### C. Frame-Rate Independent Delta-Time Physics
- All updates are computed using elapsed delta time $\Delta t = \min(t_{\text{current}} - t_{\text{last}},\, 0.08\,\text{s})$, protecting against background tab suspension jumps.
- **Velocity Drag:** $v = v \times (\text{PARTICLE\_FRICTION})^{\Delta t \times 60}$
- **Screen Shake Decay:** Shake intensity decays via time-normalized exponential decay:
  $$I_{\text{shake}} \leftarrow I_{\text{shake}} \times (\text{SHAKE\_DECAY})^{\Delta t \times 60}$$

#### D. Adaptive Performance Monitoring
The engine continuously measures rolling FPS and frame time over $500\,\text{ms}$ intervals, automatically scaling visual complexity across four tiers:

| Quality Tier | Average FPS | Active Particle Scale | Decorative Effects |
| :--- | :---: | :---: | :--- |
| **High** | $\ge 55\,\text{FPS}$ | $1.0\times$ (100% emission) | Volumetric smoke, screen shake, twinkling stars, secondary bursts |
| **Medium** | $42 - 54\,\text{FPS}$ | $0.75\times$ (75% emission) | Standard smoke, mild screen shake, stars |
| **Low** | $28 - 41\,\text{FPS}$ | $0.45\times$ (45% emission) | Reduced smoke, no screen shake, simplified sparks |
| **Minimal** | $< 28\,\text{FPS}$ | $0.20\times$ (20% emission) | Essential cursor only, smoke and explosions disabled |

---

### 3. Accessibility & Event Isolation

1. **`prefers-reduced-motion` Compliance:**
   - Detects the OS/browser accessibility query dynamically.
   - Automatically disables screen shake, disables smoke emission, and reduces fireworks to a gentle low-velocity pulse.
   - Restores settings immediately when the accessibility preference changes.
2. **Device-Aware Pointer Handling:**
   - Evaluates `(pointer: fine)` media query.
   - Touch-only devices (mobile/tablets) retain default system touch interactions; custom cursor hiding (`cursor: none`) is never applied on touch devices.
   - Pointer events handle touch bursts without locking cursor position to previous taps.
3. **Control Event Isolation:**
   - All interactive UI elements (`button`, `a`, `input`, `textarea`, `select`, `.controls-dock`, `[data-no-fx]`) are isolated.
   - Clicking on forms, buttons, or docks executes the control's action **without** triggering accidental background firework explosions.
4. **Keyboard Focus Outlines:**
   - All interactive controls feature high-contrast cyan focus indicators (`outline: 2px solid #00E5FF`) on `:focus-visible`.

---

### 4. Institutional Data Alignment

- **Web Dashboard:** Directly bound to Django database models (`Student.objects.filter(status='ACTIVE')`, `Faculty`, `Department`, `Program`). Empty database states render informative guidance banners rather than fabricated metrics.
- **Standalone Reference (`rocket-cursor.html`):** Metrics are explicitly marked with `[SAMPLE / DEMO DATA]` badges to ensure layout previews are not misrepresented as institutional records.

---

### 5. Integration Architecture

#### A. Web Application (`seshadripuram_academic_system`)
- **Engine Script:** `seshadripuram_academic_system/static/js/cosmic-engine.js`
- **Design Tokens & Styles:** `seshadripuram_academic_system/static/css/college.css`
- **Templates Integrated:**
  - `templates/accounts/dashboard.html` (authenticated operations overview)
  - `templates/accounts/login.html` (cosmic aurora sign-in portal)
- **Django Configuration:** `config/settings.py` includes `STATICFILES_DIRS = [BASE_DIR / "static"]`.

#### B. PySide6 Desktop Application (`desktop/main.py`)
- Employs matching QSS stylesheets utilizing the Section 16 palette tokens (Midnight navy `#080816`, deep royal blue `#101B63`, neon purple `#7900FF`, cyan `#00E5FF`, emerald `#00D084`, amber `#FFD700`).
- Features a left navigation sidebar, campus hero banner, and four KPI metric cards with dropshadows (`QGraphicsDropShadowEffect`).
- Authenticates against the local Django DRF API (`/api/desktop/login/`) and retrieves real live institutional metrics (`/api/desktop/summary/`).

---

### 6. Testing & Validation Results

The implementation was subjected to automated and functional testing:

| Test Suite / Inspection | Command / Target | Result | Status |
| :--- | :--- | :--- | :---: |
| **Django System Check** | `python manage.py check` | `0 issues identified` | **PASS** |
| **Database Migrations** | `python manage.py migrate` | Applied `accounts` & `academics` tables | **PASS** |
| **Backend Integration Suite** | `python manage.py test accounts` | 4 test cases executed in 13.8s | **PASS** |
| **API Health Endpoint** | `GET /api/health/` | `{"status": "ok", "phase": 2}` | **PASS** |
| **Desktop Auth & Summary** | `POST /api/desktop/login/`, `GET /api/desktop/summary/` | 200 OK with valid Token & active counts | **PASS** |
| **PySide6 Compilation** | `python -m py_compile desktop/main.py` | 0 syntax or import errors | **PASS** |
| **Particle Pool Limit** | `activeList.length <= MAX_PARTICLES` | Strict ceiling bounded at 1,200 | **PASS** |
| **Event Isolation** | Pointer events on buttons / inputs | Background fireworks suppressed | **PASS** |

---

### 7. Known Limitations & Phase 3 Roadmap

1. **Local Desktop API Boundary:**
   - The PySide6 desktop application requires the Django server to be running (`python manage.py runserver`) on `http://127.0.0.1:8000`. Offline caching and token persistence across OS reboots are scheduled for Phase 3.
2. **Attendance & Examination Metrics:**
   - Full daily timetable logging and examination results analytics will be wired into dedicated student/faculty views in subsequent milestone phases as specified in `ROADMAP.md`.
