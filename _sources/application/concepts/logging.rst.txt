.. _concepts_logging:

**************************************
Logging
**************************************

.. contents::
   :local:
   :backlinks: top


Configuration
=============

Configuration of logging is done via a configuration file. The default configuration file is `settings/config_logging.conf`
and can be substituted by setting `AHOI_LOGGING_CONFIGFILE`, e.g.

.. code-block:: sh
	
	[logging]
	configfile = "./src/settings/config_logging_user.conf"
	
Per default, above `INFO`-Level will be logged to the console and to a file at `<output_path>/logs/ahoi_<runid>.log`.

To adjust loglevels for specific subpackages or module add a section to your custom configuration file like:

.. code-block:: sh

	[logger_ahoi_util]
	level=DEBUG
	handlers=
	qualname=ahoi.util
	propagate=1

.. admonition:: Background

	To consider the output path file handlers are usually not configured with the filename in the logging configuration file,
	but with `os.devnull`. Later on in `logging_cong.py::config_logging` the file handlers are exchanged and their output is 
	directed to a file with name pattern `ahoi_<RUN_ID-JOB>.log`.
	
	
More information can be obtained from the `Logging Cookbook <https://docs.python.org/3/howto/logging-cookbook.html>`_.


.. _concepts_logging_implementation:

Implementation
==============

AHOIS uses the python logging framework. All we need in modules is the logger obtained by

.. code-block:: python

	logger = logging.getLogger('ahoi.subpackage.module')
	
Log messages are triggered by

.. code-block:: python

	logger.info("Information for the user")
	logger.info("Information for user %s: %d", "UserA", 42)
	logger.debug("Information that helps to debug code")