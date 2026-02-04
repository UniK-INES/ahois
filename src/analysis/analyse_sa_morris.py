"""
Gathers model outputs and performs Morris sensitivity analysis for
multiple output variables, supporting both scalar values and nested
dictionary structures (2-level).

It performs the following steps:

1.  Loads a `morris_param_map.csv` and `sa_variables.csv`.
2.  Defines `SCALAR_OUTPUTS` and `DICT_OUTPUTS` to analyze.
3.  Iterates through every row in the parameter map:
    a. Reads the pickle file.
    b. Extracts scalar variables directly.
    c. Checks `DICT_PROCESSING_METHOD` for each dict variable:
       - 'survivorship': Calculates conditional pass rates (sequential).
       - 'distribution': Calculates share of total events (categorical/branching).
       - 'raw': Uses the absolute numbers.
    d. Flattens the resulting dictionary.
4.  Merges the extracted outputs back into the parameter map.
5.  Performs Morris analysis for each variable.
6.  Saves results to `morris_results_combined.xlsx`.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
"""

import sys
import os
import pandas as pd
import numpy as np
import glob
from SALib.analyze import morris

# Adjust path to find helper modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from helpers.config import settings, get_output_path

# --- Define Constants ---

# File locations
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
PARAM_MAP_FILE = os.path.join(ANALYSIS_DIR, 'morris_param_map.csv') 
VARS_FILE = os.path.join(ANALYSIS_DIR, 'sa_variables.csv')
COMBINED_RESULTS_FILE = os.path.join(ANALYSIS_DIR, 'morris_results_combined.xlsx')
MISSING_LOG_FILE = os.path.join(ANALYSIS_DIR, 'missing_runs_report.csv') # <--- NEW LOG FILE

# Analysis parameters
FILES_PREFIX = 'DEZ_Baseline'
SEED_SEQUENCE_LENGTH = 8

# --- 1. DEFINE YOUR OUTPUT VARIABLES ---

# Simple numeric variables (Scalar)
SCALAR_OUTPUTS = [
    'Scenario fulfilment',
]

# Nested dictionary variables (e.g., {Key1: {Key2: Number}})
DICT_OUTPUTS = [
    'Obstacles',
    'Stage flows',
    ]

# --- 2. CONFIGURATION FOR DICTIONARY PROCESSING ---
INITIAL_AGENT_COUNT = 514

# Map each dictionary variable to a method: 'raw', 'survivorship', or 'distribution'
DICT_PROCESSING_METHOD = {
    'Obstacles': 'survivorship',   # Good for linear pipelines (Rate = Count / Prev_Count)
    'Stage flows': 'distribution'  # Good for branching/loops (Share = Count / Sum_of_Stage)
}
# ---------------------------------------


def flatten_nested_dict(root_name, data_dict):
    """
    Recursively flattens a 2-level dictionary into a single dictionary
    with composite keys.
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
                    col_name = f"Y_{root_name}__{k1}__{k2}"
                    flattened[col_name] = v2
        elif isinstance(v1, (int, float, np.number)):
            col_name = f"Y_{root_name}__{k1}"
            flattened[col_name] = v1
            
    return flattened


def convert_counts_to_rates(root_dict, total_agents):
    """
    Method: 'survivorship'
    Converts absolute counts of SURVIVORS to conditional pass rates.
    """
    converted_dict = {}
    
    for option_key, stages in root_dict.items():
        current_pool = total_agents
        option_rates = {}
        
        if isinstance(stages, dict):
            # Iterate through sequential stages
            for stage_name, survivor_count in stages.items():
                if current_pool > 0:
                    rate = survivor_count / current_pool
                    if rate > 1.0: rate = 1.0
                    current_pool = survivor_count
                else:
                    rate = 0.0
                    current_pool = 0
                
                option_rates[stage_name] = rate
        else:
            option_rates = stages

        converted_dict[option_key] = option_rates
        
    return converted_dict


def calculate_stage_distributions(root_dict):
    """
    Method: 'distribution'
    Calculates the relative share (probability) of each outcome within its specific stage.
    """
    processed_dict = {}
    
    for stage_name, outcomes in root_dict.items():
        stage_rates = {}
        
        if isinstance(outcomes, dict):
            # 1. Calculate the total volume for THIS specific stage
            total_stage_events = sum(val for val in outcomes.values() if isinstance(val, (int, float, np.number)))
            
            if total_stage_events > 0:
                for key, count in outcomes.items():
                    if isinstance(count, (int, float, np.number)):
                        # Calculate share (0.0 to 1.0)
                        stage_rates[key] = count / total_stage_events
            else:
                # If stage was empty, all probabilities are 0
                for key in outcomes.keys():
                    stage_rates[key] = 0.0
        else:
            # Fallback for non-dict structures
            stage_rates = outcomes
                
        processed_dict[stage_name] = stage_rates
        
    return processed_dict


def analyze_morris_results():
    """
    Main function to load data, gather outputs, and run Morris analysis.
    """
    
    # --- Load Input Files ---
    print(f"--- 1. Loading Inputs ---")
    try:
        param_map_df = pd.read_csv(PARAM_MAP_FILE)
        sa_vars_df = pd.read_csv(VARS_FILE)
    except FileNotFoundError as e:
        print(f"Error: File not found. {e}")
        return

    print(f"Loaded '{PARAM_MAP_FILE}' ({len(param_map_df)} runs).")
    print(f"Loaded '{VARS_FILE}' ({len(sa_vars_df)} parameters).")
    
    # --- Build SALib Problem ---
    print(f"\n--- 2. Building SALib Problem ---")
    try:
        problem = {
            'num_vars': len(sa_vars_df),
            'names': sa_vars_df['name'].tolist(),
            'bounds': sa_vars_df[['min', 'max']].values.tolist()
        }
    except Exception as e:
        print(f"Error building SALib problem: {e}")
        return

    # --- Gather Model Outputs ---
    print(f"\n--- 3. Gathering Model Outputs ---")
    print(f"Scalars: {SCALAR_OUTPUTS}")
    print(f"Dicts:   {DICT_OUTPUTS}")
    
    extracted_y_data = [] 
    
    files_processed = 0
    seeds_with_missing_files = set()
    
    missing_runs_log = []

    for index, row in param_map_df.iterrows():
        run_id = int(row['Run_id'])
        seed = int(row['Replication_Seed'])
        
        row_outputs = {'Run_id': run_id, 'Replication_Seed': seed}
        
        try:
            pickle_folder = get_output_path(runid=run_id, subfolder='pickles')
            seed_sequence = str(seed) * SEED_SEQUENCE_LENGTH
            search_pattern = os.path.join(pickle_folder, f"model_df_{FILES_PREFIX}_*_{seed_sequence}.pkl")
            files_found = glob.glob(search_pattern)
            
            # --- CHECK 1: File Existence ---
            if not files_found:
                seeds_with_missing_files.add(seed)
                missing_runs_log.append({
                    'Run_id': run_id, 
                    'Seed': seed, 
                    'Error': 'File Not Found',
                    'Pattern': search_pattern
                })
                # Print a small dot or 'X' to indicate progress/failure without spamming
                # print("x", end="", flush=True) 
                continue
            
            # --- CHECK 2: Empty DataFrame ---
            output_df = pd.read_pickle(files_found[0])
            if output_df.empty:
                seeds_with_missing_files.add(seed)
                missing_runs_log.append({
                    'Run_id': run_id, 
                    'Seed': seed, 
                    'Error': 'Empty DataFrame',
                    'File': files_found[0]
                })
                continue
                
            files_processed += 1
            last_row = output_df.iloc[-1]
            
            # 1. Extract Scalars
            for var_name in SCALAR_OUTPUTS:
                if var_name in last_row:
                    row_outputs[f"Y_{var_name}"] = last_row[var_name]
            
            # 2. Extract Dictionaries (With Transformation)
            for var_name in DICT_OUTPUTS:
                if var_name in last_row:
                    raw_data = last_row[var_name]
                    method = DICT_PROCESSING_METHOD.get(var_name, 'raw')
                    
                    if method == 'survivorship':
                        data_to_flatten = convert_counts_to_rates(raw_data, INITIAL_AGENT_COUNT)
                    elif method == 'distribution':
                        data_to_flatten = calculate_stage_distributions(raw_data)
                    else:
                        data_to_flatten = raw_data
                    
                    flat_data = flatten_nested_dict(var_name, data_to_flatten)
                    row_outputs.update(flat_data)
            
            extracted_y_data.append(row_outputs)

        except Exception as e:
            print(f"  [ERROR] Run {run_id}: {e}")
            seeds_with_missing_files.add(seed)
            missing_runs_log.append({
                'Run_id': run_id, 
                'Seed': seed, 
                'Error': f"Exception: {str(e)}",
                'File': 'Unknown'
            })

    print(f"\nGathering complete. Processed {files_processed} files.")
    
    if missing_runs_log:
        print(f"\n[WARNING] {len(missing_runs_log)} runs were missing or invalid!")
        
        # Save detailed log to CSV for easy sorting
        missing_df = pd.DataFrame(missing_runs_log)
        missing_df.to_csv(MISSING_LOG_FILE, index=False)
        print(f"-> Detailed list of missing runs saved to: {MISSING_LOG_FILE}")
        
        # Print first 5 to console as a sample
        print("-> Sample of missing runs:")
        print(missing_df[['Run_id', 'Seed', 'Error']].head(5).to_string(index=False))
        print("...")
    else:
        print("-> All files found successfully.")

    if not extracted_y_data:
        print("No output data extracted. Exiting.")
        return

    # Create DataFrame
    y_df = pd.DataFrame(extracted_y_data)
    full_df = pd.merge(param_map_df, y_df, on=['Run_id', 'Replication_Seed'], how='left')

    # --- 4. Main Analysis Loop ---
    sheets_to_save = {}
    ALL_VARS_TO_ANALYZE = SCALAR_OUTPUTS + DICT_OUTPUTS
    
    for root_var in ALL_VARS_TO_ANALYZE:
        print(f"\n--- Analyzing Root Variable: {root_var} ---")
        
        target_cols = []
        exact_col = f"Y_{root_var}"
        prefix_col = f"Y_{root_var}__"
        
        for col in full_df.columns:
            if col == exact_col:
                target_cols.append(col)
            elif col.startswith(prefix_col):
                target_cols.append(col)
                
        if not target_cols:
            print(f"No data columns found for '{root_var}'. Skipping.")
            continue
            
        print(f"Found {len(target_cols)} sub-metrics for '{root_var}'.")

        root_individual_results = []
        root_aggregated_rows = []
        
        for col_name in target_cols:
            if col_name == exact_col:
                sub_metric_name = "Total"
            else:
                sub_metric_name = col_name.replace(prefix_col, "")

            missing_count = full_df[col_name].isna().sum()
            if missing_count == len(full_df):
                continue

            # -- Analysis Per Replication --
            all_mu_star = []
            all_sigma = []
            
            unique_seeds = sorted(full_df['Replication_Seed'].unique())
            
            for seed in unique_seeds:
                if seed in seeds_with_missing_files: 
                    continue
                
                rep_data = full_df[full_df['Replication_Seed'] == seed].copy()
                rep_data.dropna(subset=[col_name], inplace=True)
                
                if rep_data.empty: continue
                
                Y = rep_data[col_name].values
                X = rep_data[problem['names']].values
                
                if len(Y) != len(X): continue
                
                Si = morris.analyze(problem, X, Y, print_to_console=False)
                
                all_mu_star.append(Si['mu_star'])
                all_sigma.append(Si['sigma'])
                
                df_indiv = pd.DataFrame({
                    'Sub_Metric': sub_metric_name,
                    'Replication_Seed': seed,
                    'Parameter': problem['names'],
                    'mu_star': Si['mu_star'],
                    'sigma': Si['sigma']
                })
                root_individual_results.append(df_indiv)

            # -- Aggregation --
            if all_mu_star:
                mu_star_mean = np.mean(all_mu_star, axis=0)
                mu_star_std = np.std(all_mu_star, axis=0)
                sigma_mean = np.mean(all_sigma, axis=0)
                sigma_std = np.std(all_sigma, axis=0)
                
                for i, param_name in enumerate(problem['names']):
                    root_aggregated_rows.append({
                        'Sub_Metric': sub_metric_name,
                        'Parameter': param_name,
                        'mu_star_Mean': mu_star_mean[i],
                        'mu_star_Std': mu_star_std[i],
                        'sigma_Mean': sigma_mean[i],
                        'sigma_Std': sigma_std[i]
                    })

        # -- Compile Tables --
        if root_aggregated_rows:
            agg_df = pd.DataFrame(root_aggregated_rows)
            cols = ['Sub_Metric', 'Parameter', 'mu_star_Mean', 'mu_star_Std', 'sigma_Mean', 'sigma_Std']
            agg_df = agg_df[cols]
            
            clean_name = "".join(c for c in root_var if c.isalnum() or c in (' ', '_')).rstrip()
            sheet_name = f"Agg_{clean_name}"[:31]
            sheets_to_save[sheet_name] = agg_df

        if root_individual_results:
            indiv_df = pd.concat(root_individual_results, ignore_index=True)
            clean_name = "".join(c for c in root_var if c.isalnum() or c in (' ', '_')).rstrip()
            sheet_name = f"Indiv_{clean_name}"[:31]
            sheets_to_save[sheet_name] = indiv_df

    # --- 5. Save All Results ---
    print(f"\n\n========================================================")
    print(f"--- 5. Saving All Results ---")
    print(f"========================================================")
    
    if not sheets_to_save:
        print("No results generated.")
        return

    sorted_sheets = sorted(
        sheets_to_save.items(),
        key=lambda x: (not x[0].startswith('Agg'), x[0])
    )

    try:
        with pd.ExcelWriter(COMBINED_RESULTS_FILE) as writer:
            for sheet_name, df in sorted_sheets:
                print(f"  Saving sheet: {sheet_name}")
                df.to_excel(writer, sheet_name=sheet_name, index=False, float_format="%.4f")
        
        print(f"\nSuccessfully saved to '{COMBINED_RESULTS_FILE}'")
        
    except Exception as e:
        print(f"[ERROR] Failed to save Excel. {e}")

if __name__ == '__main__':
    analyze_morris_results()