"""
AuraForest — Acoustic Spectrum & Spectrogram Visualizer
High-fidelity frequency spectrum analysis, 32-band octave visualizer,
and 2D interactive Log-Mel Spectrogram for edge acoustic intelligence.
"""

from __future__ import annotations

import io
from typing import Any
import numpy as np
import scipy.signal
import plotly.graph_objects as go
import streamlit as st


# Frequency band limits for 32 log-spaced bands (20 Hz - 8000 Hz at 16kHz SR)
BAND_EDGES_32 = np.logspace(np.log10(20), np.log10(8000), 33)
BAND_CENTERS_32 = [np.sqrt(BAND_EDGES_32[i] * BAND_EDGES_32[i + 1]) for i in range(32)]


def generate_acoustic_signal(
    event_label: str,
    mic_level: float = 500.0,
    duration: float = 3.0,
    sr: int = 16000,
) -> np.ndarray:
    """Generate or synthesize realistic acoustic waveforms based on the detected event."""
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples, endpoint=False)
    label_lower = str(event_label or "").lower()

    # Base noise floor
    base_noise = np.random.normal(0, 0.015, n_samples)

    if "chainsaw" in label_lower:
        # Chainsaw: 160 Hz fundamental + harmonics + engine jitter + mechanical rasp
        f0 = 165.0
        jitter = 1.0 + 0.05 * np.sin(2 * np.pi * 7.5 * t)
        harmonics = np.zeros(n_samples)
        for h in range(1, 14):
            amp = (1.0 / (h ** 0.85)) * (0.8 + 0.4 * np.sin(2 * np.pi * (h * 1.5) * t))
            harmonics += amp * np.sin(2 * np.pi * (f0 * h * jitter) * t)
        # Add high-frequency cutting teeth noise
        teeth_noise = scipy.signal.convolve(
            np.random.normal(0, 0.2, n_samples),
            np.ones(12) / 12,
            mode="same",
        )
        sig = 0.5 * harmonics + 0.25 * teeth_noise + base_noise

    elif any(k in label_lower for k in ["gunshot", "explosion", "firecracker"]):
        # Gunshot: sharp impulse + shockwave + low-frequency reverberant tail
        sig = base_noise.copy()
        shot_times = [0.35, 1.65] if "firecracker" in label_lower else [0.5]
        for st_time in shot_times:
            idx = int(st_time * sr)
            if idx < n_samples:
                decay_len = min(int(0.8 * sr), n_samples - idx)
                decay_t = np.linspace(0, 0.8, decay_len)
                impulse = np.exp(-decay_t * 18.0) * (
                    0.8 * np.sin(2 * np.pi * 95 * decay_t) +
                    0.6 * np.random.normal(0, 0.4, decay_len)
                )
                sig[idx:idx + decay_len] += impulse

    elif any(k in label_lower for k in ["fire", "smoke", "crackle"]):
        # Fire: low-frequency turbulent rumble + random crackle pops (Poisson spikes)
        rumble = scipy.signal.convolve(
            np.random.normal(0, 0.25, n_samples),
            np.hanning(80) / np.sum(np.hanning(80)),
            mode="same",
        )
        crackle = np.zeros(n_samples)
        n_pops = int(duration * 25)
        pop_indices = np.random.randint(0, n_samples - 200, n_pops)
        for p_idx in pop_indices:
            pop_t = np.linspace(0, 0.012, 180)
            pop_wave = np.sin(2 * np.pi * np.random.uniform(900, 2400) * pop_t) * np.exp(-pop_t * 350)
            crackle[p_idx:p_idx + 180] += pop_wave * np.random.uniform(0.3, 0.85)
        sig = rumble * 1.2 + crackle + base_noise

    elif any(k in label_lower for k in ["bird", "bioacoustic", "chirp"]):
        # Birdsong: FM frequency sweeps in the 2.5 kHz to 6 kHz range with pauses
        sig = base_noise.copy()
        # Add chirp motifs scaled to duration
        motifs = [(0.15 * duration, 0.35 * duration), (0.45 * duration, 0.65 * duration), (0.75 * duration, 0.95 * duration)]
        for start_s, end_s in motifs:
            i_start = int(start_s * sr)
            i_end = int(end_s * sr)
            if i_start < n_samples and i_end > i_start:
                i_end = min(i_end, n_samples)
                n_chirp = i_end - i_start
                chirp_t = np.linspace(0, (i_end - i_start) / sr, n_chirp)
                # Frequency modulated sweep
                f_inst = 3200 + 1800 * np.sin(2 * np.pi * 8.0 * chirp_t) + 400 * np.cos(2 * np.pi * 16.0 * chirp_t)
                phase = 2 * np.pi * np.cumsum(f_inst) / sr
                envelope = np.sin(np.pi * np.linspace(0, 1, n_chirp))
                sig[i_start:i_end] += 0.75 * envelope * np.sin(phase)

    elif any(k in label_lower for k in ["rain", "storm", "water"]):
        # Rain: pink noise with random droplet high-mid resonant splashes
        b_pink = np.random.normal(0, 0.2, n_samples)
        # Simple 1-pole filter to get 1/f characteristic
        pink_filt = scipy.signal.lfilter([0.049922035, -0.095993537, 0.050612699, -0.004408786], [1, -2.494956002, 2.017265875, -0.522189400], b_pink)
        sig = pink_filt * 1.5 + base_noise

    elif any(k in label_lower for k in ["wind", "storm"]):
        # Wind: Deep low-frequency surges (< 200 Hz)
        low_noise = scipy.signal.convolve(
            np.random.normal(0, 0.4, n_samples),
            np.hanning(300) / np.sum(np.hanning(300)),
            mode="same",
        )
        gust = 1.0 + 0.6 * np.sin(2 * np.pi * 0.4 * t)
        sig = low_noise * gust + base_noise * 0.5

    else:
        # Default Ambient / Quiet Forest
        gain = min(1.0, max(0.1, mic_level / 1500.0))
        sig = np.random.normal(0, 0.04 * gain, n_samples)
        # Gentle natural ambient resonance
        sig += 0.03 * gain * np.sin(2 * np.pi * 220 * t) + 0.02 * gain * np.sin(2 * np.pi * 440 * t)

    # Normalize to -1.0 .. 1.0 range
    max_val = np.max(np.abs(sig))
    if max_val > 0.001:
        sig = sig / max_val * 0.95
    return sig.astype(np.float32)


def compute_spectral_features(audio_signal: np.ndarray, sr: int = 16000) -> dict[str, Any]:
    """Calculate spectral features including FFT power, 32-band energies, centroid, and rolloff."""
    if len(audio_signal) == 0:
        audio_signal = np.zeros(sr, dtype=np.float32)

    # Compute FFT
    fft_vals = np.abs(np.fft.rfft(audio_signal))
    freqs = np.fft.rfftfreq(len(audio_signal), d=1.0 / sr)
    power = fft_vals ** 2 + 1e-12

    # Peak Frequency
    peak_idx = int(np.argmax(fft_vals))
    peak_freq = float(freqs[peak_idx])

    # Spectral Centroid (Center of mass)
    spectral_centroid = float(np.sum(freqs * power) / np.sum(power))

    # Spectral Rolloff (85% energy point)
    cumulative_power = np.cumsum(power)
    rolloff_threshold = 0.85 * cumulative_power[-1]
    rolloff_idx = np.searchsorted(cumulative_power, rolloff_threshold)
    spectral_rolloff = float(freqs[min(rolloff_idx, len(freqs) - 1)])

    # RMS in dBFS
    rms = float(np.sqrt(np.mean(audio_signal ** 2) + 1e-12))
    rms_dbfs = float(20 * np.log10(rms))

    # Spectral Flatness (Wiener entropy)
    geom_mean = np.exp(np.mean(np.log(power)))
    arith_mean = np.mean(power)
    spectral_flatness = float(geom_mean / arith_mean) if arith_mean > 0 else 0.0

    # 32 Logarithmic frequency band energy levels
    band_energies = []
    for i in range(32):
        low_f = BAND_EDGES_32[i]
        high_f = BAND_EDGES_32[i + 1]
        mask = (freqs >= low_f) & (freqs < high_f)
        if np.any(mask):
            band_p = np.mean(power[mask])
            # Convert to dB relative scale normalized 0-100%
            band_db = 10 * np.log10(band_p)
            norm_val = np.clip((band_db + 80) / 80.0 * 100.0, 5.0, 100.0)
        else:
            norm_val = 5.0
        band_energies.append(float(norm_val))

    return {
        "peak_frequency": peak_freq,
        "spectral_centroid": spectral_centroid,
        "spectral_rolloff": spectral_rolloff,
        "rms_dbfs": rms_dbfs,
        "spectral_flatness": spectral_flatness,
        "band_energies": band_energies,
        "band_centers": [float(f) for f in BAND_CENTERS_32],
    }


def create_spectrogram_figure(
    audio_signal: np.ndarray,
    sr: int = 16000,
    title: str = "Acoustic Log-Mel Spectrogram",
) -> go.Figure:
    """Generate an interactive Plotly Heatmap of the STFT / Log-Mel Spectrogram."""
    nperseg = 512
    noverlap = 384
    f, times, Zxx = scipy.signal.stft(
        audio_signal,
        fs=sr,
        nperseg=nperseg,
        noverlap=noverlap,
        window="hann",
    )
    # Convert to power in dBFS
    spec_db = 20 * np.log10(np.abs(Zxx) + 1e-5)
    # Clamp dynamic range to [-70, 0] dB
    spec_db = np.clip(spec_db, -70, 0)

    # Custom Bio-Sentinel Color Gradient: Dark -> Deep Green -> Vibrant Cyan -> Gold -> Coral
    custom_colorscale = [
        [0.0, "#080d0f"],
        [0.2, "#0b261e"],
        [0.4, "#145942"],
        [0.65, "#27c4b8"],
        [0.85, "#f2c66d"],
        [1.0, "#ff5e5e"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=spec_db,
            x=times,
            y=f,
            colorscale=custom_colorscale,
            colorbar=dict(
                title=dict(text="dBFS", font=dict(color="#7f9290", size=10, family="JetBrains Mono")),
                tickfont=dict(color="#7f9290", size=9, family="JetBrains Mono"),
                thickness=12,
                len=0.85,
                outlinewidth=0,
            ),
            hovertemplate="Time: %{x:.2f}s<br>Freq: %{y:.0f} Hz<br>Power: %{z:.1f} dBFS<extra></extra>",
        )
    )

    fig.update_layout(
        title=dict(
            text=f"◈ {title}",
            font=dict(color="#edf5f2", size=13, family="DM Sans"),
            x=0.02,
            y=0.96,
        ),
        paper_bgcolor="rgba(13,19,22,0.95)",
        plot_bgcolor="rgba(8,13,15,0.95)",
        margin=dict(l=55, r=20, t=38, b=45),
        height=280,
        xaxis=dict(
            title=dict(text="Time (seconds)", font=dict(color="#7f9290", size=10, family="DM Sans")),
            tickfont=dict(color="#7f9290", size=9, family="JetBrains Mono"),
            gridcolor="rgba(32,48,54,0.4)",
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="Frequency (Hz)", font=dict(color="#7f9290", size=10, family="DM Sans")),
            tickfont=dict(color="#7f9290", size=9, family="JetBrains Mono"),
            gridcolor="rgba(32,48,54,0.4)",
            range=[0, 8000],
            zeroline=False,
        ),
    )
    return fig


def render_spectrum_section(event_label: str, mic_level: float = 500.0) -> None:
    """Render the Acoustic Frequency Spectrum & Spectrogram section in Streamlit."""
    st.markdown(
        '<div class="section"><div class="section-title">Acoustic Spectrum & Frequency Analyzer</div>'
        '<div class="section-meta">REAL-TIME 32-BAND FFT · LOG-MEL SPECTROGRAM · SPECTRAL ENERGY DISTRIBUTION</div></div>',
        unsafe_allow_html=True,
    )

    # Top Control Bar: Source Mode Selector
    ctrl_col1, ctrl_col2, ctrl_spacer = st.columns([1.5, 1.5, 2.0])

    with ctrl_col1:
        source_mode = st.selectbox(
            "Spectrum Signal Source",
            options=[
                "Live Sentinel Event",
                "Preset: Chainsaw (Chainsaw / Engine)",
                "Preset: Gunshot / Firecracker",
                "Preset: Forest Fire Crackle",
                "Preset: Bioacoustic Birdsong",
                "Preset: Wind & Storm Turbulence",
                "Preset: Heavy Rain Noise",
                "Custom WAV Upload",
            ],
            index=0,
            key="spectrum_source_mode",
            help="Select the acoustic input signal to visualize in the spectrum analyzer",
        )

    custom_audio_bytes = None
    with ctrl_col2:
        if source_mode == "Custom WAV Upload":
            uploaded_file = st.file_uploader(
                "Upload WAV (16 kHz mono)",
                type=["wav"],
                key="spectrum_custom_wav",
                label_visibility="collapsed",
            )
            if uploaded_file is not None:
                custom_audio_bytes = uploaded_file.read()

    # Determine label / audio signal
    sr = 16000
    if source_mode == "Custom WAV Upload" and custom_audio_bytes:
        try:
            import scipy.io.wavfile as wavfile
            sr_file, raw_data = wavfile.read(io.BytesIO(custom_audio_bytes))
            if raw_data.ndim > 1:
                raw_data = raw_data[:, 0]  # Take first channel
            if raw_data.dtype == np.int16:
                audio_sig = raw_data.astype(np.float32) / 32768.0
            else:
                audio_sig = raw_data.astype(np.float32)
            sr = sr_file
            active_label = "Custom WAV File"
        except Exception as e:
            st.error(f"Error parsing WAV file: {e}")
            audio_sig = generate_acoustic_signal(event_label, mic_level, duration=3.0, sr=16000)
            active_label = event_label
    elif "Chainsaw" in source_mode:
        active_label = "Chainsaw"
        audio_sig = generate_acoustic_signal("chainsaw", mic_level, duration=3.0, sr=16000)
    elif "Gunshot" in source_mode:
        active_label = "Gunshot"
        audio_sig = generate_acoustic_signal("gunshot", mic_level, duration=3.0, sr=16000)
    elif "Fire" in source_mode:
        active_label = "Fire"
        audio_sig = generate_acoustic_signal("fire", mic_level, duration=3.0, sr=16000)
    elif "Bird" in source_mode:
        active_label = "Birdsong"
        audio_sig = generate_acoustic_signal("bird", mic_level, duration=3.0, sr=16000)
    elif "Wind" in source_mode:
        active_label = "Windstorm"
        audio_sig = generate_acoustic_signal("wind", mic_level, duration=3.0, sr=16000)
    elif "Rain" in source_mode:
        active_label = "Heavy Rain"
        audio_sig = generate_acoustic_signal("rain", mic_level, duration=3.0, sr=16000)
    else:
        active_label = event_label
        audio_sig = generate_acoustic_signal(event_label, mic_level, duration=3.0, sr=16000)

    # Compute Spectral Features
    features = compute_spectral_features(audio_sig, sr=sr)

    # Top Acoustic Diagnostics Metrics Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(
            f"""
            <div class="metric-card metric-card-gold">
                <div class="metric-header">
                    <span class="metric-label">Peak Frequency</span>
                    <span class="metric-icon-badge">🎯</span>
                </div>
                <div class="metric-value">{features['peak_frequency']:.0f}<span class="metric-unit">Hz</span></div>
                <div class="metric-sub">dominant harmonic</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            f"""
            <div class="metric-card metric-card-cyan">
                <div class="metric-header">
                    <span class="metric-label">Spectral Centroid</span>
                    <span class="metric-icon-badge">💡</span>
                </div>
                <div class="metric-value">{features['spectral_centroid']:.0f}<span class="metric-unit">Hz</span></div>
                <div class="metric-sub">acoustic brightness</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            f"""
            <div class="metric-card metric-card-purple">
                <div class="metric-header">
                    <span class="metric-label">Spectral Rolloff</span>
                    <span class="metric-icon-badge">📈</span>
                </div>
                <div class="metric-value">{features['spectral_rolloff']:.0f}<span class="metric-unit">Hz</span></div>
                <div class="metric-sub">85% energy boundary</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m4:
        st.markdown(
            f"""
            <div class="metric-card metric-card-emerald">
                <div class="metric-header">
                    <span class="metric-label">RMS Sound Power</span>
                    <span class="metric-icon-badge">🔊</span>
                </div>
                <div class="metric-value">{features['rms_dbfs']:.1f}<span class="metric-unit">dBFS</span></div>
                <div class="metric-sub">acoustic energy level</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with m5:
        tonality = "TONAL" if features['spectral_flatness'] < 0.15 else ("NOISY" if features['spectral_flatness'] > 0.45 else "BALANCED")
        tonality_accent = "gold" if tonality == "TONAL" else ("coral" if tonality == "NOISY" else "cyan")
        st.markdown(
            f"""
            <div class="metric-card metric-card-{tonality_accent}">
                <div class="metric-header">
                    <span class="metric-label">Spectral Texture</span>
                    <span class="metric-icon-badge">🔬</span>
                </div>
                <div class="metric-value" style="font-size:24px;">{tonality}</div>
                <div class="metric-sub">flatness {features['spectral_flatness']:.3f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Side-by-side: 32-Band Visualizer + Spectrogram Heatmap
    spec_left, spec_right = st.columns([1.1, 1.4])

    with spec_left:
        # Build 32-band CSS Equalizer Visualizer with Peak Hold Dots
        bands = features["band_energies"]
        bars_html = []
        for i, val in enumerate(bands):
            # Dynamic multi-stop neon gradients based on frequency band
            if i < 6:
                bar_color = "linear-gradient(180deg, #ff7070, #ff9f43)"
                dot_color = "#ff7070"
            elif i < 14:
                bar_color = "linear-gradient(180deg, #feca57, #ff9f43)"
                dot_color = "#feca57"
            elif i < 22:
                bar_color = "linear-gradient(180deg, #1dd1a1, #7cf0b2)"
                dot_color = "#1dd1a1"
            elif i < 28:
                bar_color = "linear-gradient(180deg, #00d2d3, #73d9e8)"
                dot_color = "#00d2d3"
            else:
                bar_color = "linear-gradient(180deg, #82b1ff, #a55eea)"
                dot_color = "#82b1ff"

            peak_pos = min(98.0, val + 6.0)
            bar_elem = (
                f'<div style="flex:1;display:flex;flex-direction:column;align-items:center;height:100%;justify-content:flex-end;position:relative;">'
                f'<div style="position:absolute;bottom:{peak_pos:.1f}%;width:100%;max-width:8px;height:2px;background:{dot_color};border-radius:1px;box-shadow:0 0 6px {dot_color};"></div>'
                f'<div style="width:100%;max-width:8px;height:{val:.1f}%;background:{bar_color};border-radius:3px 3px 0 0;box-shadow:0 0 10px {dot_color}44;transition:height 0.3s ease;"></div>'
                f'</div>'
            )
            bars_html.append(bar_elem)

        joined_bars = "".join(bars_html)

        st.markdown(
            f"""
            <div class="panel" style="padding:18px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                    <div class="panel-title" style="margin-bottom:0;">32-Band Octave Equalizer</div>
                    <span class="live-pill" style="padding:4px 10px;font-size:10px;"><span class="dot"></span>{active_label.upper()}</span>
                </div>
                <div style="height:155px;display:flex;gap:3px;align-items:flex-end;padding:12px 8px;background:rgba(6,10,12,0.92);border:1px solid var(--line);border-radius:14px;margin-bottom:10px;box-shadow:inset 0 2px 8px rgba(0,0,0,0.6);">
                    {joined_bars}
                </div>
                <div style="display:flex;justify-content:space-between;color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:9px;padding:0 6px;font-weight:600;">
                    <span style="color:#ff7070">20Hz Sub</span>
                    <span style="color:#feca57">250Hz Bass</span>
                    <span style="color:#1dd1a1">1kHz Mid</span>
                    <span style="color:#00d2d3">4kHz High</span>
                    <span style="color:#82b1ff">8kHz Air</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with spec_right:
        # Render Interactive Plotly Spectrogram Heatmap
        fig = create_spectrogram_figure(
            audio_sig,
            sr=sr,
            title=f"Log-Mel Spectrogram [{active_label}]",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
