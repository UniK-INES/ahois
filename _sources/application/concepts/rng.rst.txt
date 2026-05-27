.. _concepts_rng:

************************
Random Number Generation
************************

`Overview of stochastic processes <./AHOISpro_RandomProcesses.xlsx>`__

Control Random Number Streams
=============================

To test the reproducibility of random processes it is possible to output the use of random number for each 
particular RNG. To enable the feature, set

.. code-block:: toml
   :caption: Config of random stream ouput
   
	[debug]
	output_randomstreaminvocations = true
	
More information is in the :ref:`API documentation <api-test_rng>`.
