# AuraForest: Adaptive Edge AI Sentinel
## Product Requirements Document (PRD)

---

## 1. Executive Summary

**AuraForest** is an autonomous, energy-efficient Edge AI environmental sentinel system designed to protect natural reserves, national parks, and semi-natural biomes from illegal deforestation, wildlife poaching, forest fires, and unauthorized intrusions. 

By combining on-device **Environmental Sound Classification (ESC)** with **Context-Aware Adaptive Decision Intelligence (CADIE)**, multimodal gas/environmental sensors (MQ-2, MQ-135, DHT11, BH1750, SW-420), and **Open-Set Unknown Sound Discovery (DBSCAN + Embedding Extraction)**, AuraForest eliminates false alarms and operates reliably even in harsh, off-grid conditions.

---

## 2. Problem Statement & Motivation

Real-world outdoor monitoring poses critical technical challenges:
1. **Unstructured Soundscapes**: Background noise (heavy rain, wind turbulence, animal vocalizations) overlaps with threat signals (chainsaws, gunshots, vehicle engines), causing naive classifiers to fail.
2. **Bandwidth & Latency Constraints**: Transmitting continuous 24/7 raw audio over cellular/satellite is prohibitively expensive and power-draining. Edge inference is required.
3. **Open-Set Unknowns**: New or unseen acoustic phenomena in forests (rare fauna, unusual machinery) trigger misclassifications if the model is forced into closed-set output.
4. **False Alarm Fatigue**: Sound alone can mislead (e.g., thunder resembling an explosion, branch snapping resembling a gunshot). Multimodal corroboration (gas, vibration, thermal) is essential.

---

## 3. Core Functional Requirements

### 3.1. Edge Acoustic Perception & Classification
- **Sample Rate & Precision**: 16,000 Hz, 16-bit mono PCM.
- **Audio Capture Window**: 5.0-second rolling or triggered buffers.
- **Inference Latency**: Under 250 ms on edge hardware / CPU.
### 3.1. Edge Acoustic Perception & Classification
- **Sample Rate & Precision**: 16,000 Hz, 16-bit mono PCM.
- **Audio Capture Window**: 5.0-second rolling or triggered buffers.
- **Inference Latency**: Under 250 ms on edge hardware / CPU.
- **Threat & Alert Priority Hierarchy**:

| Category | Constituent Acoustic Classes | Priority Tier | Default Action |
| :--- | :--- | :---: | :---: |
| 🔥 **Fire** | Forest Fire, smoke crackle, explosion, gunshot | **HIGH (Highest Priority)** | `DISPATCH_RANGERS` |
| 🪚 **Logging** | Chainsaw, power drills, jackhammers, tree felling | **HIGH (Highest Priority)** | `DISPATCH_RANGERS` |
| 🚗 **Vehicles** | Diesel trucks, motor engines, unauthorized transit | **MODERATE (Need to be addressed)** | `INTERCEPT_VEHICLE` |
| 👤 **Human** | Intrusive speech, shouting, footsteps | **MODERATE (Need to be addressed)** | `INVESTIGATE_INTRUSION` |
| 🌿 **Others** | Wildlife, birds, insects, rain, wind, ambient stream | **LOW** | `MONITOR` |

- **Noise-Robust Preprocessing**: Dynamic noise estimation, Wiener/spectral subtraction, and high-pass filtering (80 Hz cut-off) to strip wind turbulence.

### 3.2. Context-Aware Decision Engine (CADIE)
- Evaluates acoustic predictions with **Confidence-First Primacy**:
  - **High Confidence ($\ge 85\%$)**: Triggers immediate `CRITICAL` alert autonomously.
  - **Moderate Confidence ($60\%–84\%$)**: Cross-referenced with physical gas (MQ-2/135) and seismic vibration (SW-420) sensors for additive corroboration.
  - **Low Priority Events**: Handled in background monitoring mode without alerting fatigue.
- Outputs standardized triage:
  - **Risk Levels**: `MINIMAL`, `ELEVATED`, `HIGH`, `CRITICAL`.
  - **Recommended Actions**: `MONITOR`, `RECORD_EVIDENCE`, `TRANSMIT_ALERT`, `DISPATCH_RANGERS`.
  - **Explainability Rationale**: Human-readable list of contributing sensor factors.

### 3.3. Open-Set Unknown Sound Discovery Pipeline
- **Open-Set Rejection Gate**: Samples where prediction confidence is below dynamic threshold $\tau_{\text{conf}}$ or softmax margin is below $\Delta_{\text{margin}}$ are flagged as *Unknown Sound Events*.
- **Feature Embedding**: 128-dimensional dense acoustic embeddings extracted per unknown sound.
- **Persistent Evidence Buffer**: High-fidelity audio and metadata saved for unclustered observations.
- **Autonomous DBSCAN Clustering**: Periodic or forced density-based clustering to discover novel acoustic clusters without ground-truth labels.
- **Human-in-the-Loop Labeling UI**: Ranger dashboard for listening to retained WAV audio, assigning taxonomy labels, and retraining.

### 3.4. Hardware & Power Architecture (ESP32-S3)
- **Microcontroller**: ESP32-S3 N16R8 (Xtensa dual-core 240 MHz, 16 MB Flash, 8 MB Octal PSRAM).
- **Microphone**: INMP441 omnidirectional MEMS I2S microphone (16 kHz, 24-bit DMA shifted to 16-bit PCM).
- **Environmental Sensors**:
  - DHT11 (Temperature & Humidity)
  - BH1750 (Ambient Illumination Lux)
  - MAX17048 (I2C LiPo Fuel Gauge & Voltage)
  - SW-420 (Piezoelectric Vibration Sensor with ISR latch)
  - MQ-2 (Smoke, LPG, Combustible Gas)
  - MQ-135 (CO, Air Quality, Smoke Index)
- **Positioning**: NEO-6M GPS UART receiver with auto fallback to pre-calibrated coordinates.
- **Storage & Communications**:
  - High-speed MicroSD SPI card interface (`/telemetry_log.jsonl` offline cache).
  - Wi-Fi 802.11 b/g/n HTTP REST client with auto-reconnect.

### 3.5. Persistence & Database Management
- **Database Engine**: SQLite 3 with WAL (Write-Ahead Logging) and indexed foreign keys.
- **Data Retention**:
  - `telemetry_history`: Time-series sensor snapshots (temp, humidity, lux, battery, gas voltages, vibration).
  - `events`: Audio inference events, CADIE triage, and explainability factors.
  - `unknown_samples` & `clusters`: Embedded vectors, cluster metadata, audio file links.
  - `experiment_logs`: Systematic benchmark and distance-validation test runs.
  - `emergency_alerts`: High-priority incident logs, acknowledgment status, and timestamp audit trails.

### 3.6. Local Emergency Alert Notification Subsystem
- **Multi-Channel Dispatch Trigger**: Automatically activates on high-confidence ($C \ge 0.85$) threat classification (`Chainsaw`, `Gunshot`, `Fire`) or `CRITICAL` risk level.
- **Hardware Strobe / Siren**: Injects trigger instruction to ESP32-S3 edge node to activate visual flashing beacon or buzzer.
- **Base Station Webhooks**: Formats structured emergency payloads for external ranger systems and mesh networks.
- **Mobile Phone Notification Bar (PWA & HTML5 Web Push)**: Automatically pops up in the Android / iOS notification bar with high priority, custom haptic vibration patterns, synthesized emergency siren audio, and ntfy mobile push support.
- **Operator Incident Workflow**: Real-time pulsing alert banner on dashboard with 1-click incident acknowledgment and siren silencing.

### 3.7. Citizen Eco-Observation & Threat Reporting Portal
- **Live Access**: [https://auraforest-sentinel.streamlit.app/](https://auraforest-sentinel.streamlit.app/)
- **Registration & Verification**: 6-digit email OTP verification via SMTP before tip submission privileges are granted.
- **Geotagged Incident Reporting**:
  - Live HTML5 browser GPS capture of the observer's exact field position.
  - Camera snapshot / file upload with client-side preview.
  - Incident category selection (Poaching, Illegal Logging, Forest Fire, Wildlife Distress).
- **Chief Dispatch & Field Resolution**:
  - Chief Ranger reviews pending citizen reports and marks them for unit dispatch.
  - Dispatched reports appear in real-time on the Tactical Radar map.
  - Field Rangers resolve incidents on-scene; resolved points automatically transition to the persistent **Resolved Incidents Historical Audit Log**.

---

## 4. Non-Functional Requirements

| Metric | Target Requirement |
| :--- | :--- |
| **Live Cloud Availability** | 99.9% uptime at [https://auraforest-sentinel.streamlit.app/](https://auraforest-sentinel.streamlit.app/) |
| **System Reliability** | 99.9% uptime with autonomous Wi-Fi reconnect and local SD fail-safe |
| **Audio Ingestion Latency** | $< 1.5$ seconds round-trip from capture to CADIE triage |
| **Database Query Speed** | $< 15$ ms for latest 100 historical telemetry points |
| **Edge Memory Footprint** | $< 250$ KB internal SRAM; 160 KB audio buffer isolated in Octal PSRAM |
| **UI Responsiveness** | $< 100$ ms Streamlit page refresh rate with 3-second live auto-polling |
| **False Positive Rejection** | $> 85\%$ reduction in weather-induced false alarms via CADIE fusion |

---

## 5. User Personas

1. **Park Ranger / Forest Warden**:
   - Needs instantaneous alert notifications when illegal chainsaws or gunshots are detected.
   - Requires GPS coordinates, confidence levels, and sensor explainability to dispatch field teams.
2. **Wildlife Conservation Biologist**:
   - Reviews discovered unknown sound clusters to detect uncatalogued avian or mammalian species.
   - Listens to raw audio evidence and assigns taxonomical human labels.
3. **Public Citizen / Eco-Observer**:
   - Submits geotagged photo reports of wildlife distress, fire, or illegal logging with email OTP security.
4. **Edge Systems Engineer**:
   - Monitors device battery voltage, sensor hardware health, Wi-Fi RSSI, and transmission policy states.

