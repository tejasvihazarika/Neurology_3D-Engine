import pandas as pd
import os
import tarfile
import glob
import gzip
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch

# ---------------- GLOBAL SETTINGS ---------------- #
ORIGINAL_FS = 256
TARGET_FS = 32
DOWNSAMPLE_FACTOR = ORIGINAL_FS // TARGET_FS  # = 8

# ---------------- FILTER FUNCTIONS ---------------- #

def bandpass_filter(data, lowcut=0.5, highcut=15, fs=TARGET_FS, order=4):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return filtfilt(b, a, data, axis=0)

def notch_filter(data, freq=50, fs=TARGET_FS, Q=30):
    b, a = iirnotch(freq/(fs/2), Q)
    return filtfilt(b, a, data, axis=0)

# ---------------- MAIN FUNCTION ---------------- #

def extract_and_clean():
    
    inner_archives_folder = os.path.join('eeg_data_temp', 'smni_eeg_data')
    archives = glob.glob(os.path.join(inner_archives_folder, "*.tar.gz"))
    
    if not archives:
        print(f"Error: No .tar.gz files found in {inner_archives_folder}")
        return

    target_archive = archives[0]
    print(f"Diving into archive: {target_archive}")
    
    data = []
    
    with tarfile.open(target_archive, "r:gz") as tar:
        member = next((m for m in tar.getmembers() if ".rd." in m.name), None)
        
        if member:
            print(f"Extracting signal data from: {member.name}")
            f = tar.extractfile(member)
            raw_bytes = f.read()

            if raw_bytes.startswith(b'\x1f\x8b'):
                print("Decompressing internal Gzip layer...")
                content = gzip.decompress(raw_bytes).decode('utf-8')
            else:
                content = raw_bytes.decode('utf-8')
            
            for line in content.splitlines():
                if line.startswith('#'): 
                    continue
                parts = line.split()
                if len(parts) >= 4:
                    data.append([parts[1], int(parts[2]), float(parts[3])])

    if not data:
        print("Error: Could not find or parse raw signal data.")
        return

    # ---------------- DATAFRAME ---------------- #

    df_raw = pd.DataFrame(data, columns=['Channel', 'Index', 'Value'])
    df_pivot = df_raw.pivot(index='Index', columns='Channel', values='Value')

    # ---------------- 🔽 DOWNSAMPLING ---------------- #

    print("\nDownsampling from 256 Hz → 32 Hz...")
    df_downsampled = df_pivot.iloc[::DOWNSAMPLE_FACTOR]

    # ---------------- BASELINE CORRECTION ---------------- #

    print("Applying baseline correction...")

    # Drift at 0.25 sec → now at 32 Hz:
    # 0.25 * 32 = 8 samples
    window_size = 8

    rolling_mean = df_downsampled.rolling(window=window_size, center=True, min_periods=1).mean()
    df_corrected = df_downsampled - rolling_mean

    # ---------------- 📊 PLOT ---------------- #

    channel = df_corrected.columns[0]
    time_axis = df_corrected.index * (1/TARGET_FS)

    os.makedirs('processed_data', exist_ok=True)

    plt.figure()
    plt.plot(time_axis, df_downsampled[channel], label="Raw (Downsampled)")
    plt.plot(time_axis, rolling_mean[channel], label="Baseline")
    plt.plot(time_axis, df_corrected[channel], label="Corrected")

    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude")
    plt.title("Baseline Correction (32 Hz)")
    plt.legend()

    plt.savefig('processed_data/baseline_32hz.png')
    plt.close()

    # ---------------- NOISE REMOVAL ---------------- #

    print("Applying bandpass filter...")
    filtered = bandpass_filter(df_corrected.values)

    # ⚠️ 50 Hz notch NOT needed (above Nyquist of 16 Hz)
    df_filtered = pd.DataFrame(filtered, index=df_corrected.index, columns=df_corrected.columns)

    # ---------------- TIME AXIS ---------------- #

    df_filtered.index = df_filtered.index * (1/TARGET_FS)
    df_filtered.index.name = 'Time (s)'

    # ---------------- SAVE ---------------- #

    df_filtered.to_csv('processed_data/clean_eeg_32hz.csv')

    print("\n✅ Success!")
    print("✔ Data downsampled to 32 Hz")
    print("✔ Baseline corrected")
    print("✔ Filtered data saved")

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    extract_and_clean()