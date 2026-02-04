"""
Generates settings files for sensitivity analysis (SA).

This script automates the setup for SA by performing the following steps:
1.  Loads a base settings file (`settings.xlsx`).
2.  Reads SA variables from `sa_variables.csv`.
3.  Checks the `SA_METHOD` variable ('sobol', 'morris', or 'lhs').
4.  Uses SALib or Scipy to generate parameter samples:
    - For 'sobol', it uses `saltelli.sample` (generating N*(2D+2) samples).
    - For 'morris', it uses `morris.sample` (generating N*(D+1) samples).
    - For 'lhs', it uses `scipy.stats.qmc` with Maximin optimization (generating N samples).
5.  Creates replicated parameter sets for stochasticity.
6.  Saves the final parameter sets to `settings_SOBOL.xlsx`, `settings_MORRIS.xlsx`
    or `settings_LHS.xlsx`.
7.  Saves a "parameter map" (e.g., `lhs_param_map.csv`) to the analysis
    folder to link run IDs to outputs for the analysis step.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
 
"""

import sys
import os
import pandas as pd
from SALib.sample import saltelli, morris
from pyDOE2 import ff2n
from scipy.stats import qmc
import numpy as np

current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
from helpers.config import settings

# --- CHOOSE YOUR ANALYSIS METHOD ---
# Options: 'sobol', 'morris', 'lhs', or 'full_factorial'
SA_METHOD = settings.experiments.sa_method
# -----------------------------------

# Define File Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(BASE_DIR)
SETTINGS_DIR = os.path.join(SRC_DIR, 'settings')
ANALYSIS_DIR = os.path.join(SRC_DIR, 'analysis')

# Input files
BASE_SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.xlsx')
SA_VARS_FILE = os.path.join(ANALYSIS_DIR, 'sa_variables.csv')

# Output files
SA_SETTINGS_FILE = os.path.join(SETTINGS_DIR, f'settings_{SA_METHOD.upper()}.xlsx')
SA_MAP_FILE = os.path.join(ANALYSIS_DIR, f'{SA_METHOD}_param_map.csv')

# --- Set SA Parameters ---

# Common parameters
N_REPLICATIONS = settings.experiments.sa_nreplications
SA_SAMPLING_SEED = settings.experiments.sa_seed

# Sobol/LHS parameters
# For Sobol: N_SAMPLES is the 'N' in N*(2D+2)
# For LHS: N_SAMPLES is the total number of design points (N)
N_SAMPLES = settings.experiments.sa_nsamples 

# Morris-specific parameters
N_TRAJECTORIES = settings.experiments.sa_ntrajectories  
NUM_LEVELS = settings.experiments.sa_nlevels        

# A list of all column names in the settings file that control randomness.
SEED_COLUMNS = [
    'network.scenario_id', 'seeds.model_init', 'seeds.model_run', 'seeds.house_init',
    'seeds.milieu_init', 'seeds.heating_init', 'seeds.information_source_run',
    'seeds.houseowner_run', 'seeds.plumber_run'
]

def generate_sa_settings():
    """
    Main function to manage the generation of the SA settings file.
    """
    print(f"--- Starting SA Settings Generation ---")
    print(f"--- Method Selected: {SA_METHOD.upper()} ---")

    try:
        base_settings_df = pd.read_excel(BASE_SETTINGS_FILE)
        if base_settings_df.empty:
            print(f"Error: Base settings file is empty: {BASE_SETTINGS_FILE}")
            return
        default_settings = base_settings_df.iloc[0].copy()

        sa_vars_df = pd.read_csv(SA_VARS_FILE)

        print(f"Successfully loaded base settings from: {BASE_SETTINGS_FILE}")
        print(f"Successfully loaded SA variables from: {SA_VARS_FILE}")
        print(f"Found {len(sa_vars_df)} variables for SA.")

    except FileNotFoundError as e:
        print(f"Error: File not found. {e}")
        print("\nPlease ensure your files are in the correct 'src/settings' and 'src/analysis' folders.")
        return
    except Exception as e:
        print(f"An error occurred while loading files: {e}")
        return

    # Define the SALib Problem ---
    problem = {
        'num_vars': len(sa_vars_df),
        'names': sa_vars_df['name'].tolist(),
        'bounds': sa_vars_df[['min', 'max']].values.tolist()
    }

    print("\nSALib Problem Definition:")
    print(problem)

    # --- Generate Parameter Samples (Method-Specific) ---
    np.random.seed(SA_SAMPLING_SEED)
    
    if SA_METHOD == 'sobol':
        print(f"\nGenerating Sobol (Saltelli) samples...")
        param_values = saltelli.sample(problem, N_SAMPLES, calc_second_order=False)
        num_base_runs = param_values.shape[0]
        print(f"Generated {num_base_runs} base Sobol samples.")

    elif SA_METHOD == 'morris':
        print(f"\nGenerating Morris samples...")
        param_values = morris.sample(problem, N=N_TRAJECTORIES, num_levels=NUM_LEVELS)
        num_base_runs = param_values.shape[0]
        print(f"Generated {num_base_runs} base Morris samples.")

    elif SA_METHOD == 'lhs':
        print(f"\nGenerating Maximin Latin Hypercube samples...")
        sampler = qmc.LatinHypercube(d=problem['num_vars'], optimization="random-cd", seed=SA_SAMPLING_SEED)
        sample_unit = sampler.random(n=N_SAMPLES)
        l_bounds = [b[0] for b in problem['bounds']]
        u_bounds = [b[1] for b in problem['bounds']]
        param_values = qmc.scale(sample_unit, l_bounds, u_bounds)
        num_base_runs = param_values.shape[0]
        print(f"Generated {num_base_runs} base Maximin LHS samples.")

    elif SA_METHOD == 'full_factorial':
        print(f"\nGenerating Full Factorial samples (2^k)...")
        num_vars = problem['num_vars']

        # Safety Check for Exponential Explosion
        if num_vars > 12:
            print(f"WARNING: You are requesting a Full Factorial for {num_vars} variables.")
            print(f"This requires 2^{num_vars} = {2**num_vars} base runs.")
            print("This may crash the computer or take forever to save. Exiting.")
            exit()

        # 1. Generate Design Matrix (2^k rows, k columns)
        # Returns matrix of -1.0 and 1.0
        design_matrix = ff2n(num_vars)

        # 2. Scale samples from [-1, 1] to [min, max]
        l_bounds = np.array([b[0] for b in problem['bounds']])
        u_bounds = np.array([b[1] for b in problem['bounds']])
        
        # Scaling formula: min + ((val + 1) / 2) * (max - min)
        param_values = l_bounds + (design_matrix + 1) / 2 * (u_bounds - l_bounds)

        num_base_runs = param_values.shape[0]
        print(f"Generated {num_base_runs} base Full Factorial samples.")
        print(f"(Design: 2^{num_vars} unique combinations)")
        
    else:
        print(f"Error: Unknown SA_METHOD: '{SA_METHOD}'.")
        return

    # --- Create the new SA Settings DataFrame ---
    new_settings_list = []
    sa_map_list = [] 
    sa_param_names = problem['names']

    available_seed_cols = [col for col in SEED_COLUMNS if col in default_settings.index]
    print(f"\nWill manage {len(available_seed_cols)} seed columns.")

    total_run_counter = 0

    # Outer loop for replications
    for r in range(N_REPLICATIONS):
        current_seed_value = r
        print(f"Generating sample set {r}/{N_REPLICATIONS - 1}...")

        # Inner loop for the parameter sets
        for i, param_set in enumerate(param_values):
            new_row = default_settings.copy()
            map_row = {} 

            if 'ID' in new_row:
                new_row['ID'] = total_run_counter
            
            if 'main.run_id' in new_row:
                 new_row['main.run_id'] = i
            
            map_row['Run_id'] = i
            map_row['Replication_Seed'] = current_seed_value

            for seed_col in available_seed_cols:
                new_row[seed_col] = current_seed_value
            
            new_row['experiments.sa_active'] = True

            for j, name in enumerate(sa_param_names):
                if name not in new_row:
                    continue

                new_val = param_set[j]
                var_type = sa_vars_df.loc[sa_vars_df['name'] == name, 'type'].values[0]

                if var_type == 'int':
                    new_val = int(round(new_val))
                elif var_type == 'float':
                    new_val = float(new_val)

                new_row[name] = new_val
                map_row[name] = new_val 

            new_settings_list.append(new_row)
            sa_map_list.append(map_row) 
            
            total_run_counter += 1

    # Create the final DataFrames
    sa_settings_df = pd.DataFrame(new_settings_list)
    sa_map_df = pd.DataFrame(sa_map_list)

    try:
        sa_settings_df = sa_settings_df[base_settings_df.columns]
    except KeyError:
        pass

    # Save the Output Files
    try:
        sa_settings_df.to_excel(SA_SETTINGS_FILE, index=False)
        print(f"\nSuccessfully generated: {SA_SETTINGS_FILE}")
        sa_map_df.to_csv(SA_MAP_FILE, index=False)
        print(f"Successfully generated: {SA_MAP_FILE}")
        
        print(f"\nTotal scenarios/rows created: {len(sa_settings_df)}")
        print(f"  ({num_base_runs} base samples x {N_REPLICATIONS} replications)")

    except Exception as e:
        print(f"\nError: Could not save the output file(s). {e}")

if __name__ == '__main__':
    generate_sa_settings()