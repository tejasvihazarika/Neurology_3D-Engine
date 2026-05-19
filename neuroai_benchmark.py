"""
NeuroAI Benchmark Pipeline
===========================
Inspired by Meta FAIR's NeuralBench framework.
Takes EEG features from the LORETA pipeline and runs:
  1. Feature extraction (band powers, region activity, combined)
  2. Dataset preparation (train/test split)
  3. Model training (MLP, SVM, Random Forest)
  4. Evaluation (accuracy, precision, recall, F1, confusion matrix)
  5. Experiment comparison (which feature set works best)

Outputs results as JSON for the frontend dashboard.
"""

import pandas as pd
import numpy as np
from scipy.fft import fft, fftfreq
import json
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.neural_network import MLPClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report
)

# ────────────────── CONSTANTS ────────────────── #

SAMPLING_RATE = 32  # Hz (matches clean_data.py output)

FREQ_BANDS = {
    "Delta": (0.5, 4),
    "Theta": (4, 8),
    "Alpha": (8, 13),
    "Beta":  (13, 30),
    "Gamma": (30, 45)
}

CHANNEL_REGION_MAP = {
    "FP1": "Frontal", "FP2": "Frontal", "FPZ": "Frontal",
    "AF1": "Frontal", "AF2": "Frontal", "AF7": "Frontal", "AF8": "Frontal",
    "AFZ": "Frontal",
    "F1": "Frontal", "F2": "Frontal", "F3": "Frontal", "F4": "Frontal",
    "F5": "Frontal", "F6": "Frontal", "F7": "Frontal", "F8": "Frontal",
    "FZ": "Frontal",
    "FC1": "Frontal", "FC2": "Frontal", "FC3": "Frontal", "FC4": "Frontal",
    "FC5": "Frontal", "FC6": "Frontal", "FCZ": "Frontal",
    "FT7": "Temporal", "FT8": "Temporal",
    "C1": "Parietal", "C2": "Parietal", "C3": "Parietal", "C4": "Parietal",
    "C5": "Parietal", "C6": "Parietal", "CZ": "Parietal",
    "CP1": "Parietal", "CP2": "Parietal", "CP3": "Parietal", "CP4": "Parietal",
    "CP5": "Parietal", "CP6": "Parietal", "CPZ": "Parietal",
    "T7": "Temporal", "T8": "Temporal",
    "TP7": "Temporal", "TP8": "Temporal",
    "P1": "Parietal", "P2": "Parietal", "P3": "Parietal", "P4": "Parietal",
    "P5": "Parietal", "P6": "Parietal", "P7": "Parietal", "P8": "Parietal",
    "PZ": "Parietal",
    "PO1": "Occipital", "PO2": "Occipital", "PO7": "Occipital", "PO8": "Occipital",
    "POZ": "Occipital",
    "O1": "Occipital", "O2": "Occipital", "OZ": "Occipital",
}

# Cognitive state labels based on dominant frequency band
BAND_LABELS = {
    "Delta": "Deep Sleep",
    "Theta": "Drowsy / Memory",
    "Alpha": "Relaxed",
    "Beta":  "Focused",
    "Gamma": "High Cognitive Load"
}


# ────────────────── FEATURE EXTRACTION ────────────────── #

def compute_band_power(signal, fs, band):
    """Compute power in a specific frequency band using FFT."""
    N = len(signal)
    if N < 4:
        return 0.0
    yf = fft(signal)
    xf = fftfreq(N, 1.0 / fs)
    pos_mask = xf >= 0
    xf_pos = xf[pos_mask]
    yf_pos = np.abs(yf[pos_mask]) ** 2
    band_mask = (xf_pos >= band[0]) & (xf_pos <= band[1])
    return float(np.mean(yf_pos[band_mask])) if np.any(band_mask) else 0.0


def extract_raw_features(segment, channels):
    """Extract raw statistical features from EEG segment."""
    features = []
    for ch in channels:
        signal = segment[ch].dropna().values
        if len(signal) < 4:
            features.extend([0, 0, 0, 0])
            continue
        features.extend([
            float(np.mean(signal)),
            float(np.std(signal)),
            float(np.max(signal) - np.min(signal)),
            float(np.median(np.abs(signal - np.median(signal))))
        ])
    return features


def extract_band_features(segment, channels):
    """Extract frequency band power features from EEG segment."""
    features = []
    for ch in channels:
        signal = segment[ch].dropna().values
        for band_name, band_range in FREQ_BANDS.items():
            features.append(compute_band_power(signal, SAMPLING_RATE, band_range))
    return features


def extract_loreta_features(segment, channels):
    """Extract LORETA-style region-aggregated features."""
    regions = ["Frontal", "Parietal", "Temporal", "Occipital"]
    region_band_power = {r: {b: [] for b in FREQ_BANDS} for r in regions}

    for ch in channels:
        signal = segment[ch].dropna().values
        region = CHANNEL_REGION_MAP.get(ch)
        if region and len(signal) >= 4:
            for band_name, band_range in FREQ_BANDS.items():
                power = compute_band_power(signal, SAMPLING_RATE, band_range)
                region_band_power[region][band_name].append(power)

    features = []
    for region in regions:
        for band_name in FREQ_BANDS:
            vals = region_band_power[region][band_name]
            features.append(float(np.mean(vals)) if vals else 0.0)
    return features


def extract_combined_features(segment, channels):
    """Combine band + LORETA features for maximum information."""
    return extract_band_features(segment, channels) + extract_loreta_features(segment, channels)


def get_dominant_region(segment, channels):
    """Determine the most active brain region for labeling."""
    regions = {"Frontal": 0.0, "Parietal": 0.0, "Temporal": 0.0, "Occipital": 0.0}
    region_counts = {"Frontal": 0, "Parietal": 0, "Temporal": 0, "Occipital": 0}

    for ch in channels:
        signal = segment[ch].dropna().values
        region = CHANNEL_REGION_MAP.get(ch)
        if region and len(signal) >= 4:
            # Use total signal power as activity measure
            power = float(np.sum(np.abs(signal) ** 2)) / len(signal)
            regions[region] += power
            region_counts[region] += 1

    # Normalize by channel count
    for r in regions:
        if region_counts[r] > 0:
            regions[r] /= region_counts[r]

    return max(regions, key=regions.get)


def get_activity_level(segment, channels):
    """Classify EEG segment into activity levels based on amplitude."""
    total_power = 0.0
    count = 0
    for ch in channels:
        signal = segment[ch].dropna().values
        if len(signal) >= 4:
            total_power += float(np.std(signal))
            count += 1
    avg_power = total_power / count if count > 0 else 0

    # Quantize into activity levels
    if avg_power < 3:
        return "Low Activity"
    elif avg_power < 6:
        return "Moderate Activity"
    elif avg_power < 10:
        return "High Activity"
    else:
        return "Very High Activity"


# ────────────────── DATASET BUILDER ────────────────── #

def build_dataset(df, channels, extractor_fn, window_size=4, step=2, label_fn="region"):
    """
    Build a dataset by sliding a window over the EEG data.
    Each window becomes one sample with features + label.

    Args:
        df: DataFrame with EEG channels
        channels: List of channel names to use
        extractor_fn: Function to extract features from a segment
        window_size: Number of samples per window
        step: Step size for sliding window
        label_fn: Labeling strategy - "region" or "activity"
    """
    X = []
    y = []
    total_samples = len(df)

    for start in range(0, total_samples - window_size + 1, step):
        segment = df.iloc[start:start + window_size]
        features = extractor_fn(segment, channels)

        if label_fn == "activity":
            label = get_activity_level(segment, channels)
        else:
            label = get_dominant_region(segment, channels)

        if not any(np.isnan(features)) and not any(np.isinf(features)):
            X.append(features)
            y.append(label)

    return np.array(X), np.array(y)


# ────────────────── MODEL TRAINING ────────────────── #

def train_and_evaluate(X, y, model_name="MLP"):
    """
    Train a model using cross-validation and return metrics.

    Returns dict with accuracy, precision, recall, f1, confusion_matrix.
    """
    if len(np.unique(y)) < 2:
        return {
            "accuracy": 0, "precision": 0, "recall": 0, "f1": 0,
            "confusion_matrix": [], "classes": [],
            "error": "Not enough class diversity in data"
        }

    # Encode labels
    le = LabelEncoder()
    y_encoded = le.fit_transform(y)
    classes = le.classes_.tolist()

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Pick model
    if model_name == "MLP":
        model = MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=500, random_state=42,
            early_stopping=False
        )
    elif model_name == "SVM":
        model = SVC(kernel='rbf', random_state=42)
    elif model_name == "RandomForest":
        model = RandomForestClassifier(
            n_estimators=50, max_depth=10, random_state=42
        )
    else:
        model = MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=300, random_state=42)

    # Cross-validation
    min_class_count = min(np.bincount(y_encoded))
    if min_class_count < 2:
        # Too few samples for cross-validation, do simple train/test
        model.fit(X_scaled, y_encoded)
        y_pred = model.predict(X_scaled)
        acc = accuracy_score(y_encoded, y_pred)
        cm = confusion_matrix(y_encoded, y_pred)
        return {
            "accuracy": round(float(acc) * 100, 1),
            "precision": round(float(acc) * 100, 1),
            "recall": round(float(acc) * 100, 1),
            "f1": round(float(acc) * 100, 1),
            "confusion_matrix": cm.tolist(),
            "classes": classes,
            "num_samples": len(X),
            "num_features": X.shape[1],
            "num_classes": len(classes),
            "note": "Train-only evaluation (too few samples per class for CV)"
        }

    n_splits = min(5, min_class_count)
    n_splits = max(2, n_splits)

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    scoring = ['accuracy', 'precision_weighted', 'recall_weighted', 'f1_weighted']
    try:
        cv_results = cross_validate(model, X_scaled, y_encoded, cv=cv,
                                    scoring=scoring, return_train_score=False)
    except Exception as e:
        # Fallback: simple fit
        model.fit(X_scaled, y_encoded)
        y_pred = model.predict(X_scaled)
        acc = accuracy_score(y_encoded, y_pred)
        cm = confusion_matrix(y_encoded, y_pred)
        return {
            "accuracy": round(float(acc) * 100, 1),
            "precision": round(float(acc) * 100, 1),
            "recall": round(float(acc) * 100, 1),
            "f1": round(float(acc) * 100, 1),
            "confusion_matrix": cm.tolist(),
            "classes": classes,
            "num_samples": len(X),
            "num_features": X.shape[1],
            "num_classes": len(classes),
            "note": f"Fallback evaluation: {str(e)}"
        }

    # Final fit for confusion matrix
    model.fit(X_scaled, y_encoded)
    y_pred = model.predict(X_scaled)
    cm = confusion_matrix(y_encoded, y_pred)

    return {
        "accuracy": round(float(np.mean(cv_results['test_accuracy'])) * 100, 1),
        "precision": round(float(np.mean(cv_results['test_precision_weighted'])) * 100, 1),
        "recall": round(float(np.mean(cv_results['test_recall_weighted'])) * 100, 1),
        "f1": round(float(np.mean(cv_results['test_f1_weighted'])) * 100, 1),
        "confusion_matrix": cm.tolist(),
        "classes": classes,
        "num_samples": len(X),
        "num_features": X.shape[1],
        "num_classes": len(classes)
    }


# ────────────────── MAIN BENCHMARK ────────────────── #

def run_benchmark():
    """Run the full NeuroAI benchmark pipeline."""

    csv_path = os.path.join("processed_data", "clean_eeg.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join("processed_data", "clean_eeg_32hz.csv")
    if not os.path.exists(csv_path):
        print("Error: No processed EEG data found. Run clean_data.py first.")
        return

    print("=" * 60)
    print("  NeuroAI Benchmark Pipeline")
    print("  Inspired by Meta FAIR NeuralBench")
    print("=" * 60)

    # Load data
    print("\n[1/6] Loading EEG data...")
    df = pd.read_csv(csv_path, index_col=0)
    drop_cols = [c for c in ["X", "Y", "nd"] if c in df.columns]
    df = df.drop(columns=drop_cols, errors="ignore")
    channels = [c for c in df.columns if c in CHANNEL_REGION_MAP]
    print(f"       {len(channels)} channels, {len(df)} samples")

    # ── Experiment 1: Raw EEG Features ──
    print("\n[2/6] Experiment 1: Raw EEG Features...")
    X_raw, y_raw = build_dataset(df, channels, extract_raw_features, window_size=4, step=2)
    print(f"       Dataset: {X_raw.shape[0]} samples, {X_raw.shape[1]} features")

    raw_results = {}
    for model_name in ["MLP", "SVM", "RandomForest"]:
        print(f"       Training {model_name}...")
        raw_results[model_name] = train_and_evaluate(X_raw, y_raw, model_name)
        print(f"       -> Accuracy: {raw_results[model_name]['accuracy']}%")

    # ── Experiment 2: Frequency Band Features ──
    print("\n[3/6] Experiment 2: Frequency Band Features...")
    X_band, y_band = build_dataset(df, channels, extract_band_features, window_size=4, step=2)
    print(f"       Dataset: {X_band.shape[0]} samples, {X_band.shape[1]} features")

    band_results = {}
    for model_name in ["MLP", "SVM", "RandomForest"]:
        print(f"       Training {model_name}...")
        band_results[model_name] = train_and_evaluate(X_band, y_band, model_name)
        print(f"       -> Accuracy: {band_results[model_name]['accuracy']}%")

    # ── Experiment 3: LORETA Features ──
    print("\n[4/6] Experiment 3: LORETA Source Features...")
    X_loreta, y_loreta = build_dataset(df, channels, extract_loreta_features, window_size=4, step=2)
    print(f"       Dataset: {X_loreta.shape[0]} samples, {X_loreta.shape[1]} features")

    loreta_results = {}
    for model_name in ["MLP", "SVM", "RandomForest"]:
        print(f"       Training {model_name}...")
        loreta_results[model_name] = train_and_evaluate(X_loreta, y_loreta, model_name)
        print(f"       -> Accuracy: {loreta_results[model_name]['accuracy']}%")

    # ── Experiment 4: Combined Features ──
    print("\n[5/6] Experiment 4: Combined Features (Band + LORETA)...")
    X_combined, y_combined = build_dataset(df, channels, extract_combined_features, window_size=4, step=2)
    print(f"       Dataset: {X_combined.shape[0]} samples, {X_combined.shape[1]} features")

    combined_results = {}
    for model_name in ["MLP", "SVM", "RandomForest"]:
        print(f"       Training {model_name}...")
        combined_results[model_name] = train_and_evaluate(X_combined, y_combined, model_name)
        print(f"       -> Accuracy: {combined_results[model_name]['accuracy']}%")

    # ── Build comparison summary ──
    print("\n[6/6] Building benchmark summary...")

    experiments = {
        "Raw EEG": raw_results,
        "Frequency Bands": band_results,
        "LORETA Source": loreta_results,
        "Combined": combined_results
    }

    # Find best overall
    best_acc = 0
    best_combo = ("", "")
    comparison = []
    for exp_name, models in experiments.items():
        for model_name, metrics in models.items():
            acc = metrics.get("accuracy", 0)
            comparison.append({
                "experiment": exp_name,
                "model": model_name,
                "accuracy": acc,
                "precision": metrics.get("precision", 0),
                "recall": metrics.get("recall", 0),
                "f1": metrics.get("f1", 0)
            })
            if acc > best_acc:
                best_acc = acc
                best_combo = (exp_name, model_name)

    # ── Assemble output ──
    output = {
        "benchmark_info": {
            "framework": "NeuroAI Benchmark (Inspired by Meta FAIR NeuralBench)",
            "total_channels": len(channels),
            "total_samples": len(df),
            "sampling_rate": SAMPLING_RATE,
            "window_size": 4,
            "step_size": 2,
            "models_tested": ["MLP", "SVM", "RandomForest"],
            "experiments_run": 4
        },
        "experiments": {
            "raw_eeg": {
                "name": "Raw EEG Features",
                "description": "Statistical features (mean, std, range, MAD) from raw EEG signals",
                "num_features": X_raw.shape[1],
                "num_samples": X_raw.shape[0],
                "results": raw_results
            },
            "frequency_bands": {
                "name": "Frequency Band Features",
                "description": "Power in Delta, Theta, Alpha, Beta, Gamma bands per channel",
                "num_features": X_band.shape[1],
                "num_samples": X_band.shape[0],
                "results": band_results
            },
            "loreta_source": {
                "name": "LORETA Source Features",
                "description": "Region-aggregated band powers (Frontal, Parietal, Temporal, Occipital)",
                "num_features": X_loreta.shape[1],
                "num_samples": X_loreta.shape[0],
                "results": loreta_results
            },
            "combined": {
                "name": "Combined Features",
                "description": "Frequency band + LORETA source features combined",
                "num_features": X_combined.shape[1],
                "num_samples": X_combined.shape[0],
                "results": combined_results
            }
        },
        "comparison": comparison,
        "best_result": {
            "experiment": best_combo[0],
            "model": best_combo[1],
            "accuracy": best_acc
        }
    }

    # Save
    out_path = os.path.join("frontend", "benchmark_results.json")
    os.makedirs("frontend", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  BENCHMARK COMPLETE")
    print(f"  Best: {best_combo[0]} + {best_combo[1]} -> {best_acc}% accuracy")
    print(f"  Results saved to: {out_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_benchmark()
