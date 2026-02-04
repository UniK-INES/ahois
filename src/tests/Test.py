"""
A script for miscellaneous testing, debugging, and data exploration.

This file serves as a "scratchpad" for developers to run quick, ad-hoc tests,
experiments, or data checks. It is not part of the formal, automated test
suite and contains several independent functions for different purposes.

These include:
- A simple Monte Carlo simulation function.
- Functions to test breakdown probabilities using a Weibull distribution.
- A utility to perform a detailed, column-by-column comparison of two
  simulation output DataFrames.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import numpy as np
import pandas as pd
from helpers.config import settings

systems = settings.heating_systems.list
systems_distr = [0.2, 0.7, 0.1, 0]

result = ["Failure", "Success"]
results_distr = [0.8, 0.2]


def monte_carlo(steps, lists, weights):
    """Performs a simple Monte Carlo simulation for a discrete choice.

    This function simulates a random choice from a list of outcomes a given
    number of times, where each choice is weighted by a corresponding
    probability. It then prints the frequency of each outcome.

    Parameters
    ----------
    steps : int
        The number of simulation trials to run.
    lists : list
        A list of the possible outcomes to choose from.
    weights : list
        A list of probabilities corresponding to the outcomes in `lists`.
    """
    statistics = dict.fromkeys(lists, 0)

    for i in range(0, steps):
        result = np.random.choice(lists, p=weights)
        for i in statistics:
            if i == result:
                statistics[i] += 1

    print(statistics)


# monte_carlo(1000, systems, systems_distr)


def breakdown_check(age):
    """
    Checks for a system breakdown based on a Weibull distribution.

    This function simulates whether a component of a certain `age` fails. The
    probability of failure is determined by a Weibull distribution with
    hardcoded scale and shape parameters.

    Parameters
    ----------
    age : int or float
        The current age of the component to be checked.

    Returns
    -------
    bool
        True if a breakdown occurs, False otherwise.
    """
    scale = 1387
    shape = 2.218
    if scale * np.random.weibull(shape) < age:
        breakdown = True
    else:
        breakdown = False
    return breakdown


def weibull_trial(trials):
    """
    Runs multiple breakdown checks to observe the failure frequency.

    This function calls `breakdown_check` repeatedly for a component of a
    fixed age to see how many times it fails over a large number of trials.

    Parameters
    ----------
    trials : int
        The number of breakdown checks to perform.
    """
    statistics = {True: 0, False: 0}

    for i in range(0, trials):
        result = breakdown_check(156)
        for i in statistics:
            if i == result:
                statistics[i] += 1

    print(statistics)


# weibull_trial(450)


def compare_runs():
    """
    Compares two agent DataFrame pickle files for differences.

    This utility function loads two specified `agent_df` pickle files and
    performs a deep, column-by-column comparison. It reports which columns are
    identical and which ones differ. It includes special logic to handle
    floating-point comparisons within a column of dictionaries. This is
    useful for debugging and verifying model determinism between runs.
    """
    df1 = pd.read_pickle(f"data/agent_df_Emissions_-20%_03_0_00000000.pkl")
    df2 = pd.read_pickle(f"data/agent_df_Emissions_-20%_03_1_00000000.pkl")

    columns_identical = (df1.columns == df2.columns).all()
    if not columns_identical:
        print("The DataFrames have different columns or column order.")

    for column in df1.columns:
        if column in df2.columns:
            # Check if the two columns are identical
            if column == "Attribute ratings":
                is_different = False
                for idx, (dict1, dict2) in enumerate(zip(df1[column], df2[column])):
                    if dict1 is None and dict2 is None:
                        continue

                    if not np.isclose(
                        list(dict1.values()), list(dict2.values()), rtol=1e-5, atol=1e-8
                    ).all():
                        is_different = True
                        break

                (
                    print(f"Column {column} differs.")
                    if is_different
                    else print(f"Column {column} is the same.")
                )

            elif not (df1[column].equals(df2[column])):
                print(f"Column {column} differs.")
            else:
                print(f"Column {column} is the same.")
        else:
            print(f"Column {column} is missing in one of the DataFrames.")

if __name__ == "__main__":
    compare_runs()
