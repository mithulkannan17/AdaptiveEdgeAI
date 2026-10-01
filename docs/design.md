# AuraForest: UI/UX Design System & Directions

---

## 1. Design Philosophy: "Bio-Sentinel Command"

AuraForest's user interface is built to evoke an **executive-grade, bioacoustic intelligence command center**. It combines high aesthetic sophistication with military-grade operational clarity.

### Core Visual Tenets:
1. **Dark Bio-Acoustic Palette**: Deep obsidian backgrounds (`#070b0d`) accented by bio-luminescent emerald (`#7cf0b2`), cyber cyan (`#73d9e8`), warning amber (`#f2c66d`), and alert coral (`#ff7777`).
2. **Instant Scannability**: Rangers and operators in high-stress situations must assess threat level, confidence, and sensor confirmation in under 2 seconds.
3. **Data Density with Breathing Room**: Metric cards, spectrograms, and decision badges use rounded glassmorphic containers (`border-radius: 18px`, `padding: 20px`) with subtle borders (`#203036`).
4. **Dual Typography Harmony**: Elegant, geometric sans-serif (`DM Sans`) for labels and narrative text paired with monospaced precision (`JetBrains Mono`) for telemetry values, coordinates, and status pills.

---

## 2. Design Tokens & Color Palette

### 2.1. Color System
```css
:root {
    /* Backgrounds & Panels */
    --bg:        #070b0d; /* Primary Canvas */
    --panel:     #0d1316; /* Primary Card Container */
    --panel-2:   #101c20; /* Elevated Surface */
    --line:      rgba(32, 54, 62, 0.7); /* Subtle Glass Border */
    --line-glow: rgba(124, 240, 178, 0.2);
    
    /* Typography */
    --text:      #edf6f3; /* High-contrast Primary Text */
    --muted:     #829a97; /* Secondary / Subtitle Text */
    --dark-mute: #526563; /* Timestamp / Footer Text */
    
    /* Semantic & Accent Status Colors */
    --green:     #7cf0b2; /* Operational / Nominal / Low Risk */
    --cyan:      #73d9e8; /* Discovery / Unknown Cluster Active */
    --amber:     #f2c66d; /* Elevated Risk / Warning / Warming Up */
    --red:       #ff7070; /* Critical Threat / Hardware Failure */
    --purple:    #bb86fc; /* Vibration / Sensor Latch */
    --blue:      #82b1ff; /* Radio / Network / GPS Connected */
    --gold:      #feca57; /* Optical Lux / Peak Frequency */
}
```

### 2.2. Typography Hierarchy
- **Brand / Kicker**: `JetBrains Mono`, 10px–11px, `letter-spacing: 0.18em`, uppercase.
- **Hero Title**: `DM Sans`, 32px, bold, `letter-spacing: -0.04em` with multi-stop emerald gradient clipping.
- **Acoustic Event Main Header**: `DM Sans`, 40px, bold, `letter-spacing: -0.04em`.
- **Primary Metric Figures**: `DM Sans`, 28px, bold with unit subtext.
- **Telemetry Values & Badges**: `JetBrains Mono`, 11px, tabular numbers.
- **Micro Labels**: `DM Sans`, 11px, `letter-spacing: 0.09em`, uppercase.

---

## 3. UI Component Library & Layout Structure

### 3.1. Header & Live Connection Pill
- **Hero Section**: Displays AuraForest branding, operational subtitle, and live connection status.
- **Pill Component**:
  ```html
  <div class="live-pill">
      <span class="dot"></span>SENTINEL ONLINE
  </div>
  ```
  Animated green pulse dot (`animation: pulseDot 2s infinite ease-in-out`).

---

### 3.2. Live Telemetry Strip
- 6-column grid displaying key physical metrics with distinct accent bars and glowing icon badges:
  - **Temperature (°C)**: Amber top bar (`🌡️`)
  - **Humidity (%)**: Electric Cyan top bar (`💧`)
  - **Light (lux)**: Sun Gold top bar (`☀️`)
  - **Battery (%)**: Bio-Emerald top bar (`⚡`)
  - **Vibration**: Violet / Coral seismic latch (`📳`)
  - **Atmosphere / Gas**: Toxic Mint / Coral composite risk (`🧪`)
  - **Battery (%)**: MAX17048 fuel gauge + voltage.
  - **Vibration**: Latched SW-420 seismic detection badge.
  - **Atmosphere / Gas**: MQ-2 & MQ-135 composite air quality and risk score.

---

### 3.3. Acoustic Intelligence & CADIE Decision Panel
- **Acoustic Event Card**:
  - Displays detected event name in 42px font.
  - Smooth animated confidence bar with color interpolation.
- **CADIE Triage Box**:
  - Prominent Risk Badge (`MINIMAL`, `ELEVATED`, `HIGH`, `CRITICAL`).
  - Recommended Action banner (`MONITOR`, `RECORD_EVIDENCE`, `DISPATCH_RANGERS`).
  - **Explainability Rationale**: Bulleted causal breakdown (e.g. *"Gas anomaly ratio (1.82x) corroborates fire acoustic signature"*).
- **Inference Diagnostics**: Model execution latency ($ms$), open-set rejection status, and buffer capacity.

---

### 3.4. 32-Band Spectrum & Log-Mel Spectrogram Analyzer
- **Interactive Signal Source Selector**:
  - Lets users toggle between Live Sentinel stream, physical presets (Chainsaw, Gunshot, Fire Crackle, Birdsong, Wind/Rain), or custom WAV file uploads.
- **5-Metric Acoustic Diagnostic Strip**:
  - *Peak Frequency (Hz)*
  - *Spectral Centroid (Hz)*
  - *Spectral Rolloff (Hz)*
  - *RMS Energy (dBFS)*
  - *Spectral Texture (Tonal / Noisy / Balanced)*
- **Dual Visualizer**:
  - **Left**: 32-Band responsive CSS equalizer with frequency band tags (Sub-Bass, Bass, Mid, High, Air).
  - **Right**: Plotly interactive 2D Log-Mel Spectrogram Heatmap with dark Bio-Sentinel colormap and microsecond hover tooltips.

---

### 3.5. Unknown Sound Discovery & Human-in-the-Loop Review
- **Discovery Grid**: Pending samples, total unknown observations, cluster counts, and progress to next DBSCAN batch.
- **Clustering Action Bar**: One-click manual trigger and pending buffer flush.
- **Audio Review Queue**:
  - Discovered cluster cards with sample counts and noise breakdown.
  - **Integrated Audio Player**: Streams original WAV recordings directly from the backend.
  - **Labeling Form**: Quick-action text field with instant persistence to SQLite database.

---

### 3.6. Node Integrity & Location Panel
- **Hardware Health Matrix**: Tabular status for all onboard modules (`INMP441`, `BH1750`, `MAX17048`, `DHT11`, `SW-420`, `NEO-6M`, `MicroSD`, `WiFi`).
- **GPS Coordinates**: Real-time latitude, longitude, altitude, accuracy, and timestamp with fallback indicator.

---

## 4. Tactical Radar & Real-Time Geospatial Visualizer

- **Live URL**: [https://auraforest-sentinel.streamlit.app/](https://auraforest-sentinel.streamlit.app/)
- **Pydeck 3D Canvas**:
  - Dark-matter basemap styling (`mapbox://styles/mapbox/dark-v11`).
  - Interactive pitch and bearing adjustments for 3D terrain exploration.
- **Dynamic Layer Hierarchy**:
  - **Hexagon Sentinel Nodes (`#73d9e8`, cyan)**: Radius 250m with elevation based on telemetry throughput.
  - **Field Ranger Tactical Pins (`#7cf0b2`, bio-emerald)**: Live position pins displaying callsign, rank, and battery.
  - **Dispatched Citizen Tip Beacons (`#f2c66d`, warning amber)**: Highlighted pins with citizen description and tip photo popups.
  - **Emergency Strobe Halo (`#ff7070`, alert red)**: Outer blast radius (500m) + inner pulsing shockwave ring with 5px red border (`@keyframes radarEmergencyStrobe`).
- **Sanctuary Sector Quick-Switcher**:
  - Instant camera re-centering to major Indian national parks (Bandipur, Nagarhole, Kaziranga, Mudumalai, Corbett, Sundarbans) or Live Device GPS.

---

## 5. Mobile & High-Priority Emergency Strobe HUD

```css
@keyframes radarEmergencyStrobe {
    0%   { background-color: rgba(255, 112, 112, 0.15); border-color: rgba(255, 112, 112, 0.4); }
    50%  { background-color: rgba(255, 60, 60, 0.45); border-color: rgba(255, 70, 70, 1.0); box-shadow: 0 0 35px rgba(255, 70, 70, 0.6); }
    100% { background-color: rgba(255, 112, 112, 0.15); border-color: rgba(255, 112, 112, 0.4); }
}

.strobe-alert-hud {
    animation: radarEmergencyStrobe 1.2s infinite ease-in-out;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 20px;
}
```

