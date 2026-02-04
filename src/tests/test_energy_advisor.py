"""
Unit tests for the `EnergyAdvisor` agent and its services.

This file contains unit tests for the `EnergyAdvisor` agent, with a specific
focus on its consultation service. It uses Python's built-in `unittest`
framework to create a mock environment. This includes mock versions
of the model, space, and other agents to isolate the `EnergyAdvisor`'s
behaviour and verify that it correctly processes and completes jobs from its queue.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
import unittest
import pandas as pd
from mesa import Model
from mesa.time import BaseScheduler
from mesa.datacollection import DataCollector
from agents.EnergyAdvisor import EnergyAdvisor
from modules.Heating_systems import (
    init_param_table,
    )
from tests.test_intermediary import TestHouse, TestHouseowner
from modules.Excel_input_read import Milieu_table
from modules.Agent_properties import (
    Heating_preferences,
)
from modules.Scenario import *

from modules.Excel_input_read import (
    Heating_params_table,
    )

class MockSpace:
    """
    A minimal mock version of the Mesa-Geo `GeoSpace` for testing.
    """
    def __init__(self) -> None:
        self.agents = dict()


class MockModel(Model):
    """
    A simplified mock model for testing the `EnergyAdvisor` agent.

    This class provides a minimal, self-contained environment for the agent
    to operate in during tests. It includes a `MockSpace`, a `DataCollector`
    with the necessary table structures, and stubs for scenario information
    and obstacle tracking required by the agent's logic.
    """
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.space = MockSpace()
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
        super().__init__(*args, **kwargs)
        options = [
            "Heating_system_oil",
            "Heating_system_gas",
            "Heating_system_heat_pump",
            "Heating_system_electricity",
            "Heating_system_pellet",
            "Heating_system_network_district",
            "Heating_system_network_local",
            "Heating_system_heat_pump_brine",
        ]
        decisions = [
            "Take_Unsubsidised",
            "Take_Unsubsidised+Loan",
            "Drop_Unsubsidised",
            "Take_Subsidised",
            "Take_Subsidised+Loan",
            "Drop_Subsidised",
        ]
        self.scenario = globals()["Scenario_heat_pumps"]()
        self.heating_params_table = Heating_params_table()
        self.dropout_counter = pd.DataFrame(0, index=options, columns=decisions)
        self.obstacles = {
            hs_option: {
                "Triggered": set(),
                "Deciding": set(),
                "Knowledge": set(),
                "Affordability": set(),
                "Riskiness": set(),
                "Evaluation": set(),
                "Feasibility": set()
            }
            for hs_option in self.scenario.hs_targets.keys()
        }
         
    def step(self) -> None:
        self.schedule.step()


class ConsultationServiceEnergyAdvisorTest(unittest.TestCase):
    """
    Test case for the `EnergyAdvisor`'s consultation service.
    """
    def setUp(self):
        """
        Sets up the test environment before each test method is run.

        This method creates all the necessary mock objects for a single test
        scenario. It instantiates a `MockModel`, a `TestHouse` with a
        `TestHouseowner`, and an `EnergyAdvisor`. A consultation job for the
        houseowner is then added to the energy advisor's queue, and the advisor
        is added to the model's schedule, ensuring each test starts with a
        fresh and consistent state.
        """
        init_param_table()
        self.mock_subsidy = Subsidy("Test", "Test", 0.8, Heating_system_heat_pump)
        self.mock_model = MockModel()
        self.mock_model.schedule = BaseScheduler(self.mock_model)
        self.mock_heatingsystem = Heating_system_gas()
        self.mock_house1 = TestHouse(1, self.mock_model, 2023, current_heating=self.mock_heatingsystem)
        self.mock_heatingsystem.calculate_all_attributes(house=self.mock_house1)
        
        self.mock_houseowner1 = TestHouseowner(
            unique_id=f"Houseowner 1",
            house=self.mock_house1,
            model=self.mock_model,
        )
        self.mock_houseowner1.hs_budget = 18800 + 150
        
        self.mock_model.space.agents = {}
        self.mock_model.space.agents[1] = self.mock_house1

        self.mock_energy_advisor = EnergyAdvisor(
            "Test",
            self.mock_model,
            known_hs=[Heating_system_heat_pump(), Heating_system_gas()],
            known_subsidies=[self.mock_subsidy],
            heating_preferences=Heating_preferences(table=Milieu_table()),
        )
        self.mock_energy_advisor.Services[0].queue_job(self.mock_houseowner1)
        self.mock_model.schedule.add(self.mock_energy_advisor)

    def test_job_completion(self):
        """
        Tests the full lifecycle of a consultation job.

        This test simulates the progression of the model by calling `model.step()`
        multiple times. Its primary purpose is to ensure that the job processing
        logic within the `EnergyAdvisor` runs to completion without raising any
        errors.

        Notes
        -----
        This test acts as a "smoke test" as it does not include explicit `assert`
        statements to verify the final state of the agents.
        """
        self.mock_model.step()
        self.mock_model.step()
        self.mock_model.step()


if __name__ == "__main__":
    unittest.main()
