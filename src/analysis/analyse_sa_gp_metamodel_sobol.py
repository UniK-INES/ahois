"""
Trains a Gaussian Process (GP) Metamodel on model outputs and performs 
Sobol' Sensitivity Analysis on the emulator.

Steps:
1.  Loads `lhs_param_map.csv` and `sa_variables.csv`.
2.  Gathers model outputs (handling nested dicts/stochasticity).
    -> Aggregates Stochastic seeds: Calculates MEAN of the 5 seeds per Run ID.
3.  Iterates through every output variable (columns in the gathered data):
    a. Trains a GP Regressor (Matern Kernel).
    b. Validates using 5-Fold Cross-Validation (Calculates Q2 score).
    c. If Q2 is good, generates 100,000 synthetic Sobol samples.
    d. Predicts outcomes using the GP.
    e. Calculates Sobol Indices (S1, ST).
4.  Saves results to `gp_sobol_results.xlsx`.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
"""

import sys
import os
import pandas as pd
import numpy as np
import glob
import joblib  # For saving the trained models
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel
from sklearn.model_selection import KFold
from sklearn.metrics import r2_score
from sklearn.preprocessing import MinMaxScaler
from SALib.sample import saltelli
from SALib.analyze import sobol

# Adjust path to find helper modules
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from helpers.config import settings, get_output_path

# --- CONSTANTS ---
ANALYSIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Note: Changing this to the LHS map we generated previously
PARAM_MAP_FILE = os.path.join(ANALYSIS_DIR, 'lhs_param_map.csv') 
VARS_FILE = os.path.join(ANALYSIS_DIR, 'sa_variables.csv')
RESULTS_FILE = os.path.join(ANALYSIS_DIR, 'gp_sobol_results.xlsx')
MODEL_SAVE_DIR = os.path.join(ANALYSIS_DIR, 'trained_metamodels')

# Analysis parameters
FILES_PREFIX = 'DEZ_Baseline'
SEED_SEQUENCE_LENGTH = 8

# GP Configuration
GP_RESTARTS = 10  # Number of optimizer restarts to find global optimum
SOBOL_N_SAMPLES = 4096  # N for Sobol (Total synthetic runs = N * (2D + 2))
MIN_Q2_THRESHOLD = 0.5  # Only run Sobol if Q2 (Predictivity) is above this

# --- OUTPUT VARIABLES (Same as Morris) ---
SCALAR_OUTPUTS = ['Scenario fulfilment']
DICT_OUTPUTS = [] #'Obstacles', 'Stage flows'
INITIAL_AGENT_COUNT = 514
DICT_PROCESSING_METHOD = {
    'Obstacles': 'survivorship',
    'Stage flows': 'distribution'
}


def flatten_nested_dict(root_name, data_dict):
    """
    Recursively flattens a 2-level dictionary into a single dictionary 
    with composite keys.

    Used to convert nested model outputs (e.g., {'Stage1': {'Success': 10}})
    into flat columns (e.g., 'Y_RootName__Stage1__Success') suitable for 
    DataFrame storage.

    Args:
        root_name (str): The prefix for the flattened keys (usually the variable name).
        data_dict (dict): The nested dictionary to flatten.

    Returns:
        dict: A flattened dictionary where keys are composite strings.
    """
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
    """
    Converts absolute counts of survivors to conditional pass rates (Survivorship).

    Logic:
    Calculates the probability of an agent passing from the previous stage 
    to the current stage. Rate = Count / Previous_Stage_Count.

    Args:
        root_dict (dict): Dictionary where keys are stages and values are agent counts.
        total_agents (int): The initial pool of agents (denominator for the first stage).

    Returns:
        dict: A dictionary of the same structure but with float rates (0.0 to 1.0) 
              instead of absolute integers.
    """
    converted_dict = {}
    for option_key, stages in root_dict.items():
        current_pool = total_agents
        option_rates = {}
        if isinstance(stages, dict):
            for stage_name, survivor_count in stages.items():
                if current_pool > 0:
                    rate = survivor_count / current_pool
                    current_pool = survivor_count
                else:
                    rate = 0.0
                if rate > 1.0: rate = 1.0
                option_rates[stage_name] = rate
        else:
            option_rates = stages
        converted_dict[option_key] = option_rates
    return converted_dict

def calculate_stage_distributions(root_dict):
    """
    Calculates the relative share (probability) of each outcome within its specific stage.

    Logic:
    Normalizes the values within a sub-dictionary so they sum to 1.0. 
    Useful for branching logic (e.g., of the 50 agents who reached Stage X, 
    30% took path A, 70% took path B).

    Args:
        root_dict (dict): Dictionary containing sub-dictionaries of absolute counts.

    Returns:
        dict: A dictionary where counts are replaced by their relative share 
              of the total volume in that specific stage.
    """
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


def load_and_process_data():
    """
    Loads raw model outputs, processes nested structures, and aggregates stochastic seeds.

    Steps:
    1. Reads `lhs_param_map.csv` to link Run IDs to Parameters.
    2. Iterates through every run, loading the corresponding pickle file.
    3. Extracts scalar outputs and processes dictionary outputs (using 
       `flatten_nested_dict` and conversion helpers).
    4. Aggregates stochastic replications: Groups by `Run_id` (unique parameter set)
       and calculates the Mean and Standard Deviation of the 5 random seeds.

    Returns:
        tuple: 
            - X (np.array): Matrix of input parameters (averaged over seeds).
            - Y_df (pd.DataFrame): DataFrame of output means (target variables).
            - param_names (list): List of parameter names.
            - sa_vars_df (pd.DataFrame): Metadata about variables (bounds, etc.).
    """
    print(f"--- 1. Loading and Processing Data ---")
    
    if not os.path.exists(PARAM_MAP_FILE):
        print(f"Error: Parameter map not found at {PARAM_MAP_FILE}")
        return None, None, None

    param_map_df = pd.read_csv(PARAM_MAP_FILE)
    sa_vars_df = pd.read_csv(VARS_FILE)
    
    # Identify parameter columns
    param_names = sa_vars_df['name'].tolist()
    
    # Store all raw extracted rows here
    raw_data_list = []
    
    print(f"Processing {len(param_map_df)} map rows...")

    for index, row in param_map_df.iterrows():
        run_id = int(row['Run_id'])
        seed = int(row['Replication_Seed'])
        
        # Base dict with inputs
        row_data = {col: row[col] for col in param_names}
        row_data['Run_id'] = run_id
        row_data['Replication_Seed'] = seed

        try:
            pickle_folder = get_output_path(runid=run_id, subfolder='pickles')
            seed_sequence = str(seed) * SEED_SEQUENCE_LENGTH
            search_pattern = os.path.join(pickle_folder, f"model_df_{FILES_PREFIX}_*_{seed_sequence}.pkl")
            files_found = glob.glob(search_pattern)

            if not files_found:
                continue # Skip missing
            
            output_df = pd.read_pickle(files_found[0])
            if output_df.empty:
                continue

            last_row = output_df.iloc[-1]

            # Process Scalars
            for var_name in SCALAR_OUTPUTS:
                if var_name in last_row:
                    row_data[f"Y_{var_name}"] = last_row[var_name]

            # Process Dicts
            for var_name in DICT_OUTPUTS:
                if var_name in last_row:
                    raw_dict = last_row[var_name]
                    method = DICT_PROCESSING_METHOD.get(var_name, 'raw')
                    
                    if method == 'survivorship':
                        proc_dict = convert_counts_to_rates(raw_dict, INITIAL_AGENT_COUNT)
                    elif method == 'distribution':
                        proc_dict = calculate_stage_distributions(raw_dict)
                    else:
                        proc_dict = raw_dict
                    
                    flat_data = flatten_nested_dict(var_name, proc_dict)
                    row_data.update(flat_data)
            
            raw_data_list.append(row_data)

        except Exception as e:
            continue

    if not raw_data_list:
        print("No valid data found.")
        return None, None, None

    # Convert to DF
    full_df = pd.DataFrame(raw_data_list)
    
    # --- AGGREGATION STEP ---
    # We group by 'Run_id' (which represents one unique parameter set)
    # and average the 5 random seeds.
    print(f"Aggregating {len(full_df)} raw runs into unique parameter sets...")
    
    # Columns to group by (all parameter columns + Run_id)
    group_cols = ['Run_id'] + param_names
    
    # Calculate Mean and Std
    df_grouped = full_df.groupby(group_cols)
    df_mean = df_grouped.mean().reset_index()
    df_std = df_grouped.std().reset_index() # Good to check noise levels later
    
    # Extract X (Parameters) and Y (Outputs)
    # Ensure X is sorted by Run_id to match Y
    df_mean = df_mean.sort_values('Run_id')
    
    X = df_mean[param_names].values
    Y_df = df_mean.drop(columns=group_cols + ['Replication_Seed'], errors='ignore')
    
    print(f"Final Training Set: {len(X)} unique samples.")
    return X, Y_df, param_names, sa_vars_df

def run_gp_and_sobol():
    """
    Main orchestration function for Metamodeling and Sensitivity Analysis.

    Workflow:
    1. Data Prep: Loads data and normalizes inputs (X) to [0, 1] using MinMaxScaler.
    2. Sampling: Generates a massive synthetic dataset using Saltelli sampling 
       (enabled for Second-Order indices).
    3. Loop: Iterates through every output variable in `Y_df`.
    4. Metamodeling:
       - Configures a robust Gaussian Process (Constant * Matern + WhiteKernel).
       - Performs 5-Fold Cross-Validation to calculate Q2 (Predictivity) and RMSE.
       - Skips analysis if Q2 < Threshold (model is invalid).
       - Fits the final GP on all data.
    5. Sensitivity Analysis (Sobol):
       - Uses the trained GP to predict outcomes for the synthetic dataset.
       - Calculates Sobol Indices (S1, ST, and S2).
    6. Filtering & Saving:
       - Filters Pairwise Interactions (S2) using a "Smart Threshold" (>1% variance).
       - Saves Main Effects and Significant Interactions to `gp_sobol_results.xlsx`.
    """
    INTERACTION_THRESHOLD = 0.01 
    
    X, Y_df, param_names, sa_vars_df = load_and_process_data()
    if X is None: 
        print("No X found, re-run the analysis")
        return

    # --- FIX 1: Normalize Inputs ---
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Setup Results Storage
    sobol_results_list = []
    validation_results_list = []
    
    # Setup SALib Problem
    problem = {
        'num_vars': len(param_names),
        'names': param_names,
        'bounds': sa_vars_df[['min', 'max']].values.tolist()
    }
    
    # --- Generate Synthetic Inputs with Second Order ---
    print(f"\nGenerating synthetic inputs for Sobol analysis (2nd Order Enabled)...")
    
    X_synthetic_raw = saltelli.sample(problem, SOBOL_N_SAMPLES, calc_second_order=True)
    
    # Scaling logic (Raw Bounds -> 0..1)
    bounds = np.array(problem['bounds'])
    lower_bounds = bounds[:, 0]
    upper_bounds = bounds[:, 1]
    X_synthetic_scaled = (X_synthetic_raw - lower_bounds) / (upper_bounds - lower_bounds)

    if not os.path.exists(MODEL_SAVE_DIR):
        os.makedirs(MODEL_SAVE_DIR)

    # --- LOOP OVER OUTPUTS ---
    output_cols = [c for c in Y_df.columns if c.startswith('Y_')]
    print(f"\n--- Starting Metamodeling Loop for {len(output_cols)} variables ---")

    for target_col in output_cols:
        y = Y_df[target_col].values
        
        # Diagnostics
        global_variance = np.var(y)
        print(f"\n>> Analyzing: {target_col}")
        print(f"   Range: {np.min(y):.2f} to {np.max(y):.2f}")
        print(f"   Global Variance: {global_variance:.4f}")
        
        if global_variance < 1e-6:
            print(f"   Skipping: Variance is approx 0.")
            continue

        # --- Robust Kernel Setup ---
        k_matern = Matern(length_scale=np.ones(X.shape[1]), 
                          length_scale_bounds=(1e-2, 1e2), nu=2.5)
        k_constant = ConstantKernel(constant_value=1.0, constant_value_bounds=(1e-3, 1e3))
        k_white = WhiteKernel(noise_level=1.0, noise_level_bounds=(1e-5, 1e1)) #Option: 1e2
        
        kernel = k_constant * k_matern + k_white
        
        #n_restarts_optimizer=50
        gp = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=15, normalize_y=True)

        # Cross-Validation
        kf = KFold(n_splits=5, shuffle=True, random_state=42)
        y_preds_cv = np.zeros_like(y)
        
        for train_index, test_index in kf.split(X_scaled):
            X_train, X_test = X_scaled[train_index], X_scaled[test_index]
            y_train, y_test = y[train_index], y[test_index]
            
            gp_cv = GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5, normalize_y=True)
            gp_cv.fit(X_train, y_train)
            y_preds_cv[test_index], _ = gp_cv.predict(X_test, return_std=True)

        q2 = r2_score(y, y_preds_cv)
        rmse = np.sqrt(np.mean((y - y_preds_cv)**2))
        
        print(f"   Q2 Score: {q2:.4f}")
        
        validation_results_list.append({
            'Variable': target_col,
            'Q2_Score': q2,
            'RMSE': rmse
        })

        if q2 < MIN_Q2_THRESHOLD:
            print("   [!] Q2 too low. Model failed to capture trend.")
            continue

        # Train Final Model
        gp.fit(X_scaled, y)
        clean_name = target_col.replace("Y_", "").replace(" ", "_")[:50]
        joblib.dump(gp, os.path.join(MODEL_SAVE_DIR, f"gp_{clean_name}.pkl"))

        # --- Run Sobol on Emulator ---
        print("   Running Sobol prediction on emulator...")
        y_synthetic_pred = gp.predict(X_synthetic_scaled, return_std=False)
        
        # ENABLE interactions here
        Si = sobol.analyze(problem, y_synthetic_pred, print_to_console=False, calc_second_order=True)
        
        # --- Store Results ---
        
        # 1. Main Effects
        for i, name in enumerate(problem['names']):
            sobol_results_list.append({
                'Type': 'Main_Effect',
                'Output_Variable': target_col,
                'Parameter_1': name,
                'Parameter_2': '-',
                'Score': Si['S1'][i],
                'Total_Score': Si['ST'][i],
                'Conf': Si['ST_conf'][i],
                'Model_Q2': q2
            })
            
        # 2. Interactions (Filtered by Threshold)
        # S2 is a square matrix. We iterate the upper triangle (j > i)
        for i in range(len(param_names)):
            for j in range(i + 1, len(param_names)):
                s2_val = Si['S2'][i][j]
                
                if s2_val > INTERACTION_THRESHOLD:
                    sobol_results_list.append({
                        'Type': 'Interaction',
                        'Output_Variable': target_col,
                        'Parameter_1': param_names[i],
                        'Parameter_2': param_names[j],
                        'Score': s2_val,
                        'Total_Score': '-', # Not applicable for pairs
                        'Conf': Si['S2_conf'][i][j],
                        'Model_Q2': q2
                    })

    # --- SAVE TO EXCEL ---
    print(f"\n--- Saving Results ---")
    if sobol_results_list:
        df_sobol = pd.DataFrame(sobol_results_list)
        df_valid = pd.DataFrame(validation_results_list)
        
        # Reorder columns for readability
        cols = ['Type', 'Output_Variable', 'Parameter_1', 'Parameter_2', 'Score', 'Total_Score', 'Conf', 'Model_Q2']
        # Filter to only existing columns (in case some are missing in early iterations)
        existing_cols = [c for c in cols if c in df_sobol.columns]
        df_sobol = df_sobol[existing_cols]

        with pd.ExcelWriter(RESULTS_FILE) as writer:
            df_sobol.to_excel(writer, sheet_name='Sobol_Indices', index=False)
            df_valid.to_excel(writer, sheet_name='Validation_Scores', index=False)
            
        print(f"Saved results to {RESULTS_FILE}")
    else:
        print("No results generated.")

if __name__ == '__main__':
    run_gp_and_sobol()