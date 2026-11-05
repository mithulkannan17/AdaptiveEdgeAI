# AuraForest Sentinel - Exact 10-Box Landscape System Architecture Prompt

Use this comprehensive prompt in **Midjourney**, **DALL-E 3**, **Imagen 3**, **Canva AI**, or **Gamma.app** to generate the exact 10-box landscape system architecture diagram with sub-boxes, sensor details, Wi-Fi bridge, and triage dispatch.

---

### 🎨 The Exact 10-Box Landscape Architecture Breakdown

```
========================================================================================================================
ROW 1 (TOP TIER: SENSING, NODE DEVICE & LOCAL ADAPTIVE PROFILING — LEFT TO RIGHT FLOW)
========================================================================================================================

[BOX 1: Environmental Acoustic Events]
• Sound Sources: Birds, Chainsaw, Human, Vehicle, Rain, Wind
       │
       ▼ (Acoustic Pressure Waves & Environmental Phenomena)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [BOX 2: Node Device Sensing & Power Subsystem] (3 Sub-Boxes Side-by-Side)              │
│ ┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐ │
│ │ SUB-BOX 2.1: AUDIO SENSOR│ │ SUB-BOX 2.2: ENV SENSORS │ │ SUB-BOX 2.3: POWER SYSTEM│ │
│ │ • INMP441 MEMS (Voice)   │ │ • DHT11 (Temp & Humidity)│ │ • MAX17048 Fuel Gauge    │ │
│ │ • 16 kHz I2S Digital Bus │ │ • BH1750 (Ambient Light) │ │ • 2x 3.7V Li-Ion Battery │ │
│ │                          │ │ • SW-420 (Vibration)     │ │ • Dynamic Power Control  │ │
│ │                          │ │ • MQ-2 & MQ-135 (Smoke)  │ │ • 15 µA Deep Sleep Mode  │ │
│ │                          │ │ • NEO-6M GPS Module      │ │                          │ │
│ └──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘ │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ (Digital I2S Audio + ADC/I2C Telemetry)
                                            ▼
[BOX 3: ESP32-S3 Edge Node]
• Core Capabilities:
  1. Edge Computing (240 MHz Dual-Core Xtensa LX7)
  2. Real-Time Processing
  3. Low Power Optimization
  4. Wi-Fi Connectivity
       │
       ▼ (Structured Sensor Readings & Audio Windows)
[BOX 4: Environment Adaptive Profiling]
• Function: Builds dynamic baseline profile using real-time environmental context & noise floor
       │
       ▼ (Calibrated Audio Stream & Context Vector)
[BOX 5: Adaptive Event Prioritization Engine]
• Function: Prioritizes events by severity, uniqueness, and environmental impact (Rating 1 to 5)
       │
       ▼ 📶 [Wi-Fi Wireless Transmission Bridge]
========================================================================================================================
ROW 2 (BOTTOM TIER: AI INFERENCE, CADIE REASONING & MULTI-STAKEHOLDER TRIAGE — FLOWS TO STAKEHOLDERS)
========================================================================================================================
[BOX 6: Audio Preprocessing & Feature Extraction]
• Pipeline: Noise reduction (spectral quantile subtraction), 25ms framing, 50% overlap, MFCC & 128 Mel-Bins
       │
       ▼ (Log-Mel Spectrogram Tensors)
[BOX 7: CNN-Based Environmental Sound Classification]
• Architecture: Deep Convolutional Neural Network (MobileNetV3 backbone, 14 classes, < 420 ms latency)
       │
       ▼ (Acoustic Confidence Probability Vector)
[BOX 8: Context-Aware Decision Intelligence Engine (CADIE)]
• Intelligence: Combines CNN classification + environmental context to infer high-level events & 4-tier risk
       │
       ▼ (Verified Incident Dossier & GPS Triangulation)
[BOX 9: Database and Dashboard]
• Functions: Stores events locally (SQLite/FastAPI) and visualizes live telemetry in real-time Streamlit GIS
       │
       ▼ (Actionable Multichannel Dispatch)
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ [BOX 10: Tri-Tier Stakeholder Triage Dispatch] (3 Sub-Boxes Side-by-Side)              │
│ ┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────────────┐ │
│ │ SUB-BOX 10.1: CHIEF EXEC │ │ SUB-BOX 10.2: RANGERS    │ │ SUB-BOX 10.3: COMMUNITIES│ │
│ │ • Forest Chief Executive │ │ • Field Ranger Patrols   │ │ • Local Communities     │ │
│ │ • Web Command Center     │ │ • Tactical GPS Intercept │ │ • SMS Hazard Warnings    │ │
│ │ • Strategic Audit & Dossier│ │ • Threat Vector & Audio│ │ • Evacuation Advisories  │ │
│ └──────────────────────────┘ └──────────────────────────┘ └──────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 🖼️ Master Image Generation Prompt (Photorealistic / Engineering Schematic)

*(Copy and paste this into **Midjourney**, **DALL-E 3**, **Imagen 3**, **Canva**, or **Gamma.app**)*:

```text
A professional academic engineering system architecture flowchart in a wide 16:9 landscape format, set on a completely pure solid white background (#FFFFFF). The diagram is organized into a clean sequential box structure arranged in two horizontal tiers with crisp connecting lines and directional flow arrows:

TOP HORIZONTAL TIER (Row 1):
• BOX 1 (Cyan border): Titled "1. Environmental Acoustic Events" — Features icons and chips for Birds, Chainsaw, Human, Vehicle, Rain, and Wind.
  -> Connected by an arrow to:
• BOX 2 (Large Blue container titled "2. Node Device Subsystem", containing three distinct side-by-side sub-boxes):
  - Sub-box 2.1 (Cyan): "Acoustic Sensor" — INMP441 MEMS Microphone (16 kHz I2S Digital Audio).
  - Sub-box 2.2 (Emerald): "Environmental Sensors" — DHT11 (Temp & Humidity), BH1750 (Light), SW-420 (Vibration), MQ-2 and MQ-135 (Smoke/Gas), NEO-6M GPS.
  - Sub-box 2.3 (Amber): "Power System" — MAX17048 I2C Fuel Gauge and 2x 3.7V Li-Ion Battery Pack with 15 uA Deep Sleep.
  -> All three sub-boxes feed forward into:
• BOX 3 (Dark Navy border): "3. ESP32-S3 Edge Node" — Features an icon of the ESP32-S3 microcontroller with text bullets: "1. Edge Computing, 2. Real-Time Processing, 3. Low Power & Wi-Fi Connectivity".
  -> Connected by an arrow to:
• BOX 4 (Green border): "4. Environment Adaptive Profiling" — Subtext: "Builds dynamic baseline profile using real-time environmental context".
  -> Connected by an arrow to:
• BOX 5 (Purple border): "5. Adaptive Event Prioritization Engine" — Subtext: "Prioritizes events by severity, uniqueness, and environmental impact".
  -> Exiting Box 5 is a downward connecting line with a blue Wi-Fi transmission badge ("Wi-Fi").

BOTTOM HORIZONTAL TIER (Row 2):
• BOX 6 (Cyan border): "6. Audio Preprocessing & Feature Extraction" — Subtext: "Noise reduction, framing, MFCC & 128 Mel-Bins extraction".
  -> Connected by an arrow to:
• BOX 7 (Blue border): "7. CNN-Based Sound Classification" — Subtext: "Deep Convolutional Neural Network for 14-class audio classification".
  -> Connected by an arrow to:
• BOX 8 (Purple border): "8. Context-Aware Decision Intelligence Engine (CADIE)" — Subtext: "Combines classification + microclimate context to infer high-level events & 4-tier risk".
  -> Connected by an arrow to:
• BOX 9 (Emerald border): "9. Database and Dashboard" — Subtext: "Stores events locally and visualizes telemetry in real-time GIS console".
  -> Connected by an arrow to:
• BOX 10 (Large Red container titled "10. Tri-Tier Stakeholder Triage Dispatch", containing three side-by-side sub-boxes):
  - Sub-box 10.1 (Amber): "Forest Chief Executive" — Web Command Center, strategic audit.
  - Sub-box 10.2 (Emerald): "Field Rangers" — Tactical Intercept GPS Push, threat vectors.
  - Sub-box 10.3 (Red): "Local Communities" — SMS Hazard Warnings, evacuation notices.

Design Style: Clean IEEE engineering publication aesthetic, modular rounded card containers (#F8FAFC) on pure white background (#FFFFFF), crisp bold deep navy typography (#0F172A), vibrant accent borders, clear directional arrow flowlines, landscape widescreen orientation, 8k resolution.
```

---

### 💡 Short Prompt (For Quick AI Slides / Gamma / Canva)

```text
16:9 Landscape engineering architecture flowchart on pure white background (#FFFFFF):
[Box 1: Acoustic Events (Chainsaw, Birds, Human, Rain, Wind)] -> 
[Box 2: 3 Side-by-side Sub-boxes: (2.1 INMP441 Mic) + (2.2 DHT11, BH1750, SW420, MQ-2, MQ-135, GPS) + (2.3 MAX17048 Fuel Gauge + 2x 3.7V Li-Ion Battery)] -> 
[Box 3: ESP32-S3 Edge Node (1. Edge Computing, 2. Real-Time Processing, 3. Low Power & Wi-Fi)] -> 
[Box 4: Environment Adaptive Profiling] -> 
[Box 5: Adaptive Event Prioritization Engine] -> 
(Wi-Fi Symbol) -> 
[Box 6: Audio Preprocessing & Feature Extraction (Noise reduction, framing, MFCC)] -> 
[Box 7: CNN-Based Sound Classification] -> 
[Box 8: CADIE Context-Aware Decision Engine] -> 
[Box 9: Database and Dashboard] -> 
[Box 10: 3 Side-by-side Sub-boxes: (10.1 Chief Web Console) + (10.2 Ranger GPS Push) + (10.3 Community SMS)].
Modern clean boxes with colored borders, bold navy labels, connecting arrows, landscape widescreen layout.
```

