"""
Create bash scripts for simulation on SLURM managed cluster,
transfer these scripts to the cluster and optionally execute them.

:Instructions:

- Define scenarios/parameter sets in excel scenario sheet, referenced by config ID
- execute main

:Authors: 

* Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>

"""

import os
import logging

from helpers.config import (
    settings, load_config_for_id, config_logging, 
    get_output_path,
    get_cluster_output_path
)
from experiments.slurm_script_generation import generate_script

logger = logging.getLogger("ahoi.cluster.batchscript")


def transferSlurmFiles(maxRunId):
    """
    Transfer files to cluster via SCP

    Parameters
    ----------
    maxRunID: int
        maximum run ID of this job set
    """
    sshstransfer = (
        "ssh "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + " \"mkdir -p "
        + get_cluster_output_path(
            runid=maxRunId, subfolder=settings.slurm.target_execfile
        )
        +"\""
    )

    if settings.slurm.transferSlurmFile:
        logger.info("Create directories for slurm files...")
        logger.debug("Statement: " + sshstransfer)
        os.system(sshstransfer)

    localTargetDirExecfile = os.path.join(
        get_output_path(runid=maxRunId, subfolder=settings.slurm.target_execfile)
    )
    scpstatement = (
        "scp -r "
        + os.path.expanduser(localTargetDirExecfile)
        + "/* "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + ":\""
        + get_cluster_output_path(
            runid=maxRunId, subfolder=settings.slurm.target_execfile
            )
        + "\""
    )
    logger.debug(scpstatement)
    if settings.slurm.transferSlurmFile:
        logger.debug("Transfer slurm files...")
        os.system(scpstatement)


def transferSettingsFile():
    """
    Transfer settings.toml
    """
    settings_filename = os.getenv("AHID_SETTINGS_FILE_FOR_DYNACONF")
    if not settings_filename:
        # if variable is not set, settings_filename will be None
        settings_filename = "settings_local_cluster.toml"
    scpsettings = (
        "scp "
        + os.path.dirname(os.path.realpath(__file__))
        + "/../settings/"
        + settings_filename
        + " "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + ":\""
        + settings.slurm.target_cluster_modelbase
        + "/settings/settings_local.toml"
        + "\""
    )
    logger.debug(scpsettings)
    if settings.slurm.transferSettingsFile:
        logger.info("Transfer settings file...")
        os.system(scpsettings)


def transferScenarioFile():
    """
    Transfer Scenario Config Excel File
    """

    sshCreateFolder = (
        "ssh "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + " \"mkdir -p "
        + settings.slurm.target_cluster_modelbase
        + os.path.dirname(settings.main.excel_scenario_file)
        + "\""
    )
    logger.debug(sshCreateFolder)
    if settings.slurm.transferScenarioExcelFile:
        logger.info("Create directories...")
        os.system(sshCreateFolder)

    scpsTransferFile = (
        "scp "
        + os.path.dirname(os.path.realpath(__file__))
        + "/../"
        + settings.main.excel_scenario_file
        + " "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + ":\""
        + settings.slurm.target_cluster_modelbase
        + settings.main.excel_scenario_file
        + "\""
    )
    logger.debug(scpsTransferFile)
    if settings.slurm.transferScenarioExcelFile:
        logger.info("Transfer scenario file...")
        os.system(scpsTransferFile)


def executeSlurmScript(execScriptFilename, maxRunId):
    """
    Execute slurm batch runs on cluster via SSH

    Parameters
    ----------
    execScriptFilename: str
        Script file to execute
    maxRunId: int
        maximum Run ID to enter correct folder
    """

    scriptfile = (
        get_cluster_output_path(
            runid=maxRunId, subfolder=settings.slurm.target_execfile
        )
        + "/"
        + execScriptFilename
    )

    sshstatement = (
        "ssh "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + " "
        + "\"bash -l -c 'cd "
        + get_cluster_output_path(
            runid=maxRunId, subfolder=settings.slurm.target_execfile
        )
        + "; "
        + "chmod u+x "
        + scriptfile
        + "; "
        + scriptfile
        +"'\""
    )
    logger.debug(sshstatement)
    if settings.slurm.executeSLURMscripts:
        logger.info("Execute slurm script on cluster (max runID: %d)...", maxRunId)
        logger.debug(sshstatement)
        os.system(sshstatement)



def generateAndTransfer():
    """
    Generates required files, transfers these to the cluster and executes the SLURM script on the cluster.
    In particular:

    * generate SLURM scripts
    * transfer SLURM scripts to cluster
    * transfer settings file to cluster
    * transfer scenario file to cluster
    * execute SLURM scripts on cluster

    Particular steps can be enabled/disabled by parameter settings (see below).

    Considered parameters:

    * settings.slurm.batchconfig_file
    * settings.slurm.batchconfig_sheetname
    * settings.slurm.batchconfig_rows
    * settings.slurm.editbatchConfigFile (default: True)
    * settings.slurm.generateSlurmFile (default: True)
    * settings.slurm.transferSlurmFile (default: True)
    * settings.slurm.transferSettingsFile (default: True)
    * settings.slurm.transferScenarioExcelFile (default: True)
    * settings.slurm.executeSLURMscripts (default: False)

    """
    logger.info("Generate and transfer...")
    
    
    logger.info("Running in BATCH mode (1:N config_id:run_id)")

    base_run_id = settings.main.run_id
    logger.info(f"Using dynamically loaded base run_id: {base_run_id} for all operations.")

    execScriptFilename = generate_script()
    transferSlurmFiles(base_run_id)
    transferSettingsFile()
    transferScenarioFile()
    executeSlurmScript(execScriptFilename, base_run_id)

    logger.info("Done.")

        
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    generateAndTransfer()