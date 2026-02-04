"""
Unit tests for the base `Service` class.

This file contains unit tests for the generic `Service` class, which serves
as a base for more specific services within the model. It uses the `unittest`
framework to test fundamental service functionalities, such as generating
unique job IDs and handling the job queue.

A mock service and a test plumber are used to create a controlled environment
for verifying these behaviours.
:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
from collections import deque
import unittest

from agents.base.Job import Job
from agents.base.Service import Service
from mesa.time import BaseScheduler
from tests.test_intermediary import MockModel, TestPlumber, TestHouse, TestHouseowner

class MockService(Service):
    """
    A minimal mock implementation of the `Service` base class for testing.

    This class inherits from `Service` and provides placeholder implementations
    for the abstract methods `begin_job` and `complete_job`. This allows it
    to be instantiated and used in tests that focus on other `Service` methods,
    like ID generation and queue management.
    """
    def begin_job(self, job: Job):
        """
        Imitates job start 
        """
        pass

    def complete_job(self, job: Job):
        """
        Imitates job completion 
        """
        pass


class ServiceTestCase(unittest.TestCase):
    """
    Test case for the base `Service` class functionalities.
    """
    def setUp(self):
        """
        Sets up a consistent test environment before each test method.

        This method creates all necessary mock and test objects, including a
        `MockModel`, `TestHouseowner` agents, a `MockService`, and a
        `TestPlumber`. The service is assigned to the plumber, and its job
        queue is pre-populated with two jobs. This setup provides the necessary
        context to test the service's methods.
        """
        self.mock_job_queue = deque()
        mock_service = MockService(job_queue = self.mock_job_queue)
        self.mock_model = MockModel()
        self.mock_model.schedule = BaseScheduler(self.mock_model)
        self.mock_house1 = TestHouse(1, self.mock_model, 2023)
        self.mock_houseowner1 = TestHouseowner(
            unique_id=f"Houseowner 1", house=self.mock_house1, model=self.mock_model
        )

        self.mock_house2 = TestHouse(2, self.mock_model, 2023)
        self.mock_houseowner2 = TestHouseowner(
            unique_id=f"Houseowner 2", house=self.mock_house2, model=self.mock_model
        )
        
        self.mock_job_queue.append(
            Job("1", self.mock_houseowner1, mock_service, duration=1)
        )
        self.mock_job_queue.append(
            Job("2", self.mock_houseowner2, mock_service, duration=1)
        )

        self.mock_active_jobs = {
            2: [Job("3", self.mock_houseowner1, mock_service, duration=1)],
            3: [Job("4", self.mock_houseowner2, mock_service, duration=1)],
        }
        self.mock_completed_jobs = {}
        self.mock_max_concurrent_jobs = 2
        self.mock_active_jobs_counter = 2

        self.mock_plumber = TestPlumber(
            "Test_intermediary",
            self.mock_model,
            active_jobs=self.mock_active_jobs,
            max_concurrent_jobs=self.mock_max_concurrent_jobs,
            active_jobs_counter=self.mock_active_jobs_counter,
            completed_jobs=self.mock_completed_jobs,
            service = mock_service,
        )
        self.mock_plumber.mock_service = mock_service
        mock_service.intermediary = self.mock_plumber
        mock_service.mock_job_queue = self.mock_job_queue
        mock_service.job_counter = 4

    def test_job_id_generation(self):
        """
        Tests the format and uniqueness of generated job IDs.

        This test verifies that the `generate_id` method correctly constructs
        a unique identifier by combining the intermediary's ID, the service's
        class name, and an incrementing job counter.
        """
        self.assertEqual(
            self.mock_plumber.mock_service.generate_id(),
            "Test_intermediary-MockService-4",
        )

    def test_job_processing(self):
        """
        Tests that duplicate jobs for the same customer are not added to the queue.
        """
        self.assertEqual(len(self.mock_plumber.Services[0].job_queue), 2)
        # add job of Houseowner already in queue (is not added):
        self.mock_plumber.mock_service.queue_job(self.mock_houseowner1)
        self.assertEqual(len(self.mock_plumber.Services[0].job_queue), 2)


if __name__ == "__main__":
    unittest.main()
