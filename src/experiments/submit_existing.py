"""
Tries to submit existing scripts in the cluster, if there are any.
Needs the config_id ranges in settings.toml to define which scripts to look for and run.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Enhanced by Gemini

"""

import os
import logging
import subprocess
import sys
import textwrap
import pandas as pd

# Import from your existing codebase
from helpers.config import (
    settings, 
    get_cluster_output_path
)

# --- CONFIGURATION ---
EXCEL_COL_CONFIG_ID = "ID"
EXCEL_COL_RUN_ID = "main.run_id"
# ---------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger("ahoi.cluster.submit_existing")

def get_excel_path():
    filename = settings.main.excel_scenario_file
    if os.path.isabs(filename) and os.path.exists(filename):
        return filename
    base_dir = os.path.dirname(os.path.realpath(__file__))
    candidate_1 = os.path.normpath(os.path.join(base_dir, "..", filename))
    if os.path.exists(candidate_1):
        return candidate_1
    if os.path.exists(filename):
        return os.path.abspath(filename)
    logger.error(f"Could not find Excel file '{filename}'.")
    sys.exit(1)

def preload_run_id_map(start_id, end_id):
    excel_path = get_excel_path()
    logger.info(f"Reading Excel map from: {excel_path}")
    try:
        if excel_path.endswith('.csv'):
            df = pd.read_csv(excel_path)
        else:
            df = pd.read_excel(excel_path)
        df.columns = df.columns.str.strip()
        
        if EXCEL_COL_CONFIG_ID not in df.columns or EXCEL_COL_RUN_ID not in df.columns:
            logger.error(f"Missing columns. Found: {df.columns.tolist()}")
            sys.exit(1)

        mask = (df[EXCEL_COL_CONFIG_ID] >= start_id) & (df[EXCEL_COL_CONFIG_ID] <= end_id)
        filtered_df = df.loc[mask]
        
        return dict(zip(
            filtered_df[EXCEL_COL_CONFIG_ID], 
            filtered_df[EXCEL_COL_RUN_ID].astype(int)
        ))
    except Exception as e:
        logger.error(f"Failed to read scenario file: {e}")
        sys.exit(1)

def sanitize_path_for_linux(path_str):
    """
    Converts Windows paths and Tildes to Linux-friendly format.
    Example: '~\ahoi\0' -> '$HOME/ahoi/0'
    """
    # 1. Replace backslashes with forward slashes (Windows fix)
    clean = path_str.replace("\\", "/")
    
    # 2. Replace tilde with $HOME (Bash quote fix)
    # Note: We use ${HOME} to be safe in all contexts
    if clean.startswith("~"):
        clean = clean.replace("~", "${HOME}", 1)
        
    return clean

def generate_bulk_submission_script(start_id, end_id, meta_script_name="bulk_submit_generated.sh"):
    
    run_id_map = preload_run_id_map(start_id, end_id)
    total_configs = end_id - start_id + 1
    logger.info(f"Generating logic for {total_configs} configs...")

    lines = [
        "#!/bin/bash",
        "echo 'Starting bulk submission...'",
        ""
    ]

    count = 0

    for config_id in range(start_id, end_id + 1):
        
        if config_id not in run_id_map:
            continue
            
        current_run_id = run_id_map[config_id]
        
        # 1. Get Standard Path (and sanitize it)
        settings.main.run_id = current_run_id
        raw_path_standard = get_cluster_output_path(runid=current_run_id, subfolder="")
        path_standard = sanitize_path_for_linux(raw_path_standard)
        
        # 2. Get Hardcoded Path (and sanitize it)
        path_hardcoded = f"${{HOME}}/ahoi/{current_run_id}"
        
        # We inject the {config_id} directly into the 'find' command.
        # It looks for:
        #   1. sbatchScript_AHOI_123.sh  (Standard ID)
        #   2. sbatchScript_AHOI_123-123.sh (Range format)
        bash_block = textwrap.dedent(f"""
            # --- Config {config_id} -> Run {current_run_id} ---
            TARGET_DIR="{path_hardcoded}"
            if [ ! -d "$TARGET_DIR" ]; then
                TARGET_DIR="{path_standard}"
            fi
            
            if [ -d "$TARGET_DIR" ]; then
                # SEARCH FOR THE SPECIFIC CONFIG ID FILE
                # We look for files ending in _{config_id}.sh OR _{config_id}-*.sh
                SCRIPT_FILE=$(find "$TARGET_DIR" -name "sbatchScript_*_{config_id}.sh" -o -name "sbatchScript_*_{config_id}-*.sh" | head -n 1)
                
                if [ -n "$SCRIPT_FILE" ]; then
                    echo "Submitting matches for Config {config_id}: $SCRIPT_FILE"
                    dos2unix "$SCRIPT_FILE" > /dev/null 2>&1
                    sbatch "$SCRIPT_FILE"
                else
                    echo "MISSING: Specific script for Config {config_id} not found in $TARGET_DIR"
                fi
            else
                echo "MISSING: Directory Run {current_run_id} not found"
            fi
        """)

        lines.append(bash_block)
        
        count += 1
        if count % 50 == 0:
             sys.stdout.write(f"\rProcessed {count} configs...")
             sys.stdout.flush()

    print("")
    lines.append("echo 'Bulk submission complete.'")

    with open(meta_script_name, "w", encoding="utf-8", newline='\n') as f:
        f.write("\n".join(lines))
    
    return meta_script_name

def run_remote_submission(meta_script_name):
    remote_dest = f"/tmp/{meta_script_name}"
    
    logger.info("Transferring bulk script...")
    subprocess.run(
        ["scp", meta_script_name, f"{settings.slurm.username}@{settings.slurm.host}:{remote_dest}"],
        check=True
    )

    logger.info("Executing bulk script...")
    # bash -l ensures $HOME is set correctly
    subprocess.run(
        ["ssh", f"{settings.slurm.username}@{settings.slurm.host}", f"bash -l {remote_dest} && rm {remote_dest}"],
        check=True
    )

if __name__ == "__main__":
    try:
        _ = settings.main.config_id_start 
    except Exception:
        pass

    s_id = settings.main.config_id_start
    e_id = settings.main.config_id_end

    script_name = generate_bulk_submission_script(s_id, e_id)
    run_remote_submission(script_name)
    
    if os.path.exists(script_name):
        os.remove(script_name)
        
    logger.info("Done.")