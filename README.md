# NeuroAI EEG Benchmarking Engine

A unified EEG signal processing and machine learning benchmarking pipeline. Processes raw brain signals, extracts features using LORETA source localization, trains ML classifiers, and visualizes everything in an interactive web dashboard.

**Inspired by** [Meta FAIR's NeuralBench](https://github.com/facebookresearch/neuroai/tree/main/neuralbench-repo) framework.

## What This Does

```
Raw EEG Data → Clean → FFT → Feature Extraction → ML Training → Benchmark Results
                                                                        ↓
                                            Interactive Dashboard (3D Brain, Charts, AI Results)
```

1. **EEG Processing** — Cleans raw EEG recordings (64 channels, 256 Hz)
2. **LORETA Pipeline** — Computes frequency band powers and maps to brain regions
3. **NeuroAI Benchmark** — Trains MLP, SVM, and Random Forest classifiers on 4 different feature sets
4. **Web Dashboard** — Displays everything: brain activity charts, 3D brain model, and ML benchmark results

## Quick Start

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run the Pipeline
```bash
# Step 1: Clean raw EEG data (if starting from raw .tar.gz archives)
python clean_data.py

# Step 2: Run LORETA analysis (generates loreta_results.json for the dashboard)
python loreta_pipeline.py

# Step 3: Run NeuroAI benchmark (trains ML models, generates benchmark_results.json)
python neuroai_benchmark.py

# Step 4: Open the dashboard
cd frontend
python -m http.server 8080
# Open http://localhost:8080 in your browser
```

## Project Structure

```
├── clean_data.py              # Step 1: Raw EEG data cleaning
├── loreta_pipeline.py         # Step 2: LORETA source localization & analysis
├── neuroai_benchmark.py       # Step 3: ML benchmark pipeline (NEW)
├── app.py                     # Streamlit alternative interface
├── requirements.txt           # Python dependencies
│
├── processed_data/            # Cleaned EEG CSV files
│   ├── clean_eeg.csv
│   └── clean_eeg_32hz.csv
│
└── frontend/                  # Interactive web dashboard
    ├── index.html             # Main page (10 views including AI Benchmark)
    ├── app.js                 # Chart rendering & data loading
    ├── styles.css             # Styling
    ├── loreta_results.json    # LORETA pipeline output
    └── benchmark_results.json # ML benchmark output (generated)
```

## NeuroAI Benchmark Details

The benchmark runs **4 experiments** with **3 ML models** each:

### Feature Sets
| Experiment | Features | Description |
|---|---|---|
| Raw EEG | Mean, Std, Range, MAD per channel | Basic statistical features |
| Frequency Bands | Delta/Theta/Alpha/Beta/Gamma power | FFT-based band power per channel |
| LORETA Source | Region-aggregated band powers | Frontal, Parietal, Temporal, Occipital |
| Combined | Band + LORETA features merged | Maximum information |

### Models
- **MLP** — Multi-Layer Perceptron (neural network)
- **SVM** — Support Vector Machine (kernel-based)
- **RandomForest** — Ensemble of decision trees

### Classification Task
Classifies which **brain region** (Frontal, Parietal, Temporal, Occipital) is most active in each time window.

## Dashboard Views

| View | Description |
|---|---|
| Home | Recording overview & brain region activity |
| Information | Dataset details & signal statistics |
| Signal Steps | FFT, band distribution, region mapping |
| 3D Brain | Interactive Three.js brain model |
| Results | Analysis findings & region comparison |
| Charts | Band power & region activity charts |
| Comparison | First half vs second half temporal comparison |
| **AI Benchmark** | **ML model performance, confusion matrix, experiment comparison** |
| Summary | Plain-English findings report |
| Glossary | Scientific term definitions |

## Tech Stack
- **Python**: NumPy, Pandas, SciPy, scikit-learn
- **Frontend**: HTML/CSS/JS, Plotly.js, Three.js
- **No GPU required** — runs on any laptop

## Credits
- EEG dataset: [UCI ML Repository](https://archive.ics.uci.edu/ml/datasets/EEG+Database)
- Framework concept: [Meta FAIR NeuralBench](https://github.com/facebookresearch/neuroai)
