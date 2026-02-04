"""
Main execution script for running agent-based model simulations.

It is designed to automate the process of running multiple simulations 
for different experimental setups.

The script reads a range of configuration IDs from environment variables or a
settings file and then loops through them. For each ID, it loads the
corresponding configuration, initialises the model with those parameters, and
runs the simulation for a specified number of steps. It also handles logging
and provides progress feedback to the user in the console.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import os
import logging
from dotenv import load_dotenv
from logging import exception
load_dotenv()

from Model import Prototype_Model
from helpers.config import (
    settings,
    load_config_for_id,
    config_logging,
    get_output_path,
    output_conf,
    )
from modules.Heating_systems import init_param_table
import helpers.warnings_custom

try:
    import winsound
    usewin = True
except ImportError:
    usewin = False
    
config_id_start = os.getenv("AHOI_CONFIG_ID_START")
config_id_end = os.getenv("AHOI_CONFIG_ID_END")

if __name__ == "__main__":
    if config_id_start is None:
        config_id_start = settings.main.config_id_start
    if config_id_end is None:
        config_id_end = settings.main.config_id_end
    
    # Loop through each configuration ID and run the model with that configuration
    for config_id in range(int(config_id_start), int(config_id_end) + 1):
        load_config_for_id(config_id)  # Load settings for the current configuration ID
        
        runid = os.getenv("AHOI_MAIN_RUNID")
        if runid is None:
            runid = settings.main.run_id
        
        init_param_table()
        config_logging()
        
        """
        if settings.output.output_settings:
            output_conf() """
    
        # Initialize the model with the loaded parameters
        m = Prototype_Model(
            P=settings.main.number_of_plumbers,
            E=settings.main.number_of_energy_advisors,
            scenario=settings.main.current_scenario,
        )
        print(f"Running {settings.main.current_scenario}, prefix = {settings.main.files_prefix}, run_id = {runid},  config_id = {config_id}")
        # Run the model for the specified number of steps
    
        m.run(steps=settings.main.steps, run_id=runid, config_id = config_id)
        print("Simulation complete!")
        print(f"Collected data is located in {get_output_path(runid=runid, subfolder='pickles')}")
        print("Use the command 'python -m plotting.Build_plots' from the 'src' folder to plot the results")
        if settings.output.simplenames:
            try:
                runid = int(runid) + 1
            except:
                logging.getLogger("ahoi").warn("Could not increment run ID!")
    
    # Play a sound notification once all simulations are complete
    if usewin:
        winsound.PlaySound("SystemQuestion", winsound.SND_ALIAS)
    
