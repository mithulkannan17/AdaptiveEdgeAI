# AuraForest Sentinel - Simple Box-Structure System Architecture Prompt (Battery-Powered / Non-Solar)

Use this prompt to generate a clean, modular, sequential box-by-box system architecture diagram where each stage is enclosed in a dedicated box and the flow continues seamlessly with directional arrows.

---

### 🎨 The Simple Box Flow Diagram

```
┌────────────────────────────────────────────────────────┐
│  BOX 1: MULTIMODAL SENSING (CANOPY PERIPHERALS)       │
│  • INMP441 Digital MEMS Microphone (16 kHz I2S Audio)  │
│  • DHT22 Ambient Temperature & Relative Humidity       │
│  • MQ-135 Smoldering Timber Smoke & Gas Sensor         │
└───────────────────────────┬────────────────────────────┘
                            │ (Digital Signals: I2S / GPIO / ADC)
                            ▼
┌────────────────────────────────────────────────────────┐
│  BOX 2: ESP32-S3 COMPUTE & POWER MANAGEMENT            │
│  • 240 MHz Dual-Core Xtensa LX7 (Core 0: DSP / Core 1: AI)
│  • MAX17048 I2C Fuel Gauge (0x36) Battery Monitoring   │
│  • High-Capacity LiPo/Li-Ion Cell (15 µA Deep Sleep)   │
└───────────────────────────┬────────────────────────────┘
                            │ (Digital Audio Window & Telemetry)
                            ▼
┌────────────────────────────────────────────────────────┐
│  BOX 3: NOISE-ROBUST DSP & SPECTROGRAM EXTRACTION      │
│  • Adaptive Quantile Spectral Subtraction (-75 dB Rain)│
│  • 25ms Hann Windowing with 50% Frame Overlap          │
│  • 128 Log-Mel Filterbank Frequency Bins               │
└───────────────────────────┬────────────────────────────┘
                            │ (128x157 Spectrogram Tensor)
                            ▼
┌────────────────────────────────────────────────────────┐
│  BOX 4: ON-DEVICE AI CLASSIFIER (MOBILENETV3-SMALL)    │
│  • Lightweight Depthwise Separable Convolutions        │
│  • 14 Unified Acoustic Classes (Chainsaw, Axe, Gunshot)│
│  • Sub-Second Edge Inference (< 420 ms Latency)        │
└───────────────────────────┬────────────────────────────┘
                            │ (Acoustic Confidence & Class Label)
                            ▼
┌────────────────────────────────────────────────────────┐
│  BOX 5: CADIE CONTEXT-AWARE DECISION ENGINE            │
│  • Cross-Sensory Bayesian Correlation                  │
│  • Audio Confidence + Temperature/Smoke Spike Analysis │
│  • 4-Tier Risk Assessment (Critical, High, Med, Low)   │
└───────────────────────────┬────────────────────────────┘
                            │ (Verified Threat Level & GPS Coordinates)
                            ▼
┌────────────────────────────────────────────────────────┐
│  BOX 6: TRI-TIER STAKEHOLDER TRIAGE DISPATCH           │
│  • Tier 1: Forest Chief Executive (Web Command Center) │
│  • Tier 2: Field Rangers (Tactical Intercept GPS Push) │
│  • Tier 3: Local Communities (SMS Hazard Warnings)     │
└────────────────────────────────────────────────────────┘
```

---

### 🖼️ Master Image Generation Prompt (For Midjourney / DALL-E 3 / Imagen / Canva)

```text
Professional academic engineering system architecture flowchart presented as a clean sequential box structure on a pure solid white background (#FFFFFF). 

The diagram features six elegant rounded rectangular boxes arranged vertically in a sequential top-to-bottom pipeline, connected by bold, clean directional downward flow arrows:

1. Box 1 (Top, Cyan border): "1. MULTIMODAL SENSING" — Icons of MEMS microphone, DHT22 temperature sensor, and MQ-135 smoke sensor. Crisp text: "16 kHz I2S Audio + Ambient Microclimate".
2. Box 2 (Second, Royal Blue border): "2. ESP32-S3 COMPUTE & POWER" — Icon of dual-core microcontroller chip, MAX17048 fuel gauge IC, and rechargeable LiPo/Li-Ion battery pack. Crisp text: "Dual-Core 240 MHz + MAX17048 Battery Fuel Gauge + 15 uA Deep Sleep".
3. Box 3 (Third, Cobalt Blue border): "3. NOISE-ROBUST DSP ENGINE" — Graphic of audio waveform transforming into a 128-bin Log-Mel Spectrogram. Crisp text: "Quantile Denoising + 128 Mel-Bins Extraction".
4. Box 4 (Fourth, Emerald Green border): "4. ON-DEVICE AI CLASSIFIER" — Neural network icon labeled "MobileNetV3-Small". Crisp text: "14 Sound Classes + Sub-Second Latency (<420ms)".
5. Box 5 (Fifth, Purple/Indigo border): "5. CADIE CONTEXT ENGINE" — Multi-sensor fusion icon cross-checking sound + heat + smoke. Crisp text: "Bayesian Reasoning + 91.5% False Alarm Suppression".
6. Box 6 (Bottom, Crimson Red border): "6. TRI-TIER TRIAGE DISPATCH" — Three distinct outgoing alert paths: Chief Command Dashboard, Ranger Tactical GPS Push, and Community Safety Warning.

Design Style: Modern flat technical engineering schematic, crisp bold typography in deep slate navy (#0F172A), subtle soft card backgrounds (#F8FAFC), colored border accents, high-contrast text, completely pure solid white background with zero dark vignette or gradients, IEEE academic conference presentation slide standard, vector graphic aesthetic, 8k resolution.
```

---

### 💡 Short Version (For Quick AI Slide Prompts / Gamma / Canva)

```text
Clean engineering system design flowchart on pure white background (#FFFFFF). Sequential box-by-box pipeline with downward flow arrows:
[Box 1: 16kHz Multimodal Sensors (INMP441 + DHT22 + MQ-135)] -> 
[Box 2: ESP32-S3 Dual-Core Compute & MAX17048 Battery Power (15uA Sleep)] -> 
[Box 3: Denoising DSP & 128 Log-Mel Spectrogram] -> 
[Box 4: MobileNetV3-Small On-Device AI (<420ms)] -> 
[Box 5: CADIE Context Fusion Engine (Audio + Temp + Smoke)] -> 
[Box 6: Tri-Tier Triage Alerts: Chief, Ranger, Public].
Modern modular boxes with clean colored borders, bold navy typography, emerald and cyan accents, IEEE conference slide standard.
```
