# Neurology 3D Visualization Engine – Project Overview

## 1. High‑level Workflow

1. **Raw EEG acquisition** – Sensors placed on the scalp capture voltage changes at **256 Hz**.
2. **Baseline correction** – Small DC drift is removed so the signal is centred around zero.
3. **FFT (Fast Fourier Transform)** – The time‑domain signal is transformed into the frequency domain.
4. **Frequency‑band aggregation** – Power is summed into the classic EEG bands (Delta, Theta, Alpha, Beta, Gamma).
5. **LORETA source localisation** – Using the band‑power map the algorithm estimates which cortical region generated the activity.
6. **Classification** – The dominant region & dominant band are mapped to a human‑readable brain‑state description.
7. **Visualization** – The results are displayed in:
   * a **light‑themed dashboard** with cards, bar charts and a comparison slider,
   * a **3‑D brain model** (glTF) coloured by region intensity, and
   * a **glossary** that explains every technical term for beginners.

## 2. Repository Layout

```
Neurology-3D-Viz-Engine-master/
│
├─ frontend/               # All client‑side files (HTML/CSS/JS)
│   ├─ index.html          # Main page, navigation and placeholders for the 8 views
│   ├─ styles.css          # Light theme, borders, layout utilities
│   ├─ app.js              # Core JavaScript: data loading, Plotly charts, Three.js brain
│   ├─ brain_model.glb     # Low‑poly 3‑D brain mesh (GLTF)
│   ├─ loreta_results.json # Processed result produced by loreta_pipeline.py
│   └─ … (additional assets: images, icons)
│
├─ loreta_pipeline.py      # Python pipeline that reads raw CSV, corrects baseline, runs FFT & LORETA
├─ clean_data.py           # Helper script used while preparing training data (not shipped)
├─ app.py                  # Simple Flask‑like wrapper used for local testing (optional)
├─ .gitignore              # Ignores large raw data folders, virtual‑env, .env etc.
└─ README.md               # Project description for GitHub
```

## 3. What Each Front‑end File Does

| File | Role | Key Features |
|------|------|--------------|
| **index.html** | Skeleton of the single‑page app. Contains a sidebar navigation (`nav-item`), a top bar, and eight hidden `view‑content` sections (Dashboard, 3D Brain, Charts, Comparison, Report, Glossary, etc.). | Uses semantic `<section>` elements, loads `app.js` at the bottom. |
| **styles.css** | Defines the **light‑theme design system** – colour tokens, typography, borders, cards, responsive grids, and the new blue `#93C5FD` boundary you asked for. | Uses CSS custom properties (`--primary‑blue`, `--border‑color`), adds `2px` solid blue borders to cards, sidebar, top‑bar. |
| **app.js** | JavaScript "engine" that:
- fetches `loreta_results.json`
- populates all cards & charts via Plotly
- builds the comparison slider
- creates the 3‑D brain with Three.js, applies a **normalised blue → purple → red gradient**, makes the material glossy (`metalness:0.3, roughness:0.25`).
- disables Plotly zoom (`fixedrange:true`). | Centralises all UI logic, keeps the code modular with helper functions (`renderDashboard()`, `render2DViz()`, `initBrain3D()`). |
| **brain_model.glb** | Low‑poly representation of the human brain. Loaded with `GLTFLoader`. | Vertices are coloured per‑vertex based on region intensity. |
| **loreta_results.json** | The final output of the Python pipeline. Holds:
- global statistics (sampling rate, duration, etc.)
- frequency‑band distribution
- region percentages & intensities
- classification (label, description, confidence)
- comparison between first/second half of the recording |
| **loreta_pipeline.py** | Pure‑Python processing script (run locally). Steps: load raw CSV → baseline correction → FFT → band‑power → LORETA → write JSON. | Uses `numpy`, `scipy`, and the publicly‑available LORETA algorithm. |
| **clean_data.py** | Utility for trimming huge raw EEG folders (not needed for the web demo). | Ignored by `.gitignore`. |
| **app.py** | Tiny convenience script that can `python -m http.server 8080` from the `frontend/` folder. | Not part of the production build – just for quick local testing. |

## 4. How the Project Works – End‑to‑End

1. **Start the server** (e.g. `python -m http.server 8080` from `frontend/`).
2. Browser loads `index.html`. The sidebar navigation automatically marks the first view (**Dashboard**) as active.
3. `app.js` immediately fetches `loreta_results.json`. All UI components are populated:
   - **Dashboard cards** show sensor count, sampling rate, duration, classification, dominant band, etc.
   - **Bar charts** (region activity, band distribution) are drawn with Plotly – zoom disabled for a clean experience.
   - **3‑D brain** is built with Three.js. Each vertex colour is computed from the **normalised intensity** of its region, using the blue‑purple‑red gradient. A glossy material gives a premium look.
   - **Comparison slider** lets the user slide between `first_half` and `second_half` activity, updating a detail card.
   - **Glossary** explains every term (EEG, FFT, LORETA, etc.) in beginner‑friendly language.
4. Users may rotate, pan and zoom the 3‑D brain with the mouse (OrbitControls). The left‑click‑drag‑zoom is disabled – only rotation & pan remain (as requested).
5. All charts are static (no streaming). Changing the underlying `loreta_results.json` and reloading the page will instantly update the whole UI.

## 5. Project Outcome

- **Visual output**: an interactive, student‑friendly web dashboard that shows *where* in the brain activity is happening and *what* the brain is likely doing (e.g., “Drowsy / Memory Processing”).
- **Educational value**: the glossary and the simplified language let beginners understand EEG concepts without digging into research papers.
- **Deployable**: the whole front‑end lives in the `frontend/` folder and can be published on GitHub Pages (`gh‑pages` branch). No backend server is required beyond serving static files.

## 6. Terminology & Why It Is Used

| Term | Meaning in this Project | Reason for Inclusion |
|------|------------------------|----------------------|
| **EEG (Electroencephalogram)** | Voltage measured on the scalp using 64 sensors. | Provides the raw brain‑wave data that fuels the whole analysis. |
| **Baseline correction** | Subtracts the mean (or a low‑order polynomial) from the raw signal. | Removes slow drift caused by electrode‑skin impedance, giving cleaner FFT results. |
| **FFT (Fast Fourier Transform)** | Converts the time‑domain EEG into frequency‑domain power spectra. | Allows us to separate activity into the standard brain‑wave bands. |
| **Frequency band** | Delta (0.5‑4 Hz), Theta (4‑8 Hz), Alpha (8‑13 Hz), Beta (13‑30 Hz), Gamma (30‑45 Hz). | Different bands are associated with distinct cognitive states; the dominant band drives the classification label. |
| **LORETA (Low‑Resolution Electromagnetic Tomography)** | Inverse‑modelling algorithm that estimates the *source* of EEG activity inside the brain volume. | Gives a spatial map (region percentages) that we can visualise on the 3‑D brain. |
| **Region percentages / intensity** | Percentage of total power contributed by Frontal, Parietal, Temporal, Occipital lobes; intensity is a normalised scalar (0‑1). | Drives the colour of each brain lobe, letting users instantly see which area is most active. |
| **Classification** | Human‑readable label (e.g., *Drowsy / Memory Processing*) together with a confidence score. | Summarises the entire pipeline into a simple phrase a beginner can understand. |
| **Plotly** | JavaScript charting library used for all 2‑D visualisations (bar charts, pie charts, etc.). | Provides interactive, responsive charts with minimal code and excellent aesthetics. |
| **Three.js** | WebGL‑based 3‑D engine for rendering the brain mesh. | Enables a real‑time, rotatable 3‑D brain that reacts to the data. |
| **Glossary** | A dedicated page that defines every technical term in plain English. | Bridges the gap between a professional research tool and a learning platform. |
| **GitHub Pages (`gh‑pages` branch)** | Static hosting service that serves the `frontend/` folder as a live website. | Gives you a zero‑cost, always‑on URL (`https://<user>.github.io/Neurology_3D-Engine/`). |

## 7. Detailed Step‑by‑Step Walkthrough (for a New Contributor)

1. **Clone the repo**
   ```bash
   git clone https://github.com/tejasvihazarika/Neurology_3D-Engine.git
   cd Neurology_3D-Engine
   ```
2. **Run the Python pipeline** (if you have new raw data)
   ```bash
   python loreta_pipeline.py raw_data.csv
   # Produces loreta_results.json inside frontend/
   ```
3. **Launch the web UI**
   ```bash
   cd frontend
   python -m http.server 8080
   # Open http://localhost:8080 in a browser
   ```
4. **Explore the UI** – use the sidebar to jump between:
   - *Dashboard* – quick stats & classification.
   - *3D Brain* – rotate, pan, watch the colour gradient per region.
   - *Charts* – band distribution and region percentages.
   - *Comparison* – slider to compare first vs. second half of the recording.
   - *Report* – a printable summary of the session.
   - *Glossary* – definitions for every term.
5. **Update the design** – edit `styles.css` for colours/borders, `app.js` for chart options, or replace `brain_model.glb` for a higher‑poly mesh.
6. **Deploy** – after committing changes, push `main` and `gh‑pages` as demonstrated earlier.

---

*Prepared for Vedant Kalla – May 2026* 

---

*The PDF version of this document can be generated by running `pandoc PROJECT_OVERVIEW.md -o PROJECT_OVERVIEW.pdf` on a machine with Pandoc installed.*
