"""
Fetch result data back from cluster to local hard drive.

:Instructions:

- Define scenarios/parameter sets in settings_local.toml
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


def fetch_outputfiles_from_cluster(run_id: int = None):
    """
    Fetch output files from cluster via SCP

    Other Parameters
    ----------------

    - settings.slurm.fetch_pattern
    - settings.slurm.output_path
    - settings.slurm.host
    - settings.slurm.username
    - settings.merge_output.run_ids

    """
    if run_id is None:
        run_id = settings.main.run_id
        
    logger.info(
        f"Fetch pickle files from cluster for runID {run_id}..."
    )
    
    scpstatement = (
        "scp -r "
        + settings.slurm.username
        + "@"
        + settings.slurm.host
        + ":"
        + get_cluster_output_path(runid=run_id)
        + "/"
        + settings.slurm.fetch_pattern
        + " "
        + get_output_path(runid=run_id, subfolder=os.path.dirname(settings.slurm.fetch_pattern))
    )
    logger.debug(scpstatement)
    os.system(scpstatement)
            
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    for run_id in range(settings.slurm.fetch_runid_start, settings.slurm.fetch_runid_end + 1):
        fetch_outputfiles_from_cluster(run_id = run_id)

