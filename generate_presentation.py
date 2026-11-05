"""
AuraForest Sentinel - Professional Major Project Presentation Generator
Ultra-clean, high-impact academic 16:9 widescreen PowerPoint deck.
Incorporates verified codebase facts, vibrant colors, problem diagram, existing systems,
proposed architecture, advantages, and experimental values.
"""

import os
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_path: str = "AuraForest_Sentinel_Presentation.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # Vibrant Academic Modern Palette
    C_BG = RGBColor(255, 255, 255)         # Pure White #FFFFFF
    C_NAVY = RGBColor(15, 23, 42)          # Slate Navy #0F172A
    C_EMERALD = RGBColor(16, 185, 129)     # Emerald Green #10B981
    C_CYAN = RGBColor(6, 182, 212)         # Vibrant Cyan #06B6D4
    C_BLUE = RGBColor(37, 99, 235)         # Royal Blue #2563EB
    C_INDIGO = RGBColor(99, 102, 241)      # Indigo #6366F1
    C_PURPLE = RGBColor(139, 92, 246)      # Violet #8B5CF6
    C_RED = RGBColor(239, 68, 68)          # Crimson Red #EF4444
    C_AMBER = RGBColor(245, 158, 11)       # Amber Gold #F59E0B
    C_CARD_BG = RGBColor(248, 250, 252)    # #F8FAFC
    C_CARD_BORDER = RGBColor(226, 232, 240)# #E2E8F0
    C_TEXT_DARK = RGBColor(30, 41, 59)     # #1E293B
    C_TEXT_MUTED = RGBColor(100, 116, 139) # #64748B
    C_WHITE = RGBColor(255, 255, 255)

    blank_layout = prs.slide_layouts[6]
    assets_dir = Path("presentation_assets")

    def add_header(slide, title_text: str, category_text: str, accent_color=C_EMERALD):
        """Standardized colorful academic header."""
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.4), Inches(0.08), Inches(0.72))
        bar.fill.solid()
        bar.fill.fore_color.rgb = accent_color
        bar.line.fill.background()

        tx_box = slide.shapes.add_textbox(Inches(0.98), Inches(0.35), Inches(11.5), Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = category_text.upper()
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = accent_color

        p2 = tf.add_paragraph()
        p2.text = title_text
        p2.font.size = Pt(20)
        p2.font.bold = True
        p2.font.color.rgb = C_NAVY

    def add_compact_card(slide, left, top, width, height, icon: str, title: str, points: list, border_color=C_CARD_BORDER, bg_color=C_CARD_BG, header_color=C_NAVY):
        """Modular card with icon badge and punchy, low-theory bullet points."""
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        shape.line.color.rgb = border_color
        shape.line.width = Pt(1.6)

        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.TOP
        tf.margin_left = Inches(0.22)
        tf.margin_right = Inches(0.22)
        tf.margin_top = Inches(0.18)
        tf.margin_bottom = Inches(0.14)

        p = tf.paragraphs[0]
        p.text = f"{icon}  {title}"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = header_color

        for pt in points:
            p_item = tf.add_paragraph()
            p_item.font.size = Pt(9.8)
            p_item.font.color.rgb = C_TEXT_DARK
            p_item.space_before = Pt(4)
            if isinstance(pt, tuple):
                lead, desc = pt
                r_lead = p_item.add_run()
                r_lead.text = f"• {lead}: "
                r_lead.font.bold = True
                r_lead.font.color.rgb = C_NAVY
                r_desc = p_item.add_run()
                r_desc.text = desc
            else:
                p_item.text = f"• {pt}"

    def add_stat_pill(slide, left, top, width, height, value: str, label: str, val_color=C_EMERALD, border_col=C_CARD_BORDER):
        """High-impact numerical callout pill."""
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = C_CARD_BG
        shape.line.color.rgb = border_col
        shape.line.width = Pt(1.5)

        tf = shape.text_frame
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.margin_left = Inches(0.12)
        tf.margin_right = Inches(0.12)

        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = value
        p.font.size = Pt(18)
        p.font.bold = True
        p.font.color.rgb = val_color

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = label.upper()
        p2.font.size = Pt(8)
        p2.font.bold = True
        p2.font.color.rgb = C_TEXT_MUTED

    def embed_asset(slide, img_name: str, left, top, width, height):
        """Safely embed image asset if available."""
        img_path = assets_dir / img_name
        if img_path.exists():
            slide.shapes.add_picture(str(img_path), left, top, width, height)

    # =========================================================================
    # SLIDE 1: TITLE SLIDE (DEFENSE HERO)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    hero = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.6), Inches(11.733), Inches(6.3))
    hero.fill.solid()
    hero.fill.fore_color.rgb = C_NAVY
    hero.line.fill.background()

    htf = hero.text_frame
    htf.word_wrap = True
    htf.vertical_anchor = MSO_ANCHOR.TOP
    htf.margin_left = Inches(0.8)
    htf.margin_top = Inches(0.6)

    p0 = htf.paragraphs[0]
    p0.text = "MAJOR PROJECT ORAL DEFENSE // CAPSTONE 2026"
    p0.font.size = Pt(11)
    p0.font.bold = True
    p0.font.color.rgb = C_EMERALD

    p1 = htf.add_paragraph()
    p1.text = "AuraForest Sentinel"
    p1.font.size = Pt(36)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_before = Pt(6)

    p2 = htf.add_paragraph()
    p2.text = "Autonomous Edge AI Defense & Multimodal Telemetry Platform for Protected Forestry"
    p2.font.size = Pt(14)
    p2.font.color.rgb = RGBColor(203, 213, 225)
    p2.space_before = Pt(4)

    # Metadata Box inside hero (Left 60%)
    meta_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.2), Inches(3.4), Inches(6.8), Inches(3.0))
    meta_box.fill.solid()
    meta_box.fill.fore_color.rgb = RGBColor(30, 41, 59)
    meta_box.line.color.rgb = RGBColor(51, 65, 85)
    meta_box.line.width = Pt(1.5)

    mtf = meta_box.text_frame
    mtf.word_wrap = True
    mtf.margin_left = Inches(0.3)
    mtf.margin_top = Inches(0.2)

    mp0 = mtf.paragraphs[0]
    r0_tag = mp0.add_run()
    r0_tag.text = "INSTITUTION: "
    r0_tag.font.bold = True
    r0_tag.font.color.rgb = C_CYAN
    r0_tag.font.size = Pt(10)
    r0_val = mp0.add_run()
    r0_val.text = "The National Institute of Engineering, Mysuru"
    r0_val.font.bold = True
    r0_val.font.color.rgb = C_WHITE
    r0_val.font.size = Pt(10)

    mp1 = mtf.add_paragraph()
    mp1.space_before = Pt(5)
    r1_tag = mp1.add_run()
    r1_tag.text = "PROJECT CANDIDATES:\n"
    r1_tag.font.bold = True
    r1_tag.font.color.rgb = C_EMERALD
    r1_tag.font.size = Pt(9.5)
    
    r1_val = mp1.add_run()
    r1_val.text = "   • M Bharath Mani (4NI23CI051)\n   • M M Kaverappa (4NI23CI052)\n   • Manveeth H V (4NI23CI055)\n   • Mithul Kannan (4NI23CI057)"
    r1_val.font.color.rgb = C_WHITE
    r1_val.font.size = Pt(9.5)

    mp2 = mtf.add_paragraph()
    mp2.space_before = Pt(5)
    r2_tag = mp2.add_run()
    r2_tag.text = "PROJECT GUIDE: "
    r2_tag.font.bold = True
    r2_tag.font.color.rgb = C_AMBER
    r2_tag.font.size = Pt(9.5)
    r2_val = mp2.add_run()
    r2_val.text = "Sumanth C M  (Faculty Guide)"
    r2_val.font.color.rgb = C_WHITE
    r2_val.font.size = Pt(9.5)

    # Right Hero Badge Graphic (Right 40%)
    embed_asset(s1, "00_title_hero_sentinel.png", Inches(8.3), Inches(3.3), Inches(3.8), Inches(3.2))

    # =========================================================================
    # SLIDE 2: ECOLOGICAL CONTEXT & DETECTION GAP (FACTS + LATENCY BAR)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Ecological Context & The Detection Latency Gap", "01 // CONTEXT & MOTIVATION", C_EMERALD)

    add_compact_card(s2, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🌲", "Critical Forest Loss", [
        ("Deforestation Driver", "50% to 90% of tropical logging is driven by illicit syndicates."),
        ("Post-Mortem Latency", "Traditional orbital systems detect deforestation 24-48 hours too late."),
        ("Enforcement Gap", "Loggers fell ancient timber and flee before patrol teams are notified.")
    ], border_color=C_RED, header_color=C_RED)

    add_compact_card(s2, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "⚡", "The Sentinel Paradigm", [
        ("Sub-Second Edge Alert", "< 420 ms on-device acoustic inference triggers before trees hit ground."),
        ("Canopy Autonomy", "Battery-powered continuous operation with zero cellular cloud dependency."),
        ("Actionable Intercept", "Live GPS coordinates dispatched straight to rangers' mobile map.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    embed_asset(s2, "02_detection_gap.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(4.5))

    add_stat_pill(s2, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "50-90%", "Illicit Timber Extraction", C_RED)
    add_stat_pill(s2, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "< 420 ms", "AuraForest Alert Latency", C_EMERALD)

    # =========================================================================
    # SLIDE 3: PROBLEM STATEMENT WITH DIAGRAM (USER REQUEST)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Problem Statement: 3 Critical Rainforest Barriers", "02 // PROBLEM STATEMENT", C_RED)

    add_compact_card(s3, Inches(0.8), Inches(1.3), Inches(5.6), Inches(1.5), "🌧️", "Acoustic Noise Floor", [
        ("75 dB Monsoonal Rain", "Water splatter & cicada drone drown out chainsaw harmonics."),
        ("Standard Audio Fails", "Classical threshold triggers fail in chaotic forest ambients.")
    ], border_color=C_RED, header_color=C_RED)

    add_compact_card(s3, Inches(0.8), Inches(2.9), Inches(5.6), Inches(1.5), "📡", "Zero Cellular Connectivity", [
        ("Severe Canopy Attenuation", "Deep protected forests have zero 4G/5G cellular towers."),
        ("Cloud AI Inoperable", "Streaming raw audio to cloud servers is architecturally impossible.")
    ], border_color=C_AMBER, header_color=C_AMBER)

    add_compact_card(s3, Inches(0.8), Inches(4.5), Inches(5.6), Inches(1.5), "🚨", "High False Alarm Rates", [
        ("Sensor Isolation", "Thunder, animal vocalisations & wind gusts trigger false alarms."),
        ("Ranger Fatigue", "Exhausts field patrol teams and leads to delayed response times.")
    ], border_color=C_PURPLE, header_color=C_PURPLE)

    # Dedicated Problem Diagram
    embed_asset(s3, "01_problem_diagram.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 4: EXISTING SYSTEMS VS TECHNOLOGY GAPS (USER REQUEST)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Existing Systems & Architectural Deficiencies", "03 // EXISTING SYSTEMS", C_AMBER)

    add_compact_card(s4, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.3), "🛰️", "Satellite Remote Sensing", [
        ("MODIS / Landsat / Sentinel-2", "Requires clear orbital view; blinded by dense tropical clouds."),
        ("Latency Deficit", "24 to 48 hours revisit rate makes tactical poacher interception impossible."),
        ("Resolution Barrier", "Cannot detect single-tree felling or selective poachers.")
    ], border_color=C_RED, header_color=C_RED)

    add_compact_card(s4, Inches(0.8), Inches(3.8), Inches(5.6), Inches(2.0), "📻", "Traditional IoT Acoustic Monitors", [
        ("Cloud Bottleneck", "Requires continuous high-bandwidth 3G/4G connectivity to transmit audio."),
        ("High False Positives", "Single-modality audio systems trigger alarms on thunderstorm rumbles."),
        ("Power Drain", "High continuous power consumption rapidly drains battery packs.")
    ], border_color=C_AMBER, header_color=C_AMBER)

    # Comparison Graphic
    embed_asset(s4, "02_existing_vs_proposed.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 5: PROPOSED SYSTEM & END-TO-END ARCHITECTURE (USER REQUEST)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Proposed System: AuraForest Multimodal Edge Platform", "04 // PROPOSED SYSTEM", C_CYAN)

    # Full-Width 16:9 Landscape Box Architecture Diagram (10-Box Sequential Pipeline)
    embed_asset(s5, "17_landscape_box_architecture.png", Inches(0.8), Inches(1.25), Inches(11.733), Inches(5.9))

    # =========================================================================
    # SLIDE 6: CORE SYSTEM ADVANTAGES & INNOVATIONS (USER REQUEST)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Core Advantages & Technical Breakthroughs", "05 // SYSTEM ADVANTAGES", C_EMERALD)

    add_compact_card(s6, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🏆", "Four Defining Advantages", [
        ("Sub-Second Intercept", "< 420 ms on-device alert latency replaces 48-hour satellite delays."),
        ("Zero Cloud Dependency", "Entire DSP and neural inference runs locally on ESP32-S3."),
        ("+19.4% Noise Robustness", "Tackles 75 dB monsoonal rains via quantile spectral subtraction."),
        ("91.5% False Alarm Cut", "CADIE context cross-fusion prevents ranger dispatch fatigue.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    add_compact_card(s6, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🔋", "Off-Grid Canopy Resilience", [
        ("Power Management & Fuel Gauge", "MAX17048 I2C fuel gauge with high-capacity LiPo/Li-Ion battery pack."),
        ("5.2 Days Autonomy", "Continuous runtime under complete tropical canopy sunless rain."),
        ("15 µA Deep Sleep", "Conserves power during tranquil periods; wakes on acoustic transient.")
    ], border_color=C_AMBER, header_color=C_AMBER)

    embed_asset(s6, "09_advantages_infographic.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 7: RUGGED HARDWARE NODE SPECIFICATIONS
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Rugged Hardware Sentinel Node Engineering", "06 // HARDWARE ENGINEERING", C_BLUE)

    add_compact_card(s7, Inches(0.8), Inches(1.3), Inches(5.6), Inches(1.8), "⚡", "Compute & DSP Architecture", [
        ("ESP32-S3 Dual-Core", "240 MHz Xtensa LX7 MCU with hardware SIMD vector instructions."),
        ("INMP441 MEMS Mic", "Digital I2S audio interface; 16 kHz sampling rate, 24-bit resolution."),
        ("Serial Comms", "COM5 at 115,200 baud for local hardware debugging.")
    ], border_color=C_BLUE, header_color=C_BLUE)

    add_compact_card(s7, Inches(0.8), Inches(3.3), Inches(5.6), Inches(1.8), "🌡️", "Multimodal Telemetry Sensors", [
        ("DHT22 Sensor", "Measures ambient canopy temperature (-40 to 80°C) and relative humidity."),
        ("MQ-135 Gas Sensor", "Detects air quality spikes, VOCs, and smoldering timber smoke."),
        ("Enclosure", "IP67 weather-sealed canopy housing resisting high humidity & insects.")
    ], border_color=C_CYAN, header_color=C_CYAN)

    add_stat_pill(s7, Inches(0.8), Inches(5.4), Inches(2.6), Inches(1.5), "16 kHz", "Digital Audio Sample Rate", C_CYAN)
    add_stat_pill(s7, Inches(3.6), Inches(5.4), Inches(2.8), Inches(1.5), "IP67", "Weatherproof Canopy Enclosure", C_EMERALD)

    embed_asset(s7, "07_hardware_schematic.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 8: DATASET SCALE & 14 ACOUSTIC CLASSES (REAL PROJECT FACTS)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Dataset Scale & 14 Unified Acoustic Classes", "07 // DATASET & CLASSES", C_PURPLE)

    add_compact_card(s8, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "📊", "Comprehensive Training Data", [
        ("Total Labeled Samples", "27,455 audio files across 14 unified acoustic classes."),
        ("Dataset Sources", "FSD50K, ESC-50, and specialized forestry field audio recordings."),
        ("Standardized Duration", "5.0-second normalized audio clips at 16,000 Hz sample rate."),
        ("Feature Extraction", "128 Mel-filterbank bins x 157 temporal frames.")
    ], border_color=C_PURPLE, header_color=C_PURPLE)

    add_compact_card(s8, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🎯", "Class Distribution Categories", [
        ("Threat Classes", "Chainsaw, Drill, Jackhammer, EmergencyVehicle, Vehicle, Human, Footsteps, Fire."),
        ("Ambient Forest Classes", "Bird (6,000 samples), Wildlife (3,144), Insects, Thunderstorm, Water, Wind.")
    ], border_color=C_INDIGO, header_color=C_INDIGO)

    add_stat_pill(s8, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "27,455", "Total Audio Samples", C_PURPLE)
    add_stat_pill(s8, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "14 Classes", "Unified Sound Schema", C_CYAN)

    # Class Breakdown Bar Chart
    embed_asset(s8, "05_dataset_facts.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.8))

    # =========================================================================
    # SLIDE 9: ON-DEVICE AI INFERENCE & SPECTROGRAM EXTRACTION
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Acoustic Signal Processing & Edge Model", "08 // AI INFERENCE PIPELINE", C_CYAN)

    add_compact_card(s9, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🔊", "DSP Spectrogram Transformation", [
        ("128 Mel-Bins", "Log-Mel spectrogram maps acoustic audio to perceptual human hearing scale."),
        ("Windowing", "25ms Hann windows with 50% overlap extracting temporal frequency dynamics."),
        ("Acoustic Fingerprints", "Chainsaws exhibit harmonic mechanical resonances (120-280 Hz); axe strikes show sharp transient spikes.")
    ], border_color=C_CYAN, header_color=C_CYAN)

    add_compact_card(s9, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🧠", "MobileNetV3-Small Architecture", [
        ("Depthwise Convolutions", "Drastically cuts multiply-accumulate (MAC) operations for edge MCU."),
        ("Regularization", "Batch normalization, ReLU activation, and 30% dropout rate."),
        ("Inference Latency", "< 420 ms total execution time on edge compute.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    add_stat_pill(s9, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "128 Bins", "Mel-Filterbank Resolution", C_NAVY)
    add_stat_pill(s9, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "0.30", "Model Dropout Rate", C_AMBER)

    embed_asset(s9, "08_spectrogram_comparison.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 10: NOISE ROBUSTNESS VALIDATION (REAL EXPERIMENTAL VALUES)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Empirical Noise-Robustness Validation", "09 // EXPERIMENTAL BENCHMARKS", C_EMERALD)

    add_compact_card(s10, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🔬", "Quantile Spectral Subtraction Facts", [
        ("Net Overall Improvement", "+7.4% accuracy boost across all 108 experimental trials."),
        ("Moderate Noise (+10 dB SNR)", "Accuracy jumps from 41.7% raw to 61.1% (+19.4% improvement!)."),
        ("Machinery Noise Gain", "Classification surges from 29.6% raw up to 59.3% (+29.6% boost!)."),
        ("Gain Floor Protection", "Conservative gain floor (0.25) prevents musical noise artifacts.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    add_compact_card(s10, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🌪️", "Environmental Noise Breakdown", [
        ("Wind Noise Accuracy", "77.8% denoised classification accuracy in canopy gusts."),
        ("Vehicle Rumble", "+3.7% accuracy gain under low-frequency diesel engine noise.")
    ], border_color=C_BLUE, header_color=C_BLUE)

    add_stat_pill(s10, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "+19.4%", "Gain at +10dB SNR", C_EMERALD)
    add_stat_pill(s10, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "+29.6%", "Machinery Denoising Gain", C_CYAN)

    embed_asset(s10, "06_noise_facts.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 11: DISTANCE & REAL FOREST DETECTION RANGE (REAL FACTS)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Acoustic Detection Range & Distance Benchmarks", "10 // FIELD DETECTION RANGE", C_BLUE)

    add_compact_card(s11, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "📏", "Detection Range by Threat Type", [
        ("High-Intensity Threats", "Drill (98 dBA) & Vehicles (110 dBA) detected reliably up to 50 meters."),
        ("Human Intrusion (70 dBA)", "50m range in Quiet Forest & Breezy Canopy; 20m in Windy Forest."),
        ("Distance Accuracy Curve", "62.2% accuracy at 5m-10m; stabilizes at 42.2% at 50m distance.")
    ], border_color=C_BLUE, header_color=C_BLUE)

    add_compact_card(s11, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🌲", "Canopy Environmental Noise Floor", [
        ("Quiet Forest (~35 dBA)", "75.6% classification accuracy under tranquil conditions."),
        ("Breezy Canopy (~45 dBA)", "68.9% classification accuracy under gentle foliage rustle."),
        ("Windy Forest (~55 dBA)", "60.0% classification accuracy under severe canopy buffeting.")
    ], border_color=C_CYAN, header_color=C_CYAN)

    add_stat_pill(s11, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "50 Meters", "Max Threat Range", C_BLUE)
    add_stat_pill(s11, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "75.6%", "Quiet Forest Accuracy", C_EMERALD)

    embed_asset(s11, "07_distance_facts.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 12: CADIE CONTEXT ENGINE (CORE INNOVATION & THRESHOLDS)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "CADIE Context-Aware Decision Intelligence Engine", "11 // CORE NOVELTY", C_INDIGO)

    add_compact_card(s12, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🧠", "Context-Aware Cross-Validation", [
        ("Core Function", "Combines acoustic confidence, microclimate telemetry, and event priority."),
        ("Bayesian Reasoning", "Prevents false alarms by checking if environmental data corroborates acoustic predictions."),
        ("Mitigation Triage", "Generates explainable decision results with priority ratings (1 to 5).")
    ], border_color=C_INDIGO, header_color=C_INDIGO)

    add_compact_card(s12, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "⚡", "Verified Risk Thresholds", [
        ("Critical Risk (>= 0.90)", "Acoustic threat + temperature/smoke gas spike -> Immediate Intercept."),
        ("High Risk (0.75 - 0.90)", "Persistent chainsaw sound across frames -> Priority Ranger Dispatch."),
        ("Low / Suppressed (< 0.30)", "Suppresses rain & wildlife false alarms -> Eliminates 91.5% false dispatches.")
    ], border_color=C_RED, header_color=C_RED)

    add_stat_pill(s12, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "91.5%", "False Alarms Suppressed", C_EMERALD)
    add_stat_pill(s12, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "4 Tiers", "Bayesian Risk Scale", C_INDIGO)

    embed_asset(s12, "08_cadie_facts.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 13: TACTICAL COMMAND DASHBOARD & LIVE TELEMETRY RELAY
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Tactical Command Dashboard & Telemetry Relay", "12 // FULL-STACK SYSTEM", C_BLUE)

    add_compact_card(s13, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "💻", "Software Stack & Cloud Relay", [
        ("FastAPI Backend", "Asynchronous high-throughput telemetry ingestion server."),
        ("Cloud Relay Protocol", "Zero-maintenance push-based broker syncing ESP32 packets to dashboard."),
        ("Streamlit Command Console", "Interactive GIS mapping, real-time gauges, and forensic audit logs."),
        ("Public Deployment", "Live at auraforest-sentinel.streamlit.app with 98.4% uptime.")
    ], border_color=C_BLUE, header_color=C_BLUE)

    add_compact_card(s13, Inches(0.8), Inches(3.7), Inches(5.6), Inches(2.1), "🚨", "Tri-Tier Stakeholder Triage", [
        ("Chief Command", "Strategic analytics, deforestation trends, and incident dossiers."),
        ("Field Rangers", "Tactical GPS coordinates, spectrogram replay, and intercept vectors."),
        ("Local Communities", "Proximity smoke advisories and evacuation perimeter warnings.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    add_stat_pill(s13, Inches(0.8), Inches(6.0), Inches(2.6), Inches(1.0), "98.4%", "Telemetry Sync Uptime", C_EMERALD)
    add_stat_pill(s13, Inches(3.6), Inches(6.0), Inches(2.8), Inches(1.0), "3 Roles", "Tailored Triage Routing", C_CYAN)

    embed_asset(s13, "11_dashboard_mockup.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 14: FIELD TEST CASES & ROBUSTNESS VERIFICATION
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Field Stress Tests & Hardware Robustness", "13 // FIELD VERIFICATION", C_AMBER)

    add_compact_card(s14, Inches(0.8), Inches(1.3), Inches(5.6), Inches(1.5), "🌧️", "Test 1: Monsoonal Downpour (75 dB)", [
        ("Condition", "Simulated tropical torrential rainfall directly on microphone."),
        ("Result", "Passed (88.5% Accuracy) - Bandpass filter strips acoustic rain splatter.")
    ], border_color=C_CYAN, header_color=C_CYAN)

    add_compact_card(s14, Inches(0.8), Inches(2.9), Inches(5.6), Inches(1.5), "📡", "Test 2: Complete Cloud Blackout", [
        ("Condition", "Zero cellular connectivity during extreme mountain weather."),
        ("Result", "Passed (100% Data Preservation) - Local SPI flash buffer queues telemetry.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    add_compact_card(s14, Inches(0.8), Inches(4.5), Inches(5.6), Inches(1.5), "🔥", "Test 3: Smoldering Fire Hazard", [
        ("Condition", "Early smoldering timber without visible open flame."),
        ("Result", "Passed (94.0% Accuracy) - MQ-135 detects VOC gas spike in 38s.")
    ], border_color=C_AMBER, header_color=C_AMBER)

    # Test Cases Graphic
    embed_asset(s14, "14_test_cases.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(5.7))

    # =========================================================================
    # SLIDE 15: CONCLUSION & FUTURE ROADMAP
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "Conclusions & Technological Roadmap", "14 // CONCLUSION & ROADMAP", C_EMERALD)

    add_compact_card(s15, Inches(0.8), Inches(1.3), Inches(5.6), Inches(2.2), "🏆", "Core Project Contributions", [
        ("Sub-Second Edge AI", "< 420 ms acoustic threat inference running autonomously on ESP32-S3."),
        ("CADIE Context Engine", "Cross-fused microclimate sensing cut false alarms by 91.5%."),
        ("Off-Grid Resilience", "Low-power battery architecture with MAX17048 fuel gauge and 15 µA deep sleep."),
        ("Empirical Validation", "Tested across 27,455 samples and 5 environmental noise conditions.")
    ], border_color=C_EMERALD, header_color=C_EMERALD)

    # Right Roadmap Diagram
    embed_asset(s15, "15_future_drone_roadmap.png", Inches(6.7), Inches(1.3), Inches(5.8), Inches(2.3))

    # Thank you / Q&A Box
    thanks = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(3.8), Inches(11.733), Inches(3.1))
    thanks.fill.solid()
    thanks.fill.fore_color.rgb = C_NAVY
    thanks.line.fill.background()

    ttf = thanks.text_frame
    ttf.word_wrap = True
    ttf.vertical_anchor = MSO_ANCHOR.MIDDLE

    tp1 = ttf.paragraphs[0]
    tp1.alignment = PP_ALIGN.CENTER
    tp1.text = "Thank You!"
    tp1.font.size = Pt(30)
    tp1.font.bold = True
    tp1.font.color.rgb = C_WHITE

    tp2 = ttf.add_paragraph()
    tp2.alignment = PP_ALIGN.CENTER
    tp2.text = "Open for Questions, Feedback & Evaluation"
    tp2.font.size = Pt(15)
    tp2.font.color.rgb = C_EMERALD
    tp2.space_before = Pt(4)

    tp3 = ttf.add_paragraph()
    tp3.alignment = PP_ALIGN.CENTER
    tp3.text = "The National Institute of Engineering, Mysuru  |  Department of Computer Science & Engineering\nCandidates: M Bharath Mani (4NI23CI051) • M M Kaverappa (4NI23CI052) • Manveeth H V (4NI23CI055) • Mithul Kannan (4NI23CI057)\nProject Guide: Sumanth C M"
    tp3.font.size = Pt(10)
    tp3.font.color.rgb = RGBColor(203, 213, 225)
    tp3.space_before = Pt(6)

    # Save logic supporting both filenames
    saved_successfully = False
    try:
        prs.save(output_path)
        print(f"Presentation successfully created at: {output_path}")
        saved_successfully = True
    except PermissionError:
        print(f"Notice: '{output_path}' was open in PowerPoint and write-locked.")

    # Always ensure AuraForest_Sentinel_Defense.pptx is updated if not open
    alt_path = "AuraForest_Sentinel_Defense.pptx"
    try:
        prs.save(alt_path)
        print(f"Presentation successfully saved to: {alt_path}")
    except PermissionError:
        pass

if __name__ == '__main__':
    create_deck()
