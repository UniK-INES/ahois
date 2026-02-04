"""
Generates heatmaps from a grid of simulation output files.

This script is a post-processing tool designed to visualise the results of a
parameter sweep across a two-dimensional parameter space (e.g., varying the
number of plumbers vs. energy advisors). It operates by scanning a directory
of pickle files, where the filename of each file encodes the coordinates of
that simulation run within the parameter grid.

The script performs two distinct analyses in sequence:
1.  **Replacements Analysis**: It processes `model_df` pickle files, extracts the
    total number of heating system replacements at specific time intervals
    (0, 5, 10, 15, and 20 years), and assembles this data into a matrix.
2.  **Heat Pump Adoption Analysis**: It processes `agent_df` pickle files, counts
    the number of agents who have adopted a `Heating_system_heat_pump` at the
    same time intervals, and assembles this data into a matrix.

For each analysis and time interval, it generates a heatmap image visualizing
the results across the parameter space and saves the underlying data matrix as
a CSV file.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import os
import pickle
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
from helpers.config import settings, get_output_path
from helpers.i18n import _


if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(__file__)
    # Define paths relative to the script location
    pickle_folder = get_output_path(runid=settings.main.config_id_start, subfolder='pickles')
    output_folder = os.path.join(script_dir, "../data/output/heatmaps")
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)
    
    # Directory containing the pickle files
    folder_path = get_output_path(runid=settings.main.config_id_start, subfolder='pickles')
    
    # Define year labels and corresponding rows
    year_labels = ["0 years", "5 years", "10 years", "15 years", "20 years"]
    row_indices = [0, 260, 520, 780, 1039]
    
    # Regular expression to extract x and y from the filename
    filename_pattern = re.compile(r"model_df_(\d+)-(\d+)_06_0_0_00000000\.pkl")
    
    # Initialize a dictionary to store matrices for each year
    results_matrices = {year: pd.DataFrame(index=range(1, 11), columns=range(1, 11)) for year in year_labels}
    
    # Process pickle files
    for file_name in os.listdir(pickle_folder):
        match = filename_pattern.match(file_name)
        if match:  # Process only files that match the pattern
            try:
                x, y = map(int, match.groups())  # Extract x and y as integers
                file_path = os.path.join(pickle_folder, file_name)
    
                # Load the pickle file
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
    
                # Check the loaded data
                print(f"Processing file: {file_name}")
                if isinstance(data, pd.DataFrame):
                    print(f"Loaded DataFrame with columns: {data.columns}")
                else:
                    print(f"File {file_name} did not contain a DataFrame.")
                    continue
    
                # Extract values for each year
                for i, row_index in enumerate(row_indices):
                    if row_index < len(data):  # Ensure the row exists
                        if "Replacements" in data.columns:
                            replacements_dict = data["Replacements"].iloc[row_index]
                            if isinstance(replacements_dict, dict):
                                value_sum = sum(replacements_dict.values())
                                results_matrices[year_labels[i]].loc[x, y] = value_sum
                            else:
                                print(f"Row {row_index} in {file_name} does not contain a dictionary.")
                        else:
                            print(f"'Replacements' column not found in {file_name}.")
            except Exception as e:
                print(f"Failed to process {file_name}: {e}")
    
    # Ensure all matrices have numeric values and replace NaNs with zeros
    for year in results_matrices:
        results_matrices[year] = results_matrices[year].apply(pd.to_numeric).fillna(0)
    
    # Generate and save heatmaps
    for year, matrix in results_matrices.items():
        data_array = matrix.values
        fig, ax = plt.subplots(figsize=(8, 8))  # Create a square figure
        heatmap = ax.imshow(data_array, cmap="coolwarm", aspect="equal")  # Ensure square cells
    
        # Add color bar
        cbar = plt.colorbar(heatmap, ax=ax)
        cbar.set_label(_("Sum of Replacements"), labelpad=10)
    
        # Add title and labels
        ax.set_title(_("Heatmap for {year}").format(year=year), pad=20)
        ax.set_xlabel(_("Advisors"), labelpad=10)
        ax.set_ylabel(_("Plumbers"), labelpad=10)
    
        # Set ticks and labels for both axes
        ax.set_xticks(np.arange(10))  # 10 columns
        ax.set_yticks(np.arange(10))  # 10 rows
        ax.set_xticklabels(range(1, 11))  # x-axis labels
        ax.set_yticklabels(range(1, 11))  # y-axis labels
    
        # Reverse the y-axis to align 1 with 1 at the bottom-left corner
        ax.invert_yaxis()
    
        # Remove excess space around the heatmap
        plt.tight_layout()
    
        # Save the heatmap as a PNG file
        heatmap_path = os.path.join(output_folder, f"heatmap_{year.replace(' ', '_')}.png")
        plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
        plt.close()
    
        # Save the matrix as a CSV file
        csv_path = os.path.join(output_folder, f"result_matrix_{year.replace(' ', '_')}.csv")
        matrix.to_csv(csv_path)
    
    print("Data processing and heatmap generation completed successfully.")
    
    """New method!!!"""
    # Define year labels and corresponding rows
    year_labels = ["0 years", "5 years", "10 years", "15 years", "20 years"]
    row_indices = [1, 261, 521, 781, 1040]  # Adjusted indices for steps starting at 1
    
    # Regular expression to extract x and y from the filename
    filename_pattern = re.compile(r"agent_df_(\d+)-(\d+)_06_0_00000000\.pkl")
    
    # Initialize a dictionary to store matrices for each year
    results_matrices = {year: pd.DataFrame(index=range(1, 11), columns=range(1, 11)) for year in year_labels}
    
    # Process pickle files
    for file_name in os.listdir(pickle_folder):
        match = filename_pattern.match(file_name)
        if match:  # Process only files that match the pattern
            try:
                x, y = map(int, match.groups())  # Extract x and y as integers
                file_path = os.path.join(pickle_folder, file_name)
    
                # Load the pickle file
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
    
                # Check the loaded data
                print(f"Processing file: {file_name}")
                if isinstance(data, pd.DataFrame):
                    print(f"Loaded DataFrame with MultiIndex: {data.index.names}")
                else:
                    print(f"File {file_name} did not contain a DataFrame.")
                    continue
    
                # Ensure MultiIndex and "Heating" column are present
                if isinstance(data.index, pd.MultiIndex) and "Heating" in data.columns:
                    # Group by the first level of the MultiIndex (Step)
                    heating_counts = (
                        data.groupby(level="Step")["Heating"]
                        .apply(lambda col: (col == "Heating_system_heat_pump").sum())
                    )
    
                    # Aggregate by the year labels (rows corresponding to steps)
                    for i, step in enumerate(row_indices):
                        if step in heating_counts.index:
                            heating_count = heating_counts.loc[step]
                            results_matrices[year_labels[i]].loc[x, y] = heating_count
                        else:
                            print(f"Step {step} not found in {file_name}")
                else:
                    print(f"File {file_name} does not have a MultiIndex or 'Heating' column.")
            except Exception as e:
                print(f"Failed to process {file_name}: {e}")
    
    # Ensure all matrices have numeric values and replace NaNs with zeros
    for year in results_matrices:
        results_matrices[year] = results_matrices[year].apply(pd.to_numeric).fillna(0)
    
    # Generate and save heatmaps
    for year, matrix in results_matrices.items():
        data_array = matrix.values
        fig, ax = plt.subplots(figsize=(8, 8))  # Create a square figure
        heatmap = ax.imshow(data_array, cmap="coolwarm", aspect="equal")  # Ensure square cells
    
        # Add color bar
        cbar = plt.colorbar(heatmap, ax=ax)
        cbar.set_label("Count of Heating_system_heat_pump", labelpad=10)
    
        # Add title and labels
        ax.set_title(_("Heatmap for {year}").format(year=year), pad=20)
        ax.set_xlabel(_("Advisors"), labelpad=10)
        ax.set_ylabel(_("Plumbers"), labelpad=10)
    
        # Set ticks and labels for both axes
        ax.set_xticks(np.arange(10))  # 10 columns
        ax.set_yticks(np.arange(10))  # 10 rows
        ax.set_xticklabels(range(1, 11))  # x-axis labels
        ax.set_yticklabels(range(1, 11))  # y-axis labels
    
        # Reverse the y-axis to align 1 with 1 at the bottom-left corner
        ax.invert_yaxis()
    
        # Remove excess space around the heatmap
        plt.tight_layout()
    
        # Save the heatmap as a PNG file
        heatmap_path = os.path.join(output_folder, f"heatmap_{year.replace(' ', '_')}.png")
        plt.savefig(heatmap_path, dpi=300, bbox_inches="tight")
        plt.close()
    
        # Save the matrix as a CSV file
        csv_path = os.path.join(output_folder, f"result_matrix_{year.replace(' ', '_')}.csv")
        matrix.to_csv(csv_path)
    
    print("Data processing and heatmap generation completed successfully.")
