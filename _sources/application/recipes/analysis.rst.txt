.. _recipes_analysis:

****************
Analysis
****************

.. contents::
   :local:
   :backlinks: top


Figures
=======

`Overview of implemented figures <./AHOISpro_Figures_Overview_SH.ods>`__


.. note::
	You may set global matplotlib setting in a .plt file specified by
	`settings.data.plt_settings` (default is `plotting/config_plt_unik.yaml`).

.. _recipes_analysis_figurelabels:

Figure labels
-------------

Labels of figures work via l18n, using python's gettext feature, i.e. figures can be labeled by any translation which is defined
by the setting `AHOI_EVAL__LANGUAGE`. 


Update new labels from code
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Update the Portable Object Template (POT) file (call in AHOIS' root folder):

.. code-block::

	python setup.py extract_messages 
		--output-file=src/helpers/ahoi_parsed.pot
	
Combine (automatically) created POT-file with (manually) defined POT file with outside-code-strings (e.g. defined in settings):


.. hint::
	`xgettext` is shipped with `POedit <https://poedit.net/>`_ (see below). To make it available at the command line
	add the bin folder (e.g. `C:\\Program Files (x86)\\Poedit\\GettextTools\\bin`) to your PATH-variable.
	
.. code-block::
	:caption: Unix
	
	xgettext src/helpers/ahoi_parsed.pot
		src/helpers/ahoi_manual.pot
		-o src/helpers/ahoi.pot

.. code-block::
	:caption: Windows
	
	xgettext.exe src/helpers/ahoi_parsed.pot
		src/helpers/ahoi_manual.pot
		-o src/helpers/ahoi.pot
		
Editing Labels
^^^^^^^^^^^^^^

Often it makes sense to create a separate language/label set per project to label figures with project-specific terms.
**New languages** can be added as follows:

Create a .po file for the new language/label set:

.. code-block::

	python setup.py init_catalog  -l en_GB
	
.. hint::
	Often it is useful to build upon existing translations. To do so copy the desired translation (`ahid.po`) to the new translation's
	place: `building_stock_model/locale/<LOCALE>/LC_MESSAGES/ahid.po`

Fill the translations within the newly created .po file at `src/helpers/<LOCALE>/LC_MESSAGES`
by either using a text editor or `POedit <https://poedit.net/>`_.
Using POedit the required machine readable versions of the .po files (.mo) files are created automatically when saving.
Otherwise call:

.. code-block::

	python setup.py compile_catalog

.. note::
	Many labels for subsamples of result data such as building types, owner types, energy carriers, or building parts are
	defined in an excel file (default: FigureLabels.xlsx). To translate these, store the excel file with a langauge specific
	name (e.g. "FigureLabels_en_GB.xlsx") according to `eval.language` and edit the label columns within the excel sheets.
	
	
Compare Scenarios
-----------------

..	todo

1. Choose scenarios/files_prefixes to compare:

	.. code-block:: toml
	
		[scenario_comparison]
		active = true
		scenarios = ["Scenario_mix_pellet_heat_pump"]
		files_prefixes = ["DEZ_Baseline", "DEZ_Beraterkampagne"]

2. Select plots to create:

	.. code-block:: toml
	
		[scenario_comparison]
		compare_fulfillment = false
		compare_emissions = false
		compare_energy_demand = false
		compare_optimality = false
		compare_opex = false
		compare_total_expenses = false
		compare_total_effort = false
		compare_heating_systems_distribution = false
		compare_hs_knowledge = false
		compare_obstacles_counts = true
		compare_obstacles_step = -1
		compare_attributes = true

2. Execute `python Built_plots.py`


Slide Generation
----------------

..	todo
