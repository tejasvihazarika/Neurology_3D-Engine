"""
LORETA-Based EEG Source Localization Pipeline
==============================================
Reads cleaned EEG data, applies FFT-based frequency band extraction,
performs simplified LORETA source localization, maps activity to brain
regions, classifies cognitive states, and outputs results as JSON
for the frontend visualization.
"""

import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
import json
import os

# ────────────────── CONSTANTS ────────────────── #

SAMPLING_RATE = 32  # Hz (downsampled data)

# EEG Frequency Bands (Hz)
FREQ_BANDS = {
    "Delta": (0.5, 4),
    "Theta": (4, 8),
    "Alpha": (8, 13),
    "Beta":  (13, 30),
    "Gamma": (30, 45)
}

# 10-20 System channel → brain region mapping
CHANNEL_REGION_MAP = {
    # Frontal
    "FP1": "Frontal", "FP2": "Frontal", "FPZ": "Frontal",
    "AF1": "Frontal", "AF2": "Frontal", "AF7": "Frontal", "AF8": "Frontal",
    "AFZ": "Frontal",
    "F1": "Frontal", "F2": "Frontal", "F3": "Frontal", "F4": "Frontal",
    "F5": "Frontal", "F6": "Frontal", "F7": "Frontal", "F8": "Frontal",
    "FZ": "Frontal",
    "FC1": "Frontal", "FC2": "Frontal", "FC3": "Frontal", "FC4": "Frontal",
    "FC5": "Frontal", "FC6": "Frontal", "FCZ": "Frontal",
    "FT7": "Temporal", "FT8": "Temporal",

    # Central (map to Parietal for lobe-level)
    "C1": "Parietal", "C2": "Parietal", "C3": "Parietal", "C4": "Parietal",
    "C5": "Parietal", "C6": "Parietal", "CZ": "Parietal",
    "CP1": "Parietal", "CP2": "Parietal", "CP3": "Parietal", "CP4": "Parietal",
    "CP5": "Parietal", "CP6": "Parietal", "CPZ": "Parietal",

    # Temporal
    "T7": "Temporal", "T8": "Temporal",
    "TP7": "Temporal", "TP8": "Temporal",

    # Parietal
    "P1": "Parietal", "P2": "Parietal", "P3": "Parietal", "P4": "Parietal",
    "P5": "Parietal", "P6": "Parietal", "P7": "Parietal", "P8": "Parietal",
    "PZ": "Parietal",
    "PO1": "Occipital", "PO2": "Occipital", "PO7": "Occipital", "PO8": "Occipital",
    "POZ": "Occipital",

    # Occipital
    "O1": "Occipital", "O2": "Occipital", "OZ": "Occipital",
}

# Activity classification rules
ACTIVITY_RULES = [
    {"band": "Beta",  "region": "Frontal",   "label": "Focused / Attentive",       "description": "High beta activity in frontal regions indicates focused attention and active decision-making."},
    {"band": "Alpha", "region": "Occipital",  "label": "Relaxed / Visual Rest",     "description": "Dominant alpha waves in the occipital lobe suggest a relaxed state with eyes closed or minimal visual processing."},
    {"band": "Theta", "region": "Temporal",   "label": "Drowsy / Memory Processing","description": "Elevated theta in temporal regions indicates drowsiness or memory consolidation processes."},
    {"band": "Gamma", "region": "Frontal",    "label": "High Cognitive Load",       "description": "Gamma activity in frontal areas indicates complex cognitive processing and high mental effort."},
    {"band": "Delta", "region": "Frontal",    "label": "Deep Sleep / Unconscious",  "description": "Strong delta waves in frontal regions are characteristic of deep sleep or unconscious states."},
    {"band": "Alpha", "region": "Parietal",   "label": "Sensory Integration",       "description": "Alpha activity in parietal areas suggests sensory integration and spatial awareness in a calm state."},
    {"band": "Theta", "region": "Frontal",    "label": "Meditative State",          "description": "Frontal theta activity is associated with meditation, creativity, and internal focus."},
    {"band": "Beta",  "region": "Parietal",   "label": "Active Sensory Processing", "description": "Beta waves in parietal regions indicate active sensory processing and motor planning."},
]


def compute_band_power(signal, fs, band):
    """Compute power in a specific frequency band using FFT."""
    N = len(signal)
    yf = fft(signal)
    xf = fftfreq(N, 1.0 / fs)

    # Only positive frequencies
    pos_mask = xf >= 0
    xf_pos = xf[pos_mask]
    yf_pos = np.abs(yf[pos_mask]) ** 2

    # Band mask
    band_mask = (xf_pos >= band[0]) & (xf_pos <= band[1])
    power = np.mean(yf_pos[band_mask]) if np.any(band_mask) else 0.0

    return float(power)


def run_pipeline():
    """Main LORETA pipeline."""
    csv_path = os.path.join("processed_data", "clean_eeg_32hz.csv")

    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found. Run clean_data.py first.")
        return

    print("Loading cleaned EEG data...")
    df = pd.read_csv(csv_path, index_col=0)

    # Remove non-EEG columns (X, Y, nd are reference/noise columns)
    drop_cols = [c for c in ["X", "Y", "nd"] if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")

    channels = [c for c in df.columns if c in CHANNEL_REGION_MAP]
    print(f"Processing {len(channels)} EEG channels...")

    # ─── Step 1: Compute band power per channel ─── #
    print("Step 1: Computing frequency band powers per channel...")
    channel_band_power = {}

    for ch in channels:
        signal = df[ch].dropna().values
        if len(signal) < 10:
            continue
        channel_band_power[ch] = {}
        for band_name, band_range in FREQ_BANDS.items():
            power = compute_band_power(signal, SAMPLING_RATE, band_range)
            channel_band_power[ch][band_name] = power

    # ─── Step 2: LORETA - Aggregate to brain regions ─── #
    print("Step 2: LORETA source localization (region aggregation)...")
    regions = ["Frontal", "Parietal", "Temporal", "Occipital"]
    region_band_power = {r: {b: [] for b in FREQ_BANDS} for r in regions}

    for ch, bands in channel_band_power.items():
        region = CHANNEL_REGION_MAP.get(ch)
        if region:
            for band_name, power in bands.items():
                region_band_power[region][band_name].append(power)

    # Average across channels per region
    region_activity = {}
    for region in regions:
        region_activity[region] = {}
        for band_name in FREQ_BANDS:
            vals = region_band_power[region][band_name]
            region_activity[region][band_name] = float(np.mean(vals)) if vals else 0.0

    # ─── Step 3: Compute total activity per region ─── #
    print("Step 3: Computing region-level total activity...")
    region_totals = {}
    for region in regions:
        region_totals[region] = sum(region_activity[region].values())

    total_all = sum(region_totals.values())
    region_percentages = {r: round((v / total_all) * 100, 1) if total_all > 0 else 0
                          for r, v in region_totals.items()}

    dominant_region = max(region_totals, key=region_totals.get)

    # ─── Step 4: Determine dominant frequency band ─── #
    print("Step 4: Identifying dominant frequency band...")
    overall_band_power = {}
    for band_name in FREQ_BANDS:
        vals = []
        for region in regions:
            vals.append(region_activity[region][band_name])
        overall_band_power[band_name] = float(np.mean(vals))

    dominant_band = max(overall_band_power, key=overall_band_power.get)

    # Normalize band powers for display
    max_band_power = max(overall_band_power.values()) if overall_band_power else 1
    band_distribution = {b: round((v / max_band_power) * 100, 1) for b, v in overall_band_power.items()}

    # ─── Step 5: Activity classification ─── #
    print("Step 5: Classifying cognitive activity...")
    classification = None
    confidence = 0

    for rule in ACTIVITY_RULES:
        if rule["band"] == dominant_band and rule["region"] == dominant_region:
            classification = rule
            confidence = 92
            break

    # Fallback: closest match
    if classification is None:
        for rule in ACTIVITY_RULES:
            if rule["band"] == dominant_band:
                classification = rule
                confidence = 75
                break

    if classification is None:
        for rule in ACTIVITY_RULES:
            if rule["region"] == dominant_region:
                classification = rule
                confidence = 60
                break

    if classification is None:
        classification = ACTIVITY_RULES[0]
        confidence = 40

    # ─── Step 6: Compute time-series segment analysis ─── #
    print("Step 6: Computing time-segment analysis for comparison mode...")
    total_samples = len(df)
    mid = total_samples // 2
    segments = {
        "first_half": df.iloc[:mid],
        "second_half": df.iloc[mid:]
    }

    segment_results = {}
    for seg_name, seg_df in segments.items():
        seg_region_power = {r: 0.0 for r in regions}
        for ch in channels:
            signal = seg_df[ch].dropna().values
            if len(signal) < 10:
                continue
            region = CHANNEL_REGION_MAP.get(ch)
            if region:
                total_power = 0
                for band_name, band_range in FREQ_BANDS.items():
                    total_power += compute_band_power(signal, SAMPLING_RATE, band_range)
                seg_region_power[region] += total_power

        seg_total = sum(seg_region_power.values())
        segment_results[seg_name] = {
            r: round((v / seg_total) * 100, 1) if seg_total > 0 else 0
            for r, v in seg_region_power.items()
        }
        segment_results[seg_name]["dominant"] = max(seg_region_power, key=seg_region_power.get)

    # ─── Step 7: Per-channel FFT spectrum for the processing page ─── #
    print("Step 7: Computing FFT spectrum for display...")
    fft_display = {}
    sample_channels = ["FP1", "FP2", "O1", "C3"]
    for ch in sample_channels:
        if ch in df.columns:
            signal = df[ch].dropna().values
            N = len(signal)
            yf = fft(signal)
            xf = fftfreq(N, 1.0 / SAMPLING_RATE)[:N // 2]
            magnitude = (2.0 / N * np.abs(yf[:N // 2])).tolist()
            fft_display[ch] = {
                "frequencies": xf.tolist(),
                "magnitude": magnitude
            }

    # ─── Step 8: Build activity intensity map for 3D brain ─── #
    print("Step 8: Building 3D brain activity map...")

    # Normalize region activity to 0-1 range for color mapping
    max_total = max(region_totals.values()) if region_totals else 1
    region_intensity = {r: round(v / max_total, 3) for r, v in region_totals.items()}

    # ─── Step 9: Global statistics ─── #
    print("Step 9: Computing global statistics...")
    all_values = df[channels].values.flatten()
    all_values = all_values[~np.isnan(all_values)]

    global_stats = {
        "mean_signal": round(float(np.mean(all_values)), 2),
        "variance": round(float(np.var(all_values)), 2),
        "max_amplitude": round(float(np.max(all_values)), 2),
        "min_amplitude": round(float(np.min(all_values)), 2),
        "total_channels": len(channels),
        "total_samples": total_samples,
        "sampling_rate": SAMPLING_RATE,
        "duration_seconds": round(total_samples / SAMPLING_RATE, 1)
    }

    # ─── Assemble final output ─── #
    output = {
        "pipeline_status": {
            "raw_eeg": "complete",
            "fft": "complete",
            "frequency_bands": "complete",
            "loreta": "complete",
            "classification": "complete"
        },
        "global_stats": global_stats,
        "frequency_bands": {
            "distribution": band_distribution,
            "dominant": dominant_band,
            "raw_power": {b: round(v, 2) for b, v in overall_band_power.items()}
        },
        "loreta_results": {
            "region_activity": {r: {b: round(v, 2) for b, v in bands.items()}
                                for r, bands in region_activity.items()},
            "region_totals": {r: round(v, 2) for r, v in region_totals.items()},
            "region_percentages": region_percentages,
            "region_intensity": region_intensity,
            "dominant_region": dominant_region
        },
        "classification": {
            "label": classification["label"],
            "description": classification["description"],
            "dominant_region": dominant_region,
            "dominant_band": dominant_band,
            "confidence": confidence
        },
        "comparison": segment_results,
        "fft_spectrum": fft_display
    }

    # ─── Save JSON ─── #
    out_path = os.path.join("frontend", "loreta_results.json")
    os.makedirs("frontend", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[OK] LORETA pipeline complete!")
    print(f"   Dominant Region: {dominant_region}")
    print(f"   Dominant Band:   {dominant_band}")
    print(f"   Classification:  {classification['label']} ({confidence}% confidence)")
    print(f"   Output saved to: {out_path}")


if __name__ == "__main__":
    run_pipeline()
