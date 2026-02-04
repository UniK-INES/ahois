"""
Superclass for any intermediary in the model (i.e. Plumber, EnergyAdvisor (EA)), 
but not for Houseowner
Contains common methods to ensure basic functionality.

:Authors:
 - Sören Lohr
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>

"""
import pandas as pd
from copy import deepcopy
from mesa import Agent
from mesa.model import Model
from helpers.config import settings
import logging
from collections import deque
from helpers.utils import influence_by_relative_agreement

logger = logging.getLogger("ahoi.intermediary")

class Intermediary(Agent):
    """A base class for intermediary agents like Plumbers and Energy Advisors.

    This  class provides common functionality for agents that interact with 
    Houseowners to provide services. It manages the lifecycle of jobs (queuing, 
    starting, and completing), evaluates heating systems based on a set of 
    preferences, and shares knowledge and ratings with other agents.
    """
    def __init__(
        self,
        unique_id: int,
        model: Model,
        heating_preferences=None,
        known_hs=None,
        active_jobs: dict = None,
        completed_jobs: dict = None,
        max_concurrent_jobs: int = 1,
        active_jobs_counter: int = 0,
        hs_evaluation_params: list = None,
        hs_evaluation_params_rescale: list = None,
    ) -> None:
        """
        Initialises an intermediary.
        
        Parameters
        ----------
        unique_id: int
            ID of the intermediary.
        model: MESA Model
            An instance of MESA Model to contain the intermediary.
        heating_preferences: Heating_preferences
            Class containing weights for heating attribute evaluation.
        known_hs: list
            A list of heating systems the agent has learned about 
            through information gathering or social interactions.
        active_jobs: dict
            Contains jobs that intermediary does.
        completed_jobs: dict
            Contains completed jobs for data gathering.
        max_concurrent_jobs: int
            Maximum number fo jobs the intermediary can do at the same time.
        active_jobs_counter: int
            Counts the number of jobs done currently.
        hs_evaluation_params: list
            List of heating attributes to be considered during evaluation.
        hs_evaluation_params_rescale: list
            List of heating attributes to be considered during evaluation,
            rescaled if less or more attributes are needed.
        
        """
        
        super().__init__(unique_id, model)

        self.heating_preferences = heating_preferences
        self.known_hs = known_hs if known_hs is not None else []
        self.hs_evaluation_params = (
            hs_evaluation_params
            if hs_evaluation_params is not None
            else [
                "operation_effort",
                "fuel_cost",
                "emissions",
                "price",
                "installation effort",
                "opex",
            ]
        )
        self.hs_evaluation_params_rescale = (
            hs_evaluation_params_rescale
            if hs_evaluation_params_rescale is not None
            else [
                "operation_effort",
                "fuel_cost",
                "emissions",
                "price",
                "installation effort",
                "opex",
            ]
        )

        self.active_jobs = active_jobs if active_jobs is not None else dict()
        self.completed_jobs = (
            completed_jobs if completed_jobs is not None else dict()
            )

        self.max_concurrent_jobs = max_concurrent_jobs
        self.active_jobs_counter = active_jobs_counter

        self.steps_after_training = 0 #Number of steps passed after the last training

    def step(self) -> None:
        """
        Performs the common step for any intermediary.
        
        Ensures that new subclasses perform basic actions without errors.
        Should be overridden in each subclass to include specific actions.
        """
        types = [type(i) for i in self.known_hs]
        if any(types.count(t) > 1 for t in set(types)): 
            #Debug to catch duplicate options in known_hs
            raise Exception(f"{self.unique_id} has two similar systems in known_hs")
        
        for service in self.Services:
            # Different intermediaries can have different sets of services
            service.save_queue_length()
            seen_ids = set()
            filtered_jobs = deque()
            duplicates = set()
            
            # Filters out duplicates among customers in the queue
            # NOTE: there should be no duplicates in a normal situations
            for job in service.job_queue:
                cust_id = job.customer.unique_id
                if cust_id in seen_ids:
                    duplicates.add(cust_id)
                else:
                    seen_ids.add(cust_id)
                    filtered_jobs.append(job)
            # Print, which duplicates were removed
            if duplicates:
                print("Removed duplicate jobs for customers:", list(duplicates))
            # Replace the job deque with the filtered deque
            service.job_queue = filtered_jobs
        
        if (self.steps_after_training > 52
            and not self.active_jobs):
            self.update_attributes()
            self.training()
            self.steps_after_training = 0
        else:
            self.steps_after_training += 1
            self.update_attributes()
            self.work()

    def work(self):
        """ 
        Two actions:
        1. Transfers some jobs from service.job_queue to self.active_jobs.
        2. Performs service-specific job. This happens only for jobs 
        assigned for the current step.
        """
        # + 1 because schedule.steps are incremented after all agent.step()
        steps = self.model.schedule.steps + 1
        logger.debug(f"{steps}: Intermediary {self} works...")
        for service in self.Services:
            self.begin_jobs(steps, service)
            self.check_job_completion(steps)
            
        logger.debug(f"{steps}: Active jobs: {sum(len(v) for v in self.active_jobs.values())}" +
                     f" | Completed jobs: {sum(len(v) for v in self.completed_jobs.values())}")

    def training(self):
        """
        Plumber/EA compatibility method
        Plumbers have their own training, while EA use this
        """
        self.work()
        
    def update_attributes(self):
        """
        Updates data tables for known technologies when 
        dynamics values of the attributes are used.
        Synchronises own parameter table with that of the model.
        """
        if settings.data.dynamic == False:
            return
        table = self.model.heating_params_table
        for system in self.known_hs:
            system_row = table.content.loc[type(system).__name__]
            system.table = system_row

    def begin_jobs(self, steps, service):
        """
        Transfers some jobs from service.job_queue to self.active_jobs.
        Job completion is set to a step in the future.
        Number of jobs transfered depends on self.max_concurrent_jobs.
        Orders the service to begin the jobs.
        
        Parameters
        ----------
        steps: int
            ID of the step to set the job duration.
            Normally, the current step.
        service: Service
            Service to begin the job.
        """
        for _ in range(self.max_concurrent_jobs - sum(len(v) for v in self.active_jobs.values())):
            if not service.job_queue:
                return
            job = service.job_queue[0]
            self.active_jobs.setdefault(steps + job.duration, []).append(job)
            job.service.begin_job()

    def check_job_completion(self, steps):
        """
        Checks the self.active_jobs for jobs that should be finished
        at the given step.
        
        Parameters
        ----------
        steps: int
            Step ID to check the job completion.
            Normally, the current step.
        """
        job_list = self.active_jobs.pop(steps, [])
        for job in job_list:
            self.completed_jobs.setdefault(steps, []).append(job)
            job.service.complete_job(job)

    def evaluate_system(self, system):
        """
        Creates a heating system rating using heating system's parameters 
        and agent's preferences.
        
        Parameters
        ----------
        system: Heating_system
            The Heating_system object to be evaluated.
        """
    
        # Build a DataFrame of known heating systems' attributes
        systems_attributes = pd.DataFrame(
            {
                heating_system.__class__.__name__: {
                    key: (value[0] if isinstance(value, list) else value)
                    for key, value in heating_system.params.items()
                }
                for heating_system in self.known_hs
            }
        ).T
    
        # Create a DataFrame for agent preferences
        heating_preferences = pd.DataFrame([vars(self.heating_preferences)])
    
        # Normalize system attributes
        normalized_attributes = systems_attributes / systems_attributes.max()
    
        # Specify columns for rescaling
        columns_to_rescale = [
            "operation_effort",
            "fuel_cost",
            "emissions",
            "price",
            "installation_effort",
            "opex",
        ]
    
        # Rescale specified columns
        rescaled_attributes = normalized_attributes.copy()
        rescaled_attributes[columns_to_rescale] = 1 - normalized_attributes[columns_to_rescale]
    
        # Align columns to match preference DataFrame
        rescaled_attributes = rescaled_attributes[heating_preferences.columns]
    
        # Retrieve attributes of the selected system
        selected_system = rescaled_attributes.loc[type(system).__name__]
    
        # Compute the weighted sum of attributes
        system_rating = (selected_system * heating_preferences.iloc[0]).sum()
    
        # Assign and return the calculated rating
        system.rating = system_rating
        return system_rating / 6


    def share_rating(self, agent):
        """
        The intermediary shares the ratings of his known HS with a client

        Parameters
        ----------
        agent: Houseowner
            A houseowner to share the ratings of known HS.

        """
        my_known_hs = self.known_hs
        agent_known_hs = agent.known_hs

        for my_system in my_known_hs:  # For each system in my knowledge
            my_system.calculate_all_attributes(
                area=agent.house.area, energy_demand=agent.house.energy_demand,
                heat_load=agent.house.heat_load
            )
            for his_system in agent_known_hs:  # And each in owner's
                if (
                    my_system.__class__ == his_system.__class__
                ):  # Check if those are matching
                    his_system.neighbours_opinions[self.unique_id] = (
                        my_system.rating
                    )  # Modify an entry in the dictionary

    def share_knowledge(self, agent):
        """
        The intermediary shares the knowledge 
        about their known heating systems with an agent.
        It also influences agent's opinion on other known systems

        Parameters
        ----------
        counterpart: Houseowner
            A houseowner to share the knowledge about known HS.

        """
        my_known_hs = self.known_hs
        neighbours_known_hs = agent.known_hs

        # Calculate house-specific values for the systems
        for system in my_known_hs:
            system.calculate_all_attributes(
                area=agent.house.area, energy_demand=agent.house.energy_demand,
                heat_load=agent.house.heat_load
            )

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
                                                    target_system = his_system)

        # Sharing knowledge with the neighbour
        for system in my_known_hs:
            if system.__class__.__name__ not in names_of_neighbours_known_hs:
                copied_system = deepcopy(system)
                copied_system.neighbours_opinions = (
                    {}
                )  # Nullify subjective perception of the opinions of others
                neighbours_known_hs.append(copied_system)

    """
    Helpers for compatibility with the data collector.
    Can be adjusted to return some data.
    """
    def get_heating(self):
        return None

    def get_trigger(self):
        return None

    def get_stage_dynamics(self):
        return None

    def get_class(self):
        return type(self).__name__

    def get_system_age(self):
        return None

    def get_opinion(self):
        return None

    def get_satisfied_ratio(self):
        return None

    def get_preferences(self):
        return None

    def get_attributes(self):
        return None

    def get_comprehensive_metrics(self):
        return None

    def get_emissions(self):
        return None

    def get_energy_demand(self):
        return None
    
    def get_obstacles(self):
        return None
