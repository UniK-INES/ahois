"""
Gathers model outputs and performs Full Factorial Analysis (Main Effects & 2-Way Interactions).

It performs the following steps:
1.  Loads `full_factorial_param_map.csv` and `sa_variables.csv`.
2.  Gathers output data (parsing scalars and nested dictionaries).
3.  Converts inputs to "Coded Units" (-1 to +1).
4.  Generates Interaction terms (A*B).
5.  Fits an OLS Regression model to quantify Effect Size and Significance.
6.  Saves results to `full_factorial_results.xlsx`.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
"""

import sys
import os
import pandas as pd
import numpy as np
import glob
import itertools
import statsmodels.api as sm

# Adjust path to find helper modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from helpers.config import settings, get_output_path

# --- Define Constants ---

# File locations
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))

# strictly target the Full Factorial map
PARAM_MAP_FILE = os.path.join(ANALYSIS_DIR, 'full_factorial_param_map.csv')
VARS_FILE = os.path.join(ANALYSIS_DIR, 'sa_variables.csv')
RESULTS_FILE = os.path.join(ANALYSIS_DIR, 'full_factorial_results.xlsx')
MISSING_LOG_FILE = os.path.join(ANALYSIS_DIR, 'missing_runs_report.csv')

# Analysis parameters
FILES_PREFIX = 'DEZ_Baseline'
SEED_SEQUENCE_LENGTH = 8

# --- 1. DEFINE THE OUTPUT VARIABLES ---

SCALAR_OUTPUTS = [
    'Scenario fulfilment',
]

DICT_OUTPUTS = [
    'Obstacles',
    'Stage flows',
]

# --- 2. CONFIGURATION FOR DICTIONARY PROCESSING ---
INITIAL_AGENT_COUNT = 514

DICT_PROCESSING_METHOD = {
    'Obstacles': 'survivorship',
    'Stage flows': 'distribution'
}
# ---------------------------------------

def flatten_nested_dict(root_name, data_dict):
    """Recursively flattens a 2-level dictionary."""
    flattened = {}
    if not isinstance(data_dict, dict):
        return flattened

    for k1, v1 in data_dict.items():
        if isinstance(v1, dict):
            for k2, v2 in v1.items():
                if isinstance(v2, (int, float, np.number)):
                    col_name = f"Y_{root_name}__{k1}__{k2}"
                    flattened[col_name] = v2
        elif isinstance(v1, (int, float, np.number)):
            col_name = f"Y_{root_name}__{k1}"
            flattened[col_name] = v1
    return flattened

def convert_counts_to_rates(root_dict, total_agents):
    """Method: 'survivorship'"""
    converted_dict = {}
    for option_key, stages in root_dict.items():
        current_pool = total_agents
        option_rates = {}
        if isinstance(stages, dict):
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
    """Method: 'distribution'"""
    processed_dict = {}
    for stage_name, outcomes in root_dict.items():
        stage_rates = {}
        if isinstance(outcomes, dict):
            total_stage_events = sum(val for val in outcomes.values() if isinstance(val, (int, float, np.number)))
            if total_stage_events > 0:
                for key, count in outcomes.items():
                    if isinstance(count, (int, float, np.number)):
                        stage_rates[key] = count / total_stage_events
            else:
                for key in outcomes.keys():
                    stage_rates[key] = 0.0
        else:
            stage_rates = outcomes
        processed_dict[stage_name] = stage_rates
    return processed_dict

def encode_variables(df, vars_df):
    """
    Converts real-world values into Coded Units (-1 to +1).
    Essential for Full Factorial Analysis to calculate correct Effect Sizes.
    """
    df_coded = df.copy()
    names = vars_df['name'].tolist()
    
    for name in names:
        row = vars_df[vars_df['name'] == name].iloc[0]
        v_min = row['min']
        v_max = row['max']
        v_mid = (v_max + v_min) / 2
        v_half_range = (v_max - v_min) / 2
        
        if v_half_range == 0:
            df_coded[name] = 0 
        else:
            df_coded[name] = (df_coded[name] - v_mid) / v_half_range
            
    return df_coded

def analyze_full_factorial():
    """
    Main function for Full Factorial Analysis.
    """
    
    # --- Load Input Files ---
    print(f"--- 1. Loading Inputs ---")
    if not os.path.exists(PARAM_MAP_FILE):
        print(f"Error: Map file not found at {PARAM_MAP_FILE}")
        print("Did you run the settings generation script with SA_METHOD='full_factorial'?")
        return

    param_map_df = pd.read_csv(PARAM_MAP_FILE)
    sa_vars_df = pd.read_csv(VARS_FILE)

    print(f"Loaded '{os.path.basename(PARAM_MAP_FILE)}' ({len(param_map_df)} runs).")
    print(f"Loaded '{os.path.basename(VARS_FILE)}' ({len(sa_vars_df)} parameters).")
    
    # --- Gather Model Outputs ---
    print(f"\n--- 2. Gathering Model Outputs ---")
    
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
            
            if not files_found:
                seeds_with_missing_files.add(seed)
                missing_runs_log.append({'Run_id': run_id, 'Seed': seed, 'Error': 'File Not Found'})
                continue
            
            output_df = pd.read_pickle(files_found[0])
            if output_df.empty:
                seeds_with_missing_files.add(seed)
                missing_runs_log.append({'Run_id': run_id, 'Seed': seed, 'Error': 'Empty DataFrame'})
                continue
                
            files_processed += 1
            last_row = output_df.iloc[-1]
            
            # Extract Scalars
            for var_name in SCALAR_OUTPUTS:
                if var_name in last_row:
                    row_outputs[f"Y_{var_name}"] = last_row[var_name]
            
            # Extract Dictionaries
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
            missing_runs_log.append({'Run_id': run_id, 'Seed': seed, 'Error': str(e)})

    print(f"Gathering complete. Processed {files_processed} files.")
    
    if missing_runs_log:
        pd.DataFrame(missing_runs_log).to_csv(MISSING_LOG_FILE, index=False)
        print(f"[WARNING] Missing runs logged to: {MISSING_LOG_FILE}")

    if not extracted_y_data:
        print("No output data extracted. Exiting.")
        return

    # Create Full DataFrame
    y_df = pd.DataFrame(extracted_y_data)
    # Merge outputs with inputs
    full_df = pd.merge(param_map_df, y_df, on=['Run_id', 'Replication_Seed'], how='inner')

    # --- 3. Prepare Data for Regression (Coding & Interactions) ---
    print(f"\n--- 3. Preparing Statistical Model ---")
    
    input_names = sa_vars_df['name'].tolist()
    
    # A. Encode Inputs to [-1, 1]
    X_coded = encode_variables(full_df[input_names], sa_vars_df)
    
    # B. Generate Two-Way Interaction Terms
    interaction_pairs = list(itertools.combinations(input_names, 2))
    print(f"Generating terms: {len(input_names)} Main Effects + {len(interaction_pairs)} Interactions")
    
    for (var_a, var_b) in interaction_pairs:
        col_name = f"{var_a}:{var_b}"
        X_coded[col_name] = X_coded[var_a] * X_coded[var_b]

    # Add constant for Intercept
    X_coded = sm.add_constant(X_coded)

    # --- 4. Main Analysis Loop ---
    sheets_to_save = {}
    
    # Identify all Y columns
    y_cols = [c for c in full_df.columns if c.startswith("Y_")]
    
    print(f"Processing {len(y_cols)} output metrics...")

    for y_col in y_cols:
        clean_metric_name = y_col.replace("Y_", "")
        short_sheet_name = clean_metric_name.replace(":", "_").replace("__", "_")[:30] 
        
        # Drop NaNs for this specific metric
        analysis_data = pd.concat([X_coded, full_df[y_col]], axis=1).dropna()
        
        if analysis_data.empty:
            continue
            
        Y = analysis_data[y_col]
        X = analysis_data[X_coded.columns] 
        
        # -- Run OLS Regression --
        try:
            model = sm.OLS(Y, X).fit()
            
            results_df = pd.DataFrame({
                'Term': model.params.index,
                'Coefficient': model.params.values,
                # In 2-level factorial: Effect = 2 * Coeff
                'Effect_Size': model.params.values * 2, 
                'Std_Error': model.bse.values,
                't_Value': model.tvalues.values,
                'P_Value': model.pvalues.values
            })
            
            results_df = results_df[results_df['Term'] != 'const']
            
            # Categorize
            results_df['Type'] = results_df['Term'].apply(lambda x: 'Interaction' if ':' in x else 'Main Effect')
            
            # Rank by importance
            results_df['Importance_Score'] = results_df['t_Value'].abs()
            results_df = results_df.sort_values(by='Importance_Score', ascending=False)
            
            # Sig flag
            results_df['Significant'] = results_df['P_Value'] < 0.05
            
            sheets_to_save[short_sheet_name] = results_df

        except Exception as e:
            print(f"Failed to fit model for {clean_metric_name}: {e}")

    # --- 5. Save All Results ---
    print(f"\n========================================================")
    print(f"--- 5. Saving Full Factorial Results ---")
    print(f"========================================================")
    
    if not sheets_to_save:
        print("No results generated.")
        return

    try:
        with pd.ExcelWriter(RESULTS_FILE) as writer:
            # Summary sheet
            summary_rows = []
            
            for name, df in sheets_to_save.items():
                df.to_excel(writer, sheet_name=name, index=False, float_format="%.4f")
                
                top_3 = df.head(3)['Term'].tolist()
                summary_rows.append({
                    'Output': name,
                    '#1 Driver': top_3[0] if len(top_3) > 0 else '-',
                    '#2 Driver': top_3[1] if len(top_3) > 1 else '-',
                    '#3 Driver': top_3[2] if len(top_3) > 2 else '-'
                })
            
            pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"\nSuccessfully saved to '{RESULTS_FILE}'")
        
    except Exception as e:
        print(f"[ERROR] Failed to save Excel. {e}")

if __name__ == '__main__':
    analyze_full_factorial()