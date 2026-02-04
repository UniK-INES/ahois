.. _development:

###########
Development
###########


*****************
GitLab Repository
*****************

- We use the following branches

	- main (released code - only this is allowed for final project simulations)

	- <developers's initials>_feature_<feature title> for feature branches

- Versions that are used to produce final product simulations are tagged accordingly (<project-name>_<project.version>)

- For critical submissions a code review is required using merge request

- Commit message respect `best practises <https://initialcommit.com/blog/git-commit-messages-best-practices>`_:

	- Keep it short (less than 150 characters total)
	- Use the imperative mood
	- Add a title
	- Add a body (optional)


	.. admonition:: Example for a git commit message

		Add Agent property spruceness

		Needed to calculate heat demand

- Submissions to devel need to pass all tests

********************
Publish code and doc
********************

There is a `public gitlab repository <https://github.com/UniK-INES/ahois>`_. To publish the latest code to the
public repository, proceed as follows:

0. Setup your local repository (required once):

	::
	
		git remote add public_origin git@github.com:UniK-INES/ahois.git

1. Merge the code to publish into branch `public_main`, e.g.

	::
		
		git checkout public_main
		git merge -s ort -Xtheirs main --allow-unrelated-histories

2. Push `public_main` to the public repository:

	::
	
		git push public_origin public_main:main
		
Documentation is compiled as github action and will be available at
`<https://unik-ines.github.io/ahois/index.html>`_.

********************
Style Guide for Code
********************

- The main programming language is python

- Code respects PEP 8 (https://peps.python.org/pep-0008/) 

- PEP 8-check is part of code reviews and is recommended to be executed automatically via pre-commit:

	`Ruff <https://pypi.org/project/ruff>`_ is used to automatically format python code,
	`codespell <https://github.com/codespell-project/codespell>`_ to detect typos. Ruff and codespell are called by
	`pre-commit <https://pre-commit.com/>`_ before any commit. In case the code needs to be reformatted, according
	files need to be staged and the commit process is repeated. Requirements to use pre-commit:

	* pre-commit installed:

	  ::

		pip install pre-commit
		pre-commit install


	* `.pre-commit-config.yaml` present in project root (given)

	.. note::

		`codespell:ignore-begin` / `codespell:ignore-end` are not yet supported in the latest
		version of `codespell`, but will be in future (code blocks surrounded
		like this will be ignored).

- TODO-Marker should only be used for urgent tasks, further hints/tasks in the Code are marked by NOTE

- Methods and functions which are only called from within their own module are marked private (leading "_")

- Method and function parameters which do not have a definite default value are assigned `None` as default value.
	Especially for boolean variables `None` should be checked for and an exception be raised accordingly.


Documenting code
================

- Docstrings in `numpy format <https://numpydoc.readthedocs.io/en/latest/format.html#docstring-standard>`_
  Also https://pandas.pydata.org/docs/development/contributing_docstring.html contains a good overview.

- The header of each module shall contain a summary line, extended summary, optionally example(s),
  and author information. The initial author should be given as first one, subsequent editors following.
  In case the current maintainer is not the initial author, `(maintainer)` should be added the the corresponding
  author in the listing. An example header looks like this:

::

	"""
	Evaluation figures for energy demand.

	There are basically four groups:

	* single buildings energy demand
	* total energy demand
	* average energy demand per building
	* average specific energy demand per building
	* weighted average specific energy demand per building (considering scaling factor)

	With data presentation per:

	- owner type
	- building class
	- combinations of owner type and building class


	Examples
	--------

	.. code-block:: python

	    plot_total_energy_demand(
	        fstring="GT in @fargs['gts'] and BAK in @fargs['baks']",
	        fargs=immutabledict({"gts": GT_RB, "baks": BAC_RB}),
	        desc=_(" (WG)"),
	    )

	:Authors:
	 - Ivan Digel <Ivan.Digel@uni-kassel.de>
	 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
	 

	"""

- In case function authorship differs from the authors given in the model header, authors should be
  given in the function docstring as follows (note the indentation of the line after `:Authors:`; also,
  the `Notes` section is required as authors to not render correctly directly below `Parameters` or `Returns`):

::

    Notes
    -----

    :Authors:
     - Ivan Digel <Ivan.Digel@uni-kassel.de>

- Members starting with an underscore (_) will not be included in the docs.
- Often it is a good idea to list settings parameters that are considered in a function:

::

    Other Parameters
    ----------------
    settings.main.project: str
        project name

- Links to other functions:

::

	:func:`rng_milieu_init`

	:func:`~src.modules.RNG.rng_milieu_init` (shows only last part)

	:func:`pandas:pandas.pivot_table` (external libraries defined in conf.py - currently pandas and numpy)

- Math equations (formula needs to be intended relative to .. math::):

::

	.. math::
        p_{i} = \\frac{\\sum_n ix}{x^2}

- Inline math

::

	 :math:`x_{i,n}`

String formatting
=================

The use of `f-strings <https://realpython.com/python-f-strings/>`_ has precedence over `format()` and the modulo operator.
F-strings are `easier to read and perform better <https://realpython.com/python-string-formatting/>`_.
Exceptions apply when lazy evaluation of strings is required. F-Strings also allow format specifiers as 2nd argument
after a ":" within the curly brackets.

::

	message = (
		f"Number of retrieved rows ({len(mz_df)}) for BC={gtvalue}, OT={otvalue} and "
		f"BAC={bakvalue} deviates from requested number ({samplesize:5d}) by more than 1!"
	)

.. include::
	development/testing.rst

*******************
Linting
*******************

AHOIS uses `ruff <https://pypi.org/project/ruff/>`_ as linting and formatting tool. There are plugins for common IDEs
to help with issues while coding:

* `PyCharm <https://docs.astral.sh/ruff/editors/setup/#pycharm>`_
* `VS Code <https://docs.astral.sh/ruff/editors/setup/#vs-code>`_

Specific rules can be looked up by their code at `<https://docs.astral.sh/ruff/rules/>`_

.. Note::

	During a transition period when ruff rules have not yet been implemented fully
	it might be tedious to comply when committing code changes. Therefore, the `pre-commit`
	tool is currently configured for a reduced set of rules (`ruff_temp.toml`).
	However, the ruff tools in e.g. PyCharm should already consider the full set of rules
	aimed for AHOIS (`ruff.toml`).

Further, AHOIS uses `codespell <https://github.com/codespell-project/codespell>`_
to check for typos. It may be necessary to add exceptions to the file `.codespellignore`.

*******************
Documentation Guide
*******************

AHOIS uses sphinx to document concepts, modules, use instructions, API and so on.

- Resources:

 * `reStructuredText <https://www.sphinx-doc.org/en/master/usage/restructuredtext/index.html>`_
 * `reStructuredText Directives <https://docutils.sourceforge.io/docs/ref/rst/directives.html>`_
 * `Quick reStructuredText <https://docutils.sourceforge.io/docs/user/rst/quickref.html>`_


- Internal links:

	- target:
		\.. \_my-reference-label\:

	- source
		\:ref\:\`my-reference-label\`
		\:ref\:\`Link title <label-name>\`

    - automatically created chapter links (source):
    	\:ref\:\`application/api/cluster:cluster.merge\\\\_output\\\\_from\\\\_parallel\\\\_runs module\`
    	(Note the double backslashes!)


- Heading hierarchy:

	1.
		::

			#########
			1st level
			#########

	2.
		::

			*********
			2nd level
			*********

	3.
		::

			3rd level
			=========

	4.
		::

			4th level
			---------

	5.
		::

			5th level
			^^^^^^^^^

	6.
		::

			6th level
			"""""""""

Building documentation
======================

Make sure to have doc dependencies installed:

	::

		pip install -e .[docs]
		
Alternatively:

	::

		pip install -r requirements_pages.txt


- Docs for new modules can be generated by


	.. code-block:: sh
		:caption: Windows

		cd <path to ahois-pro>\doc>
		sphinx-apidoc.exe -o .\source\application\api\ ..\scr\ --templatedir .\source\_templates
	
	
	.. code-block:: sh
		:caption: Linux

		cd <path to ahois-pro>\doc>
		sphinx-apidoc -o ./source/application/api/ ../src/ --templatedir ./source/_templates


	.. note::
		To update existing modules, delete according `.rst` files, call above command
		and execute the python script `convert.py` in folder `api` to remove
		unnecessary files and add a ToC to module files.



- HTML pages

	.. code-block:: sh
		:caption: Windows

  		cd <path to ahois>/doc
  		make.bat html
  		
  		
	.. code-block:: sh
		:caption: Linux
		
  		cd <path to ahois>/doc
  		make html


	To remove the build in order to generate it anew, type:

	.. code-block:: sh
		:caption: Windows

  		cd <path to ahois>/doc
  		make.bat clean
  		
  		
	.. code-block:: sh
		:caption: Linux
		
  		cd <path to ahois>/doc
  		make clean


- Docx document

	.. code-block:: sh
		:caption: Windows

  		cd <path to ahois>/doc
  		make.bat docx
  		
  		
	.. code-block:: sh
		:caption: Linux
		
  		cd <path to ahois>/doc
  		make docx


************
Localisation
************

We apply python's `gettext feature <https://docs.python.org/3/library/gettext.html>`_, mainly for figure labels.

Dynamic texts using variables are coded as follows:

	::

		_("Gebäudetyp {0}, Baualtersklasse {1}").format(GT, BAK)

Singular/plural:

	::

		ngettext('I possess {0} laptop','I possess {0} laptops', num)


To create and maintain translation files, please see :ref:`recipes_analysis_figurelabels`.


*************
FutureWarning
*************

To detect the origin of a `FutureWarning` set parameters as follows:

 * `settings.debug.output_warnings_as_errors = true`
 * `settings.debug.warningsforerrors = "FutureWarning"`

Then, warnings are converted to errors and the printed stacktrace helps to identify the origin of the error.
Note that the responsible code in `warnings_custom.py` is not imported in all modules by default.

*******************
Logging
*******************

See :ref:`concepts_logging_implementation`.


*******************
Dynaconf Tweaks
*******************

At least in its versions before 4.0.0 dynaconf used to perform recursive evaluations every time a setting is requested.
This leads to significant performance issues. Also conversions from upper to lower case of settings names where performed
very often and found to take much time. Since version 4.0.0 is expected not before the end of 2024 a special version
containing these tweaks was developed:

 * prevent `find_the_correct_casing` after initialisation (`boxing.py`)
 * prevent recursive evaluation after initialisation (`boxing.py`)

Since after initialisation these processes are found not to be required for AHID to function properly,
after initialisation a property in dynaconf (evaluate in AHIDConfig) is set to prevent not required processing.

It is now important to stick to lower case setting names and not relying on combined terms for settings after
initialisation (e.g. changing a part of the output path). That's why some adjustments in tests were needed (e.g.
explicitly reloading settings for some tests).

The tweaked version of dynaconf can be applied as follows.
The recommended way is to setup a virtual environment in order to be able to switch to the original version in case of
unforeseen issues. Several options exist:


Virtual environment using pipenv
================================

  ::

  	pip install pipenv
  	cd <AHOIS project dir>/env/main
  	pipenv install


After setting up, these steps are required to run AHID:

  ::

	cd <AHOIS project dir>/env/main
  	pipenv shell
  	cd ../../src
  	python ./run.py
