"""
GP Sensitivity Visualizer

Description:
    Loads trained Gaussian Process models and generates detailed sensitivity visualizations:
    1. Interaction Heatmaps (S2 Indices) with a fixed color scale.
    2. Main Effect Plots (Partial Dependence) for every individual variable to check linearity.

Usage:
    Run this script in the same root folder where 'sa_variables.csv' and 
    the 'trained_metamodels' directory are located.
    
:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini
"""

import os
import sys
import glob
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from SALib.sample import saltelli
from SALib.analyze import sobol

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VARS_FILE = os.path.join(BASE_DIR, 'sa_variables.csv')
MODEL_DIR = os.path.join(BASE_DIR, 'trained_metamodels')
OUTPUT_DIR = os.path.join(BASE_DIR, 'visualisations')

# Heatmap Settings
HEATMAP_VMIN = 0.0
HEATMAP_VMAX = 0.3  # Fixed scale to compare across different outputs
CMAP = "viridis"     # Color scheme

# Analysis Settings
SOBOL_N = 4096       # Samples for heatmap generation (N * (2D + 2))
PLOT_POINTS = 100    # Resolution for the single variable line plots

def load_variables():
    """Loads variable names and bounds from CSV."""
    if not os.path.exists(VARS_FILE):
        print(f"Error: {VARS_FILE} not found.")
        sys.exit(1)
    
    df = pd.read_csv(VARS_FILE)
    names = df['name'].tolist()
    bounds = df[['min', 'max']].values.tolist()
    return names, bounds, df

def normalize_matrix(X, bounds):
    """
    Manually normalizes physical inputs to [0, 1] range.
    The GPs were trained on MinMaxScaled data.
    """
    X_norm = np.zeros_like(X)
    for i, (lower, upper) in enumerate(bounds):
        X_norm[:, i] = (X[:, i] - lower) / (upper - lower)
    return X_norm

def generate_heatmap(gp_model, problem, model_name, save_dir):
    """
    Generates synthetic data, runs Sobol Analysis, and plots S2 Interaction Matrix.
    """
    print(f"  > Calculating Interactions (S2)...")
    
    # 1. Generate Samples (Physical Units)
    X_phys = saltelli.sample(problem, SOBOL_N, calc_second_order=True)
    
    # 2. Normalize for GP Prediction [0, 1]
    X_norm = normalize_matrix(X_phys, problem['bounds'])
    
    # 3. Predict
    y_pred = gp_model.predict(X_norm, return_std=False)
    
    # 4. Analyze
    Si = sobol.analyze(problem, y_pred, calc_second_order=True, print_to_console=False)
    
    # 5. Extract S2 Matrix
    # SALib puts interactions in the upper triangle. The diagonal is NaN.
    s2_matrix = pd.DataFrame(Si['S2'], index=problem['names'], columns=problem['names'])
    
    # --- DEBUG: Print max value to console to verify 0.17 exists ---
    # Fills NaNs with -1 just for the max calculation to avoid errors
    max_val = np.nanmax(s2_matrix.values)
    print(f"    Max Interaction found: {max_val:.4f}") 

    # 6. Plotting
    plt.figure(figsize=(10, 8))
    
    # --- FIX IS HERE ---
    # Mask the LOWER triangle (tril) so the UPPER triangle (data) is visible
    # k=0 includes the diagonal in the mask (hiding the self-interaction which is NaN)
    mask = np.tril(np.ones_like(s2_matrix, dtype=bool), k=0)
    
    sns.heatmap(s2_matrix, 
                mask=mask,
                cmap=CMAP, 
                vmin=HEATMAP_VMIN, 
                vmax=HEATMAP_VMAX, 
                annot=False, 
                square=True,
                linewidths=.5,
                cbar_kws={"label": "Interaction Index (S2)"})
    
    plt.title(f"Interaction Matrix: {model_name}\n(Fixed Scale: {HEATMAP_VMIN}-{HEATMAP_VMAX})")
    plt.tight_layout()
    
    filename = f"{model_name}_Interaction_Heatmap.png"
    plt.savefig(os.path.join(save_dir, filename), dpi=300)
    plt.close()

def generate_main_effects(gp_model, names, bounds, model_name, save_dir):
    """
    Generates Partial Dependence Plots (Line charts) for every variable individually.
    Checks for linearity vs non-linearity.
    """
    print(f"  > Generating {len(names)} Single Sensitivity Plots...")
    
    plots_dir = os.path.join(save_dir, "Single_Variable_Plots")
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)
        
    # Create a base vector of Means (fix all variables to their average)
    means = np.mean(bounds, axis=1)
    
    for i, var_name in enumerate(names):
        # Prepare the grid for this specific variable
        # Row = sample, Col = variable
        X_grid_phys = np.tile(means, (PLOT_POINTS, 1))
        
        # Vary the current variable from Min to Max
        var_min, var_max = bounds[i]
        linspace = np.linspace(var_min, var_max, PLOT_POINTS)
        X_grid_phys[:, i] = linspace
        
        # Normalize
        X_grid_norm = normalize_matrix(X_grid_phys, bounds)
        
        # Predict with Uncertainty (Standard Deviation)
        y_mean, y_std = gp_model.predict(X_grid_norm, return_std=True)
        
        # Plot
        plt.figure(figsize=(7, 5))
        
        # Plot Mean Response
        plt.plot(linspace, y_mean, label='Mean Prediction', color='#2c3e50', linewidth=2)
        
        # Plot Confidence Interval (95% -> 1.96 std)
        plt.fill_between(linspace, 
                         y_mean - 1.96 * y_std, 
                         y_mean + 1.96 * y_std, 
                         alpha=0.2, 
                         color='#2c3e50',
                         label='95% Confidence')
        
        plt.xlabel(f"{var_name} (Input Value)")
        plt.ylabel("Model Output")
        plt.title(f"Main Effect: {var_name}\n(Output: {model_name})")
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.legend()
        
        # Save individual plot
        safe_var_name = var_name.replace("/", "_").replace(" ", "_")
        plt.savefig(os.path.join(plots_dir, f"{safe_var_name}.png"), dpi=150)
        plt.close()

def main():
    # 1. Setup
    print("--- Starting Visualization Pipeline ---")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    # 2. Load Metadata
    names, bounds, _ = load_variables()
    problem = {
        'num_vars': len(names),
        'names': names,
        'bounds': bounds
    }
    
    # 3. Find Models
    model_pattern = os.path.join(MODEL_DIR, "gp_*.pkl")
    model_files = glob.glob(model_pattern)
    
    if not model_files:
        print(f"No models found in {MODEL_DIR}")
        return

    print(f"Found {len(model_files)} trained models.")

    # 4. Iterate Models
    for model_path in model_files:
        try:
            # Extract clean name from filename
            # e.g., "gp_Scenario_fulfilment.pkl" -> "Scenario_fulfilment"
            filename = os.path.basename(model_path)
            model_name = filename.replace("gp_", "").replace(".pkl", "")
            
            print(f"\nProcessing: {model_name}")
            
            # Create subfolder for this output
            model_output_dir = os.path.join(OUTPUT_DIR, model_name)
            if not os.path.exists(model_output_dir):
                os.makedirs(model_output_dir)
            
            # Load the GP
            gp = joblib.load(model_path)
            
            # TASK A: Heatmap
            generate_heatmap(gp, problem, model_name, model_output_dir)
            
            # TASK B: Single Plots
            generate_main_effects(gp, names, bounds, model_name, model_output_dir)
            
        except Exception as e:
            print(f"Error processing {model_path}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n--- Done! Results saved to: {OUTPUT_DIR} ---")

if __name__ == "__main__":
    main()