"""
Gathers model outputs for a specific range of Run IDs and calculates 
summary statistics across the random seeds found for each run.

Features:
1. Iterates through a user-defined range of Run IDs.
2. Finds all available pickle files (random seeds) for each ID.
3. Extracts specific scalar and nested dictionary variables (Raw data).
4. Aggregates data by Run ID and calculates: Mean, Median, Std, Min, Max, MAD.
5. Saves results to Excel.
6. Optionally provides raw data inspection for a specific Run ID.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
"""

import sys
import os
import pandas as pd
import numpy as np
import glob

# Adjust path to find helper modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from helpers.config import settings, get_output_path

# ==========================================
# --- USER CONFIGURATION ---
# ==========================================

# 1. Define the Range of Runs to Analyze
START_ID = 1      # Start of the range
END_ID = 10       # End of the range (inclusive)

# 2. File Naming Pattern
FILES_PREFIX = 'DEZ_Baseline'

# 3. Optional: Inspect a specific Run ID in detail?
# Set to an integer (e.g., 5) to get a separate sheet with raw values AND stats for this run.
# Set to None to skip.
DETAILED_RUN_ID = None 

# 4. Output Variables
# Simple numeric variables (Scalar)
SCALAR_OUTPUTS = [
    'Scenario fulfilment',
]

# Nested dictionary variables to flatten (Raw values only)
DICT_OUTPUTS = [
    'Obstacles',
    'Stage flows',
]

# Output File Name
RESULTS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 
    'summary_statistics_results.xlsx'
)

# ==========================================


def flatten_nested_dict(root_name, data_dict):
    """
    Recursively flattens a 2-level dictionary into a single dictionary
    with composite keys. Preserves raw values.
    """
    flattened = {}
    if not isinstance(data_dict, dict):
        return flattened

    for k1, v1 in data_dict.items():
        # Level 1
        if isinstance(v1, dict):
            # Level 2
            for k2, v2 in v1.items():
                if isinstance(v2, (int, float, np.number)):
                    col_name = f"{root_name}__{k1}__{k2}"
                    flattened[col_name] = v2
        elif isinstance(v1, (int, float, np.number)):
            col_name = f"{root_name}__{k1}"
            flattened[col_name] = v1
            
    return flattened

def get_mad(x):
    """Calculate Mean Absolute Deviation (Pandas MAD is deprecated in some versions)"""
    return (x - x.mean()).abs().mean()

def p10(x):
    """10th Percentile (Lower bound of 80% confidence interval)"""
    return x.quantile(0.10)

def p90(x):
    """90th Percentile (Upper bound of 80% confidence interval)"""
    return x.quantile(0.90)

def cv(x):
    """Coefficient of Variation (Std / Mean). Measure of relative volatility."""
    mean = x.mean()
    if mean == 0:
        return 0.0
    return x.std() / mean

def main():
    print(f"--- Starting Summary Statistics Analysis ---")
    print(f"Range: Run {START_ID} to {END_ID}")
    
    all_extracted_data = []
    
    # --- 1. Data Extraction Loop ---
    # Iterate through the requested Run IDs (similar to slurm management)
    for run_id in range(START_ID, END_ID + 1):
        
        # Construct path to pickles for this run
        try:
            pickle_folder = get_output_path(runid=run_id, subfolder='pickles')
        except Exception as e:
            print(f"[WARN] Could not determine path for Run {run_id}: {e}")
            continue

        if not os.path.exists(pickle_folder):
            # print(f"[WARN] Folder not found for Run {run_id}: {pickle_folder}")
            continue

        # Find ALL pickle files for this run (ignoring seed number in filename to get all)
        # Pattern assumes: model_df_{PREFIX}_{RunID}_{Seed}.pkl
        search_pattern = os.path.join(pickle_folder, f"model_df_{FILES_PREFIX}_{run_id}_*.pkl")
        files_found = glob.glob(search_pattern)
        
        if not files_found:
            # print(f"[INFO] No files found for Run {run_id}")
            continue
            
        print(f"Processing Run {run_id}: Found {len(files_found)} seeds.")

        for file_path in files_found:
            try:
                # Load Data
                df = pd.read_pickle(file_path)
                if df.empty:
                    continue
                
                # Take the final state (last row)
                last_row = df.iloc[-1]
                
                # Extract Seed from filename if possible, or just generate an index
                # Assuming standard naming, split by underscore
                filename = os.path.basename(file_path)
                # Try to extract seed from filename string, fallback to 'Unknown'
                try:
                    seed_str = filename.replace('.pkl', '').split('_')[-1]
                    seed_val = int(seed_str)
                except:
                    seed_val = 0
                
                # Dictionary for this single run/seed combination
                row_data = {
                    'Run_id': run_id,
                    'Replication_Seed': seed_val
                }
                
                # A. Extract Scalars
                for var in SCALAR_OUTPUTS:
                    if var in last_row:
                        row_data[var] = last_row[var]
                
                # B. Extract Dicts (Flattened, Raw)
                for var in DICT_OUTPUTS:
                    if var in last_row:
                        # Direct flattening, no pre-processing/rate calculation
                        flat_dict = flatten_nested_dict(var, last_row[var])
                        row_data.update(flat_dict)
                
                all_extracted_data.append(row_data)
                
            except Exception as e:
                print(f"  [ERROR] Reading {os.path.basename(file_path)}: {e}")

    # --- 2. Check Data ---
    if not all_extracted_data:
        print("\nNo data extracted. Exiting.")
        return

    full_df = pd.DataFrame(all_extracted_data)
    print(f"\nExtraction Complete. Total records: {len(full_df)}")

    # Identify value columns (exclude ID cols)
    id_cols = ['Run_id', 'Replication_Seed']
    value_cols = [c for c in full_df.columns if c not in id_cols]

    # --- 3. Calculation: Group by Run_ID ---
    print("Calculating statistics...")
    
    # Define aggregations
    agg_funcs = ['mean', 'median', 'std', 'min', 'max', get_mad, p10, p90, cv]
    
    # Group by Run_id and apply functions to all value columns
    # resulting in a MultiIndex columns
    grouped_df = full_df.groupby('Run_id')[value_cols].agg(agg_funcs)
    
    # Rename custom functions for cleaner headers
    grouped_df = grouped_df.rename(columns={
        'get_mad': 'mad',
        'p10': '10%',
        'p90': '90%',
        'cv': 'CV'
    }, level=1)

    # Flatten Column Names: "Variable" + "Mean" -> "Variable_mean"
    grouped_df.columns = [f"{col[0]}_{col[1]}" for col in grouped_df.columns]
    grouped_df.reset_index(inplace=True)

    # --- 4. Detailed View Preparation (Optional) ---
    detailed_df = pd.DataFrame()
    detailed_stats_df = pd.DataFrame()
    
    if DETAILED_RUN_ID is not None:
        if DETAILED_RUN_ID in full_df['Run_id'].values:
            print(f"Preparing detailed extract for Run {DETAILED_RUN_ID}...")
            # Get Raw Data
            detailed_df = full_df[full_df['Run_id'] == DETAILED_RUN_ID].copy()
            detailed_df = detailed_df.sort_values(by='Replication_Seed')
            
            # Get Stats Data (Subset of grouped_df)
            detailed_stats_df = grouped_df[grouped_df['Run_id'] == DETAILED_RUN_ID].copy()
        else:
            print(f"[WARN] Detailed Run ID {DETAILED_RUN_ID} not found in extracted data.")

    # --- 5. Save to Excel ---
    print(f"Saving to {RESULTS_FILE}...")
    try:
        with pd.ExcelWriter(RESULTS_FILE) as writer:
            # Sheet 1: The Summary (Aggregated)
            grouped_df.to_excel(writer, sheet_name='Summary_Statistics', index=False, float_format="%.4f")
            
            # Sheet 2: Detailed single run (if requested)
            if not detailed_df.empty:
                sheet_name = f'Raw_Run_{DETAILED_RUN_ID}'
                
                # Write Stats Block at the top
                detailed_stats_df.to_excel(writer, sheet_name=sheet_name, startrow=0, index=False, float_format="%.4f")
                
                # Write a separator text (optional) or just spacing
                worksheet = writer.sheets[sheet_name]
                worksheet.write(2, 0, "RAW DATA BELOW:")
                
                # Write Raw Data Block below stats (leave some space)
                detailed_df.to_excel(writer, sheet_name=sheet_name, startrow=3, index=False)
            
            # Sheet 3: All Raw Data (Backup)
            full_df.to_excel(writer, sheet_name='All_Raw_Data', index=False)
            
        print("Done successfully.")
        
    except Exception as e:
        print(f"[ERROR] Could not save Excel file: {e}")
        print("Check if the file is currently open.")

if __name__ == "__main__":
    main()