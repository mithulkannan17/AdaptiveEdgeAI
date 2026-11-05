# 🌲 AuraForest Sentinel — Image Generation Prompt Suite for Project Poster

This directory contains tailored, hyper-detailed prompts engineered for state-of-the-art AI image generators (**Midjourney v6**, **DALL-E 3 / ChatGPT**, **Stable Diffusion XL / SDXL**, and **Leonardo AI**) to create visuals for your project poster, research paper, and presentation slides.

---

## 🎨 Background Design Philosophy (Poster Print Optimization)

As specifically calibrated for academic project posters and presentation boards:

1. **Diagrams & Flowcharts inside Boxes**:
   - Formatted with **Option A: Pure Clean White Background (`#FFFFFF`)** with modular, rounded container cards, subtle drop-shadows, and crisp vector arrows.
   - **Benefit**: Ensures zero black ink bleeding when printed on physical posters, and integrates seamlessly into white slide templates.
2. **Environmental & Physical Visuals**:
   - Formatted with **Authentic Natural Backgrounds** (tropical rainforest canopies, misty jungle foliage, realistic sunlight god-rays, or high-tech tactical operations command rooms).
   - **Benefit**: Delivers deep visual immersion and photorealistic storytelling.

---

## 📁 Directory Structure & File Index

| File | Content & Focus | Background Style |
| :--- | :--- | :--- |
| **[`01_workflow_pipeline_flowchart.md`](./01_workflow_pipeline_flowchart.md)** | End-to-End System Flowchart (Sensors → Edge AI → CADIE → Dispatch) | **Pure Clean White Background** (Modular Process Cards) |
| **[`02_multi_role_stakeholder_alerts.md`](./02_multi_role_stakeholder_alerts.md)** | 3 Stakeholder Profiles (Chief Command HQ, Field Ranger, Public Alert) | **Option A**: White Background Cards<br>**Option B**: In-Field Rainforest / Ops Room |
| **[`03_forest_threat_landscape.md`](./03_forest_threat_landscape.md)** | Forest Threat Landscape (Chainsaws, Gunshots, Wildfires, Encroachment) | **Authentic Rainforest Threat Environment** (Deep jungle mist) |
| **[`04_tactical_spatial_forest_map.md`](./04_tactical_spatial_forest_map.md)** | Spatial Reserve Map (Node Dots, Ranger Patrol Dots, Roads, Village) | **Option A**: 3D Floating Terrain on White<br>**Option B**: In-Situ Topographic Satellite Map |
| **[`05_adaptive_edge_ai_solution.md`](./05_adaptive_edge_ai_solution.md)** | Adaptive Edge AI Solution (Multimodal Fusion, Edge AI Classifier, CADIE) | **Pure Clean White Background** (Modular Architecture Boxes) |
| **[`06_sentinel_command_monitoring_dashboard.md`](./06_sentinel_command_monitoring_dashboard.md)** | Real-time Tactical Monitoring Dashboard UI (Spectrogram, GPS, Telemetry) | **Option A**: Realistic Curved OLED in Ops Room<br>**Option B**: Clean Floating UI Mockup on White |
| **[`07_rugged_hardware_sentinel_node.md`](./07_rugged_hardware_sentinel_node.md)** | Physical ESP32 Hardware Node 3D in Canopy & Exploded PCB View | **Option A**: Mossy Tree Canopy in Rainforest<br>**Option B**: Exploded 3D CAD on Pure White |
| **[`08_combined_hero_presentation_posters.md`](./08_combined_hero_presentation_posters.md)** | Dual-Panel Combined Visuals (Hardware + Dashboard, Threat + Intercept) | **Option C1**: Clean White Academic Poster Board<br>**Option A/B**: Dual-World Rainforest + HUD |

---

## 🛠️ How to Generate the Best Images

### 1. Midjourney v6 (Recommended for Best Visual Quality)
- Copy the text from the `Primary Prompt` code block in any file.
- Type `/imagine` in Discord and paste the prompt.
- **Parameters already included**:
  - `--v 6.0` (latest photorealism engine)
  - `--style raw` (reduces Midjourney's default fantasy bias, enforces scientific/technical accuracy)
  - `--ar 16:9` (widescreen banner) or `--ar 3:4` (vertical poster slot)

### 2. DALL-E 3 (via ChatGPT Plus / Microsoft Designer)
- Copy the `Primary Prompt` text directly.
- Tip: Prefix with: *"Generate a high-tech scientific presentation illustration with crisp infographic details: [PASTE PROMPT]"*.
- DALL-E 3 excels at text fidelity and schematic diagrams.

### 3. Stable Diffusion XL (SDXL) / Leonardo AI
- **Model Recommendation**: SDXL 1.0 Base + Refiner or Photoreal v2 on Leonardo.
- Set **Sampling Steps**: 30-40.
- Set **CFG Scale**: 7.0 - 8.5.
- Copy the `Negative Prompt` from each file into the negative prompt box to avoid artifacts.

---

## 🖨️ Printing & Poster Resolution Tips
- **Aspect Ratio for Banners**: Use `--ar 16:9` or `--ar 21:9`.
- **Aspect Ratio for Portrait Columns**: Change to `--ar 3:4` or `--ar 2:3`.
- **Upscaling for Physical A1 / A0 Print**: Run generated images through an AI upscaler like [Upscayl](https://www.upscayl.org/) (free, open source) or [Magnific AI](https://magnific.ai/) to get 4K or 8K 300 DPI print quality without pixelation.
