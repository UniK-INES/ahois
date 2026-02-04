"""
Gathers model outputs and performs Sobol sensitivity analysis for
multiple output variables.

This script links the generated parameters from `sa_param_map.csv` with
the corresponding model output files (pickles). It performs the following steps:

1.  Loads the `sa_param_map.csv` to get the `Run_id`, `Replication_Seed`,
    and parameter values for each run.
2.  Loads the `sa_variables.csv` to define the SALib 'problem' dictionary,
    including parameter names and bounds.
3.  Defines a list of `OUTPUT_VARIABLES_TO_ANALYZE`.
4.  Iterates through every row in the parameter map. For each run, it:
    a. Finds the correct output folder using `get_output_path()`.
    b. Finds the specific `.pkl` output file by matching the `FILES_PREFIX`
       and the `Replication_Seed`.
    c. Reads the pickle file and extracts the last row's value for ALL
       variables in the `OUTPUT_VARIABLES_TO_ANALYZE` list.
    d. Stores these values in new 'Y_[variable_name]' columns.
5.  Once all outputs are gathered, it enters a main loop, performing a
    separate analysis for EACH output variable.
6.  For each output variable, it:
    a. Performs the Sobol analysis (`SALib.analyze.sobol`) for each
       replication group.
    b. Calculates an aggregated table showing the mean/std of the
       S1/ST indices across all replications.
7.  It saves all results (both individual and aggregated for all output
    variables) to a single Excel file: `sa_results_combined.xlsx`,
    using separate worksheets for each result.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""

import sys
import os
import pandas as pd
import numpy as np
import glob
from SALib.analyze import sobol


current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from helpers.config import settings, get_output_path

#Define Constants ---

# File locations
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
PARAM_MAP_FILE = os.path.join(ANALYSIS_DIR, 'sobol_param_map.csv')
VARS_FILE = os.path.join(ANALYSIS_DIR, 'sa_variables.csv')
# Define output file path
COMBINED_RESULTS_FILE = os.path.join(ANALYSIS_DIR, 'sa_results_combined.xlsx')

# Analysis parameters
FILES_PREFIX = 'DEZ_Baseline'
SEED_SEQUENCE_LENGTH = 8
N_SAMPLES = settings.experiments.sa_nsamples

# --- 1. DEFINE YOUR OUTPUT VARIABLES ---
# List all output variables you want to analyze from the model.
OUTPUT_VARIABLES_TO_ANALYZE = [
    'Scenario fulfilment',
    'Average Scenario Fulfilment'
]
# ---------------------------------------


def analyze_sa_results():
    """
    Main function to load data, gather outputs, and run Sobol analysis
    for multiple output variables.
    """
    
    # Load Input Files
    print(f"--- 1. Loading Inputs ---")
    try:
        param_map_df = pd.read_csv(PARAM_MAP_FILE)
        sa_vars_df = pd.read_csv(VARS_FILE)
    except FileNotFoundError as e:
        print(f"Error: File not found. {e}")
        print("Please ensure 'sobol_param_map.csv' and 'sa_variables.csv' are in 'src/analysis/'.")
        return

    print(f"Loaded '{PARAM_MAP_FILE}' ({len(param_map_df)} runs).")
    print(f"Loaded '{VARS_FILE}' ({len(sa_vars_df)} parameters).")
    
    # Create new 'Y' columns for each output variable
    for var_name in OUTPUT_VARIABLES_TO_ANALYZE:
        col_name = f'Y_{var_name}'
        if col_name in param_map_df.columns:
            print(f"Warning: Column '{col_name}' already exists. It will be overwritten.")
        param_map_df[col_name] = np.nan

    # Build SALib Problem
    print(f"\n--- 2. Building SALib Problem ---")
    try:
        problem = {
            'num_vars': len(sa_vars_df),
            'names': sa_vars_df['name'].tolist(),
            'bounds': sa_vars_df[['min', 'max']].values.tolist()
        }
        print("SALib problem definition:")
        print(problem)
    except Exception as e:
        print(f"Error: Could not build SALib problem from '{VARS_FILE}'.")
        print(f"Ensure it has 'name', 'min', and 'max' columns. Error: {e}")
        return

    # Gather Model Outputs
    print(f"\n--- 3. Gathering Model Outputs ---")
    print(f"Searching for {len(OUTPUT_VARIABLES_TO_ANALYZE)} variables: {OUTPUT_VARIABLES_TO_ANALYZE}")
    print(f"Matching file prefix: '{FILES_PREFIX}'")
    
    outputs_found_count = {var: 0 for var in OUTPUT_VARIABLES_TO_ANALYZE}
    files_processed = 0
    
    for index, row in param_map_df.iterrows():
        try:
            run_id = int(row['Run_id'])
            seed = int(row['Replication_Seed'])
            
            # Get the folder path
            pickle_folder = get_output_path(runid=run_id, subfolder='pickles')
            
            # Create the file search pattern
            seed_sequence = str(seed) * SEED_SEQUENCE_LENGTH
            search_pattern = os.path.join(pickle_folder, f"model_df_{FILES_PREFIX}_*_{seed_sequence}.pkl")
            
            # Find the file
            files_found = glob.glob(search_pattern)
            
            if not files_found:
                print(f"  [WARN] Run {run_id}, Seed {seed}: No output file found at: {search_pattern}")
                continue
            
            if len(files_found) > 1:
                print(f"  [WARN] Run {run_id}, Seed {seed}: Found {len(files_found)} matching files. Using first one: {files_found[0]}")
            
            file_path = files_found[0]
            
            # Read pickle and extract the output value
            output_df = pd.read_pickle(file_path)
            files_processed += 1

            if output_df.empty:
                print(f"  [WARN] Run {run_id}, Seed {seed}: Output file is empty: {file_path}")
                continue
            
            # Extract the last row
            last_row = output_df.iloc[-1]
            
            # Loop through all requested variables and extract them
            for var_name in OUTPUT_VARIABLES_TO_ANALYZE:
                if var_name not in last_row:
                    if index < 5: # Only print first few errors to avoid spam
                        print(f"  [WARN] Run {run_id}, Seed {seed}: Output variable '{var_name}' not in file: {file_path}")
                    continue
                
                value = last_row[var_name]
                param_map_df.at[index, f'Y_{var_name}'] = value
                outputs_found_count[var_name] += 1

        except Exception as e:
            print(f"  [ERROR] Run {run_id}, Seed {seed}: Failed to process. Error: {e}")

    print(f"\nGathering complete. Processed {files_processed} files.")
    for var_name, count in outputs_found_count.items():
        print(f"  -> Found {count} data points for '{var_name}'")
    
    if all(count == 0 for count in outputs_found_count.values()):
        print("No outputs found for any variable. Cannot proceed with analysis. Exiting.")
        return

    # --- 4. Main Analysis Loop ---
    # We will now loop through each output variable and perform the
    # full analysis (Steps 4 and 5) for it.
    
    all_individual_dfs = {}
    all_aggregated_dfs = {}
    
    for output_var in OUTPUT_VARIABLES_TO_ANALYZE:
        print(f"\n\n========================================================")
        print(f"--- Running Analysis for: {output_var} ---")
        print(f"========================================================")
        
        output_col_name = f'Y_{output_var}'
        
        # Check if we have any data for this variable
        if outputs_found_count[output_var] == 0:
            print(f"No data found for '{output_var}'. Skipping analysis.")
            continue
            
        missing_outputs = param_map_df[output_col_name].isna().sum()
        if missing_outputs > 0:
            print(f"Warning: {missing_outputs} outputs are missing (NaN) for this variable.")
            print("Analysis will proceed by dropping missing runs for each replication.")

        # --- 4a. Run Analysis (Per Replication) ---
        print(f"\n--- 4a. Running Analysis (per Replication) ---")
    
        unique_seeds = sorted(param_map_df['Replication_Seed'].unique())
        all_s1_indices = []
        all_st_indices = []
        
        all_results_list = []
        
        for seed in unique_seeds:
            print(f"\n--- Analyzing Replication Seed: {seed} ---")
            rep_data = param_map_df[param_map_df['Replication_Seed'] == seed].copy()
            
            # Drop NaNs for THIS specific output variable
            rep_data.dropna(subset=[output_col_name], inplace=True)
            
            Y = rep_data[output_col_name].values
            
            
            if len(Y) != N_SAMPLES * (2 * problem['num_vars'] + 2):
                print(f"  Skipping seed {seed}: Not enough data points ({len(Y)}) found to run analysis.")
                print(f"  Expected {N_SAMPLES * (2 * problem['num_vars'] + 2)}, found {len(Y)} after dropping NaNs.")
                continue
                
            # Run the Sobol analysis
            Si = sobol.analyze(problem, Y, calc_second_order=True, print_to_console=False)
            
            # Store results for aggregation
            all_s1_indices.append(Si['S1'])
            all_st_indices.append(Si['ST'])
            
            # Print results for this replication
            print("  Results:")
            results_df = pd.DataFrame({
                'S1': Si['S1'],
                'S1_conf': Si['S1_conf'],
                'ST': Si['ST'],
                'ST_conf': Si['ST_conf']
            }, index=problem['names'])
            print(results_df.to_string())

            results_df_to_save = results_df.reset_index().rename(columns={'index': 'Parameter'})
            results_df_to_save['Replication_Seed'] = seed
            all_results_list.append(results_df_to_save)

        if not all_results_list:
            print("\nNo individual results were generated for this output variable.")
            individual_results_df = pd.DataFrame(columns=['Replication_Seed', 'Parameter', 'S1', 'S1_conf', 'ST', 'ST_conf'])
        else:
            individual_results_df = pd.concat(all_results_list, ignore_index=True)
            # Reorder columns for clarity
            cols = ['Replication_Seed', 'Parameter', 'S1', 'S1_conf', 'ST', 'ST_conf']
            individual_results_df = individual_results_df[cols]
            print(f"\nSuccessfully consolidated {len(all_results_list)} individual replication results.")

        # --- 4b. Aggregate Final Results ---
        print(f"\n\n--- 4b. Aggregated Results (Mean / Std across {len(all_s1_indices)} replications) ---")
        
        if not all_s1_indices:
            print(f"No results to aggregate for '{output_var}'.")
            # Create empty DF
            final_results_df = pd.DataFrame(columns=[
                'Parameter', 'S1_Mean', 'S1_Std', 'ST_Mean', 'ST_Std'
            ]).set_index('Parameter')
        else:
            # Calculate Mean and Std
            s1_mean = np.mean(all_s1_indices, axis=0)
            s1_std = np.std(all_s1_indices, axis=0)
            st_mean = np.mean(all_st_indices, axis=0)
            st_std = np.std(all_st_indices, axis=0)

            # Create final summary DataFrame
            final_results_df = pd.DataFrame({
                'Parameter': problem['names'],
                'S1_Mean': s1_mean,
                'S1_Std': s1_std,
                'ST_Mean': st_mean,
                'ST_Std': st_std
            }).set_index('Parameter')
        
        print(final_results_df.to_string(float_format="%.2f"))

        # Store DataFrames for saving later
        all_individual_dfs[output_var] = individual_results_df
        all_aggregated_dfs[output_var] = final_results_df.reset_index() # Reset index for saving

    # --- 5. Save All Results to One Excel File ---
    print(f"\n\n========================================================")
    print(f"--- 5. Saving All Results ---")
    print(f"========================================================")
    
    if not all_aggregated_dfs:
        print("No results were generated for any output variable. Nothing to save.")
        return

    try:
        with pd.ExcelWriter(COMBINED_RESULTS_FILE) as writer:
            for var_name in all_aggregated_dfs.keys():
                # Create clean sheet names (max 31 chars, no invalid chars)
                clean_name = "".join(c for c in var_name if c.isalnum() or c in (' ', '_')).rstrip()
                agg_sheet = f"Agg_{clean_name}"[:31]
                indiv_sheet = f"Indiv_{clean_name}"[:31]
                
                print(f"  Saving '{var_name}' results to sheets:")
                print(f"    -> {agg_sheet}")
                print(f"    -> {indiv_sheet}")
                
                # Save aggregated results
                all_aggregated_dfs[var_name].to_excel(
                    writer, 
                    sheet_name=agg_sheet, 
                    index=False, 
                    float_format="%.5f"
                )
                # Save individual results
                all_individual_dfs[var_name].to_excel(
                    writer, 
                    sheet_name=indiv_sheet, 
                    index=False, 
                    float_format="%.5f"
                )
                
        print(f"\nSuccessfully saved all results to '{COMBINED_RESULTS_FILE}'")
    except Exception as e:
        print(f"\n[ERROR] Failed to save combined results to Excel. Error: {e}")
        print("Note: This operation requires the 'openpyxl' package. You may need to install it (`pip install openpyxl`)")


if __name__ == '__main__':
    """
    Script entry point.
    """
    analyze_sa_results()