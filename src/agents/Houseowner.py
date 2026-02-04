"""
Defines the Houseowner agent, the central decision-making entity.

This module contains the `Houseowner` class, which represents a household agent 
responsible for decisions regarding their heating system. The agent's behavior 
is driven by psychological, social, and economic factors, and follows a 
structured decision-making process based on Bamberg's Stage Model of Self-Regulated
Behavioural Change. 
The `Houseowner` interacts with other agents like 
Plumbers, Energy Advisors, and neighbors.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
 - Sören Lohr

"""
import numpy as np
import pandas as pd
import math
import shobnetpy as sn
import logging
from collections import Counter
from helpers.utils import influence_by_relative_agreement
from modules.Rng import rng_houseowner_run
from modules.Information_sources import (
    Information_source_plumber,
    Information_source_energy_advisor,
)
from modules.Triggers import *

# initialised by string in generate_system:
from modules.Heating_systems import ( # noqa # pylint: disable=unused-import
    Heating_system_oil,
    Heating_system_gas,
    Heating_system_heat_pump,
    Heating_system_heat_pump_brine,
    Heating_system_electricity,
    Heating_system_pellet,
    Heating_system_network_district,
    Heating_system_network_local,
    Heating_system_GP_Joule,
    Heating_system_vacuum_tube,
)
from interventions.Loans import Loan


logger = logging.getLogger("ahoi")
logger_rng = logging.getLogger("ahoi.rng")

class Houseowner(sn.NetworkedGeoAgent):
    """
    An agent representing a houseowner who decides on heating system replacement.

    The `Houseowner` is a `NetworkedGeoAgent` that models the complex
    decision-making process of replacing a home heating system. Its behaviour is
    influenced by personal preferences, budget, social norms, cognitive
    limitations, and external triggers (e.g., system breakdown). The agent
    progresses through distinct stages of decision-making.
    """

    def __init__(
        self,
        unique_id,
        house,
        model,
        income,
        milieu,
        cognitive_resource,
        aspiration_value,
        known_hs,
        suitable_hs,
        desired_hs,
        hs_budget,
        current_breakpoint,
        current_stage,
        satisfaction,
        active_trigger,
        geometry,
        crs
    ):
        """
        Initialising a houseowner agent.

        Parameters
        ----------
        active_trigger: Trigger
            A Trigger object representing an event that impacts the agent's decision-making.
        aspiration_value: int
            Used to define the number of options the agent gets during data gathering before it "feels" satisfied.
        attribute_ratings: dict
            Accumulated satisfaction scores of the agent for each system and parameter.
        behavioural_control_switched: bool
            Boolean indicating whether behavioural control was updated after installation.
        budget_limit: float
            Maximum amount the agent is willing or able to invest in a heating system.
        cognitive_resource: int
            The actual amount of effort the agent can allocate in a step; this value may be modified.
        comprehensive_metrics: dict
            Stores attribute-wise evaluations of heating systems made by the agent.
        consultation_ordered: bool
            A boolean indicating whether a consultation has already been ordered.
        consulted_by_energy_advisor: bool
            Indicates whether the agent has already consulted with an energy advisor.
        crs: str
            A coordinate reference system used by the agent (e.g. "epsg:4647").
        current_breakpoint: str
            The breakpoint in the decision-making sequence that the agent is currently located at.
        current_stage: str
            The current decision-making stage of the agent.
        desired_hs: Heating_system
            An instance of a Heating_system that is desirable for the replacement.
        energy_advisor: Agent
            A reference to the energy advisor agent object.
        evaluation_factors: dict
            Collects values for opinions related to each TPB factor for data collector.
        geometry: shapely
            The geographic location of the agent; used for social network generation.
        house: House
            Represents the house of the houseowner.
        hs_budget: int
            The amount of money the houseowner uses for the heating system replacement.
        income: int
            Increases the budget of the houseowner at each step.
        infeasible: list
            A list of heating system names that are not feasible for installation in the agent’s context.
        information_sources: Any
            Collection of information sources contacted by the agent for the data collector.
        initial_aspiration_value: float
            Baseline aspiration threshold, stored for potential resetting.
        initial_cognitive_resource: int
            The base cognitive resource level used to refill the effort pool at the beginning of each step.
        installed_once: bool
            Indicates whether the agent has replaced its heating system at least once.
        installation_ordered: bool
            A boolean indicating whether an installation has already been ordered.
        known_hs: list
            A list of heating systems the agent has learned about through information gathering or social interactions.
        known_subsidies_by_hs: dict
            Maps heating systems to related subsidies the agent is aware of.
        loan_taking: bool or None
            Indicates whether the agent would consider taking a loan for system purchase.
        milieu: Milieu
            An instance of the Milieu class. Contains preferences, TPB, and RA-relative variables.
        meeting_prob: float
            A probability that an idle agent will meet someone instead of idling.
        neighbours_satisfaction: dict
            Dictionary mapping neighbour IDs their satisfaction on heating systems.
        neighbours_systems: dict
            Known heating systems of neighbouring agents.
        overload_base: int
            Value defining the agent's initial cognitive overload value.
        overload_value: int
            Value defining the agent's cognitive overload threshold.
        plumber: str
            An identifier for the plumber agent who will perform consultations and installations.
        ra_exposure: float
            Exposure to others' opinions, used in the relative agreement process.
        recommended_hs: Heating_system
            A recommended system provided by an intermediary.
        risk_tolerance: float
            Value representing how risk-tolerant the agent is when selecting a system.
        satisfaction: str
            Indicates whether the agent is satisfied with its current heating system. Has only two possible values.
        source_preferences: Information_source_preferences
            Probabilities associated with choosing various types of information sources.
        stage_counter: int
            Counter used to track the number of decision-making stages completed.
        stage_history: str
            A string recording all decision-making stages the agent passed through.
        standard: Personal_standard
            A threshold object defining which heating systems are personally acceptable to the agent.
        steps: int
            Duplicates steps counter of the model, used for some data collection steps.
        subsidy_curious: bool
            Boolean indicating whether the agent is interested in learning about subsidies.
        suitable_hs: list
            A subset of `known_hs` deemed acceptable by the agent's evaluation process.
        tpb_weights: dict
            Weights for TPB components: attitude, perceived behavioural control, and social norms.
        trigger_to_report: Trigger or None
            Stores the trigger that will be reported to the data collector.
        unique_id: str
            A unique identifier, typically in the format "Houseowner *", where * corresponds to the house_id.
        unqualified_plumbers: list
            List of plumber IDs the agent will avoid calling again during a full decision cycle.
        uncertainty_factor: float
            USed during risk calculation to define the attitude towards unknown information
        visited_neighbours: set
            Neighbours the agent has interacted with to gather heating system information during one full decision cycle.
        waiting: int
            Counts waiting time for an installation.
        weekly_expenses: float
            Opex + fuel costs tracked reported to the data collector.
        """

        # Identifying parameters
        super().__init__(unique_id=unique_id,
                         model=model,
                         geometry=geometry,
                         crs=crs)
        self.house = house

        # Socio-demographic parameters
        self.income = income  # Increases the HS budget every step
        self.hs_budget = hs_budget  # Money to spend on HS
        
        self.geometry = geometry #Used to generate social networks
        self.crs = crs
        self.budget_limit = settings.houseowner.budget_limit

        # Psychological parameters
        self.milieu_data = milieu
        self.heating_preferences = (
            self.milieu_data.heating_preferences
        )  # Preferences over HS parameters
        self.attribute_ratings = {
            system: pd.Series(
                {param: 0.0 for param in settings.heating_systems.parameters}
            )
            for system in settings.heating_systems.list
        }  # Accumulated satisfaction of the owner
        self.comprehensive_metrics = {
            system: {
                param: 0 for param in settings.heating_systems.comprehensive_metrics
            }
            for system in settings.heating_systems.list
        }
        self.evaluation_factors = {}
        self.source_preferences = (
            self.milieu_data.source_preferences
        )  # Preferences over types of information sources
        self.standard = (
            self.milieu_data.standard
        )  # Threshold to define standard that HS must meet
        self.initial_aspiration_value = aspiration_value  # Used as a base value for refreshing, because the next could be modified
        self.aspiration_value = (
            self.initial_aspiration_value
        )  # Threshold to define agent's satisfaction with obtained information
        self.overload_base = settings.houseowner.overload
        self.overload_value = self.overload_base
        self.initial_cognitive_resource = cognitive_resource  # Used as a base value for refreshing, because the next could be modified
        self.cognitive_resource = (
            self.initial_cognitive_resource
        )  # Value defining amount of effort agents can perform
        self.current_breakpoint = (
            current_breakpoint  # Current breakpoint of decision-making
        )
        self.current_stage = current_stage  # Current stage of decision-making
        self.satisfaction = (
            satisfaction  # Boolean to mark whether agents is satisfied with his HS
        )
        self.active_trigger = active_trigger  # Current trigger of the agent
        self.trigger_to_report = None
        self.stage_counter = None  # [] Should be a list
        self.tpb_weights = (
            self.milieu_data.tpb_weights
        )  # Placeholder for weights for attitude, social norm and PBC
        self.ra_exposure = (
            self.milieu_data.ra_exposure
        )  # Exposure to other's opinions, used for relative agreement
        self.meeting_prob = settings.houseowner.meeting_prob

        # Heating-related parameters
        self.known_hs = known_hs if known_hs is not None else []
        self.suitable_hs = suitable_hs if suitable_hs is not None else []
        self.neighbours_systems = {} # {neighbour_id: system_name}
        self.visited_neighbours = set()
        self.recommended_hs = None
        self.desired_hs = desired_hs
        self.infeasible = []
        self.neighbours_satisfaction = {}
        self.known_subsidies_by_hs = {}
        self.subsidy_curious = False
        self.loan_taking = None
        self.risk_tolerance = None
        self.uncertainty_factor = None
    
        # Installation-related parameters
        # Plumber agent, which will be called by the agent for consultation & installation
        self.plumber = None
        self.unqualified_plumbers = []
        self.energy_advisor = None
        self.consulted_by_energy_advisor = False
        self.consultation_ordered = False
        self.installation_ordered = False
        self.waiting = 0
        # Indicates if the owner replaced his HS at least once
        self.suboptimality = None
        # Gathers all stages, which the owner has passed during a run
        self.stage_history = ""

        # Used to help save the behavioural control, only once, after the installation
        self.installed_once = False
        self.behavioural_control_switched = False
        self.steps = settings.main.steps
        self.information_sources = None
        self.weekly_expenses = None

    def step(self):
        """
        Executes the agent's actions for a single simulation step.

        This method handles the agent's behaviour. It refills cognitive
        resources, manages the budget, checks for triggers, and, if a decision
        process is active, proceeds through the relevant stages. If not in a
        decision process, the agent may engage in social interactions.
        """
        # logger.info("AGENT {}'s turn".format(self.unique_id))
        # self.stage_counter.clear()
        self.stage_history = ""
        self.cognitive_resource = (
            self.initial_cognitive_resource
        )  # Refills cognitive resource with agent-specific value
        self.manage_budget()
        self.investigate_house()
        self.trigger_check()
        self.active_trigger.impact(self)
        # logger.info("Trigger: " + str(type(self.active_trigger).__name__))
        # logger.info("Breakpoint: " + str(self.current_breakpoint))
        # logger.info("Stage: " + str(self.current_stage))
        # Drop current trigger so it is not stuck in agent's memory
        self.trigger_to_report = self.active_trigger
        if type(self.active_trigger).__name__ != "Trigger_none":
            for hs_option in self.model.scenario.hs_targets.keys():
                self.model.obstacles[hs_option]["Triggered"].add(self.unique_id)
        self.active_trigger = Trigger_none()

        if self.current_stage != "None":
            while (
                self.cognitive_resource > 0 and self.current_stage != "None"
            ):  # Loops through the decision-making unless tired
                if self.current_breakpoint == "None":  # Enter stage 1
                    self.stage_counter = 1  
                    self.stage_history += "1"
                    self.evaluate()  
                    if self.satisfaction == "Satisfied":
                        # Breaks the loop when satisfied
                        break
                elif self.current_breakpoint == "Goal":  # Enter stage 2, 
                    for hs_option in self.model.scenario.hs_targets.keys():
                        self.model.obstacles[hs_option]["Deciding"].add(self.unique_id)
                    self.stage_counter = 2
                    self.stage_history += "2"
                    self.get_data()
                    if self.cognitive_resource == 0:
                        break
                    self.define_choice()  
                    if self.cognitive_resource == 0:
                        break
                    self.compare_hs()  
                elif self.current_breakpoint == "Behaviour":  # Enter stage 3
                    for hs_option in self.model.scenario.hs_targets.keys():
                        self.model.obstacles[hs_option]["Deciding"].add(self.unique_id)
                    self.stage_counter = 3  
                    self.stage_history += "3"
                    self.install()  
                elif self.current_breakpoint == "Implementation":  # Enter stage 4
                    for hs_option in self.model.scenario.hs_targets.keys():
                        self.model.obstacles[hs_option]["Deciding"].add(self.unique_id)
                    self.stage_counter = 4  
                    self.stage_history += "4"
                    self.calculate_satisfaction()  
            
            spent_resource = (self.initial_cognitive_resource 
                              - self.cognitive_resource)
            self.model.total_effort["Cognitive resource"] += spent_resource
            
        else:
            """Here are some agent's interactions"""
            self.stage_counter = 0
            self.stage_history += "0"
            self.waiting = 0
            self.aspiration_value = self.initial_aspiration_value
            self.overload_value = self.overload_base
            if (
                rng_houseowner_run().uniform(0, 1) < self.meeting_prob
            ):
                # logger.info("I'll go and meet someone!")
                self.meet_agent()
            else:  # Or just does nothing
                # logger.info("I am doing nothing today!")
                pass

        self.house.current_heating.age += 1
        # logger.info("           ")

    def evaluate(self):
        """
        Assesses satisfaction with the current heating system.

        The agent checks if their current heating system still meets their personal
        standard. If not, they become 'Dissatisfied' and move to the next
        decision-making stage ('Goal' breakpoint). Otherwise, they remain
        'Satisfied' and exit the decision process for this step.
        """
        cost = settings.decision_making_costs.evaluate
        if self.cognitive_resource < cost:
            # logger.info("Tired: EVALUATION BEGINNING")
            self.cognitive_resource = 0

        else:
            self.cognitive_resource -= cost
            if (
                self.check_standard(self.house.current_heating) == True
            ):  # If the heating system is still suitable
                # logger.info("My current heating system satisfies me")
                self.current_stage = "None"
                self.satisfaction = "Satisfied"
                self.model.stage_flows["Stage_1"]["Satisfied"] += 1
            else:
                # logger.info("I want to change my heating system!")
                self.current_breakpoint = "Goal"
                self.current_stage = "Stage 2"
                self.satisfaction = "Dissatisfied"
                #Dissatisfaction is incremented in check_standard
                

    def get_data(self):
        """
        Gathers information about heating systems from various sources.

        The agent chooses an information source based
        on their milieu-specific preferences. They then perform a data search,
        which consumes cognitive resources. The process stops when the agent's
        aspiration level is met, they run out of cognitive resources, or they
        are waiting for a scheduled consultation.
        """       
        if (
            self.aspiration_value == 0
        ):  # Checks whether the agent has enough of information
            # logger.info("I already know enough!")
            pass

        elif (
            self.consultation_ordered == True
        ):  # Checks whether a consultation has already been ordered
            # logger.info("I wait for my queue to come")
            self.cognitive_resource = 0

        else:  # Three different data gathering strategies depending on the chosen source
            weights = list(
                vars(self.source_preferences).values()
            )  # To use inform. source preferences as probabilities
            if self.house.current_heating.breakdown:
                # Extract weights only for plumber and energy_advisor
                weights_plumber_advisor = [
                    vars(self.source_preferences)["plumber"],
                    vars(self.source_preferences)["energy_advisor"]
                ]
                
                # Normalize the weights to sum to 1
                total_weight = sum(weights_plumber_advisor)
                normalized_weights = [weight / total_weight for weight in weights_plumber_advisor]
                
                sources_plumber_advisor = ["plumber", "energy_advisor"]
                chosen_source_str = rng_houseowner_run().choice(
                    sources_plumber_advisor, p=normalized_weights, replace=True
                )
                
                # Map the chosen source to the respective class
                if chosen_source_str == "plumber":
                    chosen_source = Information_source_plumber()
                else:
                    chosen_source = Information_source_energy_advisor()

            else:
                chosen_source = rng_houseowner_run().choice(
                    self.model.list_of_sources, p=weights, replace=True
                )  # The agent chooses a source
            self.model.information_source_calls[chosen_source.__class__.__name__] += 1
            self.model.information_source_calls[
                f"{chosen_source.__class__.__name__}_{self.house.milieu.milieu_type}"
            ] += 1
            self.information_sources = chosen_source.__class__.__name__.replace(
                "Information_source_", ""
            )
            # logger.info("I have chosen {} as a source".format(chosen_source))

            cost = settings.decision_making_costs.get_data

            if self.cognitive_resource < cost:
                # logger.info("Tired: DATA GATHERING BEGINNING")
                self.ask_neighbours(coverage = self.cognitive_resource)
                self.cognitive_resource = 0
            
            else: 
                chosen_source.data_search(agent=self, cost=cost)
    
    def define_choice(self):
        """
        Filters known heating systems to create a list of suitable options.

        The agent evaluates all known heating systems against several criteria:
        - Technical feasibility (not in the `infeasible` list).
        - Affordability of installation, either directly from their budget or
          with the help of a potential loan.
        - Affordability of running costs relative to their income.
        - Risk tolerance, filtering out options perceived as too risky.
        Systems that pass these checks are added to the `suitable_hs` list.
        """
        cost = settings.decision_making_costs.define_choice
        targets = self.model.scenario.hs_targets.keys()
        
        # Pre-calculate known names for fast lookup
        known_hs_names = {type(hs).__name__ for hs in self.known_hs}

        for hs_option in targets:
            if hs_option in known_hs_names:
                self.model.obstacles[hs_option]["Knowledge"].add(self.unique_id)
        
        if self.suitable_hs and self.consulted_by_energy_advisor:
            # Use set for fast check
            suitable_names_set = {type(hs).__name__ for hs in self.suitable_hs}
            for hs_option in targets:
                if hs_option in suitable_names_set:
                    self.model.obstacles[hs_option]["Affordability"].add(self.unique_id)
                    self.model.obstacles[hs_option]["Riskiness"].add(self.unique_id)
            return  
        
        if self.cognitive_resource < cost:
            # logger.info("Tired: CHOICE DEFINITION BEGINNING")
            self.cognitive_resource = 0

        else:
            self.cognitive_resource -= cost

            if logger_rng.isEnabledFor(logging.DEBUG):
                logger_rng.debug(f"{self}: Known HS: {self.known_hs}")
            
            # Lift invariant calculations out of the loop
            current_hs = self.house.current_heating
            current_fuel_cost = current_hs.params["fuel_cost"][0] / 52
            current_opex = current_hs.params["opex"][0] / 52
            current_total_running = current_fuel_cost + current_opex
            
            current_burden = 0
            if current_hs.loan is not None:
                current_burden = current_hs.loan.monthly_payment / 4
            
            # Maintain a set of suitable names to avoid O(N^2) behavior
            suitable_names_set = {type(o).__name__ for o in self.suitable_hs}

            # Local dictionary to batch updates
            # Key: (row_index, col_name), Value: count
            pending_dropout_updates = {}
                                    
            for option in self.known_hs:
                # Cache the name once
                option_name = type(option).__name__

                if (option.subsidised == False
                    and not option.source == "Internet"
                    and type(option).__name__ in self.known_subsidies_by_hs):
                    self.apply_subsidies(option)
                self.calculate_attitude(option)
                
                # Known HS has not to be known as infeasible
                is_feasible = option_name not in self.infeasible
                
                # Installation of the HS has to be affordable...
                price = option.params["price"][0]
                installation_affordable = (price <= self.hs_budget)
                
                loan_affordable = False
                
                # ...or a loan could cover their expenses
                if not installation_affordable:
                    self.find_loan(option)
                    if option.loan:
                        loan_affordable = (price <= self.hs_budget + option.loan.loan_amount)
                
                # Costs of the HS have to be affordable
                new_fuel_cost = option.params["fuel_cost"][0] / 52
                new_opex = option.params["opex"][0] / 52
                
                # Use pre-calculated current costs
                difference = (new_fuel_cost + new_opex) - current_total_running

                if loan_affordable:
                    payment = option.loan.monthly_payment / 4
                    difference += payment
                    
                costs_affordable = self.income - difference - current_burden >= 0
                
                # The agent adds HS to the list of suitable HS
                if is_feasible and costs_affordable:
                    if installation_affordable:
                        if option_name not in suitable_names_set:
                            self.suitable_hs.append(option)
                            suitable_names_set.add(option_name)
                        
                        # Batch Update: Take_Unsubsidised
                        key = (option_name, "Take_Unsubsidised")
                        pending_dropout_updates[key] = pending_dropout_updates.get(key, 0) + 1
                        
                    elif loan_affordable:
                        if option_name not in suitable_names_set:
                            self.suitable_hs.append(option)
                            suitable_names_set.add(option_name)
                            
                        # Batch Update: Take_Unsubsidised+Loan
                        key = (option_name, "Take_Unsubsidised+Loan")
                        pending_dropout_updates[key] = pending_dropout_updates.get(key, 0) + 1
                        
                    else:
                        self._log_drop(option, is_feasible, installation_affordable, loan_affordable, costs_affordable)
                        # Batch Update: Drop_Unsubsidised
                        key = (option_name, "Drop_Unsubsidised")
                        pending_dropout_updates[key] = pending_dropout_updates.get(key, 0) + 1
                else:
                    self._log_drop(option, is_feasible, installation_affordable, loan_affordable, costs_affordable)
                    # Batch Update: Drop_Unsubsidised
                    key = (option_name, "Drop_Unsubsidised")
                    pending_dropout_updates[key] = pending_dropout_updates.get(key, 0) + 1
            
            # Update obstacles based on suitable list (suitable_names_set is up to date)
            for hs_option in targets:
                if hs_option in suitable_names_set:
                    self.model.obstacles[hs_option]["Affordability"].add(self.unique_id)
            
            # Calculate risks for each system
            for system in self.suitable_hs:
                system.calculate_risk(agent=self)
            
            # Sort systems in descending order by riskiness (most risky first)
            self.suitable_hs.sort(key=lambda system: system.riskiness, reverse=True)
            
            # Remove the risky systems
            self.suitable_hs = [
                hs for hs in self.suitable_hs 
                if hs.riskiness <= self.risk_tolerance
                ]

            # Re-sync names after popping for the next check
            suitable_names_set = {type(hs).__name__ for hs in self.suitable_hs}

            for hs_option in targets:
                if hs_option in suitable_names_set:
                    self.model.obstacles[hs_option]["Riskiness"].add(self.unique_id)
                    
            if self.suitable_hs:
                pass

            elif (
                self.house.current_heating.breakdown == True
                and self.recommended_hs != None
            ):
                # Fallback Logic
                if (self.recommended_hs.subsidised == False
                    and type(self.recommended_hs).__name__ in self.known_subsidies_by_hs):
                    self.apply_subsidies(self.recommended_hs)
                
                rec_price = self.recommended_hs.params["price"][0]
                can_afford_rec = self.hs_budget >= rec_price
                rec_name = type(self.recommended_hs).__name__

                if (not can_afford_rec
                    and not self.recommended_hs.subsidised
                    and rec_name not in self.known_subsidies_by_hs
                    and not self.consulted_by_energy_advisor):
                    
                    self.subsidy_curious = True
                    self.cognitive_resource = 0
                    self.aspiration_value = self.initial_aspiration_value
                
                elif not can_afford_rec:
                    key = (rec_name, "Drop_Subsidised")
                    pending_dropout_updates[key] = pending_dropout_updates.get(key, 0) + 1
                    
                    # Iterating loan finding for side-effects and selection
                    budget_filtered = []
                    for system in self.known_hs:
                        if type(system).__name__ not in self.infeasible:
                            if (system.subsidised == False
                                and type(system).__name__ in self.known_subsidies_by_hs):
                                self.apply_subsidies(system)
                            
                            self.find_loan(system, bypass_avoidance = True)
                            
                            loan_amount = system.loan.loan_amount if system.loan else 0
                            if self.hs_budget + loan_amount >= system.params["price"][0]:
                                budget_filtered.append(system)
                    
                    if budget_filtered:
                        self.recommended_hs = deepcopy(min(budget_filtered, key=lambda x: x.params["price"][0]))
                    
                    else:
                        print("An agent cannot afford any system in the model!")
                        self.model.stage_flows["Stage_2"]["No_affordables"] += 1
                        self.aspiration_value = self.initial_aspiration_value
                        self.overload_value = self.overload_base
                        self.recommended_hs = None
                        self.current_stage = "None"
                        self.cognitive_resource = 0
                                
                else:
                    pass

            else:
                self.model.stage_flows["Stage_2"]["No_suitables"] += 1
                self.aspiration_value = self.initial_aspiration_value
                self.overload_value = self.overload_base
                self.current_stage = "None"
                self.cognitive_resource = 0

            # Perform all dataframe updates at once
            for (idx, col), val in pending_dropout_updates.items():
                self.model.dropout_counter.loc[idx, col] += val

    def _log_drop(self, option, is_feasible, installation_affordable, loan_affordable, costs_affordable):
        """Helper to reduce clutter in the main loop"""
        if logger_rng.isEnabledFor(logging.DEBUG):
             logger_rng.debug(f"{self}: Option {option} not added to suitable HS "
                              + f"(feasibility: {is_feasible} / Affordability: {installation_affordable} /"
                              + f" Loan affordability: {loan_affordable} / costs affordable: {costs_affordable}) ")

    def compare_hs(self):
        """
        Compares suitable heating systems and selects the most desired one.

        Using the Theory of Planned Behaviour, the agent calculates an integral
        rating for each system in `suitable_hs`. The system with the highest
        rating is chosen as the `desired_hs`. A tie-breaking rule is applied
        if the top two options have very similar ratings.
        """
        cost = settings.decision_making_costs.compare_hs

        if self.cognitive_resource < cost:
            # logger.info("Tired: COMPARISON BEGINNING")
            self.cognitive_resource = 0

        elif self.suitable_hs == []:
            # Behaviour if no system is seen to be good enough, but the decision still has to be made
            # logger.info("Someone helped me to make a decision!")
            self.cognitive_resource -= cost
            self.desired_hs = self.recommended_hs
            # logger.info("I have decided to install {}!".format(type(self.desired_hs).__name__))
            self.current_stage = "Stage 3"
            self.current_breakpoint = "Behaviour"
            self.aspiration_value = (
                self.initial_aspiration_value
            )  # Reset aspiration when the choice is made
            self.model.stage_flows["Stage_2"]["Found_desired"] += 1

        elif self.suitable_hs:
            # Normal situation when at least 1 system is suitable
            self.cognitive_resource -= cost
            integral_ratings = (
                self.calculate_integral_rating()
            )  # Dict {Instance: rating}
            sorted_integral_ratings = sorted(
                integral_ratings.items(), key=lambda item: item[1]
            )
            best = sorted_integral_ratings[-1][0]  # The best HS according to ratings
            best_rating = sorted_integral_ratings[-1][1]

            # The problem of close alternatives
            similarity_measure = 1.1
            if (len(sorted_integral_ratings) > 1 
                and sorted_integral_ratings[-2][1] * similarity_measure > best_rating):
                # The choice is too difficult, agent tosses a coin
                self.cognitive_resource -= cost
                result = rng_houseowner_run().choice([best, 
                                                      sorted_integral_ratings[-2][0]]
                )
                self.desired_hs = deepcopy(result)
            else:
                # Agent has no problem choosing the best option
                self.desired_hs = deepcopy(best)
            
            #If the desired hs is the same as the current and still running, 
            #it will not be replaced unless it is expected 
            #that it will be banned in the near future.
            availability = (self.house.current_heating.availability 
                            - self.model.schedule.steps)
            if (type(self.desired_hs) == type(self.house.current_heating)
                     and not self.house.current_heating.breakdown
                     and not availability in range(0, 105)):
                     self.desired_hs = "No"
                     self.suitable_hs = []
                     self.current_stage = "None"
                     self.current_breakpoint = "None"
                     self.cognitive_resource = 0
                     self.aspiration_value = self.initial_aspiration_value
                     self.overload_value = self.overload_base
                     self.model.stage_flows["Stage_2"]["Current_HS_best"] += 1
            else:
                # logger.info("Decided to install {}!".format(type(self.desired_hs).__name__))
                self.current_stage = "Stage 3"
                self.current_breakpoint = "Behaviour"
                # Reset aspiration and overload when the choice is made
                self.aspiration_value = self.initial_aspiration_value
                self.overload_value = self.overload_base
                #Gather metrics when the desired_hs is not a target hs
                self.store_evaluations()
                self.model.stage_flows["Stage_2"]["Found_desired"] += 1
                                   
        for hs_option in self.model.scenario.hs_targets.keys():
            if hs_option == type(self.desired_hs).__name__:
                self.model.obstacles[hs_option]["Evaluation"].add(self.unique_id)

    def install(self):
        """
        Manages the process of ordering and installing a heating system.

        The agent finds a qualified plumber for their `desired_hs`, checks for
        excessive queue times, and confirms final affordability. If all checks
        pass, they order a consultation (which leads to installation) from the
        plumber and wait. If any issues arise (e.g., the system is found to be
        infeasible), the agent may reconsider their choice or exit the process.
        """
        cost = settings.decision_making_costs.install      

        if (
            type(self.house.current_heating).__name__ == type(self.desired_hs).__name__
            and self.house.current_heating.age == 0
        ):  # Checks whether chosen HS has been installed
            # logger.info("I have {} installed!".format(type(self.house.current_heating).__name__))
            self.current_stage = "Stage 4"
            self.current_breakpoint = "Implementation"
            self.waiting = 0
            self.model.stage_flows["Stage_3"]["Installed"] += 1
            for hs_option in self.model.scenario.hs_targets.keys():
                if hs_option == type(self.house.current_heating).__name__:
                    self.model.obstacles[hs_option]["Feasibility"].add(self.unique_id)
                    self.model.obstacles[hs_option]["Affordability"].add(self.unique_id)
                    self.model.obstacles[hs_option]["Riskiness"].add(self.unique_id)
                    self.model.obstacles[hs_option]["Evaluation"].add(self.unique_id)
                    self.model.obstacles[hs_option]["Knowledge"].add(self.unique_id)
                    

        elif (self.consultation_ordered == True
              or self.installation_ordered == True):
            # logger.info("I wait for my queue to come")
            self.cognitive_resource = 0
            self.waiting += 1
        
        elif self.cognitive_resource < cost:
            # logger.info("Tired: PLANNING BEGINNING")
            self.cognitive_resource = 0  # To break the loop during the step

        elif (
            type(self.desired_hs).__name__ in self.infeasible
        ):  # Checks whether the desired HS is infeasible
            self.cognitive_resource -= cost
            self.waiting = 0
            
            # logger.info("My chosen heating cannot be installed!")
            for system in self.suitable_hs:  # Remove infeasible HS from suitable HS
                if type(system).__name__ == type(self.desired_hs).__name__:
                    self.suitable_hs.remove(system)
            self.desired_hs = "No"  # Remove infeasible HS from desired HS
            if self.suitable_hs:  # If something suitable is left...
                self.model.stage_flows["Stage_3"]["Desired_infeasible_to_stage_2"] += 1
                self.current_stage = "Stage 2"
                self.current_breakpoint = "Goal"
                self.aspiration_value = 0
                self.overload_value = self.overload_base
                return
            else:  # Otherwise, drop
                self.model.stage_flows["Stage_3"]["Desired_infeasible_to_drop"] += 1
                self.current_stage = "None"
                self.current_breakpoint = "None"
                self.aspiration_value = self.initial_aspiration_value
                self.overload_value = self.overload_base

        elif (
            type(self.desired_hs).__name__ not in self.infeasible
        ):  # Desired HS is perceived as feasible
            # The agent plans the installation
            # logger.info("Planning installation!")
            self.cognitive_resource -= cost
            if self.plumber == None:  # Finds a plumber if there is still none
                self.find_plumber_with_desired_hs()
                # If agent doesn't find a plumber for the desired heating system, he quits
                if self.plumber == None:
                    # logger.info(f"{self.unique_id} has not found a plumber that can install his desired system.")
                    self.desired_hs = "No"
                    if self.suitable_hs:  # If something suitable is left...
                        self.model.stage_flows["Stage_3"]["No_plumber_found_to_stage_2"] += 1
                        self.current_stage = "Stage 2"
                        self.current_breakpoint = "Goal"
                        self.aspiration_value = 0
                        self.overload_value = self.overload_base
                        return
                    else:  # Otherwise, drop
                        self.model.stage_flows["Stage_3"]["No_plumber_found_to_drop"] += 1
                        self.current_stage = "None"
                        self.current_breakpoint = "None"
                        self.aspiration_value = self.initial_aspiration_value
                        self.overload_value = self.overload_base
                        return
                    
            #Installation time check
            estimated_queue = self.plumber.estimate_queue_time(q_type = "Installation")
            estimated_installation = (self.plumber.Services[1].duration + 
                                      self.desired_hs.installation_time)
            if (estimated_queue + estimated_installation > 52
                and not self.recommended_hs):
                #logger.info(f"Waiting time is too long, drop desired {type(self.desired_hs)}")
                self.waiting = 0
                self.suitable_hs = [
                    system for system in self.suitable_hs if type(system).__name__ != type(self.desired_hs).__name__
                    ]
                for system in self.suitable_hs:  # Remove infeasible HS from suitable HS
                    if type(system).__name__ == type(self.desired_hs).__name__:
                        self.suitable_hs.remove(system)
                self.desired_hs = "No"  # Remove infeasible HS from desired HS
                if self.suitable_hs:  # If something suitable is left...
                    self.model.stage_flows["Stage_3"]["Long_waiting_time_to_stage_2"] += 1
                    self.current_stage = "Stage 2"
                    self.current_breakpoint = "Goal"
                    self.cognitive_resource = 0
                    self.aspiration_value = 0
                    self.overload_value = self.overload_base
                    return
                else:
                    self.model.stage_flows["Stage_3"]["Long_waiting_time_to_drop"] += 1
                    self.current_stage = "None"
                    self.current_breakpoint = "None"
                    self.cognitive_resource = 0
                    self.aspiration_value = self.initial_aspiration_value
                    self.overload_value = self.overload_base
                    return
                            
            #Final budget check
            disposable_budget = (
                self.hs_budget + self.desired_hs.loan.loan_amount
                if self.desired_hs.loan else self.hs_budget
                )
                
            can_afford_hs = disposable_budget >= self.desired_hs.params["price"][0]

            if not can_afford_hs:
                # logger.info("I don't have enough money! I'll find a loan")
                self.find_loan(self.desired_hs, 
                               bypass_avoidance = True)
                self.cognitive_resource = 0
                if not self.desired_hs.loan:
                    self.model.stage_flows["Stage_3"]["Cannot_afford_final"] += 1
                    self.current_stage = "None"
                    self.current_breakpoint = "None"
                    self.cognitive_resource = 0
                    self.aspiration_value = self.initial_aspiration_value
                    self.overload_value = self.overload_base
                    return
                          
            elif can_afford_hs:
                if self.consulted_by_energy_advisor:
                    self.order_installation()
                    self.consulted_by_energy_advisor = False
                    # logger.info("I have ordered an installation from my plumber!")
                    self.cognitive_resource = 0
                else:
                    self.order_plumber()  # Orders a consultation. The plumber will carry out the rest.
                    # logger.info("I have ordered a consultation from my plumber!")
                    self.cognitive_resource = 0

        else:
            #For debugging
            raise Exception("Installation algorithm encountered an unexpected condition.")

    def calculate_satisfaction(self):
        """
        Evaluates satisfaction with the newly installed heating system.

        After installation, the agent compares the actual performance and costs
        of the new system with their prior expectations. They also assess if their
        choice was suboptimal compared to other suitable alternatives they knew of.
        This determines their new satisfaction state.
        """

        cost = settings.decision_making_costs.calculate_satisfaction

        if self.cognitive_resource < cost:
            # logger.info("Tired: SATISFACTION ASSESSMENT")
            self.cognitive_resource = 0  # To break the loop during the step

        else:
            # logger.info("I want to assess my satisfaction")
            self.cognitive_resource -= cost
            self.known_hs = [
                x
                for x in self.known_hs
                if type(x).__name__ != type(self.desired_hs).__name__
            ]  # Drops the instance with the "expected" rating from known
            
            self.known_hs.append(
                deepcopy(self.house.current_heating)
            )  # Adds the instance with the "real" values to known
            
            for system in self.known_hs:
                self.calculate_attitude(system)
                if type(system).__name__ == type(self.house.current_heating).__name__:
                    self.house.current_heating.rating = system.rating
                    rating_true = self.house.current_heating.rating

            # Calculate suboptimality of the choice
            self.get_optimality()
            self.subsidy_curious = False

            if len(self.suitable_hs) > 1:
                sorted_suitable = sorted(self.suitable_hs, key=lambda x: x.rating)
                second_best = sorted_suitable[-2]  # Get the second best option
                # Get the attitude towards the second best
                rating_second_best = second_best.rating
                # logger.info("The second best {} option has {} rating".format(second_best.__class__.__name__, rating_second_best))

                # If installed HS is worse than the second best
                if rating_second_best > rating_true:
                    # logger.info("The second best option has {} rating, but the rating of my new heating is {}!".format(rating_second_best, rating_true))
                    # logger.info("I am not satisfied!")
                    self.model.stage_flows["Stage_4"]["Dissatisfied"] += 1
                    self.satisfaction = "Dissatisfied"
                    self.current_breakpoint = "None"
                    self.current_stage = "None"
                    self.cognitive_resource = 0  # To break the loop during the step
                else:
                    # logger.info("I am satisfied!")
                    self.model.stage_flows["Stage_4"]["Satisfied"] += 1
                    self.satisfaction = "Satisfied"
                    if (settings.triggers.adoptive_trigger 
                        == type(self.house.current_heating).__name__):
                        self.share_decision(iterations = self.cognitive_resource)
                    self.current_breakpoint = "None"
                    self.current_stage = "None"
                    self.cognitive_resource = 0  # To break the loop during the step

            else:
                # logger.info("I am satisfied!")
                self.model.stage_flows["Stage_4"]["Satisfied"] += 1
                self.satisfaction = "Satisfied"
                if (settings.triggers.adoptive_trigger 
                        == type(self.house.current_heating).__name__):
                    self.share_decision(iterations = self.cognitive_resource)
                self.current_breakpoint = "None"
                self.current_stage = "None"
                self.cognitive_resource = 0  # To break the loop during the step

            """Clear suitable, desired, and recommended HS"""
            self.suitable_hs.clear()
            self.desired_hs = "No"
            self.recommended_hs = None
            self.visited_neighbours = set()
            self.unqualified_plumbers = []
            self.infeasible = deepcopy(self.model.global_infeasibles)
            self.consulted_by_energy_advisor = False
            if (self.house.subarea == "Sued"
                and type(self.model.scenario).__name__ == "Scenario_mix_pellet_heat_pump_network"):
                self.infeasible.append("Heating_system_network_local")

    """Trigger part
    Contains methods connected to triggers of the agent
    """

    def trigger_check(self):
        """
        Checks for internal or environmental events that trigger a decision process.
        """
        remaining_lifetime = (self.house.current_heating.lifetime 
                              - self.house.current_heating.age)
        availability = (self.house.current_heating.availability 
                        - self.model.schedule.steps) 
        if (
            self.house.current_heating.breakdown == True
            and self.current_stage == "None"
            ):
            self.active_trigger = Trigger_breakdown()
            self.model.stage_flows["Stage_1"]["Dissatisfied_breakdown"] += 1
            # logger.info("My HS has broken down! A disaster!")
        elif (availability > 0
              and availability < 104
              and remaining_lifetime < 208
              and self.current_stage == "None"
              ):
            self.active_trigger = Trigger_availability()
        
    """Agent interaction part
    Contains methods of agent interaction. Has several subparts.
    """

    def meet_agent(self):
        """
        The agent meets another random agent and exchanges 
        knowledge and opinions. In case the other agent is a successor,
        the focal agent influences this successor, in case the other agent is 
        a predecessor, the predecessor influences the focal agent.
        Simulates random social interactions.
        """
        graph = self.model.grid.G
        predecessors_ids = set(graph.predecessors(self.unique_id))
        successors_ids = set(graph.successors(self.unique_id))
        all_ids = list(predecessors_ids.union(successors_ids))

        if not all_ids:
            # logger.info(f"Agent {self.unique_id} isolated")
            return
        
        partner_id = rng_houseowner_run().choice(all_ids)
        partner = self.model.grid.get_cell_list_contents([partner_id])[0]

        # Note: These are not mutually exclusive (bidirectional links exist)
        is_successor = partner_id in successors_ids
        is_predecessor = partner_id in predecessors_ids

        # ---------------------------------------------------------
        # CASE A: I influence the Partner (Successor)
        # ---------------------------------------------------------
        if is_successor:
            # Conditions: I am satisfied, systems differ, and MY system is new
            self.share_system(partner)
            self.share_satisfaction(partner)
            if (
                self.satisfaction == "Satisfied"
                and type(self.house.current_heating)
                != type(partner.house.current_heating)
                and self.house.current_heating.age <= 4
                and partner.current_stage == "None"
            ):
                partner.active_trigger = Trigger_neighbour_jealousy()
                # logger.info(f"Agent {partner_id} is jealous of my {type(self.house.current_heating).__name__}")

        # ---------------------------------------------------------
        # CASE B: Partner influences Me (Predecessor)
        # ---------------------------------------------------------
        if is_predecessor:
            partner.share_system(self)
            partner.share_satisfaction(self)
            if (
                partner.satisfaction == "Satisfied"
                and type(partner.house.current_heating)
                != type(self.house.current_heating)
                and partner.house.current_heating.age <= 4
                and self.current_stage == "None"
            ):
                self.active_trigger = Trigger_neighbour_jealousy()
                # logger.info(f"I am jealous of neighbour {partner_id}'s {type(partner.house.current_heating).__name__}")
    
    def ask_neighbours(self, coverage):
        """
        Asks neighbour about their systems as long as there is cognitive resource and 
        neighbours not visited during this decision-making cycle.
        * Transfer knowledge of predecessors' current HS to this agent.
        * Influence this agent's opinion about predecessors' known HS.
        * Append predecessors' known HS to this agent in case this agent does not know it yet. 
        * Transfer predecessors' knowledge about subsidies to this agent.
        * Add or update this agents predecessors' rating with predecessors' rating         
        
        Parameters
        ----------
        coverage : int
            The maximum number of neighbors to contact.
        """
        # Here, predecessors as the ones who influence this agent seem appropriate
        predecessors = self.model.grid.get_cell_list_contents(
            list(self.model.grid.G.predecessors(self.unique_id)))
        rng_houseowner_run().shuffle(predecessors)
    
        unvisited_neighbours = [p for p in predecessors if p.unique_id not in self.visited_neighbours]
        counter = min(coverage, len(unvisited_neighbours))
        
        if not unvisited_neighbours:
            self.aspiration_value = 0
            return
    
        for neighbour in unvisited_neighbours:
            if counter <= 0:
                break
    
            neighbour.share_knowledge(self)
            neighbour.share_rating(self)
            neighbour.share_system(self)
            neighbour.share_satisfaction(self)
    
            self.visited_neighbours.add(neighbour.unique_id)
            counter -= 1

    def share_decision(self, iterations: int = 1):
        """
        Shares the final installation decision with neighbours.
        Works as a propagation mechanism. Turned of by default
        in settings.toml.
        """
        # Here, successors as the ones this agent influences seem appropriate
        successors = self.model.grid.get_cell_list_contents(
            list(self.model.grid.G.successors(self.unique_id)))       
        rng_houseowner_run().shuffle(successors)
        
        proposed_hs = deepcopy(self.house.current_heating)
        for key, value in proposed_hs.params.items():
            value[1] = value[0] * rng_houseowner_run().uniform(
                settings.information_source.uncertainty_lower, 
                settings.information_source.uncertainty_upper
            )
        
        for _ in range(iterations):
            successor = rng_houseowner_run().choice(successors)
            if type(successor.house.current_heating) == type(proposed_hs):
                continue
            for hs in successor.known_hs:
                if type(hs) == type(proposed_hs):
                    successor.relative_agreement(new_system = proposed_hs)
                    break
            else:
                successor.known_hs.append(deepcopy(proposed_hs))
            
            for system in successor.known_hs:
                successor.calculate_attitude(system)
                if type(system) == type(successor.house.current_heating):
                    successor.house.current_heating.rating = system.rating
            
            self.share_system(neighbour = successor)
            self.share_satisfaction(neighbour = successor)
            self.share_rating(neighbour = successor)
          
            successor.active_trigger = Trigger_adoptive_comparsion()

    """Opinion sharing subpart"""
    def share_satisfaction(self, neighbour):
        """
        This agent shares his opinion about his current HS with another houseowner
        The method about sharing knowledge is down below, and always goes before this one.

        Parameters
        ----------
        neighbour : Houseowner
            The agent to share the satisfaction information with.
        """
        my_id = self.unique_id
        heating_system = self.house.current_heating
        satisfaction = self.satisfaction
        opinion = {type(heating_system).__name__: satisfaction}
        neighbour.neighbours_satisfaction[my_id] = opinion  # Nested dict

        satisfied_count = 0
        total_count = 0

        # update satisfaction ratio:
        for id, opinion in neighbour.neighbours_satisfaction.items():
            for heating_name, satisfaction in opinion.items():
                if heating_name == type(heating_system).__name__:
                    total_count += 1
                    if satisfaction == "Satisfied":
                        satisfied_count += 1

        ratio = satisfied_count / total_count if total_count > 0 else 0

        for system in neighbour.known_hs:
            if isinstance(system, type(heating_system)):
                system.satisfied_ratio = ratio

    def share_knowledge(self, neighbour):
        """The agent shares the knowledge about their known heating systems with a neighbour.
        It also influences neighbours's opinion on other known systems.
        Also shares known subsidies.

        Parameters
        ----------
        counterpart: Houseowner
            A houseowner to share the knowledge about known HS.

        """
        my_known_hs = self.known_hs
        neighbours_known_hs = neighbour.known_hs

        # Get class names of the instances in neighbours_known_hs
        names_of_neighbours_known_hs = {
            system.__class__.__name__ for system in neighbours_known_hs
        }

        # Influencing neighbours known systems parameters using Relative Agreement approach
        for my_system in my_known_hs:  # For each system in my knowledge
            for his_system in neighbours_known_hs:  # And each in owner's
                if (
                    my_system.__class__ == his_system.__class__
                ):  # Check if those are matching
                    influence_by_relative_agreement(source_system = my_system,
                                target_system = his_system,
                                exposure = neighbour.ra_exposure[self.milieu_data.milieu_type])

        # Sharing knowledge with the neighbour
        for system in my_known_hs:
            copied_system = deepcopy(system)
            if copied_system.__class__.__name__ not in names_of_neighbours_known_hs:
                for key, value in copied_system.params.items():
                    if value[1] == 0:
                        value[1] = value[0] * rng_houseowner_run().uniform(
                            settings.information_source.uncertainty_lower, 
                            settings.information_source.uncertainty_upper
                        )
                
                copied_system = deepcopy(system)
                copied_system.neighbours_opinions = (
                    {}
                )
                copied_system.subsidised = False
                copied_system.source = "Neighbour"
                neighbours_known_hs.append(copied_system)

        # Sharing knowledge about subsidies
        for key in self.known_subsidies_by_hs:
            neighbour.known_subsidies_by_hs[key] = deepcopy(self.known_subsidies_by_hs[key])

    def share_system(self, neighbour):
        """
        This agent receives the knowledge about a neighbour's current heating system.

        Parameters
        ----------
        neighbour : Houseowner
            The agent to share the system name with.
        """

        neighbour.neighbours_systems[self.unique_id] = (
            self.house.current_heating.get_name()
        )

    def share_rating(self, neighbour):
        """
        Shares the ratings of all known heating systems with a neighbor.

        This method updates the neighbor's `neighbours_opinions` attribute,
        influencing their social norm calculation.

        Parameters
        ----------
        neighbour : Houseowner
            The agent to share ratings with.
        """

        my_known_hs = self.known_hs
        neighbours_known_hs = neighbour.known_hs

        for my_system in my_known_hs:  # For each system in my knowledge
            for his_system in neighbours_known_hs:  # And each in owner's
                if (
                    my_system.__class__ == his_system.__class__
                ):  # Check if those are matching
                    his_system.neighbours_opinions[self.unique_id] = (
                        my_system.rating
                    )  # Modify an entry in the dictionary
    
    def relative_agreement(self, new_system):
        """
        Updates the agent's knowledge using the Relative Agreement model.

        This method is called when the agent receives new information about an
        already known known heating system, 
        adjusting their own knowledge based on the new data.

        Parameters
        ----------
        new_system : Heating_system
            An instance of a heating system containing new information.
        """
        for system in self.known_hs:
            if system.__class__ == new_system.__class__:
                influence_by_relative_agreement(source_system = new_system,
                                target_system = system)
    
    """Interaction with the plumber subpart"""

    def find_plumber(self):
        """
        Finds and assigns a random plumber from the model.
        """
        plumber_list = []
        for agent in self.model.schedule.agents:
            if agent.__class__.__name__ == "Plumber":
                plumber_list.append(agent)
        self.plumber = rng_houseowner_run().choice(plumber_list)

    def find_plumber_with_desired_hs(self):
        """
        Finds a plumber qualified to install the desired heating system.

        It searches for a plumber who has the `desired_hs` in their list of
        known systems. If no qualified plumber is found, the system may be
        marked as infeasible for the agent.
        """
        if not self.desired_hs:
            raise Exception("A houseowner has no desired HS yet tries to find a plumber for it!")
        plumber_list = []
        attempts = 0
        for agent in self.model.schedule.agents:
            if agent.__class__.__name__ == "Plumber" and agent.unique_id not in self.unqualified_plumbers:
                if (type(self.desired_hs) in [type(hs) for hs in agent.known_hs]):
                    plumber_list.append(agent)
                else:
                    attempts += 1
                    if self.milieu_data.milieu_type != "Leading" and attempts == 10:
                        break

        # If we find at least one suitable plumber, randomly assign one to the agent
        if plumber_list:
            self.plumber = rng_houseowner_run().choice(plumber_list)
        else:
            # Mark the desired heating system as infeasible if no plumber can install it
            # logger.info(f"{self.unique_id} I have not found any plumber, that can install my system!")
            self.infeasible.append(type(self.desired_hs).__name__)

    def order_plumber(self):
        """
        Orders a consultation from the assigned plumber.
        """
        self.plumber.Services[0].queue_job(self)
        self.consultation_ordered = True

    def order_energy_advisor(self):
        """
        Orders a consultation from the assigned energy advisor.
        """
        self.energy_advisor.Services[0].queue_job(self)
        self.consulted_by_energy_advisor = True
        self.consultation_ordered = True
    
    def find_energy_advisor(self):
        """
        The agents finds one energy advisor if he has none yet
        """
        advisor_list = []
        for agent in self.model.schedule.agents:
            if agent.__class__.__name__ == "EnergyAdvisor":
                advisor_list.append(agent)
        if advisor_list:
            self.energy_advisor = rng_houseowner_run().choice(advisor_list)

    def order_installation(self):
        """
        The agent orders a consultation from his plumber regarding installation
        """
        if self.plumber != None:
            if type(self.desired_hs) not in [type(hs) for hs in self.plumber.known_hs]:
                # logger.info("I don't know this system. We cannot work together!")
                self.unqualified_plumbers.append(self.plumber.unique_id)
                self.plumber = None
                return
        
        if self.plumber == None:
            self.find_plumber_with_desired_hs()
            if self.plumber == None:
                # logger.info(f"{self.unique_id} has not found any plumber that can install his desired system!")
                return

        self.plumber.Services[1].queue_job(self,
                                    installation_time = self.desired_hs.installation_time)
        self.installation_ordered = True
    
    """House part
    Contains methods of houseowner-house interaction
    """

    def investigate_house(self):
        """
        Updates the agent's knowledge about their own house and heating system.

        This method ensures the agent's current heating system is in their
        `known_hs` list and checks for events like system breakdowns.
        """
        if not any(
            type(i).__name__ == type(self.house.current_heating).__name__
            for i in self.known_hs
        ):
            copy = deepcopy(self.house.current_heating)
            copy.breakdown = False
            self.known_hs.append(copy)
        
        self.house.current_heating.payback_check()
        self.house.current_heating.breakdown_check()

    """Heating system part"""

    def generate_system(self, variant):
        """
        Creates an instance of a heating system from its class name.

        Parameters
        ----------
        variant : str
            The class name of the heating system to be created.

        Returns
        -------
        Heating_system
            An instance of the specified heating system class.
        """
        params_table = self.model.heating_params_table
        class_obj = globals()[variant]
        system = class_obj(table = params_table)
        return system

    """Theory of Planned Behaviour (TPB) part """
    
    def calculate_attitude(self, system):
        """
        Calculates the agent's attitude towards a specific heating system.

        This method generates a rating based on how well the system's
        attributes align with the agent's personal preferences. This represents
        the 'Attitude' component of the TPB.

        Parameters
        ----------
        system : Heating_system
            The heating system to be evaluated.
        """
        # 1. Programmatic Column Definition
        columns = settings.heating_systems.parameters

        # Create a specific list of systems to use for comparison/normalisation.
        comparison_group = [
            hs for hs in self.known_hs
            if (type(hs).__name__ not in self.infeasible) or (hs == system)
        ]

        # 2. Extract data for the COMPARISON GROUP into a NumPy array
        data_matrix = np.array([
            [
                (hs.params[col][0] if isinstance(hs.params[col], list) else hs.params[col])
                for col in columns
            ]
            for hs in comparison_group
        ], dtype=float)

        # 3. Normalize and Rescale
        max_vals = np.nanmax(data_matrix, axis=0)
        max_vals[max_vals == 0] = 1.0  # Avoid division by zero
        rescaled_matrix = 1.0 - (data_matrix / max_vals)

        # 4. Get Preferences as array
        prefs = np.array([getattr(self.heating_preferences, col) for col in columns], dtype=float)
        sum_prefs = np.sum(prefs)
        if sum_prefs > 0:
            norm_prefs = prefs / sum_prefs
        else:
            norm_prefs = np.ones_like(prefs) / len(prefs)

        try:
            system_index = comparison_group.index(system)
            selected_system_values = rescaled_matrix[system_index]
        except ValueError:
            print(f"Error: System {type(system).__name__} not found in comparison group.")
            return

        # 6. Compute Ratings
        attribute_ratings_array = selected_system_values * norm_prefs
        
        # 7. Store results
        self.attribute_ratings[type(system).__name__] = dict(zip(columns, attribute_ratings_array))
        
        # Dynamic averaging
        system.rating = np.nansum(attribute_ratings_array)

    def calculate_social_norm(self, system):
        """
        Calculates the perceived social norm related to a heating system.

        The social norm is derived from the opinions of the agent's neighbours
        and the prevalence of the system within their social network. This
        represents the 'Social Norm' component of the TPB.

        Parameters
        ----------
        system : Heating_system
            The heating system for which to calculate the social norm.
        """
        uncertainty_weight = self.uncertainty_factor
        
        # 1. Get the total physical/social network (RESTRICTED TO PREDECESSORS)
        graph = self.model.grid.G
        total_network_ids = set(graph.predecessors(self.unique_id)) # Only consider those who influence me
        total_n_count = len(total_network_ids)
        
        # Avoid division by zero if agent is isolated
        if total_n_count == 0:
            system.social_norm = 1 - uncertainty_weight
            return

        # ---------------------------------------------------------
        # Part A: Prevalence (Systems Fraction)
        # ---------------------------------------------------------
        # 1. Filter known systems to only include those in the predecessor list (The "Observed Data")
        valid_known_systems = {k: v for k, v in self.neighbours_systems.items() if k in total_network_ids}
        
        # 2. Define the Laplace variables
        # k = Number of neighbours I KNOW have this specific system
        k = list(valid_known_systems.values()).count(system.get_name())
        
        # n = Total number of neighbours whose systems I know (Sample size)
        n = len(valid_known_systems)
        
        # N_options = Number of options I am aware of (Dynamic prior)
        # This dilutes the certainty if I know many alternative systems exist
        N_options = len(self.known_hs)
        
        # 3. Calculate Base Value (Laplace Smoothed Probability)
        # Formula: (Successes + 1) / (Trials + Possible_Outcomes)
        # This assumes a uniform prior (1/N_options) before evidence is seen.
        base_val = k / n
        
        # 4. Tipping Point. Logistic Transformation / Sigmoid Activation Function
        # transition_width is a compromise between:
        # Bass Diffusion Model
        # and Kastner, I. & Matthies, E. (2014).
        transition_width = 0.3         
        k_steep = 6 / transition_width # Established approximation
        x_mid = 0.25 # Centola, D. et al. (2018) Experimental evidence for tipping points in social convention.
        
        neighbours_share_smoothed = 1 / (1 + math.exp(-k_steep * (base_val - x_mid)))
        
        # ---------------------------------------------------------
        # Part B: Opinions
        # ---------------------------------------------------------
        # Filter opinions to only include predecessors
        valid_opinions = {k: v for k, v in system.neighbours_opinions.items() if k in total_network_ids and v is not None}
        known_opinions = list(valid_opinions.values())
        n_known_opinions = len(known_opinions)

        # Calculate the "Gap".
        n_unknown_opinions = total_n_count - n_known_opinions
    
        if n_known_opinions > 0:
            raw_sum = sum(known_opinions)
        else:
            raw_sum = 0
        neutral_value = 1 - uncertainty_weight
        
        if n_known_opinions > 0:
            raw_sum = sum(known_opinions)
            # If we have opinions, average them.
            smoothed_opinions_mean = raw_sum / n_known_opinions
            # Alternative (raw_sum + (n_unknown_opinions * neutral_value)) / total_n_count
        
        else:
            # If no opinions are known, assume milieu-specific expectation.
            smoothed_opinions_mean = 1 - uncertainty_weight
            
        self.comprehensive_metrics[type(system).__name__]["social_norm"] = smoothed_opinions_mean
    
        # ---------------------------------------------------------
        # Part C: Final Calculation
        # ---------------------------------------------------------
        system.social_norm = (neighbours_share_smoothed + smoothed_opinions_mean) / 2
        
        if system.social_norm < 0 or system.social_norm > 1.000001:
             print(f"ERROR: Negative Norm. Total: {total_n_count}, Known: {n_known_opinions}, Unknown: {n_unknown_opinions}")
             raise ValueError(f"Wrong social norm: {system.social_norm}")

    def calculate_PBC(self, system):
        """
        Calculates the Perceived Behavioural Control (PBC) for a system.

        PBC is determined by the system's affordability, considering both the
        upfront installation cost relative to the agent's budget and the
        ongoing running costs relative to their income. This represents the
        'Perceived Behavioural Control' component of the TPB.

        Parameters
        ----------
        system : Heating_system
            The heating system for which to calculate the PBC.
        """
        price = system.params["price"][0]
        budget = self.hs_budget
        
        # Logic: min(budget / price, 1). Handle price=0 to avoid ZeroDivision.
        if price > 0:
            affordability_ratio = budget / price
            if affordability_ratio >= 1.0:
                affordability_score = 1.0
            else:
                affordability_score = max(0.0, affordability_ratio)
        else:
            affordability_ratio = 1.0 # For metrics
            affordability_score = 1.0

        # --- 2. Income Ratio (Running Costs) ---
        new_running_weekly = (system.params["fuel_cost"][0] + system.params["opex"][0]) / 52
        
        current_running_weekly = (self.house.current_heating.params["fuel_cost"][0] + 
                                  self.house.current_heating.params["opex"][0]) / 52
        
        difference = new_running_weekly - current_running_weekly
        
        # Logic: If new is cheaper (diff < 0), score is 1. 
        # If new is more expensive, score reduces based on how much income it eats.
        if difference >= 0:
            # Check income to avoid division by zero
            if self.income > 0:
                share_of_income = difference / self.income
                income_score = 1.0 - share_of_income
                if income_score < 0: income_score = 0.0
            else:
                # If income is 0 and difference > 0, affordability is 0
                income_score = 0.0 
        else:
            income_score = 1.0

        # --- 3. Final Calculation ---
        behavioural_control = math.sqrt(income_score * affordability_score)

        # --- 4. Store Metrics ---
        sys_name = system.get_name()
        
        self.comprehensive_metrics[sys_name]["affordability"] = affordability_ratio
        self.comprehensive_metrics[sys_name]["behavioural_control"] = behavioural_control
        
        if self.income > 0:
             self.comprehensive_metrics[sys_name]["income_ratio"] = new_running_weekly / self.income
        else:
             self.comprehensive_metrics[sys_name]["income_ratio"] = 0

        # Apply to system
        system.behavioural_control = behavioural_control

    def calculate_integral_rating(self):
        """
        Combines attitude, social norm, and PBC into a single utility score.

        This method weighs and sums the three components of the TPB to create an
        overall rating for each suitable heating system, which is then used to
        make the final installation choice.

        Returns
        -------
        dict
            A dictionary mapping `Heating_system` instances to their integral rating.
        """

        systems_ratings = {}
        
        # Early exit if no suitable systems
        if not self.suitable_hs:
            return {}

        # 1. Collect Data & Calculate Missing TPB Components
        # Matrix Shape: (N_systems, 3)
        # Column 0: Attitude (system.rating)
        # Column 1: Social Norm (system.social_norm)
        # Column 2: PBC (system.behavioural_control)
        n_systems = len(self.suitable_hs)
        data_matrix = np.zeros((n_systems, 3))

        for i, system in enumerate(self.suitable_hs):
            # Run necessary calculations
            self.calculate_social_norm(system)
            self.calculate_PBC(system)
            
            # Populate matrix
            data_matrix[i, 0] = system.rating
            data_matrix[i, 1] = system.social_norm
            data_matrix[i, 2] = system.behavioural_control

        # 2. Prepare Weights
        # Explicitly map dictionary keys to the column order [Attitude, SN, PBC]
        # Note: System attribute 'rating' corresponds to weight 'attitude'
        weights_list = [
            self.tpb_weights["attitude"],
            self.tpb_weights["social_norm"],
            self.tpb_weights["behavioural_control"]
        ]
        # Normalised to enable (possible) comparison of integral ratings
        weights_arr = np.array(weights_list) / sum(weights_list) 
        
        # 3. Apply Weights and Sum
        # Multiply: normalized_val * weight
        weighted_matrix = data_matrix * weights_arr
        
        # Sum across columns (axis=1) to get the final score per system
        final_scores = np.sum(weighted_matrix, axis=1)

        # 4. Store Results
        for i, system in enumerate(self.suitable_hs):
            rating = final_scores[i]
            systems_ratings[system] = rating
            
            # Store for data collector
            self.comprehensive_metrics[type(system).__name__]["integral_rating"] = rating

        return systems_ratings

    def check_standard(self, system):
        """Checks if a heating system meets the agent's personal standard.

        The agent's standard is a set of minimum criteria. 
        A system must meet these criteria to be considered satisfactory.
        They also depend on the Milieu.

        Parameters
        ----------
        system : Heating_system
            The heating system to check.

        Returns
        -------
        bool
            True if the system meets the standard, False otherwise.
        """
        """
        Known factors:
        Leading: efficiency (i.e. energy consumption), novelty (i.e. age), emissions. 
        Mainstream: reliability (i.e. breakdown, repairs), upfront costs, opinions of others.
        Traditionals: fine if it works, but availability is important.
        Hedonists: fine if it works.
        
        """
        # --- 1. Lifetime Check ---
        remaining_lifetime = system.lifetime - system.age
        
        if self.model.sa_active:
            limit = settings.experiments.sa_standard_lifetime
        else:
            limit = self.standard.lifetime

        if remaining_lifetime < limit:
            self.model.stage_flows["Stage_1"]["Dissatisfied_age"] += 1
            return False

        # --- 2. Milieu-Specific Check ---
        milieu = self.milieu_data.milieu_type
        can_afford = system.age >= 520 #self.hs_budget >= (self.income * self.budget_limit)

        if milieu == "Leading":
            # Dissatisfied if a cleaner option is known and affordable
            current_emissions = system.params["emissions"][0]
            if can_afford:
                for hs in self.known_hs:
                    if hs.params["emissions"][0] < current_emissions:
                        self.model.stage_flows["Stage_1"]["Dissatisfied_milieu"] += 1
                        return False
            return True

        elif milieu == "Mainstream":
            # Dissatisfied if not using the most popular system and can afford to switch
            neighbour_list = list(self.neighbours_systems.values())
            if not neighbour_list:
                return True

            counts = Counter(neighbour_list)
            dominant_adoption = max(counts.values())
            own_adoption = counts.get(system.get_name(), 0)

            if own_adoption < dominant_adoption and can_afford:
                self.model.stage_flows["Stage_1"]["Dissatisfied_milieu"] += 1
                return False
            return True

        elif milieu == "Traditionals":
            # Dissatisfied if parts availability is low AND lifetime is short
            availability = system.availability - self.model.schedule.steps
            two_years = 104
            four_years = 208

            if 0 < availability < two_years and remaining_lifetime < four_years:
                self.model.stage_flows["Stage_1"]["Dissatisfied_milieu"] += 1
                return False
            return True

        elif milieu == "Hedonists":
            return True

        return True
    
    def manage_budget(self):
        """
        Updates the agent's budget based on income and expenses.
        """
        # Adds income to the budget minus loan payments
        weekly_fuel_costs = self.house.current_heating.params["fuel_cost"][0]/52
        weekly_opex = self.house.current_heating.params["opex"][0]/52
        self.weekly_expenses = weekly_fuel_costs + weekly_opex #For the data collector
        if self.income < 0:
            print(f"Agent {self.unique_id} has negative savings!", self.income)
        if self.house.current_heating.loan is not None:
            weekly_payment = math.floor(self.house.current_heating.loan.monthly_payment / 4)
            if self.income - weekly_payment < 0:
                print(f"Indebted agent {self.unique_id} has negative savings!", self.income - weekly_payment)
            self.house.current_heating.loan.total_repayment -= weekly_payment
            self.hs_budget -= weekly_payment
            self.weekly_expenses = weekly_fuel_costs + weekly_opex + weekly_payment
            if self.house.current_heating.loan.total_repayment <= 0:
                self.house.current_heating.loan = None
        
        if self.income > 0:
            self.hs_budget += self.income
            
        self.hs_budget = math.ceil(min(self.hs_budget, self.income * self.budget_limit))
        
        if self.hs_budget < 0:
            print(f"Agent {self.unique_id} has negative refurbishment budget!", self.hs_budget)
        
    
    def find_loan(self, system, bypass_avoidance = False):
        """
        Attempts to secure a loan to cover the cost of a heating system.

        If a system's price exceeds the agent's budget, this method calculates
        whether a viable loan can be obtained based on the agent's income and
        the system's lifetime.
        
        Parameters
        ----------
        system : Heating_system
            The system for which to find a loan.
        bypass_avoidance : bool, optional
            If True, ignores the agent's general unwillingness to take a loan.
            Defaults to False.
        """
        #Starting loan
        new_fuel_cost = system.params["fuel_cost"][0] / 52
        new_opex = system.params["opex"][0] / 52
        current_fuel_cost = self.house.current_heating.params["fuel_cost"][0] / 52
        current_opex = self.house.current_heating.params["opex"][0] / 52
        difference = (new_fuel_cost + new_opex) - (current_fuel_cost + current_opex)
        expected_income = max(0, self.income - difference)
        if expected_income == 0:
            system.loan = None
            return
        if (not self.loan_taking 
            and not bypass_avoidance):
            system.loan = None
            return
        
        loan = Loan(weekly_income = expected_income, 
                    system_price = system.params["price"][0], 
                    funds = self.hs_budget)
        
        if loan.loan_amount == 0:
            system.loan = None
            return
        
        weekly_payment = loan.monthly_payment / 4
        
        #Optimizing loan
        increment = 1
        while weekly_payment > expected_income:
            #print(f"Optimising for {self.unique_id}, current term {10+increment} years!")
            loan = Loan(weekly_income = expected_income, 
                    system_price = system.params["price"][0], 
                    funds = self.hs_budget,
                    years = 10+increment)
            weekly_payment = loan.monthly_payment / 4
            increment += 1
            if increment > (system.lifetime/52) - 10 or loan.loan_amount == 0:
                #If the limiting term condition is met and the loan is still unacceptable, there will be None
                system.loan = None
                #print("No acceptable term found!")
                break
        
        else:
        # Only attach the loan if an acceptable weekly_payment was found
            system.loan = loan
    

    def apply_subsidies(self, system):
        """
        Applies any known subsidies to a heating system to reduce its price.
    
        Parameters
        ----------
        system : Heating_system
            The system to which subsidies will be applied.
        """
        if system.source == "Internet":
            return
        
        system_name = type(system).__name__
        
        if system_name not in self.known_subsidies_by_hs:
            return
        
        subsidies_by_hs = self.known_subsidies_by_hs[system_name]
            
        total_subsidy = 0  # Total volume of subsidy
        current_price = system.params["price"][0]
    
        # Calculate the maximum allowed subsidy (min of 70% price or 21,000)
        subsidy_cap = min(current_price * 0.7, 21000)
    
        for subsidy_rule in subsidies_by_hs:
            subsidy_amount = 0
            
            # Calculate subsidy amount based on rule
            if subsidy_rule.target is None:
                subsidy_amount = current_price * subsidy_rule.subsidy
                total_subsidy += subsidy_amount
            elif subsidy_rule.check_condition(system=system, agent=self):
                subsidy_amount = current_price * subsidy_rule.subsidy
                total_subsidy += subsidy_amount
    
            # Check against the cap
            if total_subsidy >= subsidy_cap:
                total_subsidy = subsidy_cap
                break
                
        if total_subsidy > 0:
            system.subsidised = True  
        
        system.params["price"][0] -= total_subsidy
            
    """Helpers for the data collector of the model"""

    def get_heating(self):
        """
        Returns the current heating system type for the data collector.
        """
        return type(self.house.current_heating).__name__

    def get_trigger(self):
        """
        Returns the most recent trigger type for the data collector.
        """
        return type(self.trigger_to_report).__name__

    def get_stage_dynamics(self):
        """
        Returns the current decision stage for the data collector.
        """
        array = np.array(self.stage_counter)
        return array

    def get_class(self):
        """
        Returns the agent's class name.
        """
        return type(self).__name__

    def get_system_age(self):
        """
        Returns the age of the current heating system in years.
        """
        return self.house.current_heating.age / 52

    def get_satisfied_ratio(self):
        """
        Returns the satisfaction ratio associated with the current heating system.
        """
        ratio = self.house.current_heating.satisfied_ratio
        return ratio

    def get_milieu(self):
        """
        Returns the agent's milieu type as a string.
        """
        milieu = self.milieu_data.milieu_type
        return milieu

    def get_opex(self):
        """
        Returns the total annual operational and fuel costs for the current heating system.
        """
        opex = self.house.current_heating.params["opex"][0]
        fuel = self.house.current_heating.params["fuel_cost"][0]
        return opex + fuel

    def get_emissions(self):
        """
        Returns the annual emissions of the current heating system.
        """
        return self.house.current_heating.params["emissions"][0]

    def get_energy_demand(self):
        """
        Returns the total annual energy demand of the current heating system.
        """
        return self.house.current_heating.total_energy_demand

    def get_optimality(self):
        """
        Calculates and stores the suboptimality of the agent's most recent choice.

        Suboptimality is calculated as the ratio of the rating of the chosen
        system to the rating of the best-rated system known to the agent at
        the time of the decision. A value of 1.0 indicates an optimal choice.
        """
        sorted_known = sorted(self.known_hs, key=lambda x: x.rating, reverse=True)

        # Check if sorted_known is empty to avoid IndexError
        if sorted_known:
            optimal_choice = sorted_known[0].rating
        else:
            # If there are no known systems, set optimal_choice to None or some default value
            optimal_choice = None

        actual_choice = next(
            (
                system.rating
                for system in sorted_known
                if isinstance(system, type(self.house.current_heating))
            ),
            None,
        )

        # Avoid division by zero or division involving None
        if actual_choice is not None and optimal_choice not in (None, 0):
            suboptimality = actual_choice / optimal_choice
        else:
            suboptimality = (
                np.nan
            )  # Or np.nan, depending on how you wish to represent undefined suboptimality

        self.suboptimality = suboptimality

    def get_preferences(self):
        """
        Returns the agent's heating preferences at the end of the simulation.
        """
        if self.model.schedule.steps == self.steps:

            preferences = {
                "operation_effort": 0,
                "fuel_cost": 0,
                "emissions": 0,
                "price": 0,
                "installation_effort": 0,
                "opex": 0,
            }

            # Iterate through each instance and add attribute values to the total sums
            preferences["operation_effort"] = self.heating_preferences.operation_effort
            preferences["fuel_cost"] = self.heating_preferences.fuel_cost
            preferences["emissions"] = self.heating_preferences.emissions
            preferences["price"] = self.heating_preferences.price
            preferences["installation_effort"] = (
                self.heating_preferences.installation_effort
            )
            preferences["opex"] = self.heating_preferences.opex

            return preferences

        else:
            return None

    def get_comprehensive_metrics(self):
        """
        Returns detailed TPB metrics for data collection once 
        at after the first installation.
        """
        if self.installed_once == True and self.behavioural_control_switched == False:
            self.behavioural_control_switched = True

            behavioral_control = {
                system: {
                    "affordability": metrics["affordability"],
                    "behavioural_control": metrics["behavioural_control"],
                    "income_ratio": metrics["income_ratio"],
                }
                for system, metrics in self.comprehensive_metrics.items()
            }

            return behavioral_control

        if self.model.schedule.steps == self.steps:
            return self.comprehensive_metrics

    def get_attributes(self):
        """
        Returns the agent's attribute-wise ratings at the end of the simulation.
        """
        if self.model.schedule.steps == self.steps:
            return self.attribute_ratings
        else:
            return None
    
    def get_house_area(self):
        """
        Returns the living area of the agent's house.
        """
        return self.house.area
    
    def store_evaluations(self):
        """
        Stores detailed evaluation data when a non-target HS is chosen.

        This method is used for data collection to analyze why an agent might
        prefer a non-target heating system over a scenario-promoted target system.
        It saves the agent's ratings for both the chosen system and the target
        systems at the moment of decision.
        """
        desired_type = type(self.desired_hs).__name__
        
        # Only proceed if the desired system is not a target system
        if desired_type not in self.model.scenario.hs_targets.keys():
            # Ensure an outer entry exists; if not, initialize it.
            if desired_type not in self.evaluation_factors:
                self.evaluation_factors[desired_type] = {}
            
            inner_keys = [desired_type] + list(self.model.scenario.hs_targets.keys())
            
            for system_key in inner_keys:
                suitable_instance = next((hs for hs in self.suitable_hs if type(hs).__name__ == system_key), None)
                if suitable_instance is not None:
                    # Get the base attribute series from the appropriate system type
                    attribute_series = pd.Series(self.attribute_ratings[type(suitable_instance).__name__])
                    # Create the modified series with extra evaluation fields
                    modified_series = attribute_series.copy()
                    modified_series["attitude"] = suitable_instance.rating
                    modified_series["social_norm"] = suitable_instance.social_norm
                    modified_series["behavioural_control"] = suitable_instance.behavioural_control
                    
                    # If an evaluation already exists for this system key, add a new column.
                    if system_key in self.evaluation_factors[desired_type]:
                        existing_eval = self.evaluation_factors[desired_type][system_key]
                        # Convert to DataFrame if necessary (first evaluation might be stored as a Series)
                        if not isinstance(existing_eval, pd.DataFrame):
                            existing_eval = existing_eval.to_frame(name='eval1')
                        # Determine new column name (e.g., eval2, eval3, …)
                        new_col_name = f'eval{existing_eval.shape[1] + 1}'
                        existing_eval[new_col_name] = modified_series
                        self.evaluation_factors[desired_type][system_key] = existing_eval
                    else:
                        # First evaluation: store as a DataFrame with one column, e.g., "eval1"
                        self.evaluation_factors[desired_type][system_key] = modified_series.to_frame(name='eval1')
            
            # Optionally, only keep the evaluation if more than one evaluation column exists overall.
            if len(self.evaluation_factors[desired_type]) <= 1:
                del self.evaluation_factors[desired_type]
    
    def __repr__(self):
        return f"{self.unique_id}: {type(self)} | Cog.Res: {self.cognitive_resource}"

    def __str__(self):
        return self.__repr__()
    