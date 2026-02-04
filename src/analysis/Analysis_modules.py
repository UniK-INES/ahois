"""
Provides a class for performing sensitivity analysis on simulation model outputs.

This module contains the Sensitivity_analysis class, which is designed to
load, merge, and analyse data from multiple simulation runs that were executed
with different scenarios and input parameters. It offers a suite of methods for
conducting various sensitivity analyses, including statistical tests (t-test),
variance analysis, and calculating sensitivity indices (FOFCSI, SOFCSI, etc.).

Note
----
This module is considered outdated and may not be compatible with the current
version of the model. Some methods may rely on data structures
that are no longer in use. Please use with caution.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import matplotlib.pyplot as plt
import statsmodels.api as sm
import numpy as np
import pandas as pd
import itertools
import os
import re
from helpers.utils import load_class
from helpers.config import settings
from scipy import stats


class Sensitivity_analysis:
    """
    A class to load simulation data and perform various sensitivity analyses.
    
    This class is initialised with a set of scenarios, run IDs, and file
    prefixes that define different experimental setups. It automatically finds
    and loads the corresponding pickled model and agent data into pandas
    DataFrames. The primary purpose is to provide methods to analyse the impact
    of input parameter changes on model outputs.

    Attributes
    ----------
    scenarios : list
        A list of scenario names being analysed.
    run_ids : list
        A list of run identifiers for the simulations.
    files_prefixes : list
        A list of file prefixes corresponding to different parameter sets.
    input_changes : pandas.DataFrame
        A DataFrame detailing the input parameter variations for each prefix.
    agents_df : pandas.DataFrame
        A merged DataFrame containing agent-level data from all specified runs.
    models_df : pandas.DataFrame
        A merged DataFrame containing model-level data from all specified runs.
    """

    def __init__(self, scenarios, run_ids, files_prefixes, agents_df=True):
        """
        Initialises the Sensitivity_analysis object by loading and merging data.

        This constructor iterates through all combinations of the provided
        scenarios, run IDs, and file prefixes. For each combination, it
        locates the corresponding agent and model output pickle files based on
        a naming convention, loads them into temporary DataFrames, and appends
        them to the main `agents_df` and `models_df` attributes.

        Parameters
        ----------
        scenarios : list
            A list of scenario name strings to be included in the analysis.
        run_ids : list
            A list of integer run identifiers.
        files_prefixes : list
            A list of strings, where each prefix identifies a unique
            experimental setup (e.g., 'baseline', 'param_A_high').
        agents_df : bool, optional
            If True, agent-level data is loaded. If False, it is skipped to
            save memory. Defaults to True.
        """
        self.scenarios = scenarios
        self.run_ids = run_ids
        self.files_prefixes = files_prefixes
        self.input_changes = self.read_input_changes()

        # Initialize empty DataFrames for agents and models
        if agents_df:
            self.agents_df = pd.DataFrame()
        self.models_df = pd.DataFrame()

        # Create all combinations of scenarios, run IDs and files prefixes
        for scenario, run_id, files_prefix in itertools.product(
            scenarios, run_ids, files_prefixes
        ):
            seeds_sequences = self.get_seeds_from_filenames(
                os.path.join("data", "pickles"),
                "agent_df",
                files_prefix,
                load_class("Scenario", scenario).id,
                run_id,
            )

            # Read the pickle files
            temp_agent_df = pd.DataFrame()
            temp_model_df = pd.DataFrame()

            for seeds_sequence in seeds_sequences:
                if agents_df:
                    new_temp_agent_df = pd.read_pickle(
                        f"data/agent_df_{files_prefix}_{load_class('Scenario', scenario).id}_{run_id}_{seeds_sequence}.pkl"
                    )
                    new_temp_agent_df["scenario"] = scenario
                    new_temp_agent_df["run_id"] = run_id
                    new_temp_agent_df["files_prefix"] = files_prefix
                    new_temp_agent_df["seeds_sequence"] = seeds_sequence

                    # Concatenate with the temporary model DataFrame
                    temp_agent_df = pd.concat(
                        [temp_agent_df, new_temp_agent_df], ignore_index=False
                    )

                # Read the model DataFrame
                new_temp_model_df = pd.read_pickle(
                    f"data/pickles/model_df_{files_prefix}_{load_class('Scenario', scenario).id}_{run_id}_{seeds_sequence}.pkl"
                )
                new_temp_model_df["scenario"] = scenario
                new_temp_model_df["run_id"] = run_id
                new_temp_model_df["files_prefix"] = files_prefix
                new_temp_model_df["seeds_sequence"] = seeds_sequence

                # Concatenate with the temporary model DataFrame
                temp_model_df = pd.concat(
                    [temp_model_df, new_temp_model_df], ignore_index=False
                )

                # Aggregate values from different milieus uncomment if needed
                # temp_model_df["Replacements"] = pd.DataFrame(temp_model_df["Replacements"].tolist()).sum(axis=1)
                # temp_model_df["Changes"] = pd.DataFrame(temp_model_df["Changes"].tolist()).sum(axis=1)

            # Append to the main DataFrames
            if agents_df:
                self.agents_df = pd.concat(
                    [self.agents_df, temp_agent_df], ignore_index=False
                )
            self.models_df = pd.concat(
                [self.models_df, temp_model_df], ignore_index=False
            )
        if agents_df:
            self.agents_df.drop(columns=["Attribute ratings"], inplace=True)

        if not os.path.exists("data/output/sensitivity_analysis"):
            os.makedirs("data/output/sensitivity_analysis")

    def get_seeds_from_filenames(
        self, directory, data_type, files_prefix, scenario_id, run_id
    ):
        """
        Extracts seed numbers from matching simulation output filenames.

        Constructs a regex pattern based on the provided parameters to find
        all output files for a specific experiment that differ only by seed.
        
        Parameters
        ----------
        directory : str
            The path to the directory to search for files.
        data_type : str
            The type of data file, e.g., 'agent_df' or 'model_df'.
        files_prefix : str
            The file prefix for the experimental setup.
        scenario_id : str
            The unique identifier for the scenario.
        run_id : int
            The run identifier.

        Returns
        -------
        list[str]
            A list of seed numbers extracted from the matching filenames.
        
        Raises
        ------
        FileNotFoundError
            If no files are found that match the constructed pattern.
        """
        pattern = rf"^{data_type}_{files_prefix}_{scenario_id}_{run_id}_\d+\.pkl$"
        matching_file_names = []
        result = []

        for filename in os.listdir(directory):
            if re.match(pattern, filename):
                matching_file_names.append(filename)

        if not matching_file_names:
            raise FileNotFoundError(f"No file found with the pattern: {pattern}")

        for matching_file_name in matching_file_names:
            element = matching_file_name.split("_")
            result.append(element[-1][: -len(".pkl")])

        return result

    def read_input_changes(self):
        """
        Reads the input parameter changes from a CSV file.

        This method loads a predefined CSV file ('data/input/input_changes.csv')
        that documents the specific input parameter values used for each
        experimental setup (identified by `files_prefix`).

        Returns
        -------
        pandas.DataFrame
            A DataFrame where the index contains variable names and the columns
            correspond to the `files_prefix` of different experiments.
        """
        file_name = os.path.join("data", "input", "input_changes.csv")

        return pd.read_csv(os.path.join(file_name), index_col="variable")

    def perform_all_methods(self, output, variables):
        """Placeholder method to sequentially run all analysis methods.
        
        Notes
        -----
        This method is not implemented.
        """
        ...

    def t_test_paired(self, output, base_prefix):
        """
        Performs a paired t-test between a base case and other setups.

        For each scenario, this method compares the mean of the specified `output`
        variable from the `base_prefix` runs against each of the other
        `files_prefixes`. The test uses data from the final simulation step.
        Results, including the t-statistic and p-value, are printed to the console.

        Parameters
        ----------
        output : str
            The column name in `models_df` of the dependent variable to test.
        base_prefix : str
            The file prefix representing the baseline or control group for comparison.
        """
        results = []
        for scenario in self.scenarios:
            # Filter the DataFrame for the current scenario and the last step
            scenario_df = self.models_df[
                (self.models_df["scenario"] == scenario)
                & (self.models_df.index == settings.main.steps - 1)
            ]

            # Gather all data for the base prefix
            base_df = scenario_df[scenario_df["files_prefix"] == base_prefix][output]

            # Compare each other file prefix against the base prefix
            for files_prefix in [fp for fp in self.files_prefixes if fp != base_prefix]:
                test_df = scenario_df[scenario_df["files_prefix"] == files_prefix][
                    output
                ]
                # Perform t-test if both DataFrames are non-empty
                if not base_df.empty and not test_df.empty:
                    stat, p_val = stats.ttest_rel(base_df, test_df)
                    results.append(
                        {
                            "scenario": scenario,
                            "base_prefix": base_prefix,
                            "test_prefix": files_prefix,
                            "t_statistic": stat,
                            "p_value": p_val,
                        }
                    )

        # Convert results to DataFrame for better visualization and handling
        results_df = pd.DataFrame(results)
        print("----")
        print("Results of paired t-test")
        print(results_df)
        print("----")

    def seed_variance(self, output, base_prefix, test_prefix):
        """
        Calculates the ratio of variance between two experimental setups.
        
        This method computes the variance of the `output` variable for a
        `base_prefix` and a `test_prefix` across different seeds and then
        calculates their ratio (test_var / base_var). This is useful for
        assessing how parameter changes affect model stability and output dispersion.
        The name contains a typo and should be "variance".

        Parameters
        ----------
        output : str
            The column name of the output variable to analyse.
        base_prefix : str
            The file prefix for the baseline setup.
        test_prefix : str
            The file prefix for the test setup to compare against the baseline.
        """

        # Filter the base and test DataFrames by 'files_prefix' and calculate the variance
        base_df = self.models_df[self.models_df["files_prefix"] == base_prefix][output]
        base_var = base_df.var()

        test_df = self.models_df[self.models_df["files_prefix"] == test_prefix][output]
        test_var = test_df.var()

        # Calculate the variance ratio
        variance_ratio = test_var / base_var

        # Create a dictionary to store the result
        result = {
            "output": output,
            "base_prefix": base_prefix,
            "test_prefix": test_prefix,
            "variance_ratio": variance_ratio,
        }

        # Convert the result into a DataFrame and transpose it for better visualization
        result_df = pd.DataFrame([result]).transpose()

        print("----")
        print("Results of the variance of the output")
        print(result_df)
        print("----")

    def FOFCSI(self, output, base_prefix, test_prefix, variable):
        """
        Calculates the First-Order Finite Change Sensitivity Index (FOFCSI).

        This method quantifies the sensitivity of a model `output` to a change
        in a single input `variable`. It is calculated as the ratio of the
        relative change in the output mean to the relative change in the input
        parameter's value between the `base_prefix` and `test_prefix` runs.

        Parameters
        ----------
        output : str
            The name of the output variable being analyzed.
        base_prefix : str
            The prefix for the baseline experiment.
        test_prefix : str
            The prefix for the experiment with the changed parameter value.
        variable : str
            The name of the input parameter that was changed.
        """
        results = []
        for scenario in self.scenarios:
            # Filter the DataFrame for the current scenario and the last step
            scenario_df = self.models_df[
                (self.models_df["scenario"] == scenario)
                & (self.models_df.index == settings.main.steps - 1)
            ]

            # Gather all data for the base prefix
            base_df = scenario_df[scenario_df["files_prefix"] == base_prefix][output]
            base_mean = base_df.mean()
            base_std = base_df.std()

            test_df = scenario_df[scenario_df["files_prefix"] == test_prefix][output]
            test_mean = test_df.mean()
            test_std = test_df.std()

            # Extract the change in the input parameter
            X_base = self.input_changes.loc[variable, base_prefix]
            delta_X = (
                self.input_changes.loc[variable, test_prefix]
                - self.input_changes.loc[variable, base_prefix]
            )

            # Calculate FOFCSI
            delta_Y = test_mean - base_mean
            FOFCSI_value = (delta_Y / base_mean) / (delta_X / X_base)

            # Calculate standard error for the difference in means
            n_base = len(base_df)
            n_test = len(test_df)
            SE = np.sqrt((base_std**2 / n_base) + (test_std**2 / n_test))

            # Compute the confidence interval (95% confidence level)
            t_value = stats.t.ppf(0.95, df=n_base + n_test - 2)
            CI_lower = FOFCSI_value - t_value * SE
            CI_upper = FOFCSI_value + t_value * SE

            # Append the results
            results.append(
                {
                    "scenario": scenario,
                    "base_prefix": base_prefix,
                    "test_prefix": test_prefix,
                    "variable": variable,
                    "FOFCSI": FOFCSI_value,
                    "CI_lower": CI_lower,
                    "CI_upper": CI_upper,
                }
            )
        results_df = pd.DataFrame(results).transpose()

        print("----")
        print("Results of the first order finite change sensitivity index")
        print(results_df)
        print("----")

    def SOFCSI(self, output, base_prefix, variable):
        """
        Calculates the Second-Order Finite Change Sensitivity Index (SOFCSI).

        This method assesses the sensitivity of an `output` to the interaction
        between two input parameters. It normalises the change in the output mean
        by the product of the relative changes in the two inputs, providing a
        measure of their combined effect.

        Parameters
        ----------
        output : str
            The name of the output variable being analysed.
        base_prefix : str
            The prefix for the baseline experiment.
        variable : str
            The name of one of the two input parameters involved in the interaction.
            The second parameter is inferred from the `test_prefix` name.
        """
        results = []
        test_prefixes = [
            col for col in self.input_changes.columns if col != base_prefix
        ]

        for scenario in self.scenarios:
            scenario_df = self.models_df[
                (self.models_df["scenario"] == scenario)
                & (self.models_df.index == settings.main.steps - 1)
            ]
            base_df = scenario_df[scenario_df["files_prefix"] == base_prefix][output]
            base_mean = base_df.mean()
            base_std = base_df.std()

            for test_prefix in test_prefixes:
                test_df = scenario_df[scenario_df["files_prefix"] == test_prefix][
                    output
                ]
                test_mean = test_df.mean()
                test_std = test_df.std()

                # Extract normalized changes for the variable of interest and the corresponding paired variable
                paired_variable = "_".join(
                    test_prefix.split("_")[:-1]
                )  # Extract a variable name from the prefix
                variables = [variable, paired_variable]
                delta_Xs = [
                    (
                        self.input_changes.loc[var, test_prefix]
                        - self.input_changes.loc[var, base_prefix]
                    )
                    / self.input_changes.loc[var, base_prefix]
                    for var in variables
                ]

                delta_X_product = np.prod(delta_Xs)

                # Calculate KOFCSI
                delta_Y = test_mean - base_mean
                KOFCSI_value = (delta_Y / base_mean) / delta_X_product

                # Calculate standard error and confidence interval
                n_base = len(base_df)
                n_test = len(test_df)
                SE = np.sqrt((base_std**2 / n_base) + (test_std**2 / n_test))
                t_value = stats.t.ppf(0.975, df=n_base + n_test - 2)
                CI_lower = KOFCSI_value - t_value * SE
                CI_upper = KOFCSI_value + t_value * SE

                results.append(
                    {
                        "scenario": scenario,
                        "base_prefix": base_prefix,
                        "test_prefix": test_prefix,
                        "variables": ", ".join(variables),
                        "KOFCSI": KOFCSI_value,
                        "CI_lower": CI_lower,
                        "CI_upper": CI_upper,
                    }
                )

        results_df = pd.DataFrame(results).transpose()
        print("----")
        print(
            f"Results of the 2nd order finite change sensitivity index for pairs of variables including {variable}"
        )
        print(results_df)
        print("----")
        return results_df

    def TOFCSI(self, output, base_prefix):
        """
        Calculates the Total-Order Finite Change Sensitivity Index (TOFCSI).

        This method measures the total effect on an `output` from changing all
        input parameters simultaneously in a given experimental setup (`test_prefix`)
        relative to the `base_prefix`.

        Parameters
        ----------
        output : str
            The name of the output variable being analysed.
        base_prefix : str
            The prefix for the baseline experiment.
        """
        results = []
        test_prefixes = [
            col for col in self.input_changes.columns if col != base_prefix
        ]

        for scenario in self.scenarios:
            scenario_df = self.models_df[
                (self.models_df["scenario"] == scenario)
                & (self.models_df.index == settings.main.steps - 1)
            ]
            base_df = scenario_df[scenario_df["files_prefix"] == base_prefix][output]
            base_mean = base_df.mean()
            base_std = base_df.std()

            for test_prefix in test_prefixes:
                test_df = scenario_df[scenario_df["files_prefix"] == test_prefix][
                    output
                ]
                test_mean = test_df.mean()
                test_std = test_df.std()

                # Extract normalized changes for the variable of interest and the corresponding paired variable
                delta_Xs = [
                    (
                        self.input_changes.loc[var, test_prefix]
                        - self.input_changes.loc[var, base_prefix]
                    )
                    / self.input_changes.loc[var, base_prefix]
                    for var in self.input_changes.index
                ]

                delta_X_product = np.prod(delta_Xs)

                # Calculate KOFCSI
                delta_Y = test_mean - base_mean
                TOFCSI_value = (
                    (delta_Y) / delta_X_product if delta_X_product != 0 else 0
                )

                # Calculate standard error and confidence interval
                n_base = len(base_df)
                n_test = len(test_df)
                SE = np.sqrt((base_std**2 / n_base) + (test_std**2 / n_test))
                t_value = stats.t.ppf(0.975, df=n_base + n_test - 2)
                CI_lower = TOFCSI_value - t_value * SE
                CI_upper = TOFCSI_value + t_value * SE

                results.append(
                    {
                        "scenario": scenario,
                        "base_prefix": base_prefix,
                        "test_prefix": test_prefix,
                        "TOFCSI": TOFCSI_value,
                        "CI_lower": CI_lower,
                        "CI_upper": CI_upper,
                    }
                )

        results_df = pd.DataFrame(results).transpose()
        print("----")
        print(f"Results of the total order finite change sensitivity index")
        print(results_df)
        print("----")
        return results_df

    def TOSI(self, output, base_prefix):
        """
        Calculates the Total Order Sensitivity Index (TOSI).

        Based on variance-based sensitivity analysis, this method estimates the
        total contribution of all input parameters to the variance of the model
        output. It is calculated as 1 minus the ratio of the conditioned
        variance to the total variance.

        Parameters
        ----------
        output : str
            The name of the output variable being analysed.
        base_prefix : str
            The prefix for the baseline experiment.
        """
        results = []
        for scenario in self.scenarios:
            scenario_df = self.models_df[
                (self.models_df["scenario"] == scenario)
                & (self.models_df.index == settings.main.steps - 1)
            ]
            base_df = scenario_df[scenario_df["files_prefix"] == base_prefix][output]
            base_var = base_df.var()
            conditional_variances = []

            for prefix in self.input_changes.columns.drop(base_prefix):
                test_df = scenario_df[scenario_df["files_prefix"] == prefix][output]
                test_var = test_df.var()
                conditional_variances.append(test_var)

            conditioned_variance = np.mean(conditional_variances)
            TOSI_value = 1 - (conditioned_variance / base_var)

            results.append(
                {"scenario": scenario, "base_prefix": base_prefix, "TOSI": TOSI_value}
            )

        results_df = pd.DataFrame(results).transpose()
        print("----")
        print(f"Results of the total order sensitivity index")
        print(results_df)
        print("----")
        return results_df

    def OLS_binary(self, output, base_prefix):
        """
        Performs Ordinary Least Squares (OLS) regression with a binary variable.

        This method quantifies the relationship between an experimental condition
        and a model `output`. It creates a binary independent variable (0 for
        `base_prefix` runs, 1 for other prefixes) and fits a linear model.
        The summary provides the magnitude, standard error, and statistical
        significance of the change.

        Parameters
        ----------
        output : str
            The dependent variable for the regression model.
        base_prefix : str
            The prefix representing the control group, which is coded as 0.
        """
        for scenario in self.scenarios:
            # Filter the DataFrame for the current scenario
            scenario_df = self.models_df[self.models_df["scenario"] == scenario].copy()

            # Limit to the last step
            scenario_df = scenario_df[
                scenario_df.index == settings.main.steps - 1
            ].copy()

            for files_prefix in [fp for fp in self.files_prefixes if fp != base_prefix]:
                # Create a binary independent variable where base_prefix is 0, others are 1
                scenario_df["is_base"] = (
                    scenario_df["files_prefix"] == base_prefix
                ).astype(int)

                # Filter to include only the current and base prefix
                filter_df = scenario_df[
                    scenario_df["files_prefix"].isin([base_prefix, files_prefix])
                ].dropna()

                # Prepare the dependent and independent variables for linear regression
                X = filter_df[["is_base"]]  # Independent variables
                y = filter_df[output]  # Dependent variable

                # Add a constant to the model (the intercept)
                X = sm.add_constant(X)

                # Fit the linear regression model using robust standard errors
                model = sm.OLS(y, X).fit(cov_type="HC3")

                print(
                    f"Comparison of {base_prefix} vs {files_prefix} in scenario {scenario}:"
                )
                print(model.summary())
