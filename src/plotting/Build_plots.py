"""
Main entry point for generating plots and visualisations from simulation results.

This script serves as the primary runner for post-processing and plotting. 
It operates in one of two main modes, depending on the configuration settings. 
It is designed to iterate through a range of configuration IDs, loading the
appropriate settings for each and generating the corresponding output.

Modes of Operation:
- **Single-Run Analysis**: When `settings.scenario_comparison.active` is `False`,
  this script instantiates the `Plots` class to generate a comprehensive set
  of visualisations for a single simulation run.
- **Comparative Analysis**: When `settings.scenario_comparison.active` is `True`,
  it uses the `Scenario_comparator` class to create plots that compare
  results across multiple scenarios or simulation runs. To improve performance,
  it caches the processed `Scenario_comparator` object in a pickle file,
  avoiding redundant data loading and processing on subsequent executions.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
from plotting.Plots import Plots
from plotting.Scenario_comparator import Scenario_comparator
import matplotlib.pyplot as plt
from helpers.config import settings, config_logging, load_config_for_id
import time
import os
import dill as pickle
import yaml
import logging
import hashlib

config_logging()

try:
    import winsound
    usewin = True
except ImportError:
    usewin = False
from helpers.config import settings, get_output_path

if __name__ == "__main__":
    logger = logging.getLogger("ahoi.plot")
    
    for config_id in range(settings.main.config_id_start, settings.main.config_id_end + 1):
        load_config_for_id(config_id)  # Load settings for the current configuration ID
        if not settings.scenario_comparison.active:
            plots = Plots(run_id = settings.main.run_id)
            start = time.time()
            print("The plots are being drawn now!")
            
            if settings.eval.process_all_outputs:
                plots.process_all_outputs()
            if settings.eval.analyze_obstacles:
                plots.analyze_obstacles()
            if settings.eval.analyze_obstacles_by_period:
                plots.analyze_obstacles_by_period()
            if settings.eval.individual_plots_by_ids:
                plots.individual_plots_by_ids(ids=[id for id in range(215, 216)])
            end = time.time()
            print(f"It took {round(end - start)} seconds to build all plots.")
            print(f"Processing finished! You will find the results in the {plots.outpath} folder")
        
        if settings.scenario_comparison.active:
            start_time = time.time()
            prefixes = f"scenario_comparator_{'-'.join(settings.scenario_comparison.files_prefixes)}_"
            if len(prefixes) >= 200:
                prefixes = "long_name_" + hashlib.md5(prefixes.encode()).hexdigest()[:8]
            picklefile = f"{get_output_path(runid=settings.main.run_id, subfolder='postprocessed')}/" + \
                         prefixes + \
                         f"{'-'.join([str(i) for i in settings.scenario_comparison.run_ids])}.pkl"
            if not os.path.exists(picklefile):
                comparator = Scenario_comparator(
                            scenarios=settings.scenario_comparison.scenarios,
                            run_ids=settings.scenario_comparison.run_ids,
                            files_prefixes=settings.scenario_comparison.files_prefixes,
                        )
                with open(picklefile, 'wb') as outp:
                    pickle.dump(comparator, outp, pickle.HIGHEST_PROTOCOL)
                
            else:
                with open(picklefile, 'rb') as inp:
                    comparator = pickle.load(inp)
                with open(settings.data.plt_settings, "r") as configfile:
                    config = yaml.safe_load(configfile)
                
                logger.info(f"Consider {picklefile}")
                    
                if "Layout" in config:
                    plt.rcParams.update(config["Layout"])
                else:
                    raise ValueError("Invalid plotting configuration file: 'Layout' section missing.")
            
            
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Scenario_comparator initialization took {elapsed_time:.2f} seconds")
        
            start_time = time.time()
            print("The plots are being built now!")
            comparator.process_all_outputs()
            comparator.make_output_table()
            print(
                f"Comparison finished! You will find the results in the 'scenario_comparison' folder"
            )
            end_time = time.time()
            elapsed_time = end_time - start_time
            print(f"Scenario_comparator output processing took {elapsed_time:.2f} seconds")
            break
    
    if usewin:
        winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)
