"""
Main script for executing sensitivity analyses on model outputs.

This script serves as the primary entry point for running the sensitivity 
analyses defined in the `Analysis_modules.py` module. It imports the 
`Sensitivity_analysis` class and initialises it using configuration parameters
(scenarios, run IDs, file prefixes) loaded from the global settings object.

The script then executes a predefined sequence of analysis methods on the 
initialised object, such as t-tests and various sensitivity indices, printing
the results directly to the console.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
from helpers.config import settings
from analysis.Analysis_modules import Sensitivity_analysis


if __name__ == "__main__":
    sensitivity = Sensitivity_analysis(
        scenarios=settings.scenario_comparison.scenarios,
        run_ids=settings.scenario_comparison.run_ids,
        files_prefixes=settings.scenario_comparison.files_prefixes,
        agents_df=False,
    )
    
    print(f"Processing started!")
    print("----")
    sensitivity.t_test_paired(output="Scenario fulfilment", base_prefix="basic")
    sensitivity.FOFCSI(
        output="Scenario fulfilment",
        base_prefix="basic",
        test_prefix="price_-20%",
        variable="price",
    )
    sensitivity.SOFCSI(output="Scenario fulfilment", base_prefix="basic", variable="fuel")
    sensitivity.TOFCSI(output="Scenario fulfilment", base_prefix="basic")
    sensitivity.TOSI(output="Scenario fulfilment", base_prefix="basic")
    sensitivity.seed_variance(
        output="Scenario fulfilment",
        base_prefix="base_seeds",
        test_prefix="test_seeds",
    )
    
    print("----")
    print(f"Processing finished!")
