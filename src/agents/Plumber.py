"""
Defines the Plumber agent and its consultation and installation services.

This module contains the `Plumber` class, an intermediary agent responsible for 
consulting houseowners about heating system options and installing new systems. 
It includes two service classes, `ConsultationServicePlumber` and 
`InstallationServicePlumber`, which manage the respective job queues and the 
logic for these tasks.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""
import numpy as np
import pandas as pd
import math
from copy import deepcopy
from modules.Rng import rng_plumber_run
from modules.Heating_systems import (
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
from helpers.config import settings
from helpers.utils import influence_by_relative_agreement
from interventions.Loans import Loan
from interventions.Subsidy import *
from agents.base.Intermediary import Intermediary
from agents.base.Service import Service
from agents.base.Job import Job, IService
import logging

logger = logging.getLogger("ahoi.intermediary.plumber")

class ConsultationServicePlumber(Service):
    """
    A service for handling heating system consultations by a Plumber.

    When a consultation job is completed, this service triggers the Plumber's 
    `consultation` method, where the Plumber shares knowledge, provides 
    recommendations, or performs a feasibility check on a desired heating system.
    """
    def __init__(self, intermediary=None):
        """
        Initializes the consultation service for a Plumber.
        Sets plumber-specific default job duration.
        """
        super().__init__(intermediary)
        self.duration = settings.plumber.cons_duration

    def begin_job(self):
        """
        Begins a consultation job.
        """
        super().begin_job()
        job = self.job_queue.popleft()
        logger.debug(f"Begin job {job}")

    def complete_job(self, job):
        """
        Completes a consultation job by calling the Plumber's `consultation` method.

        Parameters
        ----------
        job : Job
            The consultation job to be completed.
        """
        logger.debug(f"Complete job {job}")
        super().complete_job(job)
        self.intermediary.consultation(job)


class InstallationServicePlumber(Service):
    """
    A service for managing and executing heating system installations.

    This service manages the queue for installation jobs. It has a custom 
    `queue_job` method to handle variable installation times. When a job is 
    completed, it triggers the Plumber's `installation` method to finalise the 
    process in the simulation.
    """
    def __init__(self, intermediary=None):
        """
        Initializes the installation service for a Plumber.
        """
        super().__init__(intermediary)
        self.duration = settings.plumber.ins_duration
    
    def queue_job(self, houseowner, installation_time):
        """
        Adds an installation job to the queue with a specific duration.

        Parameters
        ----------
        houseowner : Houseowner
            The customer for whom the installation will be performed.
        installation_time : int
            The specific time required for this type of heating system installation.
        """
        if any(job.customer.unique_id == houseowner.unique_id for job in self.job_queue):
            print(f"Houseowner {houseowner.unique_id} already has a queued installation.")
            return
        
        self.job_counter += 1
        self.job_queue.append(Job(self.generate_id(), 
                                  houseowner, 
                                  self, 
                                  self.duration+installation_time))
    
    def begin_job(self):
        """
        Begins an installation job.
        """
        super().begin_job()
        job = self.job_queue.popleft()
        logger.debug(f"Begin job {job}")
        
    def complete_job(self, job):
        """
        Completes an installation job by calling the Plumber's `installation` method.

        Parameters
        ----------
        job : Job
            The installation job to be completed.
        """
        logger.debug(f"Complete job {job}")
        super().complete_job(job)
        self.intermediary.installation(job)


class Plumber(Intermediary):
    """
    An intermediary agent who consults on and installs heating systems.

    The Plumber agent models a trade professional who interacts directly with 
    Houseowners. Plumbers have their own knowledge base of heating systems, which 
    can be expanded through `training`. They provide consultations to help 
    Houseowners choose a system and are responsible for the entire installation 
    process, from feasibility checks to final implementation.
    """

    def __init__(
        self,
        unique_id,
        model,
        heating_preferences,
        standard,
        current_heating,
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
        active_jobs: dict = None,
        completed_jobs: dict = None,
        max_concurrent_jobs: int = 1,
        active_jobs_counter: int = 0,
        known_subsidies = None
    ):
        """
        Initializes a Plumber agent.

        Notes
        -----
        Many parameters are inherited from the Houseowner class for data 
        collector compatibility and may not be directly used in the Plumber's logic.

        Parameters
        ----------
        unique_id : int
            The unique identifier for the agent.
        model : mesa.Model
            The main model instance.
        heating_preferences : Heating_preferences
            The agent's preferences for evaluating heating systems.
        known_hs : list
            A list of known `Heating_system` objects.
        known_subsidies : list
            A list of known `Subsidy` objects.
        """
        # Other attributes
        self.heating_preferences = heating_preferences
        self.standard = standard
        self.current_heating = current_heating
        self.cognitive_resource = cognitive_resource
        self.aspiration_value = aspiration_value
        self.known_hs = known_hs
        self.suitable_hs = suitable_hs if suitable_hs is not None else []
        self.desired_hs = desired_hs
        self.hs_budget = hs_budget
        self.current_breakpoint = current_breakpoint
        self.current_stage = current_stage
        self.satisfaction = satisfaction
        self.active_trigger = active_trigger
        self.stage_counter = []
        self.trigger_for_record = "None"
        self.infeasible = []
        self.suboptimality = None
        """Plumber specific parameters below"""
        self.known_subsidies = known_subsidies
        self.organize_subsidies()
        self.consultation_power = 1  # Plumber's ability to process his queues
        self.installation_power = 1  # Plumber's ability to process his queues
        self.clients_systems = {} #{neighbour_id: system_name}

        super().__init__(
            unique_id,
            model,
            heating_preferences,
            known_hs,
            active_jobs,
            completed_jobs,
            max_concurrent_jobs,
            active_jobs_counter,
        )

        for heating in self.known_hs:
            self.evaluate_system(heating)
            
        self.Services = [
            ConsultationServicePlumber(self),
            InstallationServicePlumber(self),
        ]
        
        # Calculate values for the systems for an average house
        for system in self.known_hs:
            system.calculate_all_attributes(
                area=settings.plumber.assume_area_avg,
                energy_demand=settings.plumber.assume_energydemand_avg,
                heat_load = settings.plumber.assume_heatload_avg
            )
            for key, value in system.params.items():
                value[1] = value[0] * rng_plumber_run().uniform(
                    settings.information_source.uncertainty_lower,
                    settings.information_source.uncertainty_upper
                    )
            self.evaluate_system(system)
            

    def check_job_completion(self, steps):
        """
        Checks for and finalises any jobs scheduled for completion at the current step.

        Parameters
        ----------
        steps : int
            The current simulation step.
        """
        job_list = self.active_jobs.pop(steps + 1, [])
        for job in job_list:
            self.completed_jobs.setdefault(steps, []).append(job)
            job.service.complete_job(job)

    def estimate_queue_time(self, q_type):
        """
        Estimates the total waiting time for a given service queue.

        Parameters
        ----------
        q_type : str
            The name of the service queue ('Consultation' or 'Installation').

        Returns
        -------
        int
            The estimated total duration in steps for all jobs in the queue.
        """
        if q_type == "Consultation":
            estimate = 0
            last_active_job = max(self.active_jobs, default=0)
            active_jobs_length = last_active_job - self.model.schedule.steps
            estimate += active_jobs_length
            for job in self.Services[0].job_queue:
                estimate += job.duration
            return estimate
        
        elif q_type == "Installation":
            estimate = 0
            last_active_job = max(self.active_jobs, default=0) 
            active_jobs_length = last_active_job - self.model.schedule.steps
            estimate += active_jobs_length
            for job in self.Services[0].job_queue:
                estimate += job.duration
            return estimate
        

    """The part about plumber obtaining new knowledge and skills"""

    def training(self, system = None):
        """
        Expands the Plumber's knowledge by learning about a new heating system.
        """
        # logger.info("I want to educate myself!")
        all_options = (
            settings.heating_systems.list
        )  # List of options available during training
        known_options = list(
            type(i).__name__ for i in self.known_hs
        )  # List of types of known HS

        possible_additions = [o for o in all_options if o not in known_options]
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{self}: Possible additions: {possible_additions}") 
        
        if possible_additions:
            randomizer = rng_plumber_run().choice(
                possible_additions
            )  # Randomly choose one type among possible to learn
            if system:
                actual_addition = self.generate_system(system)
            else:
                actual_addition = self.generate_system(randomizer)
            actual_addition.calculate_all_attributes(area=106, energy_demand=147,
                                                     heat_load=19)
            for key, value in actual_addition.params.items():
                value[1] = value[0] * rng_plumber_run().uniform(
                    settings.information_source.uncertainty_lower,
                    settings.information_source.uncertainty_upper
                    )
            
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"{self}: Added through training: {actual_addition}")    
                        
            self.known_hs.append(
                actual_addition
            )  # Add previous row's result to known_hs
            # logger.info("I learned about {}".format(type(self.known_hs[-1]).__name__))
            for heating in self.known_hs:
                self.evaluate_system(heating)
        else:
            # logger.info("Apparently, I already know everything!")
            pass

    """The part about plumber consulting agents to inform them about heating systems and feasibility of their chosen heating"""

    def consultation(self, job):
        """
        Performs a consultation for a houseowner.

        This method has two main paths:
        1. If the houseowner has no desired system, the Plumber shares knowledge
           about various systems and provides a recommendation.
        2. If the houseowner has a desired system, the Plumber checks its 
           feasibility, verifies the houseowner's ability to afford it (including 
           subsidies and loans), updates the final costs, and, if successful, 
           queues an installation job.

        Parameters
        ----------
        job : Job
            The consultation job containing the customer information.
        """
        agent_to_consult = job.customer
        # Consultation part if agent has no desired HS, i.e. is gathering information
        if (
            agent_to_consult.desired_hs == "No"
        ):  # The plumber shares knowledge about known HS
            # logger.info("I share my knowledge with {}!".format(id_to_consult))
            self.share_knowledge(agent_to_consult)
            self.share_rating(
                agent_to_consult
            )  # Pass the plumber's ratings to the opinions of an agent
            self.recommend(agent_to_consult)
            self.share_systems(agent_to_consult)
            agent_to_consult.aspiration_value = 0
            agent_to_consult.consultation_ordered = False
        # Consultation part if agent has a desired HS, i.e. needs a feasibility check
        elif (
            agent_to_consult.desired_hs != "No"
        ):  # The plumber evaluates feasibility of the chosen HS
            result = None
            if (agent_to_consult.house.energy_demand >= settings.plumber.insulation_threshold
                and agent_to_consult.desired_hs.get_name() in settings.plumber.insulation_list):
                result = "Failure"
                
            if not any(isinstance(obj, type(agent_to_consult.desired_hs)) for obj in self.known_hs):
                # logger.info("I don't know this system. We cannot work together!")
                    agent_to_consult.plumber = None
                    agent_to_consult.consultation_ordered = False
                    agent_to_consult.unqualified_plumbers.append(self.unique_id)
                    return
                
            elif (
                result == "Failure"
                and type(agent_to_consult.desired_hs).__name__
                != type(agent_to_consult.house.current_heating).__name__
                and (not settings.experiments.replacement_mandates 
                     or type(agent_to_consult.desired_hs).__name__
                     not in settings.experiments.systems_mandate)
                and (not settings.experiments.enforcement 
                     or type(agent_to_consult.desired_hs).__name__
                     not in settings.experiments.enforcement_systems)
                and self.model.scenario.__class__.__name__ != "Scenario_perfect"
            ):
                # logger.info("{}'s desired HS is infeasible!".format(id_to_consult))
                agent_to_consult.infeasible.append(
                    type(agent_to_consult.desired_hs).__name__
                )
                agent_to_consult.consultation_ordered = False
               
            else:
                # logger.info("{}'s desired HS is feasible! I added it to the installation queue".format(id_to_consult))
                for system in self.known_hs:
                    system.calculate_all_attributes(
                        area=agent_to_consult.house.area, 
                        energy_demand=agent_to_consult.house.energy_demand,
                        heat_load=agent_to_consult.house.heat_load
                    )
                self.share_rating(
                    agent_to_consult
                )  # Pass the plumber's ratings to the opinions of an agent
                for hs in self.known_hs:
                    if type(hs).__name__ == type(agent_to_consult.desired_hs).__name__:
                        # If the desired_hs is more expensive than expected
                        hs_copy = deepcopy(hs)
                        hs_copy.params["price"][0] = hs_copy.calculate_installation_costs(area = agent_to_consult.house.area,
                                                                                          heat_load = agent_to_consult.house.heat_load)
                        hs_copy.params["opex"][0] = hs_copy.calculate_operating_costs(area = agent_to_consult.house.area,
                                                                                      heat_load = agent_to_consult.house.heat_load)
                        if agent_to_consult.desired_hs.heat_delivery_contract:
                            can_afford_and_sustain = self.check_affordability(agent = agent_to_consult)
                            
                            if can_afford_and_sustain:
                                self.Services[1].queue_job(agent_to_consult,
                                                   installation_time = agent_to_consult.desired_hs.installation_time)
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.installation_ordered = True
                                
                            elif agent_to_consult.suitable_hs:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "Goal"
                                agent_to_consult.current_stage = "Stage 2"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_stage_2"] += 1
                            
                            else:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "None"
                                agent_to_consult.current_stage = "None"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_drop"] += 1
                        
                        elif (
                            agent_to_consult.desired_hs.params["price"][0] < hs_copy.params["price"][0]
                            ):
                            agent_to_consult.desired_hs.params["price"][0] = hs_copy.params["price"][0]
                            agent_to_consult.desired_hs.params["price"][1] = 0
                            agent_to_consult.desired_hs.params["opex"][0] = hs_copy.params["opex"][0]
                            agent_to_consult.desired_hs.params["opex"][1] = 0
                            
                            if (type(hs_copy).__name__ in self.known_subsidies_by_hs
                                and settings.plumber.apply_subsidies):
                                self.apply_subsidies(agent_to_consult.desired_hs, agent_to_consult)

                            if agent_to_consult.desired_hs.loan:
                                    agent_to_consult.find_loan(agent_to_consult.desired_hs,
                                                               bypass_avoidance = True)
                            
                            can_afford_and_sustain = self.check_affordability(agent = agent_to_consult)
                            
                            if can_afford_and_sustain:
                                self.Services[1].queue_job(agent_to_consult,
                                                           installation_time = agent_to_consult.desired_hs.installation_time)
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.installation_ordered = True
                            
                            elif agent_to_consult.suitable_hs:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "Goal"
                                agent_to_consult.current_stage = "Stage 2"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_stage_2"] += 1
                            
                            else:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "None"
                                agent_to_consult.current_stage = "None"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_drop"] += 1
                                
                        
                        elif (
                            agent_to_consult.desired_hs.params["price"][0]
                            > hs_copy.params["price"][0]
                        ):
                            agent_to_consult.desired_hs.params["price"][0] = hs_copy.params["price"][0]
                            agent_to_consult.desired_hs.params["price"][1] = 0
                            agent_to_consult.desired_hs.params["opex"][0] = hs_copy.params["opex"][0]
                            agent_to_consult.desired_hs.params["opex"][1] = 0
                            if (not agent_to_consult.desired_hs.subsidised
                                and type(hs_copy).__name__ in self.known_subsidies_by_hs
                                and settings.plumber.apply_subsidies):
                                self.apply_subsidies(agent_to_consult.desired_hs, 
                                                     agent_to_consult)
                            if agent_to_consult.desired_hs.loan:
                                agent_to_consult.find_loan(agent_to_consult.desired_hs,
                                                           bypass_avoidance = True)
                            # Adds an agent to the installation queue if feasible
                            self.Services[1].queue_job(agent_to_consult,
                                                       installation_time = agent_to_consult.desired_hs.installation_time)
                            agent_to_consult.consultation_ordered = False
                            agent_to_consult.installation_ordered = True

                        else:
                            # Adds an agent to the installation queue if feasible
                            agent_to_consult.desired_hs.params["price"][0] = hs_copy.params["price"][0]
                            agent_to_consult.desired_hs.params["price"][1] = 0
                            agent_to_consult.desired_hs.params["opex"][0] = hs_copy.params["opex"][0]
                            agent_to_consult.desired_hs.params["opex"][1] = 0
                            if (not agent_to_consult.desired_hs.subsidised
                                and type(hs_copy).__name__ in self.known_subsidies_by_hs
                                and settings.plumber.apply_subsidies):
                                self.apply_subsidies(agent_to_consult.desired_hs, 
                                                     agent_to_consult)
                                if agent_to_consult.desired_hs.loan:
                                    agent_to_consult.find_loan(agent_to_consult.desired_hs,
                                                               bypass_avoidance = True)
                            
                            can_afford_and_sustain = self.check_affordability(agent = agent_to_consult)
                            
                            if can_afford_and_sustain:
                                self.Services[1].queue_job(agent_to_consult,
                                                           installation_time = agent_to_consult.desired_hs.installation_time)
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.installation_ordered = True
                            
                            elif agent_to_consult.suitable_hs:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "Goal"
                                agent_to_consult.current_stage = "Stage 2"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_stage_2"] += 1
                            
                            else:
                                agent_to_consult.desired_hs.loan = None
                                agent_to_consult.consultation_ordered = False
                                agent_to_consult.suitable_hs = []
                                agent_to_consult.desired_hs = "No"
                                agent_to_consult.current_breakpoint = "None"
                                agent_to_consult.current_stage = "None"
                                agent_to_consult.aspiration_value = agent_to_consult.initial_aspiration_value
                                self.model.stage_flows["Stage_3"]["Plumber_consulted_to_drop"] += 1


    def recommend(self, agent):
        """
        Recommends the best-rated heating system to a houseowner.

        The recommendation is based on the Plumber's own evaluation of the 
        systems they know.

        Parameters
        ----------
        agent : Houseowner
            The houseowner to whom the recommendation is given.
        """
        sorted_known = sorted(self.known_hs, key=lambda x: x.rating)
        
        if agent.house.energy_demand >= settings.plumber.insulation_threshold:
            names_to_remove = settings.plumber.insulation_list
            sorted_known = [hs for hs in sorted_known 
                            if hs.get_name() not in names_to_remove]
            
        filtered_sorted_known = [
            instance
            for instance in sorted_known
            if instance.__class__.__name__ not in agent.infeasible
        ]
        
        best = filtered_sorted_known[-1]  # The best HS according to ratings
        agent.recommended_hs = deepcopy(best)

    """A part about installation of a chosen heating system"""

    def installation(self, job):
        """
        Performs the installation of a new heating system for a client.

        This method is called when an installation job is completed. It finalises
        the installation, updates the model's state (e.g., counters), and 
        deducts the cost from the houseowner's budget.

        Parameters
        ----------
        job : Job
            The installation job containing the customer information.
        """
        id_to_install = job.customer.unique_id
        for agent in self.model.schedule.agents:
            if agent.unique_id == id_to_install:
                hs_to_install = type(agent.desired_hs).__name__
                if hs_to_install != type(agent.house.current_heating).__name__:
                    self.model.changes_counter[agent.house.milieu.milieu_type] += 1
                self.install_system(agent, hs_to_install)
                self.model.replacements_counter[agent.house.milieu.milieu_type] += 1
                if agent.house.current_heating.loan:
                    agent.hs_budget += agent.house.current_heating.loan.loan_amount
                if agent.hs_budget - agent.desired_hs.params["price"][0] < 0:
                    raise ValueError(
                        f"Price is higher than budget!\n"
                        f"Plumber ID: {self.unique_id}\n"
                        f"Agent ID: {agent.unique_id}\n"
                        f"Desired HS: {type(agent.desired_hs).__name__}\n"
                        f"{'Recommended: Yes' if type(agent.recommended_hs) == type(agent.desired_hs) else 'Recommended: No'}\n"
                        f"{'Subsidised: Yes' if agent.desired_hs.subsidised else 'Subsidised: No'}\n"
                        f"Loan: {(agent.desired_hs.loan.loan_amount if agent.desired_hs.loan else None)}\n"
                        f"Income: {agent.income}\n"
                        f"Budget: {agent.hs_budget}\n"
                        f"Price: {agent.desired_hs.params['price'][0]}\n"
                        f"Difference: {agent.hs_budget - agent.desired_hs.params['price'][0]}"
                    )

                agent.hs_budget -= agent.desired_hs.params["price"][0]
                self.model.houseowner_spending += agent.desired_hs.params["price"][0]
                agent.installation_ordered = False
                agent.installed_once = True
                # logger.info("I installed a new system for " + str(id_to_install)) 
    
    """Heating system part"""

    def generate_system(self, variant):
        """
        Creates an instance of a heating system from its class name.

        Parameters
        ----------
        variant : str
            The class name of the heating system to create.

        Returns
        -------
        Heating_system
            An instance of the specified heating system.
        """
        params_table = self.model.heating_params_table
        class_obj = globals()[variant]
        system = class_obj(table = params_table)
        return system

    def install_system(self, agent, heating):
        """
        Replaces the agent's old heating system with a new one.

        This is the core logic for the installation, where the houseowner's 
        `current_heating` is updated, along with all relevant 
        financial and environmental metrics in the model.

        Parameters
        ----------
        agent : Houseowner
            The houseowner receiving the new system.
        heating : str
            The class name of the heating system to install.
        """
        system = self.generate_system(heating)
        system.calculate_all_attributes(
            area=agent.house.area, energy_demand=agent.house.energy_demand,
            heat_load=agent.house.heat_load
        )
        #Data collection
        subsidy = system.params["price"][0] - agent.desired_hs.params["price"][0]
        self.model.total_effort["Subsidies"] += subsidy
        self.model.heating_distribution[type(agent.house.current_heating).__name__] -= 1
        self.model.heating_distribution[type(system).__name__] += 1
        #Proceed with installation
        system.params["price"][0] = agent.desired_hs.params["price"][0]
        system.investment = system.params["price"][0]
        system.payback = system.investment / system.lifetime
        system.lifetime = agent.desired_hs.lifetime
        system.neighbours_opinions = agent.desired_hs.neighbours_opinions
        system.rating = agent.desired_hs.rating
        system.social_norm = agent.desired_hs.social_norm
        system.behavioural_control = agent.desired_hs.behavioural_control
        
        if agent.desired_hs.subsidised:
            system.subsidised = True
        if agent.desired_hs.loan:
            system.loan = agent.desired_hs.loan
            self.model.total_effort["Loans"] += system.loan.loan_amount
        self.modify_agent_income(agent = agent, 
                                 old_system = agent.house.current_heating, 
                                 new_system = system)
        agent.house.current_heating = deepcopy(system)
        self.clients_systems[agent.unique_id] = agent.house.current_heating.get_name()
        
        
    def evaluate_system(self, system):
        """
        Rates a heating system based on the Plumber's own preferences.

        Parameters
        ----------
        system : Heating_system
            The heating system to evaluate.
        """
        # Extract parameters from known heating systems
        systems_attributes = pd.DataFrame(
            {
                heating_system.__class__.__name__: {
                    key: (value[0] if isinstance(value, list) else value)
                    for key, value in heating_system.params.items()
                }
                for heating_system in self.known_hs
            }
        ).T
    
        # Create a DataFrame of agent preferences
        heating_preferences = pd.DataFrame([vars(self.heating_preferences)])
    
        # Normalize attributes
        normalized_attributes = systems_attributes / systems_attributes.max()
    
        # Columns to rescale
        columns_to_rescale = [
            "operation_effort",
            "fuel_cost",
            "emissions",
            "price",
            "installation_effort",
            "opex",
        ]
    
        # Rescale selected columns
        rescaled_attributes = normalized_attributes.copy()
        rescaled_attributes[columns_to_rescale] = 1 - normalized_attributes[columns_to_rescale]
    
        # Match order of preferences and attributes
        rescaled_attributes = rescaled_attributes[heating_preferences.columns]
    
        # Calculate the rating for the given system
        selected_system = rescaled_attributes.loc[type(system).__name__]
        system_rating = (selected_system * heating_preferences.iloc[0]).sum()
    
        # Assign the calculated rating to the system
        system.rating = system_rating / 6

    def share_systems(self, agent):
        """
        Shares knowledge of other clients' systems with a houseowner.

        Parameters
        ----------
        agent : Houseowner
            The agent to share information with.
        """
        if settings.plumber.share_systems:
            # Here, predecessors as the ones who influence this agent seem appropriate
            predecessors = agent.model.grid.get_cell_list_contents(
                list(agent.model.grid.G.predecessors(agent.unique_id)))
            neighbours_ids = [x.unique_id for x in predecessors]
            # Get neighbour systems from self.clients_systems where the neighbour ID matches
            neighbours_systems = {
                k: v for k, v in self.clients_systems.items() if k in neighbours_ids
            }
            
            # Update agent.neighbours_systems with those, replacing existing values if necessary
            agent.neighbours_systems.update(neighbours_systems)
        
        
    def share_rating(self, agent):
        """
        Shares the Plumber's ratings of known systems with a houseowner.

        Parameters
        ----------
        agent : Houseowner
            The agent to share ratings with.
        """
        my_known_hs = self.known_hs
        agent_known_hs = agent.known_hs

        for my_system in my_known_hs:  # For each system in my knowledge
            for his_system in agent_known_hs:  # And each in owner's
                if (
                    my_system.__class__ == his_system.__class__
                ):  # Check if those are matching
                    his_system.neighbours_opinions[self.unique_id] = (
                        my_system.rating
                    )  # Modify an entry in the dictionary

    def share_knowledge(self, agent):
        """
        Shares attribute knowledge about systems with a houseowner.

        Parameters
        ----------
        agent : Houseowner
            The agent to share knowledge with.
        """
        my_known_hs = deepcopy(self.known_hs)
        neighbours_known_hs = agent.known_hs
        
        for system in my_known_hs:
            system.params["price"][0] = system.calculate_installation_costs(
                area = agent.house.area,
                heat_load = agent.house.heat_load
            )
            system.params["opex"][0] = system.calculate_operating_costs(
                area = agent.house.area,
                heat_load = agent.house.heat_load
            )

        # Get class names of the instances in neighbours_known_hs
        names_of_neighbours_known_hs = {
            type(system).__name__ for system in neighbours_known_hs
        }

        # Influencing neighbours known systems parameters using Relative Agreement approach
        for my_system in my_known_hs:  # For each system in my knowledge
            for his_system in neighbours_known_hs:  # And each in owner's
                if (
                    my_system.__class__ == his_system.__class__
                ):  # Check if those are matching
                    influence_by_relative_agreement(
                        source_system = my_system,
                        target_system = his_system
                    )

        # Sharing knowledge with the client
        for system in my_known_hs:
            if type(system).__name__ not in names_of_neighbours_known_hs:
                copied_system = deepcopy(system)
                copied_system.neighbours_opinions = (
                    {}
                )  # Nullify subjective perception of the opinions of others
                copied_system.source = "Plumber"
                neighbours_known_hs.append(copied_system)
                
        # Sharing knowledge about subsidies
        for key in self.known_subsidies_by_hs:
            agent.known_subsidies_by_hs[key] = deepcopy(self.known_subsidies_by_hs[key])
    
    def modify_agent_income(self, agent, old_system, new_system):
        """
        Adjusts a houseowner's weekly net income after a new system is installed.

        The income is modified based on the difference in weekly running costs 
        (fuel and opex) between the old and new heating systems.

        Parameters
        ----------
        agent : Houseowner
            The agent whose income is being modified.
        old_system : Heating_system
            The previously installed heating system.
        new_system : Heating_system
            The newly installed heating system.
        """
        new_fuel_cost = new_system.params["fuel_cost"][0] / 52
        new_opex = new_system.params["opex"][0] / 52
        current_fuel_cost = old_system.params["fuel_cost"][0] / 52
        current_opex = old_system.params["opex"][0] / 52
        difference = (new_fuel_cost + new_opex) - (current_fuel_cost + current_opex)
        agent.income -= math.floor(difference)
        agent.income = max(agent.income, 0)
    
    def check_affordability(self, agent):
        """
        Verifies if a houseowner can afford a new heating system.

        Checks both the upfront installation cost against the agent's budget 
        (including loans) and the ongoing running costs against the agent's income.

        Parameters
        ----------
        agent : Houseowner
            The agent whose affordability is being checked.

        Returns
        -------
        bool
            True if the agent can afford the system, False otherwise.
        """
        can_afford = (agent.desired_hs.params["price"][0] 
                      <= agent.hs_budget 
                      + (agent.desired_hs.loan.loan_amount 
                         if agent.desired_hs.loan else 0)
                      )
                            
        weekly_fuel_costs = agent.desired_hs.params["fuel_cost"][0]/52
        weekly_opex = agent.desired_hs.params["opex"][0]/52
        old_weekly_fuel_costs = agent.house.current_heating.params["fuel_cost"][0]/52
        old_weekly_opex = agent.house.current_heating.params["opex"][0]/52
        sum_new = weekly_fuel_costs + weekly_opex
        sum_old = old_weekly_fuel_costs + old_weekly_opex
        difference = sum_new - sum_old
        
        if agent.desired_hs.loan:
            payment = agent.desired_hs.loan.monthly_payment / 4
            difference += payment
            
        if agent.house.current_heating.loan != None:
            burden = agent.house.current_heating.loan.monthly_payment / 4
        else:
            burden = 0
                
        can_sustain = agent.income - difference - burden >= 0
        
        if can_afford and can_sustain:
            return True
        else:
            return False
        
    
    def organize_subsidies(self):
        """
        Structures known subsidies into a dictionary for easy lookup.
        Sorts subsidies by the type of heating system they are applied to.
        """
        self.known_subsidies_by_hs = {}
        if not self.known_subsidies:
            return
        
        for subsidy in self.known_subsidies:
            if isinstance(subsidy.heating_system, tuple):
                for hs in self.known_hs:
                    hs_name = type(hs).__name__
                    if hs_name in subsidy.heating_system:
                        self.known_subsidies_by_hs.setdefault(hs_name, []).append(
                            deepcopy(
                                Subsidy(
                                    name=subsidy.name,
                                    abbr=subsidy.abbr,
                                    subsidy=subsidy.subsidy,
                                    heating_system=hs_name,
                                    condition=subsidy.condition,
                                    target=subsidy.target
                                )
                            )
                        )
            if subsidy.heating_system == "Any":
                for hs in self.known_hs:
                    hs_name = type(hs).__name__
                    self.known_subsidies_by_hs.setdefault(hs_name, []).append(
                        deepcopy(
                            Subsidy(
                                name=subsidy.name,
                                abbr=subsidy.abbr,
                                subsidy=subsidy.subsidy,
                                heating_system=hs_name,
                                condition=subsidy.condition,
                                target=subsidy.target
                            )
                        )
                    )
            elif not isinstance(subsidy.heating_system, tuple):
                self.known_subsidies_by_hs.setdefault(subsidy.heating_system, []).append(
                    deepcopy(subsidy)
                )
    
    def apply_subsidies(self, hs, agent):
        """
        Applies relevant subsidies to a heating system for a given agent.
    
        Parameters
        ----------
        hs : Heating_system
            The heating system to which subsidies will be applied.
        agent : Houseowner
            The agent for whom the subsidy conditions are checked.
        """
        system_type = type(hs).__name__
    
        current_price = hs.params["price"][0]
        total_subsidy = 0
        
        # Calculate the maximum allowed subsidy (min of 70% price or 21,000)
        subsidy_cap = min(current_price * 0.7, 21000)
    
        for subsidy_rule in self.known_subsidies_by_hs[system_type]:
            # Check if subsidy applies
            if subsidy_rule.target is None:
                subsidy_amount = current_price * subsidy_rule.subsidy
                total_subsidy += subsidy_amount
            elif subsidy_rule.check_condition(system=hs, agent=agent):
                subsidy_amount = current_price * subsidy_rule.subsidy
                total_subsidy += subsidy_amount
    
            # Enforce the cap immediately
            if total_subsidy >= subsidy_cap:
                total_subsidy = subsidy_cap
                break
        
        if total_subsidy > 0:
            hs.subsidised = True
    
        # Apply the final price reduction
        hs.params["price"][0] -= math.ceil(total_subsidy)
        
        # Reset the price uncertainty parameter
        hs.params["price"][1] = 0
    
    """Helpers for compatibility with the data collector"""
    def get_heating(self):
        return type(self.current_heating).__name__

    def get_trigger(self):
        return self.trigger_for_record

    def get_stage_dynamics(self):
        array = np.array(self.stage_counter)
        return array

    def get_class(self):
        return type(self).__name__

    def get_system_age(self):
        return self.current_heating.age

    def get_satisfied_ratio(self):
        return self.current_heating.rating

    def get_milieu(self):
        return "Plumber"

    def get_opex(self):
        return None

    def get_preferences(self):
        return None

    def get_heating_system_evaluation(self):
        return None

    def get_attributes(self):
        return None

    def __str__(self):
        return "Plumber_" + str(self.unique_id)

    def get_comprehensive_metrics(self):
        return None
    
    def get_house_area(self):
        return None
