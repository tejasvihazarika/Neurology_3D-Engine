import pandas as pd
import os
import tarfile
import glob
import io
import gzip

def extract_and_clean():
    # 1. Path to the inner archives
    inner_archives_folder = os.path.join('eeg_data_temp', 'smni_eeg_data')
    archives = glob.glob(os.path.join(inner_archives_folder, "*.tar.gz"))
    
    if not archives:
        print(f"Error: No .tar.gz files found in {inner_archives_folder}")
        return

    target_archive = archives[0]
    print(f"Diving into archive: {target_archive}")
    
    data = []
    with tarfile.open(target_archive, "r:gz") as tar:
        # Search for the data file
        member = next((m for m in tar.getmembers() if ".rd." in m.name), None)
        
        if member:
            print(f"Extracting signal data from: {member.name}")
            f = tar.extractfile(member)
            raw_bytes = f.read()

            # FIX: Check if the internal file is gzipped (starts with 1f 8b)
            if raw_bytes.startswith(b'\x1f\x8b'):
                print("Decompressing internal Gzip layer...")
                content = gzip.decompress(raw_bytes).decode('utf-8')
            else:
                content = raw_bytes.decode('utf-8')
            
            # Parse the text format
            for line in content.splitlines():
                if line.startswith('#'): continue
                parts = line.split()
                if len(parts) >= 4:
                    data.append([parts[1], int(parts[2]), float(parts[3])])

    if not data:
        print("Error: Could not find or parse raw signal data.")
        return

    # 3. Structure and Pivot
    df_raw = pd.DataFrame(data, columns=['Channel', 'Index', 'Value'])
    df_pivot = df_raw.pivot(index='Index', columns='Channel', values='Value')
    
    # UCI Sample Rate is 256Hz
    df_pivot.index = df_pivot.index * (1/256)
    df_pivot.index.name = 'Time (s)'
    
    # 4. Save
    os.makedirs('processed_data', exist_ok=True)
    df_pivot.to_csv('processed_data/clean_eeg.csv')
    print("✅ Success! 'processed_data/clean_eeg.csv' is ready.")

if __name__ == "__main__":
    extract_and_clean()