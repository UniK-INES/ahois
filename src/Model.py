"""
The main MESA model for the agent-based simulation of heating system adoption.

This module defines the `Prototype_Model` class, which handles the entire 
agent-based simulation. It is responsible for initialising the environment, 
creating all agents (Houses, Houseowners, Plumbers, Energy Advisors), managing 
the simulation schedule, collecting data, and running the simulation loop. It 
also handles dynamic updates to the environment, such as changes in fuel costs 
or subsidy availability.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
 - Sören Lohr

"""
import os
import pandas as pd
import geopandas as gpd
import logging
import time
import warnings
import mesa_geo as mg
import math
import shobnetpy as sn
import numpy as np
from copy import deepcopy
from mesa import Model
from mesa.time import RandomActivationByType
from mesa.datacollection import DataCollector
from scipy.stats import truncnorm
from collections import defaultdict

from agents.Houseowner import Houseowner
from agents.House import House
from agents.Plumber import Plumber
from agents.EnergyAdvisor import EnergyAdvisor

from modules.Heating_systems import (
    Heating_system_oil,
    Heating_system_gas,
    Heating_system_heat_pump,
    Heating_system_heat_pump_brine,
    Heating_system_electricity,
    Heating_system_pellet,
    Heating_system_network_district,
    Heating_system_network_local,
)
from modules.Triggers import *
from modules.Rng import rng_model_init
from modules.Excel_input_read import (
    Milieu_table, 
    Heating_params_table,
    Heating_params_dynamics_table)
from modules.Agent_properties import (
    Personal_standard,
    Heating_preferences,
    Milieu,
)
from modules.Information_sources import Information_source
from modules.Scenario import *

from helpers.utils import files_name, get_file_name
from helpers.config import (settings, config_logging, 
                            get_output_path, stop_dynaconf_evaluation)

from interventions.Subsidy import *

warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
logger = logging.getLogger("ahoi")

datacollector_tables = {
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


class Prototype_Model(Model):
    """
    The main MESA model for simulating heating system replacement decisions.

    This class sets up and runs the agent-based simulation. It initialises the
    geographical space (`GeoSpace`), creates and populates it with agents based
    on input data (e.g., GeoJSON), and manages their interactions through a
    scheduler. The model also handles scenario-specific interventions, dynamic
    environmental changes, and comprehensive data collection.

    Attributes
    ----------
    space : mesa_geo.GeoSpace
        The geographical environment where agents are located.
    schedule : mesa.time.RandomActivationByType
        The scheduler that controls the order of agent activation.
    scenario : Scenario
        The scenario object defining interventions and targets for the simulation run.
    datacollector : mesa.DataCollector
        The MESA object responsible for collecting model- and agent-level data.
    grid : shobnetpy.SHoBNetworkGrid
        The social network grid managing interactions between Houseowner agents.
    num_plumbers : int
        The number of Plumber agents in the model.
    num_energy_advisors : int
        The number of EnergyAdvisor agents in the model.
    dropout_counter : pd.DataFrame
        A DataFrame tracking the reasons why houseowners did not choose certain
        heating systems.
    obstacles : dict
        A dictionary for tracking agents at various stages of the decision-making
        process for target heating systems.
    """
    def __init__(
        self,
        P,
        scenario,
        E,
        subsidy_to_observe=None,
        known_hs_to_observe=None,
        verbose=True,
        geojson_path=settings.geo.geojson_file_path,
    ):
        """Initializes the simulation model.

        This method orchestrates the complete setup of the simulation environment. 
        It involves creating the geographical space, loading and processing building 
        data from a GeoJSON file, and instantiating all agent populations: 
        Houses, Houseowners with specific milieu and economic profiles, Plumbers, 
        and Energy Advisors. It also establishes the social network between 
        houseowners, configures scenario-specific parameters, and prepares a 
        comprehensive data collector for tracking simulation outputs.

        Parameters
        ----------
        P : int
            The number of Plumber agents to create.
        scenario : str
            The name of the scenario class to be used for the simulation.
        E : int
            The number of Energy Advisor agents to create.
        subsidy_to_observe : str, optional
            A specific subsidy to observe for visualization purposes. Defaults to None.
        known_hs_to_observe : str, optional
            A specific heating system to observe for visualization. Defaults to None.
        verbose : bool, optional
            If True, enables print statements during initialization. Defaults to True.
        geojson_path : str, optional
            The file path to the GeoJSON file containing house data.
        """
        if verbose:
            print("Initialisation started!")

        # serialization and logging
        self.verbose = verbose

        start = time.time()
        # Other important params
        super().__init__()
        self.sa_active = settings.experiments.sa_active
        self.num_plumbers = P
        self.num_energy_advisors = E
        self.space = mg.GeoSpace(crs=settings.geo.coordinate_reference_system)
        self.schedule = RandomActivationByType(self)
        self.milieu_table = Milieu_table()
        self.scenario = globals()[scenario]()
        self.global_infeasibles = []
        self.list_of_sources = self.create_information_sources()
        self.heating_params_table = Heating_params_table()
        
        if settings.experiments.sa_active:
            settings.data.dynamic = False 
            df = self.heating_params_table.content
            if settings.experiments.sa_system != "None":
                system_name = settings.experiments.sa_system
                df.at[system_name, "installation_time"] = settings.experiments.sa_installation_time
                df.at[system_name, "operation_effort"] = settings.experiments.sa_operation_effort
                df.at[system_name, "fuel_cost"] = settings.experiments.sa_fuel_cost
                df.at[system_name, "emissions"] = settings.experiments.sa_emissions
                df.at[system_name, "price"] = settings.experiments.sa_price
                df.at[system_name, "heat_load_price"] = settings.experiments.sa_heat_load_price
                df.at[system_name, "availability"] = settings.experiments.sa_availability
                df.at[system_name, "installation_effort"] = settings.experiments.sa_installation_effort
            else:
                df["installation_time"] = settings.experiments.sa_installation_time
                df["operation_effort"] = settings.experiments.sa_operation_effort
                df["fuel_cost"] = settings.experiments.sa_fuel_cost
                df["emissions"] = settings.experiments.sa_emissions
                df["price"] = settings.experiments.sa_price
                df["heat_load_price"] = settings.experiments.sa_heat_load_price
                df["availability"] = settings.experiments.sa_availability
                df["installation_effort"] = settings.experiments.sa_installation_effort
        
        self.heating_params_dynamics_table = Heating_params_dynamics_table()
        self.heating_distribution = {"Heating_system_oil": 0,
                                     "Heating_system_gas": 0,
                                     "Heating_system_heat_pump": 0,
                                     "Heating_system_heat_pump_brine": 0,
                                     "Heating_system_electricity": 0,
                                     "Heating_system_pellet": 0,
                                     "Heating_system_network_district": 0,
                                     "Heating_system_network_local": 0,
                                     "Heating_system_GP_Joule": 0}

        """Agent creator"""
        # Create houses using MESA-GEO"s agent creator
        house_params = {}
        house_creator = mg.AgentCreator(
            agent_class=House,
            model=self,
            agent_kwargs=house_params,
            crs=settings.geo.coordinate_reference_system,
        )
        geo_json = gpd.read_file(geojson_path)
        # Add a column with the name of the most probable milieu
        geo_json["MGrNum"] = geo_json.apply(self.map_milieus, axis=1)
        # Create a dict of parameters to be added to the houses
        geo_dict = geo_json[
            ["flaeche", "baujahr", "Subarea", "MGrNum", "HYearkWh", "Heizlast",]
        ].to_dict(orient="index")

        houses = house_creator.from_GeoDataFrame(geo_json, unique_id="index")
        self.space.add_agents(houses)

        # Observation attributes for portrayal visualization
        self.subsidy_to_observe = subsidy_to_observe
        self.known_hs_to_observe = known_hs_to_observe

        i = 0
        for house in self.space.agents:
            # Manually adding other geojson attributes to the houses
            house.area = geo_dict[house.unique_id]["flaeche"]
            house.year = geo_dict[house.unique_id]["baujahr"]
            house.subarea = geo_dict[house.unique_id]["Subarea"]
            house.heat_load = geo_dict[house.unique_id]["Heizlast"]
            house.milieu = Milieu(
                table=self.milieu_table, milieu_type=geo_dict[house.unique_id]["MGrNum"]
            )

        self.distribute_heating_systems()
        
        # Create agents
        houseowners = []
        for house in self.space.agents:
            house.energy_demand = house.define_energy_demand(
                year=house.year, heat_demand=geo_dict[house.unique_id]["HYearkWh"]
            )
            house.current_heating.calculate_all_attributes(
                energy_demand=house.energy_demand, area=house.area,
                heat_load=house.heat_load
            )
            house.current_heating.payback = (
                house.current_heating.params["price"][0]
                / house.current_heating.lifetime
            )
            house.current_heating.investment = house.current_heating.params["price"][
                0
            ] - house.current_heating.payback * (
                house.current_heating.lifetime - house.current_heating.age
            )

            a = Houseowner(
                unique_id=i,
                house=house,
                model=self,
                income=None,
                milieu=house.milieu,
                cognitive_resource = self.define_cognitive_resource(milieu = house.milieu.milieu_type),
                aspiration_value=settings.houseowner.aspiration,
                known_hs=None,
                suitable_hs=None,
                desired_hs="No",
                hs_budget=None,
                current_breakpoint="None",
                current_stage="None",
                satisfaction="Satisfied",
                active_trigger=Trigger_none(),
                geometry = None,
                crs = None
            )
            income = self.define_income(milieu = a.milieu_data.milieu_type)
            a.income = income
            a.hs_budget = (
                a.income * settings.houseowner.budget_limit
            )
            a.risk_tolerance = self.define_risk_tolerance(milieu 
                                                          = a.milieu_data.milieu_type)
            a.uncertainty_factor = a.milieu_data.uncertainty_factor
            a.geometry = house.geometry.centroid
            a.crs = house.crs
            a.milieu = a.milieu_data.milieu_type
            a.loan_taking = rng_model_init().uniform() < settings.houseowner.loan_taking_probability
            house.set_house_owner(a)
            self.schedule.add(a)
            houseowners.append(a)
            i += 1
        
        self.space.add_agents(houseowners)
        net_settings = {"MAIN.scenario_id": settings.network.scenario_id}
        self.grid = sn.SHoBNetworkGrid(agents = houseowners, 
                                       model = self,
                                       geospace = self.space,
                                       settings = net_settings)
        stop_dynaconf_evaluation()
        
        start_id_intermediaries = 10**(round(math.log10(i))+1)
        
        self.energy_advisors = []
        for i in range(0, self.num_energy_advisors):
            a = EnergyAdvisor(
                unique_id=start_id_intermediaries + i,
                model=self,
                heating_preferences=Heating_preferences(table=self.milieu_table,
                                                        milieu_type="Leading"),
                known_subsidies=[Subsidy_pellet(),
                                 Subsidy_heat_pump(),
                                 Subsidy_heat_pump_brine(),
                                 Subsidy_network_local(),
                                 Subsidy_GP_Joule(),
                                 Subsidy_climate_speed(),
                                 Subsidy_income(),
                                 Subsidy_efficiency()],
                known_hs=[
                    Heating_system_electricity(),
                    Heating_system_gas(),
                    Heating_system_heat_pump(),
                    Heating_system_oil(),
                    Heating_system_pellet(),
                    Heating_system_network_district(),
                    Heating_system_network_local(),
                    Heating_system_heat_pump_brine(),
                    Heating_system_GP_Joule(),
                ],
            )
            self.energy_advisors.append(a)
            self.schedule.add(a)

        for i in range(0, self.num_plumbers):
            a = Plumber(
                unique_id=start_id_intermediaries*2 + i,
                model=self,
                heating_preferences=Heating_preferences(table=self.milieu_table,
                                                        milieu_type="Traditionals"),
                standard=Personal_standard(table=self.milieu_table),
                current_heating=Heating_system_oil(),
                cognitive_resource=settings.plumber.cognitive_resource,
                aspiration_value=settings.plumber.aspiration,
                known_hs=[
                    Heating_system_electricity(),
                    Heating_system_gas(),
                    Heating_system_heat_pump(),
                    Heating_system_oil(),
                    Heating_system_pellet(),
                    Heating_system_network_district(),
                    Heating_system_network_local(),
                    Heating_system_heat_pump_brine(),
                    Heating_system_GP_Joule()
                ],
                known_subsidies=[Subsidy_pellet,
                                 Subsidy_heat_pump(),
                                 Subsidy_heat_pump_brine(),
                                 Subsidy_network_local(),
                                 Subsidy_GP_Joule(),
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
            )
            self.schedule.add(a)

        # Setup scenario-specific changes
        self.scenario.setup(model=self)
        
        #Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "Replacements": lambda m: m.get_replacements_counter(),
                "Changes": lambda m: m.get_changes_counter(),
                "Emissions": lambda m: m.calculate_emissions(),
                "Energy demand": lambda m: m.calculate_energy_demand(),
                "Total expenses": lambda m: m.calculate_total_expenses(),
                "Scenario fulfilment": lambda m: m.calculate_target_fulfilment(
                    self.scenario
                ),
                "Trigger counter": "trigger_counter",
                "Trigger types": lambda m: m.get_triggers_by_type(),
                "Information source calls": lambda m: m.get_information_source_calls(),
                "Known heating systems": lambda m: m.count_known_hs(),
                "Known subsidies": lambda m: m.count_known_subsidies(),
                "Drop-outs": lambda m: m.get_dropouts(),
                "Subsidised houses": lambda m: m.get_subsidised_hs(),
                "Subsidies": lambda m: m.get_subsidies(),
                "Loans": lambda m: m.get_loans(),
                "Cognitive resource": lambda m: m.get_cognitive_resource(),
                "Heating distribution": lambda m: m.get_heating_distribution(),
                "Obstacles": lambda m: m.get_obstacles(),
                "Attribute ratings": lambda m: m.get_evaluation_quartiles(),
                "Houseowner spending": "houseowner_spending",
                "Stage flows": lambda m: m.get_stage_flows(),
            },
            agent_reporters={
                "Class": lambda a: a.get_class(),
                "Trigger": lambda a: a.get_trigger(),
                "Cognitive resource": "cognitive_resource",
                "Satisfaction": "satisfaction",
                "Heating": lambda a: a.get_heating(),
                "Stage": "stage_counter",  # lambda m: m.get_stage_dynamics(),
                "History": "stage_history",
                "Budget": "hs_budget",
                "Attribute ratings": lambda a: a.get_attributes(),
                "System age": lambda a: a.get_system_age(),
                "Satisfied_ratio": lambda a: a.get_satisfied_ratio(),
                "Milieu": lambda a: a.get_milieu(),
                "Suboptimality": "suboptimality",
                "Opex": lambda a: a.get_opex(),
                "Emissions": lambda a: a.get_emissions(),
                "Energy demand": lambda a: a.get_energy_demand(),
                "Preferences": lambda a: a.get_preferences(),
                "Comprehensive metrics": lambda a: a.get_comprehensive_metrics(),
                "Information_sources": "information_sources",
                "Weekly expenses": "weekly_expenses",
                "House area": lambda a: a.get_house_area(),
            },
            tables=datacollector_tables,
        )

        self.max_total_energy_demand = max(
            house.current_heating.total_energy_demand for house in self.space.agents
            if type(house).__name__ == "House"
        )  # For portrayal
        self.max_emissions = max(
            house.current_heating.params["emissions"][0] for house in self.space.agents
            if type(house).__name__ == "House"
        )  # For portrayal

        self.replacements_counter = {}  # Counts HS replacements per agent.
        self.changes_counter = {}  # Counts changes of HS technology per agent.
        self.trigger_counter = 0  # Counts triggers
        self.trigger_types_counter = {}
        self.houseowner_spending = 0
        
        options = [
            "Heating_system_oil",
            "Heating_system_gas",
            "Heating_system_heat_pump",
            "Heating_system_electricity",
            "Heating_system_pellet",
            "Heating_system_network_district",
            "Heating_system_network_local",
            "Heating_system_heat_pump_brine",
            "Heating_system_GP_Joule",
        ]
        decisions = [
            "Take_Unsubsidised",
            "Take_Unsubsidised+Loan",
            "Drop_Unsubsidised",
            "Take_Subsidised",
            "Take_Subsidised+Loan",
            "Drop_Subsidised",
        ]
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
        
        self.stage_flows = {
            "Stage_1": {"Satisfied": 0,
                        "Dissatisfied_age": 0,
                        "Dissatisfied_milieu": 0,
                        "Dissatisfied_breakdown": 0,
                        },
            "Stage_2": {"Overloaded": 0,
                        "No_affordables": 0,
                        "No_suitables": 0,
                        "Current_HS_best": 0,
                        "Found_desired": 0,
                        },
            "Stage_3": {"Desired_infeasible_to_stage_2": 0,
                        "Desired_infeasible_to_drop": 0,
                        "No_plumber_found_to_stage_2": 0,
                        "No_plumber_found_to_drop": 0,
                        "Long_waiting_time_to_stage_2": 0,
                        "Long_waiting_time_to_drop": 0,
                        "Plumber_consulted_to_stage_2": 0,
                        "Plumber_consulted_to_drop": 0,
                        "Cannot_afford_final": 0,
                        "Installed": 0,
                        },
            "Stage_4": {"Satisfied": 0,
                        "Dissatisfied": 0}
            }
        
        self.dropout_counter = pd.DataFrame(0, index=options, columns=decisions)
        self.information_source_calls = {
            f"Information_source_{source}": 0
            for source in settings.information_source.list
        }
        self.total_effort = {"Subsidies": 0,
                             "Loans": 0,
                             "Cognitive resource": 0,}
        
        for group in settings.milieu.groups:
            self.replacements_counter[group] = 0
            self.changes_counter[group] = 0

            for source in settings.information_source.list:
                self.information_source_calls[
                    f"Information_source_{source}_{group}"
                ] = 0
                
        #Resetting randomizer of the model to match custom random seeds
        self.reset_randomizer(seed=settings.seeds.model_init)

        end = time.time()
        print(f"It took {round(end - start)} seconds to initialize the model.")

    def step(self):
        """
        Executes a single time step in the simulation.

        This method advances the model by one step. It first updates dynamic 
        environmental variables (like fuel costs and subsidy availability), then 
        applies any scenario-specific impacts, activates all scheduled agents to 
        perform their actions, and finally collects all specified data for this step.
        """
        logger.info("STEP - " + str(self.schedule.steps))
        #Updating dynamic variables
        #self.update_ownership() Finalise the method first
        self.update_availability()
        self.update_contracts()
        self.update_emissions()
        self.update_fuel_costs()
        self.update_subsidies()
        # Scenario part
        self.scenario.impact(model=self)
        # Step part
        self.schedule.step()

        # Data collector part
        self.datacollector.collect(self)
        self.trigger_counter = 0

    def run(self, steps, run_id, config_id):
        """
        Runs the simulation for a specified number of steps and saves the results.

        This method iterates through the `step()` method for the given number of 
        steps. After the simulation is complete, it processes the data collected 
        by the `DataCollector` and saves it to output files (e.g., CSV, Pickle).

        Parameters
        ----------
        steps : int
            The total number of steps to run the simulation.
        run_id : str or int
            A unique identifier for this specific simulation run, used for file naming.
        config_id : str or int
            An identifier for the configuration used in this run.
        """
        print("Simulation started!")
        start = time.time()
        for _ in range(steps):
            self.step()

        output_shapefile_agents = None
        #output_shapefile_agents = f"{get_output_path(runid=run_id, subfolder='agents')}/{get_file_name(run_id)}_agents.shp"

        if output_shapefile_agents:
            gdf = self.space.get_agents_as_GeoDataFrame(agent_cls=House)

            def extract_building_properties(row):
                row["emissions"] = row["current_heating"].params["emissions"][0]
                row["age"] = row["current_heating"].age
                row["rating"] = row["current_heating"].rating
                row["milieu"] = row["houseowner"].milieu_data.milieu_type
                return row

            gdf = gdf.apply(extract_building_properties, axis=1)
            gdf = gdf.drop(
                [
                    "houseowner",
                    "current_heating",
                    "milieu",
                    "milieu_table",
                    ],
                axis=1,
            )
            gdf.to_file(output_shapefile_agents)

        end = time.time()
        print(f"It took {round(end - start)} seconds to run the model.")

        # Table results
        start = time.time()
        agent_results = self.datacollector.get_agent_vars_dataframe()
        agent_df = pd.DataFrame(agent_results)
        model_results = self.datacollector.get_model_vars_dataframe()
        model_df = pd.DataFrame(model_results)
        model_df["Average Scenario Fulfilment"] = model_df["Scenario fulfilment"].expanding().mean()
        intermediary_df = self.datacollector.get_table_dataframe(
            "Completed Intermediary Jobs"
        )
        intermediary_queue_df = self.datacollector.get_table_dataframe(
            "Intermediary Queue Length"
        )

        #Pickle the dataframes
        model_df.to_pickle(f"{get_output_path(runid=run_id, subfolder='pickles')}/model_df_{get_file_name(run_id)}.pkl")
        if settings.output.agentdata_as_pickle:
            agent_df.to_pickle(f"{get_output_path(runid=run_id, subfolder='pickles')}/agent_df_{get_file_name(run_id)}.pkl")
        if settings.output.intermediarydata_as_pickle:
            intermediary_queue_df.to_pickle(
            f"{get_output_path(runid=run_id, subfolder='pickles')}/intermediary_queue_df_{get_file_name(run_id)}.pkl")
            intermediary_df.to_pickle(f"{get_output_path(runid=run_id, subfolder='pickles')}/intermediary_df_{get_file_name(run_id)}.pkl")

        # to enable comparision
        if settings.output.resultdata_as_csv:
            intermediary_queue_df.to_csv(
                f"{get_output_path(runid=run_id, subfolder='csv')}/intermediary_queue_df_{get_file_name(run_id)}.csv"
            )
            intermediary_df.to_csv(f"{get_output_path(runid=run_id, subfolder='csv')}/intermediary_df_{get_file_name(run_id)}.csv")
            model_df.to_csv(f"{get_output_path(runid=run_id, subfolder='csv')}/model_df_{get_file_name(run_id)}.csv")
            agent_df.to_csv(f"{get_output_path(runid=run_id, subfolder='csv')}/agent_df_{get_file_name(run_id)}.csv")


        # Save the map with agents to geo-json
        # self.space.get_agents_as_GeoDataFrame().to_json()

        end = time.time()
        print(f"It took {round(end - start)} seconds to process model outputs.")

    """Methods used during runs"""
    def update_ownership(self):
        """
        NOTE: Needs to be finalised by generating a social network for the new agent,
        otherwise it will not have any connections, including spatial neighbours.
        Then the method should be called at the very beginning of every model step.
        Also needs testing. Also refactor cognitive resource, it should not be random.
        ------------------
        Simulates the change of house ownership for each houseowner.

        Iterates through all Houseowner agents and, based on a small probability,
        replaces an existing houseowner with a new one. The new houseowner is
        generated with a fresh set of socio-demographic and psychological attributes,
        but inherits the same house. The old agent is removed from the model schedule
        and space, and the new one is added.
        """
        for agent in list(self.schedule.agents):
            if isinstance(agent, Houseowner):
                if self.random.random() < settings.main.ownership_change_probability:
                    old_owner = agent
                    house = old_owner.house
                    unique_id = old_owner.unique_id
                    
                    milieu_types = settings.milieu.groups
                    new_milieu_type = rng_model_run().choice(milieu_types)
                    new_milieu = Milieu(table=self.milieu_table, 
                                        milieu_type=new_milieu_type)
                    
                    new_income = self.define_income(milieu=new_milieu.milieu_type)
                    
                    new_owner = Houseowner(
                        unique_id=unique_id,
                        house=house,
                        model=self,
                        income=new_income,
                        milieu=new_milieu,
                        cognitive_resource=rng_model_init().integers(3, 5),
                        perception=settings.houseowner.perception,
                        aspiration_value=settings.houseowner.aspiration,
                        known_hs=None,
                        suitable_hs=None,
                        desired_hs="No",
                        hs_budget=(new_income * settings.houseowner.budget_limit),
                        current_breakpoint="None",
                        current_stage="None",
                        satisfaction="Satisfied",
                        active_trigger=Trigger_none(),
                        geometry=house.geometry.centroid,
                        crs=house.crs
                    )
                    
                    new_owner.milieu = new_owner.milieu_data.milieu_type
                    new_owner.risk_tolerance = self.define_risk_tolerance(
                        milieu=new_owner.milieu_data.milieu_type
                    )
                    new_owner.loan_taking = (
                        rng_model_init().uniform() < settings.houseowner.loan_taking_probability
                    )
                    
                    new_owner.active_trigger = Trigger_owner_change()
                    
                    self.space.remove_agent(old_owner)
                    self.schedule.remove(old_owner)
                    
                    self.space.add_agents([new_owner])
                    self.schedule.add(new_owner)
                    
                    house.set_house_owner(new_owner)
                    
                    
    def update_availability(self):
        """
        Updates the availability of heating systems based on the current step.

        If a heating system's availability term has expired, it is added to the 
        list of globally infeasible options for all agents.
        """
        table = self.heating_params_table
        systems = [
            "Heating_system_oil",
            "Heating_system_gas",
            "Heating_system_heat_pump",
            "Heating_system_electricity",
            "Heating_system_pellet",
            "Heating_system_network_district",
            "Heating_system_network_local",
            "Heating_system_heat_pump_brine",
        ]
        blocked_systems = []
        self.global_infeasibles.extend(blocked_systems)
        
        for system in systems:
            system_row = table.content.loc[system]
            availability = system_row["availability"] - self.schedule.steps
            if availability <= 0:
                blocked_systems.append(system)
                
        for agent in self.schedule.agents:
            for system in blocked_systems:
                if system not in agent.infeasible:
                    agent.infeasible.append(system)
      
      
    def update_contracts(self):
        """
        Updates the remaining term of fixed-price fuel contracts for houseowners.
        """
        for agent in self.schedule.agents:
           if (isinstance(agent, Houseowner) 
               and agent.house.current_heating.fuel_price_contract_term is not None):
               agent.house.current_heating.fuel_price_contract_term -= 1
               if agent.house.current_heating.fuel_price_contract_term <= 0:
                   agent.house.current_heating.fuel_price_contract_term = None
                   
                   
    def update_emissions(self):
        """
        Updates the emissions factors for heating systems based on dynamic data.

        If the current step corresponds to a scheduled change in emissions, this 
        method updates the `heating_params_table` and recalculates the emissions 
        for all installed systems of that type.
        """
        if settings.data.dynamic == False:
            return
        emissions_dynamics = self.heating_params_dynamics_table.content.dropna(subset=['emissions']).drop(columns=['fuel_cost'])
        # Filter the dynamics table for the current step
        step_rows = emissions_dynamics[emissions_dynamics['step'] == self.schedule.steps]
    
        if step_rows.empty:
            return
    
        # For each technology with a change in emissions
        for _, row in step_rows.iterrows():
            system_name = row['name']
            new_emissions = row['emissions']
            #Update its table with the new fuel price
            self.heating_params_table.content.at[system_name, 'emissions'] = new_emissions
            
            #Update all existing systems with the new fuel price
            system_row = self.heating_params_table.content.loc[system_name]
            for agent in self.schedule.agents:
                if type(agent).__name__ == "Houseowner":
                    current_hs = agent.house.current_heating
                    if type(current_hs).__name__ == system_name:
                        current_hs.table = system_row
                        #Calculate a new total fuel cost for the system
                        new_emissions = current_hs.calculate_emissions(energy_demand 
                                                                        = current_hs.total_energy_demand)
                        current_hs.params["emissions"][0] = new_emissions
                        #Update the system in known_hs
                        for system in agent.known_hs:
                            if type(system).__name__ == system_name:
                                system.params["emissions"][0] = current_hs.params["emissions"][0]

    
    def update_fuel_costs(self):
        """
        Updates fuel costs for heating systems based on dynamic data.

        If the current step corresponds to a scheduled change in fuel price, this
        method updates the `heating_params_table` and recalculates the fuel costs
        for all installed systems not under a fixed-price contract. It may also
        trigger a `Trigger_fuel_price` for affected houseowners.
        """
        if settings.data.dynamic == False:
            return
        
        fuel_cost_dynamics = self.heating_params_dynamics_table.content.dropna(subset=['fuel_cost']).drop(columns=['emissions'])
        # Filter the dynamics table for the current step
        step_rows = fuel_cost_dynamics[fuel_cost_dynamics['step'] == self.schedule.steps]
    
        if step_rows.empty:
            return
    
        # For each technology with a change in fuel price
        for _, row in step_rows.iterrows():
            system_name = row['name']
            new_fuel_cost = row['fuel_cost']
            intervention_check = self.heating_params_table.content.at[system_name, 'en_price_reduction']
            #Update its table with the new fuel price
            if (intervention_check == 1
                and self.schedule.steps in [260, 520]):
                self.heating_params_table.content.at[system_name, 'fuel_cost'] += 0.01
            else:
                self.heating_params_table.content.at[system_name, 'fuel_cost'] = new_fuel_cost
            
            #Update all existing systems with the new fuel price
            system_row = self.heating_params_table.content.loc[system_name]
            for agent in self.schedule.agents:
                if type(agent).__name__ == "Houseowner":
                    current_hs = agent.house.current_heating
                    if type(current_hs).__name__ == system_name:
                        if current_hs.fuel_price_contract_term is not None:
                            continue
                        old_fuel_cost = current_hs.params["fuel_cost"][0]
                        #Update the fuel price in the system's table
                        current_hs.table = system_row
                        #Calculate a new total fuel cost for the system
                        new_fuel_cost = current_hs.calculate_fuel_costs(energy_demand 
                                                                        = current_hs.total_energy_demand)
                        current_hs.params["fuel_cost"][0] = new_fuel_cost
                        #Update the system in known_hs
                        for system in agent.known_hs:
                            if type(system).__name__ == system_name:
                                system.params["fuel_cost"][0] = current_hs.params["fuel_cost"][0]
                        
                        """
                        #Set up a trigger if costs are subjectively important                                      
                        pref_threshold = 1 - agent.heating_preferences.fuel_cost
                        cost_ratio = max((new_fuel_cost / old_fuel_cost) - 1, 0)
                        pref_check = cost_ratio > pref_threshold
                        if (pref_check
                            and agent.current_stage == "None"):
                            agent.active_trigger = Trigger_fuel_price()
                        """
    
    def update_subsidies(self):
        """
        Removes temporary subsidies from the model when they expire.
        """
        if self.schedule.steps == 260:
            for agent in self.schedule.agents:
                updated_dict = {}  
                for key, subsidies in agent.known_subsidies_by_hs.items():
                    updated_dict[key] = [
                        subsidy for subsidy 
                        in subsidies if subsidy.name != "Climate_speed"]
                agent.known_subsidies_by_hs = updated_dict
                
            for source in self.list_of_sources:
                updated_dict = {}  
                for key, subsidies in source.known_subsidies_by_hs.items():
                    updated_dict[key] = [
                        subsidy for subsidy 
                        in subsidies if subsidy.name != "Climate_speed"]
                source.known_subsidies_by_hs = updated_dict
    
    """Initialisation part"""
    def create_information_sources(self):
        """
        Creates and returns a list of all available information source objects.
        """
        list_of_sources = Information_source.instantiate_subclasses()
        return list_of_sources

    def determine_highest_milieu(self, row):
        """
        Defines the milieu with the highest probability
        """
        # Create a dictionary mapping the group names to their values
        groups = {
            "Leading": row["MGroup_LEA"],
            "Mainstream": row["MGroup_MAI"],
            "Traditionals": row["MGroup_TRA"],
            "Hedonists": row["MGroup_HED"],
        }
        # Find the group with the highest value
        highest_group = max(groups, key=groups.get)
        return highest_group

    def map_milieus(self, row):
        """
        Maps a milieu group number to its corresponding string label.

        Parameters
        ----------
        row : pd.Series
            A row from the GeoJSON DataFrame containing milieu group data.

        Returns
        -------
        str
            The string label for the milieu (e.g., 'Leading').
        """
        milieu_labels = {
            1: "Leading",
            2: "Mainstream",
            3: "Traditionals",
            4: "Hedonists",
        }

        mapped_milieu = (
            milieu_labels[row["MGrNum"]] if not pd.isna(row["MGrNum"]) else "Mainstream"
        )
        return mapped_milieu

    def generate_heating_system(self, oil, gas, heat, elec, pellet):
        """
        Generates a random heating system instance based on a given probability distribution.

        Parameters
        ----------
        oil, gas, heat, elec, pellet : float
            The probabilities for each respective heating system type.

        Returns
        -------
        Heating_system
            An instance of a randomly chosen heating system with a generated age.
        """
        if (
            oil + gas + heat + elec < 0.999999
            and oil + gas + heat + elec + pellet > 1.000001
        ):
            raise ValueError("Heating system distribution must sum up to 1! Restart the model with the right values.")

        systems = [
            "Heating_system_oil",
            "Heating_system_gas",
            "Heating_system_heat_pump",
            "Heating_system_electricity",
            "Heating_system_pellet",
        ]

        weights = [oil, gas, heat, elec, pellet]
        table = self.heating_params_table
        
        result = rng_model_init().choice(systems, p=weights)

        class_obj = globals()[result]
        system = class_obj(table = table)

        table_row = table.content.loc[system.__class__.__name__]
        system.age = self.generate_clipped_age(
            min_val=table_row["age_min"],
            max_val=table_row["age_max"],
            mean=table_row["age_mean"],
            sd=table_row["age_sd"],
        )
        while system.age > system.lifetime:
            system.age -= system.lifetime

        return system

    def generate_clipped_age(self, min_val, max_val, mean, sd):
        """
        Generates a system age from a truncated normal distribution.

        Returns
        -------
        int
            The generated age in simulation steps (weeks).
        """
        while True:
            sample = rng_model_init().normal(mean, sd)
            rounded_sample = round(sample)  # Round to the nearest integer
            if min_val <= rounded_sample <= max_val:
                rounded_sample = (settings.main.start_year - rounded_sample) * 52
                return rounded_sample

    def distribute_heating_systems(self):
        """
        Assigns initial heating systems to houses based on milieu-specific distributions.
        """

        # Create a dict to store all generated heating systems
        systems = {
            "Heating_system_oil": [],
            "Heating_system_gas": [],
            "Heating_system_heat_pump": [],
            "Heating_system_electricity": [],
            "Heating_system_pellet": [],
        }

        # Generate systems
        num_houses = sum(1 for house in self.space.agents if isinstance(house, House))
        for _ in range(0, num_houses):
            system = self.generate_heating_system(
                oil=0.12, gas=0.81, heat=0.04, elec=0.0, pellet=0.03
            )
            systems[system.__class__.__name__].append(system)

        # Filter houses for heat pumps
        houses_for_heat_pumps = [
            house
            for house in self.space.agents
            if type(house).__name__ == "House" and
            house.milieu.milieu_type in ("Leading", "Mainstream")
        ]

        # Shuffle the list of eligible houses
        rng_model_init().shuffle(houses_for_heat_pumps)

        # Assign heat pumps to houses
        for i, system in enumerate(systems["Heating_system_heat_pump"]):
            if i < len(houses_for_heat_pumps):
                house = houses_for_heat_pumps[i]
                if house.current_heating is None:
                    house.current_heating = system
                else:
                    print("Error: Attempted to assign multiple systems to one house.")
            else:
                break  # No more houses available

        # Filter houses without a heating system
        houses_for_other_systems = [
            house for house in self.space.agents if house.current_heating is None
            and type(house).__name__ == "House"
        ]

        # Shuffle the list of houses without a heating system
        rng_model_init().shuffle(houses_for_other_systems)

        # Index to track the current house for assignment
        current_house_index = 0

        for key, systems_list in systems.items():
            if (
                key != "Heating_system_heat_pump"
            ):  # Skip heat pumps since they're already distributed
                for system in systems_list:
                    if current_house_index < len(houses_for_other_systems):
                        house = houses_for_other_systems[current_house_index]
                        house.current_heating = system
                        current_house_index += 1
                    else:
                        print("Error: Not enough houses for all systems.")
                        break
        #Add generated systems to self.heating_distribution
        for system in systems:
            amount = len(systems[system])
            self.heating_distribution[system] = amount
    
    def define_income(self, milieu: str):
        """
        Generates a weekly income for a houseowner from a milieu-specific distribution.
        This time truncated normal.

        Parameters
        ----------
        milieu : str
            The milieu type of the houseowner.

        Returns
        -------
        int
            The generated weekly income.
        """
        if not isinstance(milieu, str):
            raise TypeError(f"Expected a string for 'milieu', but got {type(milieu).__name__}")
        
        milieu = milieu.strip().lower()
        mean = settings.houseowner[milieu].mean_savings
        stdev = settings.houseowner[milieu].stdev_savings
        lower_bound = 50
        upper_bound = 500
        
        while True:
            # Generate a value from the normal distribution
            value = rng_model_init().normal(loc=mean, scale=stdev)
            # Accept the value only if it lies within the bounds
            if lower_bound <= value <= upper_bound:
                return math.ceil(value)
            
    def define_risk_tolerance(self, milieu: str):
        """
        Defines a risk tolerance value for a houseowner based on their milieu.

        Parameters
        ----------
        milieu : str
            The milieu type of the houseowner.

        Returns
        -------
        float
            The agent's risk tolerance value.
        """
        if settings.experiments.sa_active == True:
            return settings.experiments.sa_risk_tolerance
        
        else:
            milieu_dict = {"Leading": settings.houseowner.leading.risk_tolerance,
                           "Mainstream": settings.houseowner.mainstream.risk_tolerance,
                           "Traditionals": settings.houseowner.traditionals.risk_tolerance,
                           "Hedonists": settings.houseowner.hedonists.risk_tolerance}
            
            if milieu not in milieu_dict:
                raise ValueError(f"Unknown milieu: {milieu}")
            
            if settings.houseowner.random_risk_tolerance:
                mean = np.clip(milieu_dict[milieu], 0, 1)
                std = settings.houseowner.risk_tolerance_std
                variance = std**2
            
                if mean == 0:
                    risk_tolerance = 0.0
                elif mean == 1:
                    risk_tolerance = 1.0
                else:
                    alpha_param = mean * ((mean * (1 - mean)) / variance - 1)
                    beta_param = (1 - mean) * ((mean * (1 - mean)) / variance - 1)
            
                    if alpha_param <= 0 or beta_param <= 0:
                        raise ValueError(f"Invalid alpha/beta parameters: alpha={alpha_param}, beta={beta_param}. Check mean={mean}, std={std}")
            
                    value = rng_model_init().beta(alpha_param, beta_param)
                    risk_tolerance = round(value, 2)
            else:
                risk_tolerance = milieu_dict[milieu]
            
            return risk_tolerance
    
    def define_cognitive_resource(self, milieu: str):
        """
        Produces milieu-specific cognitive resource values
        
        Parameters
        ----------
        milieu : str
            The milieu type of the houseowner.

        Returns
        -------
        int
            The agent's cognitive resource value.
        """
        if settings.experiments.sa_active == True:
            return settings.experiments.sa_cognitive_resource
        
        milieu_dict = {"Leading": settings.houseowner.leading.cognitive_resource,
                       "Mainstream": settings.houseowner.mainstream.cognitive_resource,
                       "Traditionals": settings.houseowner.traditionals.cognitive_resource,
                       "Hedonists": settings.houseowner.hedonists.cognitive_resource}
        
        if milieu not in milieu_dict:
            raise ValueError(f"Unknown milieu: {milieu}")
        
        return milieu_dict[milieu]
    
    def initial_meetings(self, agent, share = 1.0):
        """
        Performs initial knowledge spread to populate social norm-related
        memory parts of the Houseowner agents
        
        Parameters
        ----------
        agent : Houseowner
            The agent to perform meetings.
        share: float
            The share of predecessor neighbours to meet
        """  
        graph = self.grid.G
        predecessors_ids = set(graph.predecessors(agent.unique_id))

        if not predecessors_ids:
            # logger.info(f"Agent {self.unique_id} has no predecessors")
            return
        
        neighbours = self.grid.get_cell_list_contents(predecessors_ids)
        neighbour_count = len(neighbours)

        met_neighbours = set()
        meetings_number = math.ceil(neighbour_count * share)
        
        for i in range(0, meetings_number):
            unmet_neighbours = [n for n in neighbours if n not in met_neighbours]
            if unmet_neighbours:
                partner = rng_model_init().choice(unmet_neighbours)
                met_neighbours.add(partner)
    
                partner.share_system(agent)
                partner.share_satisfaction(agent)
            else:
                break

    """Data collector part """
    def calculate_emissions(self):
        """
        Calculates the mean annual emissions across all houses in the model.
        """
        calculations = []
        for house in self.space.agents:
            if type(house).__name__ == "House":
                calculation = house.current_heating.params["emissions"][0]
                calculations.append(calculation)

        emissions = pd.concat([pd.Series(calculations)]).reset_index(drop=True)
        return emissions.mean()

    def calculate_energy_demand(self):
        """
        Calculates the mean annual energy demand across all houses.
        """
        calculations = []
        for house in self.space.agents:
            if type(house).__name__ == "House":
                calculation = house.current_heating.total_energy_demand
                calculations.append(calculation)

        energy_demand = pd.concat([pd.Series(calculations)]).reset_index(drop=True)
        return energy_demand.mean()

    def calculate_total_expenses(self):
        """
        Calculates the mean Levelized Cost of Heat (LCOH) across all houses.
        """
        calculations = []
        for house in self.space.agents:
            if type(house).__name__ == "House":              
                opex = house.current_heating.params["opex"][0]
                fuel = house.current_heating.params["fuel_cost"][0]
                annual_price = (house.current_heating.params["price"][0] 
                                / house.current_heating.lifetime) * 52
                total = fuel+opex+annual_price
                total_energy_demand = house.energy_demand * house.area
                LCOH = total / total_energy_demand
                calculations.append(LCOH)
        
        total_expenses = pd.concat([pd.Series(calculations)]).reset_index(drop=True)
        return total_expenses.mean()
    
    def get_replacements_counter(self):
        """
        Returns a copy of the dictionary counting heating system replacements.
        """
        # Returns a copy to prevent the dictionary from being modified
        return self.replacements_counter.copy()

    def get_changes_counter(self):
        """
        Returns a copy of the dictionary counting changes in heating technology.
        """
        # Returns a copy to prevent the dictionary from being modified
        return self.changes_counter.copy()

    def get_information_source_calls(self):
        """
        Returns a dictionary summarising the calls to different information sources.
          """
        if self.schedule.steps == settings.main.steps:
            return self.information_source_calls
    
    def get_dropouts(self):
        """
        Returns a dictionary summarising the reasons agents dropped certain HS options.
        """
        return self.dropout_counter.to_dict(orient="index")
    
    def get_heating_distribution(self):
        """
        Returns a copy of the dictionary tracking the distribution of installed heating systems.
        """
        return deepcopy(self.heating_distribution)
    
    def get_triggers_by_type(self):
        """
        Returns a copy of the dictionary tracking the triggers.
        """
        return deepcopy(self.trigger_types_counter)
    
    def get_subsidised_hs(self):
        """
        Returns a number indicating the amount of houses 
        with a subsidised heating system.
        """
        counter = 0
        for agent in self.schedule.agents:
            if type(agent) == Houseowner:
                if agent.house.current_heating.subsidised:
                    counter += 1
        return counter
    
    def get_subsidies(self):
        """
        Returns the the volume of subsidies covered during a run
        """
        subsidies = self.total_effort["Subsidies"]
        return subsidies
    
    def get_loans(self):
        """
        Returns the the volume of loans taken during a run
        """
        loans = self.total_effort["Loans"]
        return(loans)
        
    def get_cognitive_resource(self):
        """
        Returns the the volume cognitive resource spent
        """
        cognitive_resource = self.total_effort["Cognitive resource"]
        return cognitive_resource
    
    def get_obstacles(self):
        """
        Returns counted obstacles for each heating system in a new dictionary
        """
        obstacles = deepcopy(self.obstacles)
        obstacles_counts = {
            hs_option: {obstacle: len(agent_set) for obstacle, agent_set in obstacle_dict.items()}
            for hs_option, obstacle_dict in obstacles.items()
        }
        return obstacles_counts
    
    def get_stage_flows(self):
        """Returns stage flows as a nested dictionary"""
        flows = deepcopy(self.stage_flows)
        return flows
    
    def get_evaluation_quartiles(self):
        """
        Computes quartiles of differences for each evaluation stored in evaluation_factors for all agents.
        
        For each agent that has evaluation_factors, for each outer key (system type),
        this method computes, for each evaluation column, the difference between the evaluation of an inner key 
        (target system) and the evaluation of the outer key (representative). Differences are collected from all agents.
        Finally, for each outer key and inner key, quartiles (Q1, median, Q3) are computed for each attribute.
        
        Returns
        -------
        quartile_dict : dict
            A nested dictionary where:
              - The first-level keys are the outer system types.
              - The second-level keys are the inner system types (all keys from the inner dictionary except the outer key).
              - Each inner value is a dictionary mapping each attribute to a tuple of quartiles (Q1, median, Q3)
                representing the distribution of differences (inner - outer) for that attribute.
        """  
        if self.schedule.steps == settings.main.steps:
            # differences[outer_key][inner_key] will hold a list of pd.Series differences (one per evaluation instance)
            differences = {}
        
            # Process all agents that have evaluation_factors
            for agent in self.schedule.agents:
                if not hasattr(agent, 'evaluation_factors') or not agent.evaluation_factors:
                    continue
        
                for outer_key, inner_dict in agent.evaluation_factors.items():
                    # Ensure we have a representative evaluation for the outer key (i.e., key equal to outer_key)
                    if outer_key not in inner_dict:
                        continue
        
                    rep_df = inner_dict[outer_key]  # Representative evaluation DataFrame for the outer key.
                    # For every inner key (each other system evaluation) in this dictionary...
                    for inner_key, target_df in inner_dict.items():
                        if inner_key == outer_key:
                            continue  # Skip the representative itself.
                        # Iterate over each evaluation column in target_df.
                        for col in target_df.columns:
                            # Compute difference: (target evaluation - representative evaluation)
                            diff_series = target_df[col] - rep_df[col]
                            differences.setdefault(outer_key, {}).setdefault(inner_key, []).append(diff_series)
        
            # Now, compute quartiles for each outer_key and inner_key pair.
            quartile_dict = {}
            for outer_key, inner_data in differences.items():
                quartile_dict[outer_key] = {}
                for inner_key, diff_list in inner_data.items():
                    # Create a DataFrame from the list of pd.Series differences.
                    df = pd.DataFrame(diff_list)
                    if df.empty:
                        quartile_dict[outer_key][inner_key] = {}
                    else:
                        q1 = df.quantile(0.25)
                        q2 = df.quantile(0.50)
                        q3 = df.quantile(0.75)
                        num_cases = len(df)
                        # Create a mapping for each attribute.
                        attr_quartiles = {attr: (q1[attr], q2[attr], q3[attr]) for attr in df.columns}
                        attr_quartiles["num_cases"] = num_cases
                        quartile_dict[outer_key][inner_key] = attr_quartiles
                        
            return quartile_dict
        
        else:
            return {}
    
    def get_attribute_ratings(self):
        """
        Creates a nested dictionary of quartiles of differences of opinions of all owners of non-target systems
        towards target systems relative to their owned system.
        
        Returns
        -------
        quartile_dict : dict
            A nested dictionary where:
              - The first-level keys are non-target systems (i.e. the owned system of the agent).
              - The second-level keys are target systems.
              - Each inner value is a dictionary mapping each attribute to a tuple of quartiles 
                (Q1, median, Q3) representing the distribution of differences between the target system's 
                ratings and the owned system's ratings.
        """
        
        if self.schedule.steps == settings.main.steps:
            all_systems = settings.heating_systems.list
            target_systems = list(self.scenario.hs_targets.keys())
            non_target_systems = list(set(all_systems) - set(target_systems))
            
            opinions = {
                non_target: {system: [] for system in list(target_systems) + [non_target]}
                for non_target in non_target_systems
            }
            
            # Gather opinions from all Houseowner agents.
            # For each agent with a non-target owned system, we store their attribute ratings for:
            #   - each target system, and
            #   - their own (non-target) system.
            for agent in self.schedule.agents:
                if type(agent).__name__ == "Houseowner":
                    current_system = type(agent.house.current_heating).__name__
                    if current_system in non_target_systems:
                        for system in list(target_systems) + [current_system]:
                            opinions[current_system][system].append(agent.attribute_ratings[system])
            
            # Now, compute differences (target rating minus owned rating) and then quartiles.
            quartile_dict = {}
            for non_target, systems_ratings in opinions.items():
                quartile_dict[non_target] = {}
                owned_list = systems_ratings[non_target]  # The list of owned system ratings
                # Process only target systems (i.e. keys not equal to the owned system)
                for system, ratings_list in systems_ratings.items():
                    if system == non_target:
                        continue  # Skip the owned system
                    # Make sure we have data in both lists.
                    if ratings_list and owned_list:
                        differences = []
                        for i in range(len(ratings_list)):
                            diff_series = ratings_list[i] - owned_list[i]
                            differences.append(diff_series)
                        # Create a DataFrame from the differences and compute quartiles per attribute.
                        df = pd.DataFrame(differences)
                        q1 = df.quantile(0.25)
                        q2 = df.quantile(0.50)
                        q3 = df.quantile(0.75)
                        # Save quartiles for each attribute as a tuple (Q1, median, Q3)
                        attr_quartiles = {attribute: (q1[attribute], q2[attribute], q3[attribute])
                                          for attribute in df.columns}
                        quartile_dict[non_target][system] = attr_quartiles
                    else:
                        quartile_dict[non_target][system] = {}
                       
            return quartile_dict
    
        # If not at final step, return an empty dictionary or handle accordingly.
        return {}
    
                    
    def count_known_subsidies(self):
        """
        Counts the total number of times each subsidy is known by a houseowner.
        """
        known_subsidies = defaultdict(int)
        for agent in self.schedule.agents:
            if isinstance(agent, Houseowner):
                for subsidies in agent.known_subsidies_by_hs.values():
                    for subsidy in subsidies:
                        known_subsidies[subsidy.name] += 1
        if dict(known_subsidies):
            return dict(known_subsidies)

    def count_known_hs(self):
        """
        Counts the total number of times each heating system is known by a houseowner.
        """
        known_hs = defaultdict(int)
        for agent in self.schedule.agents:
            if isinstance(agent, Houseowner):
                for hs in agent.known_hs:
                    known_hs[hs.__class__.__name__] += 1

        if dict(known_hs):
            return dict(known_hs)

    def calculate_target_fulfilment(self, scenario):
        """
        Calculate the fulfilment percentages for each heating system in the scenario.

        Parameters
        ----------
        scenario : object
            The scenario object containing the target distribution of heating systems.

        Returns
        -------
        float
            The total fulfillment percentage.
        """
        planned_state = scenario.hs_targets

        # Calculate percentages of installed systems of interest
        heating_amounts = {key: self.count_heating_system(key) for key in planned_state}

        # Weigh fulfilment percentages to calculate total fulfilment
        num_houses = sum(1 for house in self.space.agents if isinstance(house, House))
        total_fulfilment = (
            sum(heating_amounts[key] for key in heating_amounts)
            / num_houses
            * 100
        )

        return total_fulfilment

    def count_heating_system(self, heating_system):
        """
        Counts the number of houses with a specific heating system installed.

        Parameters
        ----------
        heating_system : str
            The class name of the heating system to count.

        Returns
        -------
        int
            The total count of the specified system.
        """
        count = 0
        for house in self.space.agents:
            if type(house).__name__ == "House":
                if type(house.current_heating).__name__ == heating_system:
                    count += 1
        return count

    def gather_house_data(self):
        """
        Generates an Excel file with summary data for all houses in the model.
        """

        house_data = {
            "Year": [house.year for house in self.space.agents if type(house).__name__ == "House"],
            "Area": [house.area for house in self.space.agents if type(house).__name__ == "House"],
            "Energy Demand": [house.energy_demand for house in self.space.agents if type(house).__name__ == "House"],
            "Current Heating": [
                type(house.current_heating).__name__ for house in self.space.agents
                if type(house).__name__ == "House"
            ],
            "Primary Demand": [
                house.current_heating.total_energy_demand for house in self.space.agents
                if type(house).__name__ == "House"
            ],
        }
        house_df = pd.DataFrame(house_data)
        house_df.to_excel("house_data.xlsx", index=False)
