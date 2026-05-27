.. _dev_testing:

******************************
Testing
******************************

We use `pytest <https://docs.pytest.org/en/7.1.x/contents.html>`_ to conduct unit tests:

	cd ahois-pro/src
    pytest
    
There are some tags assigned to tests to filter executed test methods.

    
To omit tests which usually take a **long time**, use

	cd ahois-pro/src
    pytest -m "not long"

To execute a specific test method:

	cd ahois-pro/src
    pytest tests/test_energy_advisor.py::ConsultationServiceEnergyAdvisorTest::test_job_completion


.. hint::
    
	To continue with tests that failed last time, type `pytest --ff`
