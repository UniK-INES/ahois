"""
Unit tests for the `Intermediary` agent base class and job processing logic.

This file uses the `unittest` framework to test the core functionalities of
`Intermediary` agents. The tests focus on the entire job
lifecycle: queueing new jobs, starting active jobs based on available capacity,
and completing finished jobs.

A series of mock and test-specific classes (`MockModel`, `MockService`,
`TestHouse`, etc.) are used to create a controlled and predictable environment
for verifying the agent's behaviour under different conditions.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
from collections import deque
import unittest
import logging
import mesa_geo as mg
from dotenv import load_dotenv
load_dotenv()
import geopandas as gpd
import shobnetpy as sn
from agents.base.Intermediary import Intermediary
from agents.base.Job import Job
from mesa import Model
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector
from agents.House import House
from agents.Houseowner import Houseowner
from agents.Plumber import Plumber, ConsultationServicePlumber
from modules.Triggers import Trigger_none
from modules.Excel_input_read import Milieu_table
from helpers.config import config_logging
from modules.Heating_systems import (
    Heating_system_oil,
    Heating_system_gas,
    Heating_system_heat_pump,
    Heating_system_pellet,
    init_param_table
    )

from modules.Agent_properties import (
    Personal_standard,
    Heating_preferences,
    Milieu,
)
from interventions.Subsidy import *
from modules.Excel_input_read import (
    Heating_params_table,
    )

logger = logging.getLogger("ahoi.intermediary")

class MockModel(Model):
    """
    A simplified mock model for testing `Intermediary` agents.

    This class provides essential components like a `DataCollector` and a
    `GeoSpace` without the complexity of a full model simulation. It includes
    an `init_network` method to set up the spatial relationships required for
    some tests.
    """
    def __init__(self):
        """
        Initialisation
        """
        self.datacollector = DataCollector(
            tables={
                "Completed Intermediary Jobs": {
                    "Step": [],
                    "Job": [],
                    "Intermediary": [],
                    "Houseowner": [],
                    "Service": [],
                },
                "Intermediary Queue Length": {
                    "Step": [],
                    "Intermediary": [],
                    "Intermediary ID": [],
                    "Service": [],
                    "Queue Length": [],
                },
            }
        )
        self.heating_params_table = Heating_params_table()
    
    def init_network(self, agents):
        """
        Social network initialisation
        """  
        self.space = mg.GeoSpace(crs=settings.geo.coordinate_reference_system)
        self.space.add_agents(agents)
        net_settings = {"MAIN.scenario_id": settings.network.scenario_id,
                        "MAIN.task": "test",
                        "NETWORK.restore": True,
                        }
        self.grid = sn.SHoBNetworkGrid(agents = agents, 
                                       model = self,
                                       geospace = self.space,
                                       settings = net_settings)
        
    def step(self) -> None:
        """
        Advances the model by one step.
        """
        self.schedule.step()


class MockService(ConsultationServicePlumber):
    """
    A mock `ConsultationServicePlumber` for testing job completion effects.

    This class overrides the `complete_job` method to apply a predictable,
    testable outcome. When a job is completed, it reduces the customer's
    budget and sets their heating system to a known string value, making it
    easy to assert the results.
    """
    def __init__(self, job_queue):
        """
        Initialisation
        """
        super().__init__()
        self.job_queue = job_queue
        
    def begin_job(self):
        """
        Simulates the job start.
        """
        super().begin_job()

    def complete_job(self, job: Job):
        """
        Simulates the job completion.
        """
        super().complete_job(job)
        job.customer.hs_budget -= 1500
        job.customer.current_heating = "Test"

class TestHouse(House):
    """
    A test version of a `House` agent with fixed properties.

    This class creates a `House` agent with predefined attributes (e.g., energy
    demand, area) to ensure that tests run with consistent and predictable data.
    """
    def __init__(self, unique_id, model, year, current_heating=None):
        """
        Initialisation
        """
        house_creator = mg.AgentCreator(
            agent_class=House,
            model=model,
            agent_kwargs={},
            crs=settings.geo.coordinate_reference_system,
        )
                
        geo_json = gpd.read_file(settings.geo.geojson_file_path)
        # Add a column with the name of the most probable milieu
        #geo_json["MGrNum"] = geo_json.apply(self.map_milieus, axis=1)
        # Create a dict of parameters to be added to the houses
        geo_dict = geo_json[
            ["flaeche", "baujahr", "Subarea", "MGrNum", "HYearkWh", "Heizlast",]
        ].to_dict(orient="index")

        houses = house_creator.from_GeoDataFrame(geo_json, unique_id="index")
        
        super().__init__(
            unique_id = unique_id,
            model = model,
            geometry = houses[unique_id].geometry,
            crs = houses[unique_id].crs,
            current_heating = current_heating,
            )
        self.year = year
        self.milieu = Milieu(
                table=Milieu_table(), milieu_type="Leading"
            )
        self.energy_demand = self.define_energy_demand(
                year=self.year, heat_demand=10000
            )
        self.area = 100.0
        self.subarea = 50.0
        self.heat_load = 20
        
class TestHouseowner(Houseowner):
    """
    A test version of a `Houseowner` agent.

    This class provides a `Houseowner` with a consistent set of initial
    properties for use in the test setup, avoiding randomness from the
    standard agent creation process.
    """
    def __init__(self,unique_id, house, model):
        """
        Initialisation
        """
        super().__init__(
            unique_id=unique_id,
            house=house,
            model=model,
            income=5000,
            milieu=house.milieu,
            cognitive_resource=4,
            aspiration_value=1,
            known_hs=None,
            suitable_hs=None,
            desired_hs="No",
            hs_budget=None,
            current_breakpoint="None",
            current_stage="None",
            satisfaction="Satisfied",
            active_trigger=Trigger_none(),
            geometry = house.geometry.centroid,
            crs = house.crs,
        )
        self.milieu = "Leading"

class TestPlumber(Plumber):
    """
    A test version of a `Plumber` agent for controlled testing.

    This class allows for the instantiation of a `Plumber` with specific,
    pre-populated job queues and states. This is essential for setting up
    the initial conditions for the job lifecycle tests.
    """
    def __init__(self,unique_id,
            model,
            active_jobs,
            max_concurrent_jobs,
            active_jobs_counter,
            completed_jobs,
            service):
        
        milieu_table = Milieu_table()
        init_param_table()
        super().__init__(
            unique_id=unique_id,
            model=model,
            heating_preferences=Heating_preferences(table=milieu_table),
            standard=Personal_standard(table=milieu_table),
            current_heating=Heating_system_oil(),
            cognitive_resource=settings.plumber.cognitive_resource,
            aspiration_value=settings.plumber.aspiration,
            known_hs=[
                    Heating_system_oil(),
                    Heating_system_gas(),
                    Heating_system_pellet(),
                    Heating_system_heat_pump()
            ],
            known_subsidies=[Subsidy_pellet,
                                 Subsidy_heat_pump(),
                                 Subsidy_heat_pump_brine(),
                                 Subsidy_climate_speed(),
                                 Subsidy_income(),
                                 Subsidy_efficiency()],
            suitable_hs=None,
            desired_hs="No",
            hs_budget=settings.plumber.hs_budget,
            current_breakpoint="None",
            current_stage="None",
            satisfaction="Satisfied",
            active_trigger=Trigger_none(),
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            max_concurrent_jobs=max_concurrent_jobs,
            active_jobs_counter=active_jobs_counter,            
        )
        self.Services[0] = service
        
class IntermediaryTestCase(unittest.TestCase):
    """Test case for the `Intermediary` agent's job management."""
    def setUp(self) -> None:
        config_logging()
        """
        Sets up a consistent test environment before each test method.

        This method creates a `MockModel`, `TestHouseowner` agents, and a
        `TestPlumber`. It pre-populates the plumber's job queue with two
        pending jobs and its active job list with two jobs that are already
        in progress and scheduled to finish at different future steps. This
        provides a rich initial state to test the agent's step-by-step logic.
        """
        self.mock_model = MockModel()
        self.mock_model.schedule = BaseScheduler(self.mock_model)
        self.mock_job_queue = deque()
        self.mock_service = MockService(job_queue=self.mock_job_queue)
        self.mock_house1 = TestHouse(1, self.mock_model, 2023)
        self.mock_houseowner1 = TestHouseowner(
            unique_id=0, house=self.mock_house1, model=self.mock_model
        )

        self.mock_house2 = TestHouse(2, self.mock_model, 2023)
        self.mock_houseowner2 = TestHouseowner(
            unique_id=1, house=self.mock_house2, model=self.mock_model
        )
        
        self.mock_model.init_network([self.mock_houseowner1, self.mock_houseowner2])
        
        self.mock_job_queue.append(
            Job("1", self.mock_houseowner1, self.mock_service, duration=1)
        )
        self.mock_job_queue.append(
            Job("2", self.mock_houseowner2, self.mock_service, duration=1)
        )

        self.mock_active_jobs = {
            # jobs finishing in step 3:
            2: [Job("3", self.mock_houseowner1, self.mock_service, duration=1)],
            # jobs finishing in step 4:
            3: [Job("4", self.mock_houseowner2, self.mock_service, duration=1)],
        }
        self.mock_completed_jobs = {}

        self.mock_max_concurrent_jobs = 2
        self.mock_active_jobs_counter = 2

        self.mock_plumber = TestPlumber(
            "Test",
            self.mock_model,
            active_jobs=self.mock_active_jobs,
            max_concurrent_jobs=self.mock_max_concurrent_jobs,
            active_jobs_counter=self.mock_active_jobs_counter,
            completed_jobs=self.mock_completed_jobs,
            service = self.mock_service,
        )
        self.mock_service.intermediary = self.mock_plumber

    def test_init_default(self) -> None:
        """
        Tests that an `Intermediary` initialises with correct default attributes.
        """
        
        default_intermediary = Intermediary("Test", self.mock_model)

        self.assertTrue(hasattr(default_intermediary, "active_jobs"), True)
        self.assertIsInstance(default_intermediary.active_jobs, dict)
        self.assertEqual(len(default_intermediary.active_jobs.items()), 0)

        self.assertTrue(hasattr(default_intermediary, "completed_jobs"), True)
        self.assertIsInstance(default_intermediary.completed_jobs, dict)
        self.assertEqual(len(default_intermediary.completed_jobs.items()), 0)

        self.assertTrue(hasattr(default_intermediary, "max_concurrent_jobs"), True)
        self.assertEqual(default_intermediary.max_concurrent_jobs, 1)

        self.assertTrue(hasattr(default_intermediary, "active_jobs_counter"), True)
        self.assertEqual(default_intermediary.active_jobs_counter, 0)

    def test_init_specific(self) -> None:
        """
        Tests that an `Intermediary` initialises correctly with custom, 
        pre-populated values.
        """
        
        self.assertIsInstance(self.mock_service.job_queue, deque)
        self.assertEqual(len(self.mock_service.job_queue), 2)

        self.assertIsInstance(self.mock_plumber.active_jobs, dict)
        self.assertEqual(len(self.mock_plumber.active_jobs.items()), 2)

        self.assertIsInstance(self.mock_plumber.completed_jobs, dict)
        self.assertEqual(len(self.mock_plumber.completed_jobs.items()), 0)

        self.assertEqual(self.mock_plumber.max_concurrent_jobs, 2)
        self.assertEqual(self.mock_plumber.active_jobs_counter, 2)

    def test_job_queueing(self):
        """
        Tests the full job lifecycle with unlimited job capacity.
        """
        self.mock_houseowner1.hs_budget = 3000
        self.mock_houseowner2.hs_budget = 3000
        self.mock_model.schedule.add(self.mock_plumber)
        self.mock_plumber.max_concurrent_jobs = 4
        
        # Step 0: active: 2 | queue: 2
        self.assertEqual(len(self.mock_service.job_queue), 2)
        self.assertEqual(len(self.mock_plumber.active_jobs[2]), 1)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertFalse(1 in self.mock_plumber.completed_jobs)
        
        self.mock_model.step() # steps=1>2
        # TODO why -3 ??
        # Step 1: active: 2 + 2 - 3 = 1 | queue: 0
        self.assertEqual(len(self.mock_service.job_queue), 0)
        self.assertFalse(1 in self.mock_service.job_queue)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 3)
        self.assertFalse(2 in self.mock_plumber.completed_jobs)
        
        self.mock_model.step() # steps=2>3
        # Step 2: active: 1 + 0 - 1 = 0 | queue: 0
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertFalse(3 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 3)
        self.assertEqual(len(self.mock_plumber.completed_jobs[2]), 1)
                
        self.assertEqual(self.mock_houseowner1.hs_budget, 0)
        self.assertEqual(self.mock_houseowner2.hs_budget, 0)
        self.assertEqual(self.mock_houseowner1.current_heating, "Test")

    def test_job_beginning(self):
        """
        Tests that new jobs are started from the queue 
        when capacity becomes available.
        """
        
        # will fail because mock_max_concurrent_jobs not considered
        
        # Step 0: active: 2 | queue: 2
        self.mock_houseowner1.hs_budget = 6000
        self.mock_model.schedule.add(self.mock_plumber)
        self.mock_plumber.max_concurrent_jobs = 3
        self.assertEqual(len(self.mock_service.job_queue), 2)
        self.assertEqual(len(self.mock_plumber.active_jobs[2]), 1)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertFalse(1 in self.mock_plumber.completed_jobs)
  
        self.mock_model.step() # steps=1>2
        # Step 1: active: 2 + 1 - 1 = 2 | queue: 1
        
        self.assertEqual(len(self.mock_service.job_queue), 1)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 2)

        self.assertEqual(self.mock_houseowner1.hs_budget, 3000)


    def test_job_completion(self):
        """
        Tests that active jobs are correctly moved to the completed list 
        when their duration ends.
        """
        
        self.mock_houseowner1.hs_budget = 1500
        self.mock_houseowner2.hs_budget = 1500
        
        self.mock_model.schedule.add(self.mock_plumber)
        self.mock_plumber.max_concurrent_jobs = 2
        self.mock_service.job_queue = deque()
        # Step 0: active: 2 | queue: 0
        self.assertEqual(len(self.mock_service.job_queue), 0)
        self.assertEqual(len(self.mock_plumber.active_jobs[2]), 1)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertFalse(1 in self.mock_plumber.completed_jobs)
        
        self.mock_model.step() # steps=1>2
        # Step 1: active: 2 + 0 - 1 = 1 | queue: 0
        self.assertEqual(len(self.mock_service.job_queue), 0)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 1)
        
        self.mock_model.step() # steps=2
        # Step 2: active: 1 + 0 - 1 = 0 | queue: 0
        self.assertEqual(len(self.mock_service.job_queue), 0)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertFalse(3 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[2]), 1)
        
        self.assertEqual(self.mock_houseowner1.hs_budget, 0)
        self.assertEqual(self.mock_houseowner2.hs_budget, 0)
        self.assertEqual(self.mock_houseowner1.current_heating, "Test")


    def test_limited_job_completion(self):
        """
        Tests the full job lifecycle under a limited concurrent job capacity.

        This test verifies that the intermediary correctly processes jobs
        sequentially, only starting a new job from the queue when an active
        one is completed and capacity is freed up.
        """
        # will fail because mock_max_concurrent_jobs not considered
        self.mock_houseowner1.hs_budget = 3000
        self.mock_houseowner2.hs_budget = 3000
        
        self.mock_model.schedule.add(self.mock_plumber)
        self.mock_max_concurrent_jobs = 2
        
        # Step 0: active: 2 | queue: 2
        self.assertEqual(len(self.mock_service.job_queue), 2)
        self.assertEqual(len(self.mock_plumber.active_jobs[2]), 1)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertFalse(1 in self.mock_plumber.completed_jobs)
        
        self.mock_model.step() # steps=1>2
        # Step 1: active: 2 + 0 - 1 = 1 | queue: 2
        self.assertEqual(len(self.mock_service.job_queue), 2)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.active_jobs[3]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 1)
        
        self.mock_model.step() # steps=2>3
        # Step 2: active: 1 + 1 - 2 = 0 | queue: 1
        self.assertEqual(len(self.mock_service.job_queue), 1)
        self.assertFalse(2 in self.mock_plumber.active_jobs)
        self.assertFalse(3 in self.mock_plumber.active_jobs)
        self.assertEqual(len(self.mock_plumber.completed_jobs[1]), 1)
        self.assertEqual(len(self.mock_plumber.completed_jobs[2]), 2)
        
        self.mock_model.step() # steps=3>4
        # Step 3: active: 0 + 1 - 1 = 0 | queue: 0
        self.assertEqual(len(self.mock_service.job_queue), 0)
        self.assertEqual(len(self.mock_plumber.active_jobs), 0)
        self.assertEqual(len(self.mock_plumber.completed_jobs[3]), 1)

        self.assertEqual(self.mock_houseowner1.hs_budget, 0)
        self.assertEqual(self.mock_houseowner2.hs_budget, 0)
        self.assertEqual(self.mock_houseowner1.current_heating, "Test")
        self.assertEqual(self.mock_houseowner2.current_heating, "Test")

if __name__ == "__main__":
    unittest.main()
