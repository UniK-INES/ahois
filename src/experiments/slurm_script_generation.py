"""

Create SLURM scripts to run AHOI on a linux cluster.
Creates multiple runs depending an seed range defined in scenario file (per row)
and subsample sets.

:Authors: 

* Sascha Holzhauer <Sascha.Holzhauer@uni-kassel.de>

"""

import os, stat, sys
from optparse import OptionParser
import logging
from helpers.config import (
    settings,
    get_output_path,
)

logger = logging.getLogger("ahoi.cluster.batchscript")

defaultProject = settings.main.project
defaultTask = settings.main.task
defaultId = "1"
#defaultRunnumber = settings.main.run_id
defaultPartition = settings.slurm.partition
defaultDuration = settings.slurm.duration
defaultNumSamplesets = 1
defaultNumRunsPerBatch = 1
default_config_id_start = settings.main.config_id_start
default_config_id_end = settings.main.config_id_end


def generate_script(args=sys.argv[1:]):
    """
    Creates SLURM scripts by replacing placeholders in template and generates execution script
    to call SLURM scripts.

    Parameters
    ----------
    run_id: int
        Run ID
    args: list[str]
        arguments for SLURM script creation

    Other Parameters
    ----------------

    * settings.slurm.template_file
    * settings.slurm.target_batchfiles
    * settings.slurm.target_execfile
    * settings.slurm.target_cluster_logfiles
    * settings.slurm.target_cluster_batchfiles

    Returns
    -------
    str
        filename of execution script
    """
    defaultRunnumber = settings.main.run_id
    
    parser = OptionParser(usage="usage: %prog [options]", version="%prog 1.0")

    parser.add_option(
        "-i",
        "--project-sid",
        dest="project",
        default=defaultProject,
        help="Project ID",
        metavar="PROJECT",
    )

    parser.add_option(
        "-t",
        "--task",
        dest="task",
        default=defaultTask,
        help="Task ID",
        metavar="TASK",
    )


    parser.add_option(
        "-n",
        "--runnumber",
        dest="runnumber",
        default=defaultRunnumber,
        help="Number of this run",
        metavar="RUN_NUMBER",
    )

    parser.add_option(
        "-p",
        "--partition",
        dest="partition",
        default=defaultPartition,
        help="Partition to run on",
        metavar="PARTITION",
    )

    parser.add_option(
        "-d",
        "--duration",
        dest="duration",
        default=defaultDuration,
        help="Simulated duration in s (default: %default)",
        metavar="DURATION",
    )


    parser.add_option(
        "-s",
        "--config_id_start",
        dest="config_id_start",
        default=default_config_id_start,
        help="config_id_start (default: %default)",
        metavar="CONFIG_ID_START",
    )

    parser.add_option(
        "-e",
        "--config_id_end",
        dest="config_id_end",
        default=default_config_id_end,
        help="config_id_end (default: %default)",
        metavar="CONFIG_ID_END",
    )
    
    (options, args) = parser.parse_args(args)

    # Parse IDs:
    project = options.project
    task = options.task
    runnumber = int(options.runnumber)
    partition = options.partition
    duration = int(float(options.duration))
    config_id_start = int(options.config_id_start)
    config_id_end = int(options.config_id_end)

    num_runs_per_batch = settings.slurm.num_runs_per_batch
    
    # specify target file (without file ending
    scriptTemplate = settings.slurm.template_file
    targetDirBatchfiles = get_output_path(
        runid=runnumber, subfolder=settings.slurm.target_batchfiles
    )
    targetDirExecfile = get_output_path(
        runid=runnumber, subfolder=settings.slurm.target_execfile
    )

    logger.info(f"Build scripts for config IDs {config_id_start} to {config_id_end}.")

    execScriptFilename = (
        targetDirExecfile + "/executeScript_" + project + "_" + 
            str(config_id_start) + "-" + str(config_id_end) + ".sh"
    )

    logger.info("Generate SLURM execution script to " + execScriptFilename + "...")
    execScript = open(execScriptFilename, "w", newline="\n")
    execScript.write("#!/bin/sh\n")

    for k in range(config_id_start, config_id_end + 1, num_runs_per_batch):
        logger.debug(
            "Run "
            + str(runnumber)
            + " (ID: "
            + str(k)
            + ")"
        )

        scriptFilename = (
            targetDirBatchfiles
            + "/sbatchScript_"
            + project
            + "_"
            + str(k)
            + ".sh"
        )
        script = open(scriptFilename, "w", newline="\n")

        infile = open(scriptTemplate, "r")
        inputLine = infile.readline()
        while inputLine != "":
            inputLine = inputLine.rstrip('\r\n')
            inputLine = inputLine.replace("%PROJECT%", project)
            inputLine = inputLine.replace("%TASK%", task)
            inputLine = inputLine.replace("%CONFIG_ID_START%", str(k))
            inputLine = inputLine.replace("%CONFIG_ID_END%", str(k + num_runs_per_batch - 1))
            inputLine = inputLine.replace("%RUN_ID%", str(runnumber))
            inputLine = inputLine.replace("%PARTITION%", str(partition))
            inputLine = inputLine.replace("%DURATION%", str(duration))
            inputLine = inputLine.replace("%USERNAME%", settings.slurm.username)
            script.write(inputLine + "\n")
            inputLine = infile.readline()
        infile.close()
        script.close()
        execScript.write(
            "mkdir -p "
            + settings.slurm.target_cluster_logfiles
            + "/"
            + str(runnumber)
            + "/logs"
            + "\n"
        )
        execScript.write(
            "sbatch "
            + f"~/ahoi/{runnumber}/"
            + settings.slurm.target_cluster_batchfiles
            + "/sbatchScript_"
            + project
            + "_"
            + str(k)
            + ".sh\n"
        )
        if settings.output.simplenames:
            runnumber = runnumber + 1
    execScript.close()

    st = os.stat(execScriptFilename)
    os.chmod(execScriptFilename, st.st_mode | stat.S_IEXEC)

    logger.info("Scripts for IDs " + str(config_id_start) + "-" + str(config_id_end) + " finished.")
    return "executeScript_" + project + "_" + str(config_id_start) + "-" + str(config_id_end) + ".sh"


if __name__ == "__main__":
    generateScript()
