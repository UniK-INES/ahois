"""
Performs a Mann-Whitney U statistical test to compare model outputs.

This script is designed to assess the statistical significance of differences
in simulation outputs between two experimental scenarios (e.g., a baseline vs.
a policy intervention). It locates and loads pickled model DataFrames based on
a naming convention that includes the scenario, run ID, and an experiment prefix.

The script specifically extracts data on installation obstacles encountered 
by agents for various heating systems. 
It aggregates this data across multiple simulation seeds
for each of the two scenarios being compared. Finally, it performs a
non-parametric Mann-Whitney U test on the collected samples for each obstacle
and prints the p-values to the console.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import itertools
import glob
import pandas as pd
import pickle
from scipy.stats import mannwhitneyu
from helpers.utils import load_class
from helpers.config import settings, get_output_path


def perform_obstacle_significance_test(scenarios: list, 
                                       run_ids: list, 
                                       scenario1_prefix: str, 
                                       scenario2_prefix: str):
    """
    Compares obstacle data between two scenarios using the Mann-Whitney U test.

    This function handles the process of finding data, aggregating it, and
    running statistical tests.

    The workflow is as follows:
    1.  **Data Aggregation**: It iterates through the specified scenarios and
        run IDs, searching for output pickle files matching `scenario1_prefix`
        and `scenario2_prefix`. For each file found (representing one seed),
        it extracts the 'Obstacles' dictionary from the last time step. The
        obstacle values are collected into two main groups corresponding to the
        two prefixes.
    2.  **Statistical Testing**: After gathering data from all seeds, it
        iterates through each heating system and obstacle type. For each
        obstacle, it compares the sample of values from the first scenario
        against the sample from the second.
    3.  **Output**: A two-sided Mann-Whitney U test is performed. The resulting
        p-value is printed to the console, along with an interpretation of
        whether the difference is significant at the p < 0.05 level.

    Parameters
    ----------
    scenarios : list
        A list of scenario class name strings to analyse.
    run_ids : list
        A list of integer run IDs to include in the analysis.
    scenario1_prefix : str
        The file prefix for the first group, typically the baseline or
        control group (e.g., 'DEZ_Baseline').
    scenario2_prefix : str
        The file prefix for the second group, typically the treatment or
        campaign group (e.g., 'DEZ_Beraterkampagne').
    """
    # This nested dictionary will hold the raw data from each seed, ready for testing.
    data_for_test = {
        scenario1_prefix: {},
        scenario2_prefix: {}
    }

    print("--- Searching for pickle files... ---")
    for scenario, run_id, files_prefix in itertools.product(scenarios, run_ids, [scenario1_prefix, scenario2_prefix]):
        scenario_id = load_class("Scenario", scenario).id
        pickle_path = get_output_path(runid=run_id, subfolder='pickles')
        
        pattern = f"{pickle_path}/model_df_{files_prefix}_{scenario_id}_{run_id}_*.pkl"
        model_files = glob.glob(pattern)

        if not model_files:
            print(f"Warning: No files found for pattern: {pattern}")
            continue

        print(f"Found {len(model_files)} seed(s) for prefix '{files_prefix}'")

        for file in model_files:
            try:
                df = pd.read_pickle(file)
                obstacles_for_run = df["Obstacles"].iloc[-1]

                if not isinstance(obstacles_for_run, dict):
                    continue

                for hs_option, obstacles in obstacles_for_run.items():
                    if hs_option not in data_for_test[files_prefix]:
                        data_for_test[files_prefix][hs_option] = {}
                    
                    for obstacle_name, value in obstacles.items():
                        if obstacle_name not in data_for_test[files_prefix][hs_option]:
                            data_for_test[files_prefix][hs_option][obstacle_name] = []
                        data_for_test[files_prefix][hs_option][obstacle_name].append(value)

            except Exception as e:
                print(f"Error reading {file}: {e}")

    #Perform the statistical tests and print the results ---
    print("\n" + "="*80)
    print(f"STATISTICAL SIGNIFICANCE ANALYSIS: '{scenario1_prefix}' vs '{scenario2_prefix}'")
    print("="*80)

    key_mapping = {
        "Deciding": "Deciding", "Knowledge": "Knowing", "Affordability": "Can afford",
        "Riskiness": "Accepted", "Evaluation": "Like", "Feasibility": "Installed"
    }

    all_hs_options = set(data_for_test[scenario1_prefix].keys()) | set(data_for_test[scenario2_prefix].keys())

    for hs_option in sorted(list(all_hs_options)):
        print(f"\n--- Heating System: {hs_option} ---")

        if hs_option not in data_for_test[scenario1_prefix] or hs_option not in data_for_test[scenario2_prefix]:
            print(f"  Skipping: Data on {hs_option} not available for both scenarios.")
            continue

        group1_obstacles = data_for_test[scenario1_prefix][hs_option]
        group2_obstacles = data_for_test[scenario2_prefix][hs_option]
        all_obstacle_keys = set(group1_obstacles.keys()) | set(group2_obstacles.keys())

        for obstacle_key in sorted(list(all_obstacle_keys)):
            if obstacle_key == "Triggered": continue

            sample1 = group1_obstacles.get(obstacle_key, [])
            sample2 = group2_obstacles.get(obstacle_key, [])

            if not sample1 or not sample2: continue

            try:
                _, p_value = mannwhitneyu(sample1, sample2, alternative='two-sided')
                # Significance strings without the translation function
                significance = "Significant" if p_value < 0.05 else "Not Significant"
                obstacle_name = key_mapping.get(obstacle_key, obstacle_key)
                print(f"  - Obstacle: {obstacle_name:<12} | p-value: {p_value:.4f} ({significance})")
            except ValueError:
                obstacle_name = key_mapping.get(obstacle_key, obstacle_key)
                print(f"  - Obstacle: {obstacle_name:<12} | p-value: N/A (samples are identical)")
                
if __name__ == '__main__':
    # --- Configuration ---
    SCENARIOS_TO_ANALYZE = ["Scenario_mix_pellet_heat_pump"]
    RUN_IDS_TO_ANALYZE = [0]
    
    BASELINE_SCENARIO_PREFIX = "DEZ_Baseline"
    CAMPAIGN_SCENARIO_PREFIX = "DEZ_Beraterkampagne"

    # --- Run Analysis ---
    perform_obstacle_significance_test(
        scenarios=SCENARIOS_TO_ANALYZE,
        run_ids=RUN_IDS_TO_ANALYZE,
        scenario1_prefix=BASELINE_SCENARIO_PREFIX,
        scenario2_prefix=CAMPAIGN_SCENARIO_PREFIX
    )