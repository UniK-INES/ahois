.. _concepts_config:

*************
Configuration
*************

.. contents::
   :local:
   :depth: 1
   :backlinks: top


Configuration and parameter management is done via the `Dynaconf Framework <https://www.dynaconf.com>`_.

.. warning::

	Because of bug #896 in dynaconf (and because we apply `merge_enabled=True`) it is currently
	not straight forward to prevent the merging of lists in the configuration, i.e. items of a list
	defined in `settings_default.toml` will be kept even if the setting is overridden in other places.
	Therefore, defaults of list settings which may be overriden should be initialised empty. A workaround is 
	using `CLEAR` to override list entries as the first entry of the new list. The according setting key needs to be added
	to `config/dynaconf_hooks.py`.
	 
	
Order of configuration consideration
====================================

Default values for all settings are meant to be defined in `settings/settings.toml` in the repos. Your personal settings that
might override the default ones usually go into `settings/settings_local.toml`.

1. Configuration in `settings.toml`
2. Configuration in `settings_local.toml` (or whatever is set in env var AHOI_SETTINGS_FILE_FOR_DYNACONF)
3. Configuration in `.secrets.toml`
4. Configuration in `constants.toml`
5. Configuration in Scenario XLSX file (if MAIN__EXCEL_SCENARIO_FILE is set)
6. Environment variables

.. warning::

	Note that settings integrated by includes are not processed right after the file they are defined in
	but after settings in `constants.toml` and all loaders. Special attention must be paid to settings
	which affect other loaders, e.g. `MAIN__EXCEL_SCENARIO_FILE` and `AHOI_MAIN__SCENARIO_ID`.
	Defining these as includes usually comes to late!


.. admonition:: Background

   Environment are off because we use sections to cluster parameters. Global merging is on
   because we want to combine parameters within parameter clusters.


.. hint::
	You can apply settings for specific environments/context such as the cluster by passing the 
	according settings filename (absolute or relative to `building-stock-model/building_stock_model/config`)
	to the environment variable `AHOI_SETTINGS_FILE_FOR_DYNACONF`.
	

Defining Scenarios
==================

Often, many runs need to be conducted with changes in only one or few parameters. In this case it is convenient to fill an
excel table with lines for each particular scenario parameter set, indexed by a so-called scenario ID. The scenario ID
(MAIN__SCENARIO_ID) can then be switched via an environment variable, e.g. in the SLURM configuration file when running
on a cluster or in the personal settings.toml file.

The Scenario excel file looks like this (there is a template `input_data/Scenario_Template.xlsx`):

.. csv-table:: Scenario_Template.xlsx
    :file: scenario_excel.csv
    :header-rows: 2
    :stub-columns: 1
    :align: left
    :widths: 15, 15, 15, 15, 20, 20
    :width: 100%
    
The part of the SLURM script may look like this:

.. code-block:: sh
   :caption: Part of SLURM config file

    echo "started..."
    export AHOI_MAIN__SCENARIO_ID=1
    export AHOI_OUTOUT_OUTPUT_SETTINGS=TRUE
    srun python ./src/run.py 
    echo "finished"
    
The excel file is specified via `MAIN__EXCEL_SCENARIO_FILE` (relative to `MAIN__INPUT_PATH` or absolute). To disable loading
settings from excel file, set

.. code-block:: toml
   :caption: Disable loading settings from excel file
   
    [main]
    excel_scenario_file = "@none"
	

.. _concepts_config_conserve:

Conserving Scenario Settings
============================

If `OUTPUT__OUTPUT_SETTINGS` is `True` (the default), applied settings are exported to 
`<OUTPUT__OUTPUT_PATH>/<OUTPUT__SUBFOLDER>/<OUTPUT__OUTPUT_SETTINGS_PATH>/settings.toml`

.. code-block:: toml
   :caption: Config for output of applied settings
   
    [output]
    output_settings = true
	output_settings_path = "conf"
	output_settings_filename = "settings.toml"
	

.. warning::

	Make sure to store the excel files and other input data which is referenced in the stored settings.toml as they
	are during simulation!
	
Inspecting Settings History
===========================

In case of application of unexpected settings it can be helpful to inspect the history of settings.
Simply make sure the switch `OUTPUT__OUTPUT_SETTINGS` is `True` (default) and optionally filter 
by a settings key (part) for `OUTPUT__OUTPUT_SETTINGSHISTORY_KEY`:

.. code-block:: toml
   :caption: Config for output of settings history
   
    [output]
    output_settings = true
    output_settingshistory_filename = "settings_history.json"
    output_settingshistory_key = "@none"
    
The according dynconf feature is documented as `Inspecting History <https://www.dynaconf.com/advanced/#inspecting-history>`_.
It shows first the finally applied settings and afterwards exports the history with the according loader 
and its parameters from last to first.


Settings Documentation
======================

.. contents:: Sections
   
.. include::
	settings/settings_doc.rst
	

Create settings documentation
-----------------------------

.. hint::
	CSV files can be created automatically for new settings (sections) via the script
	``doc/source/application/concepts/settings/parse_settings2doc.py``. Comment lines above the setting
	are used in the `Annotations` column.
	To add unit, type, scope, description and annotation values, use LibreOffice and store with "_edit" added.
	Use then the above mentioned script to convert line endings in multiline cells.
	Adapt the filename of edited CSV files in ``settings_doc.rst``.
