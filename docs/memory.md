# AuraForest: Project Context & Memory Log

---

## 1. Project Overview & Context

- **Repository**: `AdaptiveEdgeAI` / `AuraForest`
- **Objective**: Build an autonomous, multimodal Edge AI Sentinel for real-world environmental acoustic monitoring, threat classification, gas sensor corroboration, and open-set unknown sound discovery.
- **Current System Status**: **Production-Ready & 100% Verified** (232/232 automated pytest suite passing).

---

## 2. Completed Milestones & Accomplishments

### ✅ Task 1: Noise-Robust Preprocessing & ESC Pipeline
- Built 4th-order Butterworth high-pass filter (80 Hz) and dynamic spectral subtraction preprocessor.
- Validated performance under clean vs noisy conditions (wind, rain, vehicle hum).

### ✅ Task 2: Distance & Acoustic Propagation Testing Suite
- Implemented [`experiments/distance_detection_validator.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/experiments/distance_detection_validator.py).
- Evaluated sound propagation across 5 ambient environments (Quiet Forest, Windy Canopy, Heavy Downpour, Dense Foliage, Riverbank) from 5m to 100m.
- Generated experiment reports in CSV, JSON, and Markdown format in [`outputs/experiments/`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/outputs/experiments/).

### ✅ Task 3: Multimodal Gas Sensor Interpreter & CADIE Engine
- Implemented [`edge/sensors/gas_interpreter.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/edge/sensors/gas_interpreter.py) with rolling baseline calibration, anomaly ratio calculation, and first-order derivative trend estimation (`RISING_FAST`, `RISING`, `STABLE`, `FALLING`).
- Integrated gas assessments into [`edge/decision/cadie.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/edge/decision/cadie.py) with confidence primacy and non-blocking multimodal corroboration.

### ✅ Task 4: Complete SQLite Database Persistence
- Implemented `telemetry_history`, `events`, `unknown_samples`, `clusters`, and `experiment_logs` tables in [`backend/database.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/database.py).
- Created REST API endpoints in [`backend/main.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/main.py) for historical time-series queries and database statistics.

### ✅ Task 5: ESP32-S3 Firmware Refactoring ([`hardware.ino`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/hardware.ino))
- Refactored ~2,840 bloated lines into clean, modular C++ code.
- Configured 160 KB audio buffer in Octal PSRAM (`ps_malloc`).
- Set up DMA I2S microphone sampling (16 kHz 16-bit PCM).
- Configured hardware interrupt ISR on GPIO 16 (SW-420 vibration sensor).
- Converted BH1750 to continuous non-blocking mode.
### ✅ Task 6: UI Redesign & Spectrum Analyzer ([`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py))
- Designed dark-mode "Bio-Sentinel" interface with DM Sans & JetBrains Mono typography.
- Built interactive **32-Band FFT Equalizer** and **Plotly 2D Log-Mel Spectrogram Heatmap** with physical acoustic sound presets and WAV upload support ([`dashboard/spectrum_visualizer.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/spectrum_visualizer.py)).
- Integrated human-in-the-loop audio review queue with audio playback.

### ✅ Task 7: Local Emergency Alert Notification System
- Created [`backend/alert_dispatcher.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/alert_dispatcher.py) with automated criteria evaluation, local strobe trigger, ranger dispatch formatting, and webhook broadcasting.
- Added persistent `emergency_alerts` table and indexing in [`backend/database.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/database.py) with acknowledgment tracking.
- Exposed REST API endpoints in [`backend/main.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/main.py) for active alerts, historical logs, manual broadcast, and 1-click ranger acknowledgment.
- Embedded high-visibility glowing emergency alert banner and manual broadcast console in [`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py).
- Integrated **Mobile Phone Notification Bar Bridge** (HTML5 Web Push, custom vibration haptics `navigator.vibrate`, Web Audio API siren synthesis, and `ntfy.sh` mobile push) for instant pop-ups in Android/iOS notification drawers.
- Implemented visual strobe/siren indicator in ESP32 firmware [`hardware.ino`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/hardware.ino) when emergency alert is returned by inference engine.
- Added comprehensive unit tests in [`tests/backend/test_emergency_alerts.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/tests/backend/test_emergency_alerts.py) and [`tests/edge/decision/test_cadie.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/tests/edge/decision/test_cadie.py).

### ✅ Task 8: Dashboard Navbar & Sidebar Navigation Redesign ([`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py))
- Eliminated dashboard visual crowding by architecting a structured **Sidebar Diagnostics Control** and **5-Tab Navigation Navbar**:
  - `📡 Live Sentinel Overview`: Telemetry grid cards, dynamic threat perception card, CADIE multimodal corroboration, and adaptive context.
  - `📊 Spectrum & Acoustic AI`: 32-Band FFT Equalizer, Plotly 2D Log-Mel Spectrogram Heatmap, and Top-K Alternatives.
  - `🚨 Emergency Alert Center`: Manual threat broadcast console with priority categorization, channel status, and dispatched alert audit log.
  - `🔬 Unknown Sound Discovery`: DBSCAN discovery monitor, pending unknown buffer, human review queue with audio evidence player, and open-set gate thresholds.
  - `📈 Node Health & Logs`: Hardware component health matrix, GPS geolocation, and historical detection event streams.
- Preserved persistent glowing active emergency banner across all views so critical alerts are never missed.

### ✅ Task 9: Multi-Layer Security, Token Authentication & RBAC Architecture
- Created [`backend/security.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/security.py) providing:
  - **Edge Device Token & API Key Authentication**: Rejects rogue nodes and validates device tokens (`X-Device-Token` / `X-API-Key`).
  - **Anti-Replay & Timestamp Skew Protection**: Validates ingestion timestamps against a 300s window to prevent packet replay attacks.
  - **Physical Sensor Bounds & Anti-Spoofing Verification**: Enforces boundary sanitization on temperature, humidity, voltage, and gas readings.
  - **Role-Based Access Control (RBAC)**: Supports `Admin`, `Ranger`, and `Viewer` accounts with HMAC-SHA256 session token generation and verification.
- Added authentication endpoints in [`backend/main.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/main.py) (`/api/v1/auth/login`, `/api/v1/auth/me`, `/api/v1/auth/roles`, `/api/v1/auth/verify_key`).
- Integrated security headers into ESP32 firmware [`hardware.ino`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/hardware.ino) HTTP POST requests.
- Added interactive RBAC identity switcher in [`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py) with authenticated API requests.
- Added 21 automated unit tests in [`tests/test_security.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/tests/test_security.py).

### ✅ Task 10: Tactical Radar, Geolocation Sentry & Pulsing Shockwave Alerts
- Built Pydeck 3D geospatial radar mapping active IoT nodes, field ranger units, and citizen tips.
- Added HTML5 high-accuracy Geolocation sentry syncing live browser GPS coordinates into `st.session_state` and `db.update_ranger_location()`.
- Implemented animated dual concentric shockwave strobe halos (500m radius + pulsing 5px red border) over active threat coordinates.
- Added Sanctuary Base Sector preset selector (Bandipur, Nagarhole, Kaziranga, Mudumalai, Corbett, Sundarbans).

### ✅ Task 11: Citizen Incident Portal & Resolved Incidents Audit Log
- Implemented full citizen incident reporting flow with camera snapshot capture and 6-digit email OTP verification.
- Built Chief Ranger dispatch triage console: marking citizen reports for field unit response.
- Implemented Field Ranger on-scene incident resolution: solved reports automatically disappear from active map and transition to the dedicated **Resolved Incidents Historical Audit Log** page.

### ✅ Task 12: Production Cloud Deployment & SMTP Email Relay
- Successfully deployed live web platform on Streamlit Community Cloud: [https://auraforest-sentinel.streamlit.app/](https://auraforest-sentinel.streamlit.app/).
- Armed real SMTP relay with Google App Password support delivering verification OTPs and Ranger access credentials to real inboxes.
- Embedded live platform URL and action buttons in all automated email dispatches.

---

### ✅ Task 13: Enterprise Multi-Layer Security & Cyber-Defense Architecture
- Created [`backend/security.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/security.py) and integrated across [`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py):
  - **HMAC-SHA256 Cryptographic Session Management**: Replaced plaintext URL tokens with signed JWT-style tokens verifying `sub`, `role`, `name`, `dept`, and `exp`. Forged or expired tokens immediately trigger session termination and URL query parameter purging.
  - **Progressive Brute-Force & Credential Stuffing Defense**: Implemented `LoginRateLimiter` enforcing a 300-second lockout penalty after 5 consecutive failed login attempts, showing live remaining seconds before retry.
  - **Salted Password Hashing & Complexity**: Enforces salted SHA-256 storage and strict alphanumeric complexity requirements (min 8 characters, at least 1 letter and 1 digit). Insecure dictionary backdoors (`admin`, `chief`, `password`, `ranger`) have been completely removed.
  - **Anti-XSS & SQL Injection Defense**: HTML-escapes all citizen reports and user notes; parameterizes all SQLite queries.
  - **Chief Ranger Security Operations Center (SOC)**: Live shield status indicators, locked account counters, emergency unlock action buttons, and filterable authentication audit log.

### ✅ Task 14: CADIE Voice-First Logging & Seismic Vibration Cross-Corroboration
- Updated [`edge/decision/cadie.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/edge/decision/cadie.py):
  - Logging threats strictly require primary acoustic voice (chainsaw, drill, axe, felling).
  - **Acoustic Voice + Seismic Vibration**: Ground shock accompanied by chainsaw/drill acoustic signatures confirms active tree cutting and equipment impact $\rightarrow$ elevated to `CRITICAL` risk with `TRANSMIT_IMMEDIATELY`.
  - **Seismic Vibration Alone (No Logging Voice)**: Registered as `[SEISMIC VIBRATION] Environmental ground vibration` (possible minor tectonic tremor, animal movement, or high-wind tree sway). Suppresses false logging alarms.
  - Corroborates smoke and combustible gas readings (MQ-2 and MQ-135 ADC voltages) with acoustic fire crackle for canopy fire triage.
  - Sanitized all factor strings to standard ASCII to maintain compatibility across Windows `cp1252` and Linux `UTF-8` terminals.

### ✅ Task 15: Sanctuary Public Siren Broadcast & Web Audio Synthesizer
- Built public safety broadcast controls in [`dashboard/app.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/dashboard/app.py):
  - Field Rangers and Chief Rangers can activate the sanctuary-wide public siren (`🚨 Broadcast Siren to Public`) with instant visual and audible dispatch.
  - One-click silence button (`🔕 Silence & Deactivate Siren`) deactivates the broadcast across all connected terminals.
  - Web Audio API dual-oscillator synthesizer generates an audible emergency warble chime directly in the browser with individual user mute controls.
  - Public Citizen portal displays active safety advisories and emergency evacuation notifications during active fires or intrusions.

### ✅ Task 16: Audio Ingestion Resiliency & Dynamic Hotspot Setup
- Hardened [`backend/audio_service.py`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/backend/audio_service.py) and [`hardware.ino`](file:///d:/user/Workspace/Major%20project/AuraForest/AdaptiveEdgeAI/hardware.ino):
  - Replaced loose 2-byte MP3 check with strict 4-byte MPEG sync validation and second-frame boundary checks, eliminating false-positive MP3 classifications triggered by raw PCM16 negative ambient noise (`0xFFFF`).
  - Added resilient fallback: if compressed decoders fail on an even-aligned audio stream, it safely falls back to raw signed PCM16 processing without returning a 500 server error to the edge node.
  - Implemented mobile hotspot stability in firmware via `WiFi.setSleep(false)`.
  - Created dynamic captive portal Access Point (`AuraForest-Node-Setup` at `http://192.168.4.1`) backed by ESP32 NVS `Preferences` flash memory for on-site Wi-Fi reconfiguration.

---

## 3. Test Coverage Summary

- **Total Test Cases**: **253 Passed / 0 Failed (100%)**
- **Test Modules**:
  - `tests/test_security.py` (Edge tokens, HMAC tokens, RBAC, anti-spoofing, anti-replay) $\rightarrow$ 21 tests ✅
  - `tests/backend/` (API, Client, Database, Telemetry, Serializer, Policy, Emergency Alerts) $\rightarrow$ 36 tests ✅
  - `tests/dashboard/` (Data Provider, Runtime Source, Spectrum Visualizer) $\rightarrow$ 35 tests ✅
  - `tests/edge/` (CADIE, Adaptation, Unknown Buffer, Clusterer, Gas Interpreter) $\rightarrow$ 117 tests ✅
  - `tests/hardware/` (Sensors, Dummy Drivers, Runtime) $\rightarrow$ 26 tests ✅
  - `tests/inference/` & `tests/integration/` $\rightarrow$ 18 tests ✅

---

## 4. Key Architectural Decisions

1. **PSRAM Audio Buffer**: Allocating 160,000 bytes in internal SRAM risked heap fragmentation on ESP32-S3. Using external Octal PSRAM (`ps_malloc`) ensures system stability.
2. **Gas Anomaly Tracking**: Since uncalibrated MQ sensors cannot yield accurate absolute PPM without factory calibration chambers, tracking statistical baseline ratios ($\frac{V}{V_0}$) and slope trends ($\frac{dV}{dt}$) provides scientifically defensible corroboration.
3. **Open-Set DBSCAN Rejection**: Rather than forcing unknown sounds into predefined classes, rejecting them and clustering latent embeddings allows for continuous unsupervised learning and species discovery.
4. **Immediate Multi-Channel Emergency Dispatch**: Threat classifications with high confidence ($\ge 0.85$) or critical risk immediately dispatch strobe commands back to the edge node, push notifications to the dashboard banner, and write to persistent storage with ranger acknowledgment workflow.

---

## 5. Remaining Roadmap & Future Enhancements

| Item | Description | Priority |
| :--- | :--- | :--- |
| **LoRaWAN Gateway Integration** | Add SX1262 LoRa fallback transceiver when cellular/Wi-Fi is out of range | Medium |
| **Solar MPPT Power Management** | Deep sleep scheduling with dynamic wake-on-sound (INMP441 threshold trigger) | Medium |
| **Edge TinyML On-Device Quantization** | Export MobileNetV3 to 8-bit quantized TFLite Micro running directly on ESP32-S3 ESP-NN | Low / Future |
| **Multi-Node Mesh Triangulation** | TDoA (Time Difference of Arrival) acoustic localization using 3+ synchronized sentinels | Low / Future |
