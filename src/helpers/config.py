"""
Core configuration management for the project.

This module centralises all configuration handling using the Dynaconf library.
It loads settings from multiple sources, including default TOML files, local
overrides, and secrets. It also provides a custom loader to import specific
experimental scenarios from an Excel file based on a configuration ID.

Furthermore, it includes utility functions for:
- Saving the current configuration state to a file for reproducibility.
- Setting up a flexible logging system based on an external config file.
- Generating standardised, run-specific output paths for both local and
  remote (cluster) environments.

:Authors:
 - Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>
 - Ivan Digel <ivan.digel@uni-kassel.de>

"""
from dynaconf import Dynaconf
from dynaconf import inspect_settings
from dynaconf import loaders
from dynaconf.utils.boxing import DynaBox

try:
    from dynaconf.config import AHIDConfig
    stopeval = True
except ImportError:
    stopeval = False
    
import pandas as pd
import os
import logging.config
import pathlib
import datetime
import gitinfo
from helpers.information import get_git_version

current_directory = pathlib.Path(__file__).parent.absolute()
settings_filename = os.getenv("AHOI_SETTINGS_FILE_FOR_DYNACONF", default = "settings/settings_local.toml")

settings = Dynaconf(root_path=current_directory,
                    merge_enabled=True,
                    envvar_prefix="AHOI",
                    settings_files=["settings/settings.toml", settings_filename,
                                    "settings/.secrets.toml", "settings/constants.toml"],
                    includes=["config_post.toml"],)

output_path_task = None

logger = logging.getLogger("ahoi")

#Custom excel loader
def settings_loader(settings, filename, config_id, delimiter=","):
    """
    This function serves as a custom loader for Dynaconf. It reads a specified
    Excel file, finds the row matching the given `config_id`, and updates the
    `settings` object with the values from that row. String values containing
    the specified delimiter are automatically split into lists.

    Parameters
    ----------
    settings: Dynaconf
        The Dynaconf settings object to be updated.
    filename: str
        The path to the Excel scenario file.
    config_id: int
        The ID of the configuration row to load from the Excel file.
    delimiter: str, optional
        The delimiter used to split string values into lists, by default ",".
    """
    # Helper Function for Type Conversion
    def parse_value(item):
        """Try to convert string to int, then float, else return string."""
        cleaned_item = item.strip()
        try:
            return int(cleaned_item)
        except ValueError:
            pass
        try:
            return float(cleaned_item)
        except ValueError:
            pass
        return cleaned_item
    
    # Read the Excel file
    df = pd.read_excel(filename, sheet_name="Sheet1")
    
    # Filter the DataFrame for the specified config ID
    matching_rows = df[df['ID'] == config_id]
    
    # Check if any rows match the config_id
    if matching_rows.empty:
        raise ValueError(f"No configuration found for ID {config_id} in {filename}")
    
    # Proceed with loading the configuration data
    config_data = matching_rows.drop(columns=['ID']).to_dict(orient='records')[0]
    
    # Load each item
    for key, value in config_data.items():
        if isinstance(value, str) and delimiter in value:
            # 1. Split the string
            raw_list = value.split(delimiter)
            
            # 2. Parse each item using the helper function
            settings[key] = [parse_value(item) for item in raw_list if item.strip()]
            
        else:
            settings[key] = value

def load_config_for_id(config_id):
    """
    Loads a specific scenario configuration from the project's Excel file.
    This is a convenience wrapper around `settings_loader` that uses the
    scenario file path defined in the global settings.

    Parameters
    ----------
    config_id : int
        The ID of the configuration to load.
    """
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(base_dir, "../", settings.main.excel_scenario_file)
    settings_loader(settings, filename=filename, config_id=config_id)


def output_conf(settings_to_output=None):
    """
    Writes the current settings configuration and history to files.
    This function serialises the state of a Dynaconf settings object to disk,
    creating two files: one with the current configuration (including Git repo
    info) and another with the full settings history (how values were loaded
    and merged).

    Parameters
    ----------
    settings_to_output : Dynaconf, optional
        The settings object to output. If None, the global `settings`
        object is used, by default None.

    Other Parameters
    ----------------
    settings.output.output_settings_path : str
        The subfolder within the run's output path to save the files.
    settings.output.output_settings_filename : str
        The filename for the current settings dump.
    settings.output.output_settingshistory_filename : str
        The filename for the settings history dump.

    Notes
    -----
    The 'other parameters' are taken from the global
    settings object.


    """
    if settings_to_output is None:
        settings_to_output = settings

    if stopeval:
        AHIDConfig.evaluate = True
    data = settings_to_output.as_dict()
    data["repos"] = gitinfo.get_git_info()
    data["repos"]["version"] = get_git_version()
    loaders.write(
        os.path.join(
            get_output_path(subfolder=settings.output.output_settings_path),
            settings.output.output_settings_filename,
        ),
        DynaBox(data).to_dict(),
    )

    inspect_settings(
        settings_to_output,
        to_file=os.path.join(
            get_output_path(subfolder=settings.output.output_settings_path),
            settings.output.output_settingshistory_filename,
        ),
        dumper="json",
        key=settings.output.output_settingshistory_key,
    )
    if stopeval:
        AHIDConfig.evaluate = False
        
def stop_dynaconf_evaluation():
    """
    Disables Dynaconf's deep evaluation feature.
    This function is a performance optimisation. It disables the deep
    evaluation of settings values in Dynaconf after all necessary
    configurations have been loaded, which can prevent costly re-evaluations.
    """
    global stopeval    
    if stopeval:
        AHIDConfig.evaluate = False
        logger = logging.getLogger("ahoi")
        logger.warning("Set Dynaconf's AHIDConfig.evaluate to False!")

    
def config_logging():
    """
    Configures the project's logging system from a file.
    This function initialises the Python logging framework using a configuration
    file specified in the settings. It dynamically re-routes file handlers to
    write logs to run-specific files, ensuring that logs from different runs
    and modules are kept separate.
    """
    configfile=os.path.join(
            os.path.dirname(__file__), settings.logging.configfile
    )
    logfolder="logs"
    runidjobfolder=settings.main.run_id
        
    logging.config.fileConfig(configfile)
    os.makedirs(logfolder, exist_ok=True)

    for name in logging.root.manager.loggerDict:
        logger_to_redirect = logging.getLogger(name)
        numfilehandlers = 0
        for handler in logger_to_redirect.handlers:
            if handler.name is not None and "file" in handler.name:
                numfilehandlers += 1
                fhandler = handler

                postfix = "" if numfilehandlers < 2 else "_" + handler.name
                newhandler = logging.FileHandler(
                    os.path.join(
                        logfolder,
                        "ahoi" + str(runidjobfolder) + "_" + name + postfix + ".log",
                    ),
                    "w",
                )
                newhandler.setFormatter(fhandler.formatter)
                newhandler.setLevel(fhandler.level)
                logger_to_redirect.removeHandler(fhandler)
                logger_to_redirect.addHandler(newhandler)

    logger.info("Logging set up using config file " + configfile)
    
    
def get_output_path(
    runid=None,
    subfolder=None,
    task=None,
    createfolder=True,
):
    """
    Defines the output path for output data, logging, settings storage, slurm files.
    If not existing, the folder is created.

    Parameters
    ----------
    runid: int or string
        the run ID the output data is associated with. To refer to "RS" runs, the runid
        may be a string such as "RS0912".
    subfolder: str
        last part of the output folder
    createfolder: bool
        If True, the folder will be created if non-existent

    Other Parameters
    ----------------

    - settings.main.runid
    - settings.main.task
    - settings.main.output_path
    - settings.main.output_path_custom

    Returns
    -------
    str
        The absolute path to the designated output directory.
    """
    global output_path_task

    if runid is None:
        runid = settings.main.run_id
    if subfolder is None:
        subfolder = ""
    if task is None:
        task = settings.main.task

    if output_path_task != task:
        if not task and not task == "":
            task = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_path_task = task

    if not os.path.isabs(settings.main.output_path):
        opath = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                settings.main.output_path,
                task,
                str(runid),
            )
        )
    else:
        opath = os.path.abspath(
            os.path.join(
                settings.main.output_path,
                task,
                str(runid),
            )
        )

    output_path_sub = os.path.join(opath, subfolder)
    if createfolder:
        os.makedirs(output_path_sub, exist_ok=True)
    return output_path_sub

def get_cluster_output_path(
    runid=settings.main.run_id,
    subfolder=None,
):
    """
    Returns the output folder of output data, logging, settings storage, slurm files
    on the cluster

    Parameters
    ----------
    runid: int
        the run ID the output data is associated with
    subfolder: str
        last part of the output folder
    createfolder: bool
        If True, the folder will be created if non-existent

    Other Parameters
    ----------------

    - settings.slurm.target_cluster_mainpath
    - settings.main.project,
    - settings.main.task

    Returns
    -------

    str:
        cluster output path

    """

    if subfolder is None:
        subfolder = ""
        
    opath = os.path.join(
        settings.slurm.target_cluster_mainpath,
        settings.main.task,
        str(runid),
    )
    return str(pathlib.Path(os.path.join(opath, subfolder)).as_posix())


