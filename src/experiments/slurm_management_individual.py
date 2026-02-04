"""
Create bash scripts for simulation on SLURM managed cluster,
transfer these scripts to the cluster and optionally execute them.
Different version of slurm_management.py for 'individual_runs'.
- Aggregates all files into one TAR archive for a single transfer.
- Aggregates all execution commands into one Master Bash Script.

:Instructions:

- Define scenarios/parameter sets in excel scenario sheet, referenced by config ID
- execute main

:Authors: 

* Ivan Digel <ivan.digel@uni-kassel.de>


"""

import os
import logging
import subprocess
import sys
import shutil
import tarfile
import tempfile
import textwrap

from helpers.config import (
    settings, load_config_for_id, 
    get_output_path,
    get_cluster_output_path
)
from experiments.slurm_script_generation import generate_script

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ahoi.cluster.optimized")

def sanitize_path_for_linux(path_str):
    """Ensures paths work on Linux (forward slashes, $HOME)."""
    clean = path_str.replace("\\", "/")
    if clean.startswith("~"):
        clean = clean.replace("~", "${HOME}", 1)
    return clean

def transfer_packed_tarball(run_ids, staging_root):
    """
    Tars the local staging directory, transfers it ONCE, and extracts it on the cluster.
    """
    logger.info(f"Packing {len(run_ids)} run configurations into a single archive...")

    # 1. Create Tarball locally
    tar_filename = "payload_slurm.tar.gz"
    tar_path = os.path.join(staging_root, tar_filename)
    
    with tarfile.open(tar_path, "w:gz") as tar:
        # We add the CONTENTS of staging_root, not the root itself
        tar.add(staging_root, arcname=".", filter=lambda x: None if x.name.endswith(tar_filename) else x)

    # 2. Determine Remote Destination (The Task Root)
    # We need the parent of the run folders. 
    sample_run_id = run_ids[0]
    # Get the path to the execfile folder on cluster (e.g. .../task/run_id/slurm)
    sample_path = get_cluster_output_path(runid=sample_run_id, subfolder=settings.slurm.target_execfile)
    
    # We want to go up two levels: 
    # 1. Strip subfolder -> .../task/run_id
    # 2. Strip run_id -> .../task/
    remote_run_root = os.path.dirname(sample_path.rstrip("/\\"))
    remote_task_root = os.path.dirname(remote_run_root)
    
    remote_task_root = sanitize_path_for_linux(remote_task_root)
    remote_tar_dest = f"/tmp/{tar_filename}"

    # 3. SCP the Tarball (1 Connection)
    logger.info(f"Transferring archive ({os.path.getsize(tar_path)/1024:.1f} KB) to {remote_task_root}...")
    
    # Ensure remote task root exists before extracting
    subprocess.run(
        ["ssh", f"{settings.slurm.username}@{settings.slurm.host}", f"mkdir -p {remote_task_root}"],
        check=True
    )

    subprocess.run(
        ["scp", tar_path, f"{settings.slurm.username}@{settings.slurm.host}:{remote_tar_dest}"],
        check=True
    )

    # 4. SSH to Extract (1 Connection)
    cmd = (
        f"tar -xzf {remote_tar_dest} -C {remote_task_root} && "
        f"rm {remote_tar_dest}"
    )
    
    logger.info(f"Extracting archive on cluster...")
    subprocess.run(
        ["ssh", f"{settings.slurm.username}@{settings.slurm.host}", f"bash -l -c '{cmd}'"],
        check=True
    )

def execute_via_meta_script(script_details):
    """
    Generates one master bash script to submit all jobs locally on the cluster.
    """
    logger.info(f"Generating master execution script for {len(script_details)} jobs...")
    
    lines = [
        "#!/bin/bash",
        "echo 'Starting optimized bulk submission...'",
        ""
    ]

    for filename, run_id in script_details:
        # Resolve paths
        raw_path = get_cluster_output_path(runid=run_id, subfolder=settings.slurm.target_execfile)
        target_dir = sanitize_path_for_linux(raw_path)
        script_path = f"{target_dir}/{filename}"

        lines.append(textwrap.dedent(f"""
            # --- Run {run_id} ---
            if [ -f "{script_path}" ]; then
                cd "{target_dir}"
                dos2unix "{filename}" > /dev/null 2>&1
                chmod u+x "{filename}"
                # Execute the wrapper, which will submit the sbatch files
                bash "{filename}"
            else
                echo "ERROR: Script not found: {script_path}"
            fi
        """))
    
    lines.append("echo 'All jobs submitted.'")
    
    # Write locally
    meta_name = "master_submit.sh"
    with open(meta_name, "w", newline='\n') as f:
        f.write("\n".join(lines))
        
    # Transfer & Execute
    remote_dest = f"/tmp/{meta_name}"
    logger.info("Submitting master script to cluster...")
    
    subprocess.run(
        ["scp", meta_name, f"{settings.slurm.username}@{settings.slurm.host}:{remote_dest}"],
        check=True
    )
    
    subprocess.run(
        ["ssh", f"{settings.slurm.username}@{settings.slurm.host}", f"bash -l {remote_dest} && rm {remote_dest}"],
        check=True
    )
    
    if os.path.exists(meta_name):
        os.remove(meta_name)

def transferSettingsFile():
    settings_filename = os.getenv("AHID_SETTINGS_FILE_FOR_DYNACONF", "settings_local_cluster.toml")
    local_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../settings/", settings_filename)
    remote_path = f"{settings.slurm.target_cluster_modelbase}/settings/settings_local.toml"
    
    cmd = f"scp {local_path} {settings.slurm.username}@{settings.slurm.host}:\"{remote_path}\""
    if settings.slurm.transferSettingsFile:
        logger.info("Transferring settings file...")
        os.system(cmd)

def transferScenarioFile():
    local_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../", settings.main.excel_scenario_file)
    remote_path = f"{settings.slurm.target_cluster_modelbase}{settings.main.excel_scenario_file}"
    
    dir_cmd = f"ssh {settings.slurm.username}@{settings.slurm.host} \"mkdir -p $(dirname {remote_path})\""
    os.system(dir_cmd)
    
    scp_cmd = f"scp {local_path} {settings.slurm.username}@{settings.slurm.host}:\"{remote_path}\""
    if settings.slurm.transferScenarioExcelFile:
        logger.info("Transferring scenario file...")
        os.system(scp_cmd)

def generateAndTransferOptimized():
    logger.info("Starting OPTIMIZED Generate and Transfer...")

    if not settings.slurm.get("individual_runs", False):
        logger.error("This script is optimized for 'individual_runs = True' only.")
        return

    start_id = settings.main.config_id_start
    end_id = settings.main.config_id_end
    
    script_details = [] 
    run_ids_processed = []

    with tempfile.TemporaryDirectory() as staging_dir:
        logger.info(f"Created temporary staging area: {staging_dir}")
        logger.info(f"Step 1: Generating and Staging scripts ({start_id}-{end_id})...")
        
        for i, config_id in enumerate(range(start_id, end_id + 1)):
            sys.stdout.write(f"\rProcessing: {i+1}/{end_id-start_id+1}")
            sys.stdout.flush()

            logging.getLogger("ahoi").setLevel(logging.WARNING)
            load_config_for_id(config_id)
            logging.getLogger("ahoi").setLevel(logging.INFO)
            
            current_run_id = settings.main.run_id
            
            # 1. Generate the files (Wrapper + Batchfiles)
            # execScriptFilename is usually 'run_simulation.sh'
            execScriptFilename = generate_script(
                args=["-s", str(config_id), "-e", str(config_id), "-n", str(current_run_id)]
            )
            
            script_details.append((execScriptFilename, current_run_id))
            run_ids_processed.append(current_run_id)

            # --- STAGING STRATEGY (UPDATED) ---
            
            # A. Copy the Execution Wrapper (e.g. slurm/run_sim.sh)
            real_local_exec_dir = get_output_path(runid=current_run_id, subfolder=settings.slurm.target_execfile)
            real_exec_path = os.path.join(real_local_exec_dir, execScriptFilename)
            
            staging_exec_path = os.path.join(staging_dir, str(current_run_id), settings.slurm.target_execfile)
            os.makedirs(staging_exec_path, exist_ok=True)
            shutil.copy2(real_exec_path, staging_exec_path)

            # B. Copy the Batchfiles Folder (e.g. batchfiles/*.sh)
            # This was missing in the previous version!
            real_local_batch_dir = get_output_path(runid=current_run_id, subfolder=settings.slurm.target_batchfiles)
            
            staging_batch_path = os.path.join(staging_dir, str(current_run_id), settings.slurm.target_batchfiles)
            
            # Copy the whole directory (dirs_exist_ok=True allows merging if dirs are same)
            if os.path.exists(real_local_batch_dir):
                shutil.copytree(real_local_batch_dir, staging_batch_path, dirs_exist_ok=True)
            else:
                logger.warning(f"\nWarning: Batchfile dir not found locally: {real_local_batch_dir}")

        print("") # Newline
        logger.info("Generation and Staging complete.")

        logger.info("Step 2: Transferring shared files...")
        transferSettingsFile()
        transferScenarioFile()
        
        if settings.slurm.transferSlurmFile:
            transfer_packed_tarball(run_ids_processed, staging_dir)
        else:
            logger.info("Skipping SLURM file transfer (config setting).")

    if settings.slurm.executeSLURMscripts:
        logger.info("Step 3: Executing jobs...")
        execute_via_meta_script(script_details)
    else:
        logger.info("Skipping execution (config setting).")

    logger.info("Done.")

if __name__ == "__main__":
    generateAndTransferOptimized()