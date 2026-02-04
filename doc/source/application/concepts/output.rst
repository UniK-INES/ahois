.. _concepts_output:

**************************************
Output
**************************************

.. contents::
   :local:
   :backlinks: top


The following is considered output

 * applied settings
 * excel and pickle files with data
 * log files (from logger framework and slurm)
 * figures
 * slurm batch files


.. _concepts_output_structure:

Folder Structure
================

Output files are stored according to the following structure:

 * Output folder (<AHOI_MAIN__OUTPUT_PATH>)
 	* Project name (<AHID_MAIN__PROJECT> is usually part of <AHID_MAIN__OUTPUT_PATH>)
 		* Task (<AHID_MAIN__TASK>)
 			* Run ID
 				* Subfolder conf|slurm|log|output
 
The output folder and subfolders are defined in section :ref:`settings [main] <application/concepts/settings/settings_doc:main>`:

.. code-block:: sh

	[main]
	# Used as target for output files (specified excluding task but including project):
	output_path =  "@format ~/AHID/{this.main.project}"
	project="Project"
	task = "Task"
	runid = 77


.. hint::

	To define **different output folders e.g. for local execution and cluster runs**, one can use the ``dynaconf_include = 
	["settings_local.toml"]`` directive. This way all other custom settings can be synchronised between local and cluster 
	runs by synchronizing ``AHOI_SETTINGS_FILE_FOR_DYNACONF`` (usually ``settings.toml``) alone.
	The file ``settings_local.toml`` may look like this:
	
	.. code-block:: sh

		[main]
		output_path =  "@format ~/ahois/{this.main.project}"


.. note::

	For aggregated results, the folder is created according to the pattern
	``<max(runIDs)>-<min(runs)>``.
	

Further output information
==========================

 * :ref:`concepts_config_conserve`
 * :ref:`concepts_logging`
 * :ref:`recipes_analysis`
 * :ref:`recipes_slurmClusterRuns`
 