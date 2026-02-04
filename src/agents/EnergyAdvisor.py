"""
This module provides the implementation for the EnergyAdvisor, an intermediary 
agent that consults Houseowners on heating systems, subsidies, and financing. 
It includes the `EnergyAdvisor` class itself and the `ConsultationServiceEnergyAdvisor` 
class, which handles the logic of performing a consultation.

:Authors:
 - Sören Lohr
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>

"""
import logging
from copy import deepcopy
from mesa.model import Model
from agents.base.Intermediary import Intermediary
from agents.base.Service import ConsultationService
from interventions.Subsidy import *
from helpers.config import settings
from modules.Triggers import *

logger = logging.getLogger("ahoi")


class ConsultationServiceEnergyAdvisor(ConsultationService):
    """
    A specialized consultation service provided by an EnergyAdvisor.

    This service handles the process of a consultation job. When a job is 
    completed, it evaluates heating systems based on the houseowner's specific
    situation, applies relevant subsidies, filters for feasibility and 
    affordability, and provides a tailored recommendation.
    """
    def __init__(self, intermediary=None):
        """
        Initializes the consultation service for an EnergyAdvisor.
        Sets the job length specific to energy advisors.

        Parameters
        ----------
        intermediary : EnergyAdvisor, optional
            The EnergyAdvisor agent providing this service. Defaults to None.
        """
        super().__init__(intermediary)
        self.duration = settings.energy_advisor.cons_duration

    def begin_job(self):
        """
        Begins a consultation job by adding it to active jobs 
        and removes it from the job queue.
        """
        super().begin_job()
        self.job_queue.popleft()

    def complete_job(self, job):
        """Completes a consultation job and provides advice to the houseowner.

        This method performs the core logic of the consultation. It assesses
        heating systems known to the advisor, calculates house-specific costs,
        applies subsidies, and filters the options based on the customer's
        budget. The most suitable options are then presented to the houseowner.

        Parameters
        ----------
        job : Job
            The consultation job to be completed.
        """
        super().complete_job(job)

        known_hs = deepcopy(self.intermediary.known_hs)

        # 1. Calculate costs and apply subsidies
        for hs in known_hs:
            hs.calculate_all_attributes(
                area=job.customer.house.area,
                energy_demand=job.customer.house.energy_demand,
                heat_load=job.customer.house.heat_load
            )

            system_type = type(hs).__name__

            if system_type in self.intermediary.known_subsidies_by_hs:
                total_subsidy = 0
                current_price = hs.params["price"][0]
                
                # Cap is the lesser of 70% of price or 21,000
                subsidy_cap = min(current_price * 0.7, 21000)

                for subsidy_rule in self.intermediary.known_subsidies_by_hs[system_type]:
                    
                    if subsidy_rule.target is None:
                        subsidy_amount = current_price * subsidy_rule.subsidy
                        total_subsidy += subsidy_amount
                    elif subsidy_rule.check_condition(system=hs, agent=job.customer):
                        subsidy_amount = current_price * subsidy_rule.subsidy
                        total_subsidy += subsidy_amount
                    
                    # Enforce cap on standard subsidies
                    if total_subsidy >= subsidy_cap:
                        total_subsidy = subsidy_cap
                        break
                
                # Apply Premium (5% of base price)
                total_subsidy += current_price * 0.05
                
                if total_subsidy > 0:
                    hs.subsidised = True
                
                hs.params["price"][0] -= total_subsidy
                hs.params["price"][1] = 0

        # 2. Rate and Sort Systems
        # Evaluate current heating
        self.intermediary.evaluate_system(job.customer.house.current_heating)
        
        # Evaluate potential systems
        hs_ratings = {hs: self.intermediary.evaluate_system(hs) for hs in known_hs}
        
        # Sort by rating descending
        sorted_hs_items = sorted(hs_ratings.items(), key=lambda item: item[1], reverse=True)
        
        for hs, rating in sorted_hs_items:
            hs.rating = rating

        # 3. Filter, Check Loans, and Collect Data
        filtered_hs = {}

        # Filter 1: Feasibility (Must not be in infeasible list)
        feasible_items = [
            (hs, rating) for hs, rating in sorted_hs_items
            if type(hs).__name__ not in job.customer.infeasible
        ]

        for hs, rating in feasible_items:
            hs_name = type(hs).__name__

            # Check Budget & Find Loan
            if hs.params["price"][0] > job.customer.hs_budget:
                job.customer.find_loan(hs)

            # Data Collection: Categorize dropout status
            affordable = hs.params["price"][0] <= job.customer.hs_budget
            has_loan = hs.loan is not None
            
            # Determine specific dataframe column
            category = ""
            if hs.subsidised:
                if affordable:   category = "Take_Subsidised"
                elif has_loan:   category = "Take_Subsidised+Loan"
                else:            category = "Drop_Subsidised"
            else:
                if affordable:   category = "Take_Unsubsidised"
                elif has_loan:   category = "Take_Unsubsidised+Loan"
                else:            category = "Drop_Unsubsidised"
            
            job.customer.model.dropout_counter.loc[hs_name, category] += 1

            # Filter 2: Affordability (Must be affordable or have a loan)
            if affordable or has_loan:
                filtered_hs[hs] = rating

        # 4. Formulate Recommendation
        if filtered_hs:
            # Candidates are already sorted by rating from step 2
            recommendation_candidates = list(filtered_hs.keys())
            
            # Apply insulation threshold filter if necessary
            if job.customer.house.energy_demand >= settings.plumber.insulation_threshold:
                recommendation_candidates = [
                    hs for hs in recommendation_candidates
                    if type(hs).__name__ not in settings.plumber.insulation_list
                ]
            
            # Set the best candidate
            if recommendation_candidates:
                best_hs = recommendation_candidates[0]
                job.customer.recommended_hs = deepcopy(best_hs)
            
            # Share subsidy knowledge for the surviving options
            for hs in filtered_hs:
                hs_type = type(hs).__name__
                if hs_type in self.intermediary.known_subsidies_by_hs:
                    job.customer.known_subsidies_by_hs[hs_type] = (
                        self.intermediary.known_subsidies_by_hs[hs_type]
                    )

        # 5. Final Knowledge Update
        self.intermediary.share_knowledge(agent=job.customer)
        
        job.customer.aspiration_value = 0
        job.customer.consultation_ordered = False
        job.customer.subsidy_curious = False
        if job.customer.current_stage == "None":
            job.customer.active_trigger = Trigger_consulted()


class EnergyAdvisor(Intermediary):
    """An intermediary agent providing expert advice on heating systems.

    The EnergyAdvisor specializes in knowledge about heating technologies and
    financial subsidies. It consults houseowners to help them find the most
    suitable and cost-effective heating solutions based on their specific
    needs and financial situation.

    Attributes
    ----------
    known_hs : list
        A list of `Heating_system` objects the advisor is knowledgeable about.
    heating_preferences : Heating_preferences
        The preferences used by the advisor to evaluate heating systems.
    known_subsidies : list
        A list of `Subsidy` objects the advisor is aware of.
    infeasible : list
        A list of heating system names considered infeasible by this advisor.
    perceived_uncertainty : dict
        A mapping of heating system names to perceived uncertainty values.
    known_subsidies_by_hs : dict
        A dictionary organizing known subsidies by the heating systems they apply to.
    Services : list
        A list of services offered by the advisor.
    """
    def __init__(
        self,
        unique_id: int,
        model: Model,
        heating_preferences=None,
        known_hs=None,
        known_subsidies=None,
    ) -> None:
        """Initializes an EnergyAdvisor agent.

        Parameters
        ----------
        unique_id : int
            The unique identifier for the agent.
        model : Model
            The main MESA model instance.
        heating_preferences : Heating_preferences, optional
            The agent's preferences for evaluating heating systems.
        known_hs : list, optional
            A list of known heating systems.
        known_subsidies : list, optional
            A list of known subsidies.
        """
        super().__init__(unique_id, model)
        self.known_hs = known_hs
        self.heating_preferences = heating_preferences
        self.known_subsidies = known_subsidies
        self.infeasible = []
        self.perceived_uncertainty = {"Heating_system_heat_pump": 1,
                           "Heating_system_heat_pump_brine": 0.7,
                           "Heating_system_gas": 0.5,
                           "Heating_system_network_district": 0.3,
                           "Heating_system_network_local": 0.3,
                           "Heating_system_GP_Joule": 0.3,
                           "Heating_system_oil": 0.2,
                           "Heating_system_pellet": 0,
                           "Heating_system_electricity": 0,
                           }
        self._organize_subsidies()

        self.Services = [ConsultationServiceEnergyAdvisor(self)]

    def _organize_subsidies(self):
        """Organises the list of known subsidies into a dictionary 
        for efficient lookup.

        This internal method structures the `known_subsidies` list into the
        `known_subsidies_by_hs` dictionary, mapping heating system names to
        a list of applicable subsidies.
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

        
    def evaluate_system(self, system):
        """Evaluates a heating system based on the advisor's preferences.

        This method extends the base `evaluate_system` from the `Intermediary`
        class. It can be modified to include advisor-specific evaluation criteria.

        Parameters
        ----------
        system : Heating_system
            The heating system to be evaluated.

        Returns
        -------
        float
            The calculated rating for the system.
        """
        rating = super().evaluate_system(system)

        return rating
    
    def share_knowledge(self, agent):
        """Shares detailed, house-specific knowledge about heating systems.

        The advisor calculates house-specific parameters for its known
        systems and updates the houseowner's knowledge base. New systems are
        added, and existing ones are updated with the advisor's expert data.

        Parameters
        ----------
        agent : Houseowner
            The houseowner agent to share knowledge with.
        """
        my_known_hs = self.known_hs
        neighbours_known_hs = agent.known_hs
        names_of_neighbours_known_hs = {
            system.__class__.__name__ for system in neighbours_known_hs
        }

        # Calculate house-specific values for the systems
        for system in my_known_hs:
            system.calculate_all_attributes(
                area=agent.house.area, energy_demand=agent.house.energy_demand,
                heat_load=agent.house.heat_load
            )
        
        # Sharing knowledge with the neighbour
        for system in my_known_hs:
            for his_system in neighbours_known_hs:
                if type(system).__name__ == type(his_system).__name__:
                    his_system.params = deepcopy(system.params)
                    his_system.source = "Energy Advisor"
                    
        for system in my_known_hs:
            if system.__class__.__name__ not in names_of_neighbours_known_hs:
                copied_system = deepcopy(system)
                copied_system.neighbours_opinions = (
                    {}
                )  # Nullify subjective perception of the opinions of others
                neighbours_known_hs.append(copied_system)
                
    def share_rating(self, agent, systems_list):
        """Shares the advisor's ratings of heating systems with a houseowner.

        This method updates the houseowner's `neighbours_opinions` for each
        system, effectively influencing the houseowner's perception of those systems.

        Parameters
        ----------
        agent : Houseowner
            The houseowner to share ratings with.
        systems_list : list
            The list of `Heating_system` objects whose ratings are to be shared.
        """
        my_known_hs = systems_list
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
    
               
    def get_milieu(self):
        """Returns the agent's type for the data collector."""
        return "EnergyAdvisor"

    def get_opex(self):
        """Returns None, as advisors do not have operational expenses."""
        return None
    
    def get_house_area(self):
        """Returns None, as advisors are not associated with a house."""
        return None

    def __repr__(self):
        return f"{self.unique_id}: {type(self)}"

    def __str__(self):
        return self.__repr__()