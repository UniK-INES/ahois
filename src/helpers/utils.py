"""
A collection of miscellaneous utility functions for the project.

This module provides various helper functions that support different parts of
the application. Responsibilities include dynamically loading classes,
generating standardized filenames for output data and images, converting
data formats, and implementing specific model-related calculations.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import importlib
import sys
import os
import pandas as pd
import itertools
from helpers.config import settings, get_output_path, config_logging
import glob
import logging

# Dynamically add the 'modules/' folder to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))  # Get the current directory (analysis folder)
modules_dir = os.path.join(current_dir, '..', 'modules')  # Construct the path to the modules folder
sys.path.append(os.path.abspath(modules_dir))  # Add the modules directory to sys.path

logger = logging.getLogger("ahoi.util")

def load_class(module_name, class_name):
    """
    This function imports a module by its string name and then retrieves a
    class from that module, also by its string name. This allows for flexible
    instantiation of objects based on configuration settings.

    Parameters
    ----------
    module_name : str
        The name of the module to import.
    class_name : str
        The name of the class to retrieve from the module.

    Returns
    -------
    class
        The requested class object.
    """
    module = importlib.import_module(module_name)
    class_ = getattr(module, class_name)
    return class_


files_name = " "
images_name = " "

def get_file_name(run_id: int = None) -> str:
    """
    This function creates a unique filename based on the project's
    configuration settings. The name can be a simple run ID or a more
    descriptive name including the scenario ID and random seeds, depending
    on the `settings.output.simplenames` flag.

    Parameters
    ----------
    run_id : int, optional
        The ID of the run. If not provided, the `run_id` from the global
        settings is used.

    Returns
    -------
    str
        The generated filename without an extension.
    """
    # Use the provided run_id or the one from settings
    run_id = run_id if run_id is not None else settings.main.run_id
    
    if settings.output.simplenames:
        return f"{run_id}"
    else:
        scenario_id = load_class('Scenario', settings.main.current_scenario).id
        seed_string = ''.join(map(str, settings.seeds.values()))
        return f"{settings.main.files_prefix}_{scenario_id}_{run_id}_{seed_string}"

def get_images_name(milieu: str = None) -> str:
    """
    Creates a unique name for an image based on the current run ID, file
    prefix, and scenario ID from the global settings. An optional 'milieu'
    string can be included to further specify the image content.

    Parameters
    ----------
    milieu : str, optional
        A string identifier to append to the image name, by default None.

    Returns
    -------
    str
        The generated image name without an extension.
    """
    scenario_id = load_class('Scenario', settings.main.current_scenario).id
    # Use milieu if provided, otherwise leave as base name
    images_name = f"{settings.main.run_id}_{settings.main.files_prefix}_{scenario_id}_{'_' + milieu if milieu else ''}"
    return images_name


def pickle_to_hdf5(resulttype="model"):
    """
    This function scans output directories for pickled pandas DataFrames based
    on a set of scenarios, run IDs, and file prefixes defined in the global
    settings. It reads each pickle file and stores its contents in a single
    HDF5 file, which is more efficient for querying and analysis.

    Parameters
    ----------
    resulttype : str, optional
        A string that is part of the pickle filename to identify the type
        of result to process (e.g., 'model' or 'agent'), by default "model".
    """
    scenarios=list(settings.scenario_comparison.scenarios)
    run_ids=settings.scenario_comparison.run_ids
    files_prefixes=settings.scenario_comparison.files_prefixes
    
    with pd.HDFStore(os.path.join(
            get_output_path(runid=run_ids[0], subfolder='hdf5'),
            settings.output.hdf5_filename)) as hdf:
        for scenario, run_id, files_prefix in itertools.product(scenarios, run_ids, files_prefixes):
                scenario_id = load_class("Scenario", scenario).id
                pickle_path = get_output_path(runid=run_id, subfolder='pickles')
                pattern = f"{pickle_path}/{resulttype}_df_{files_prefix}_{scenario_id}_{run_id}_*.pkl"
                model_files = glob.glob(pattern)
                
                for file in model_files:
                    try:
                        rseed_code = file.split("_")[-1][0:-4]
                        df = pd.read_pickle(file)
                        logger.info(f"Add DF for {files_prefix}_{rseed_code} to HDF5 store...")
                        hdf.put(key=files_prefix + "_" + rseed_code, value=df, format=settings.output.hdf5_format, data_columns=True)
                    except Exception as e:
                        print(f"Error reading {file}: {e}")


def influence_by_relative_agreement(source_system, target_system, exposure = 1):
    """
    This function models knowledge exchange between two houseowners related to a single system type. 
    It updates the parameters (opinion and uncertainty) of a `target_system` based on
    the parameters of a `source_system`. The update is governed by the overlap
    between their uncertainty intervals, and the strength of the influence is
    controlled by the `exposure` parameter. Based on Relative Agreement approach.

    Parameters
    ----------
    source_system : Heating_system
        The system that exerts influence.
    target_system : Heating_system
        The system that is being influenced. Its parameters will be modified
        in-place.
    exposure : float, optional
        A coefficient determining the strength of the influence, by default 1.
    """
    
    for key, value in target_system.params.items():
        # Relative agreement calculation
        o_target = value[0]
        o_source = source_system.params[key][0]
        u_target = value[1]
        u_source = source_system.params[key][1]

        v = min(o_target + u_target, o_source + u_source) - max(
            o_target - u_target, o_source - u_source
        )
        # Calculate kernel function
        # kernel = (v / u_source) - 1 if v > 0 else 0
        kernel = (v / (2 * u_source)) if v > 0 else 0
        if kernel > 0:  # Only update if kernel indicates convergence
            new_o = o_target + exposure * kernel * (o_source - o_target)
            new_u = u_target + exposure * kernel * (u_source - u_target)
            
            # Ensuring strictly positive values
            value[0] = max(new_o, 1e-6)
            value[1] = max(new_u, 1e-6)

    
if __name__ == '__main__':
    config_logging()                        
    pickle_to_hdf5()      
        