"""
This module provides the classes and logic for how agents gather information.
It features a base `Information_source` class that implements the core
information-seeking process, where an agent receives potentially biased and
uncertain data about a heating system.

Specific subclasses, such as `Information_source_internet` and
`Information_source_plumber`, represent different channels through which an
agent can seek information. Each source has its own characteristics, including
the scope of its knowledge (content), the cost to consult it, and the specific
interaction mechanics.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import math
from copy import deepcopy
from helpers.config import settings
from modules.Rng import rng_information_source_run
from interventions.Subsidy import *


class Information_source:
    """
    A base class for a generic source of information.

    This class provides the structure and methods for all information
    sources in the model. It defines standard attributes like search cost and
    distortion levels and contains the core `data_search` method, which
    simulates the process of an agent acquiring and perceiving information.

    Attributes
    ----------
    cost : int
        The cognitive resource cost for an agent to perform one search action.
    distortion : float
        The base (maximum) factor for distorting a heating system's true parameters.
    min_distortion : float
        The minimum distortion (for a 100% market share system).
    uncertainty_lower : float
        The lower bound for the uncertainty range applied to parameters.
    uncertainty_upper : float
        The upper bound for the uncertainty range applied to parameters.
    content : list or None
        A list of heating system names that this source can provide information on.
    """

    def __init__(self):
        """
        Initialises a generic Information_source instance.

        This constructor sets the default attributes for an information source,
        such as cost and distortion levels, by loading them from the global
        settings.
        """
        # Other params
        self.cost = settings.decision_making_costs.get_data
        
        # This is the worst max_distortion (for a 0% market share tech)
        self.distortion = settings.information_source.distortion 
        # This is the best maximum distortion (for a 100% market share tech)
        self.min_distortion = 0.1
        
        self.uncertainty_lower = settings.information_source.uncertainty_lower  # To be used for uncertainty ranges
        self.uncertainty_upper = settings.information_source.uncertainty_upper
        self.content = None  # Default content is None, subclasses can override
        self.known_subsidies_by_hs = {}
        self.subsidy_finding_prob = settings.information_source.subsidy_finding_prob

    # returns a list of all subclasses
    @classmethod
    def instantiate_subclasses(cls):
        """
        Creates and returns an instance of each direct subclass.

        This factory method is a convenient way to get a list of all available
        information source objects in the simulation.

        Returns
        -------
        list[Information_source]
            A list containing one instance of each subclass.
        """
        return [subclass() for subclass in cls.__subclasses__()]

    def data_search(self, agent, cost):
        """
        Simulates an agent's process of searching for information using
        Internet or Magazine.

        This method models an agent spending cognitive resources to acquire
        information about a heating system. The process involves several steps:
        1. A random heating system is selected from the source's content.
        2. A "perceived" version of this system is created, where its true
           parameters are distorted.
        3. The distortion is "pessimistic-only" (>= 1.0) and its
           upper bound is based on the system's market share.
           - New tech (low share) = wide range [0.0, MAX] -> unpredictable
           - Old tech (high share) = narrow range [0.0, MIN] -> predictable
        4. An uncertainty range is added to each perceived parameter.
        5. If the system is new to the agent, it's added to their knowledge base.
        6. If the agent already knows the system, their existing perception is
           updated using a relative agreement mechanism.
        The source also add knowledge about subsidies.
        The search continues until the agent runs out of cognitive resources,
        finds a satisfactory option, or becomes overloaded with information.

        Parameters
        ----------
        agent : Houseowner
            The agent performing the information search.
        cost : int
            The cognitive resource cost for this specific search action.
        """
        # Get the model's heating distribution
        distribution = agent.model.heating_distribution
        total_houses = sum(distribution.values())

        # Define the min/max for distortion width
        max_distortion = self.distortion     
        min_distortion = self.min_distortion 
        
        while (
            agent.cognitive_resource >= self.cost
        ):  # Repeat data search while having enough cognitive resource

            if len(agent.known_hs) == len(self.content) or (
                len(agent.known_hs) > 1 and agent.aspiration_value == 0
            ):  # The agent knows more than his own system and is aspired
                # logger.info("I already have enough data! Proceed!")
                break

            randomizer = rng_information_source_run().choice(
                self.content, replace=True
            )  # Get data about random HS from the chosen source
            
            # 1. Get market share for the chosen system
            market_share = 0.0
            if total_houses > 0:
                market_share = distribution.get(randomizer, 0) / total_houses
            
            # 2. Calculate this system's dynamic *top* distortion
            dynamic_top_distortion = min_distortion + (1.0 - market_share) * (max_distortion - min_distortion)
            
            
            # Corrects parameters of newly found HS with perception and distortion, thus forming "expectations"
            found_system = agent.generate_system(randomizer)
            found_system.calculate_all_attributes(
                area=agent.house.area, energy_demand=agent.house.energy_demand, heat_load = agent.house.heat_load
            )#using tailored for system params
            #if averaged info: area=106, energy_demand=147, heat_load=19
            # logger.info("I got info about " + str(type(found_system).__name__))
            
            bot_distortion = -dynamic_top_distortion
            top_distortion = dynamic_top_distortion
            
            for key in [
                "operation_effort",
                "fuel_cost",
                "emissions",
                "price",
                "installation_effort",
                "opex",
            ]:
                random_noise = rng_information_source_run().uniform(
                    bot_distortion, top_distortion
                    )
                
                distortion_factor = max(0.5, 1 + random_noise)

                # Multiply
                found_system.params[key][0] = found_system.params[key][0] * distortion_factor
            

            # Setting the uncertainty range
            for key, value in found_system.params.items():
                value[1] = value[0] * rng_information_source_run().uniform(
                    self.uncertainty_lower, self.uncertainty_upper
                )

            if type(found_system).__name__ in agent.infeasible:
                break
                # logger.info(f"I know that type(found_system).__name__ is infeasible!")

            elif not any(
                type(i).__name__ == type(found_system).__name__ for i in agent.known_hs
            ):  # Checks whether the agent does not know this HS
                agent.cognitive_resource -= cost
                found_system.source = "Internet"
                agent.known_hs.append(
                    found_system
                )  # Add system with "expected" parameters to the list of known HS
                for system in agent.known_hs:
                    agent.calculate_attitude(system)
                    if type(system).__name__ == type(agent.house.current_heating).__name__:
                        agent.house.current_heating.rating = system.rating

                if found_system.rating > agent.house.current_heating.rating:
                    agent.aspiration_value -= 1  # Get closer to the aspiration point
                else:
                    agent.overload_value -= 1  # Get closer to the overload
                if agent.aspiration_value == 0:
                    # logger.info("I obtained enough data!") #Marks aspiration
                    break
                elif agent.overload_value == 0:
                    # logger.info("I am overloaded!") #Marks overload
                    agent.current_stage = "None"
                    agent.model.stage_flows["Stage_2"]["Overloaded"] += 1
                    break

            else:  # Use relative agreement if the system is already known
                agent.cognitive_resource -= cost
                agent.relative_agreement(new_system = found_system)
                for system in agent.known_hs:
                    agent.calculate_attitude(system)
            
            
            #Subsidies part
            if rng_information_source_run().uniform() < self.subsidy_finding_prob:
                hs_name = type(found_system).__name__
                if hs_name in self.known_subsidies_by_hs:
                    agent.known_subsidies_by_hs[hs_name] = deepcopy(self.known_subsidies_by_hs[hs_name])
            
            #Overload part
            if agent.overload_value == 0:  # Marks information overload
                # logger.info("I've spent all my resource but found nothing good! I quit!")
                agent.current_stage = "None"
                agent.model.stage_flows["Stage_2"]["Overloaded"] += 1
                

class Information_source_internet(Information_source):
    """
    Represents the Internet as a source of information.
    """
    def __init__(self):
        """
        Initialises the Internet source.
        The Internet is configured to have knowledge of all heating systems
        and subsidies listed in the project settings.
        """
        super().__init__()
        self.content = (
            settings.heating_systems.list
        )  # List of options to provide to an agent
        self.known_subsidies_by_hs = {}
        self.organize_subsidies()
        
    def organize_subsidies(self):
        """
        Populate the source's knowledge of available subsidies.

        This method compiles a list of subsidies applicable to the heating
        systems that the source provides information about.
        """
        subsidies_list = [Subsidy_pellet(),
                          Subsidy_heat_pump(),
                          Subsidy_heat_pump_brine(),
                          Subsidy_network_local(),
                          Subsidy_GP_Joule(),
                          Subsidy_climate_speed(),
                          Subsidy_income(),
                          Subsidy_efficiency()]
        for subsidy in subsidies_list:
            if isinstance(subsidy.heating_system, tuple):
                    for hs_name in self.content:
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
                for hs_name in self.content:
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

class Information_source_magazine(Information_source):
    """
    Represents a professional magazine as a source of information.
    """
    def __init__(self):
        """
        Initialises the magazine source.

        A magazine is configured with a limited set of conventional heating
        systems that it can provide information about.
        """
        super().__init__()
        self.content = [
            "Heating_system_gas",
            "Heating_system_heat_pump",
            "Heating_system_electricity",
            "Heating_system_pellet",
        ]  # List of options to provide to an agent
        self.known_subsidies_by_hs = {}
        self.organize_subsidies()
        
    def organize_subsidies(self):
        """
        Populates the source's knowledge of available subsidies.
        This method compiles a list of subsidies applicable to the heating
        systems that the source provides information about.
        """
        subsidies_list = [Subsidy_pellet(),
                          Subsidy_heat_pump(),
                          Subsidy_heat_pump_brine(),
                          Subsidy_network_local(),
                          Subsidy_GP_Joule(),
                          Subsidy_climate_speed(),
                          Subsidy_income(),
                          Subsidy_efficiency()]
        for subsidy in subsidies_list:
            if isinstance(subsidy.heating_system, tuple):
                    for hs_name in self.content:
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
                for hs_name in self.content:
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


class Information_source_plumber(Information_source):
    """
    Represents a plumber as a source of information.
    Not the plumber itself. This subclass facilitates
    exclusively the data search part 
    of houseowner-plumber interaction.
    """
    def __init__(self):
        """
        Initializes the plumber information source.
        """
        super().__init__()
        self.known_subsidies_by_hs = {}

    def data_search(self, agent, cost):
        """
        Simulate an agent consulting a plumber.

        This method models the specific interaction of ordering a consultation
        from a plumber. The agent finds a plumber (if they don't already have
        one) and requests a service. The actual information exchange is then
        handled by the plumber agent's logic.

        Parameters
        ----------
        agent : Houseowner
            The agent seeking a consultation.
        cost : int
            The cognitive resource cost of contacting the plumber.
        """
        if agent.cognitive_resource >= cost:
            agent.cognitive_resource -= cost
            if agent.plumber == None:  # Finds a plumber if none has been found yet
                agent.find_plumber()
                # logger.info("I have found a new plumber -- {}".format(self.plumber))
    
            agent.order_plumber()  # Orders a consultation. The plumber will carry out the rest.
            # logger.info("I have ordered a consultation from my plumber!")
            agent.cognitive_resource = 0


class Information_source_neighbours(Information_source):
    """
    Represents neighbours as a source of information.
    Not the neighbours themselves. This subclass facilitates
    exclusively the information search among neighbours.
    """
    def __init__(self):
        """
        Initialises the neighbours information source.
        """
        super().__init__()
        self.known_subsidies_by_hs = {}

    def data_search(self, agent, cost):
        """
        Simulate an agent asking their neighbours for information.

        This method triggers the agent's behaviour to interact with their
        neighbours to gather opinions and information about their heating
        systems. The information exchange is handled by the agent's
        `ask_neighbours` method.

        Parameters
        ----------
        agent : Houseowner
            The agent asking neighbors.
        cost : int
            The cognitive resource cost (not used in this implementation).
        """
        if agent.cognitive_resource >= cost:
            agent.ask_neighbours(coverage = 514)
            agent.cognitive_resource = 0

class Information_source_energy_advisor(Information_source):
    """
    Represents an energy advisor as a source of information.
    Not the EA itself. This subclass facilitates
    exclusively the data search part 
    of houseowner-EA interaction.
    """
    def __init__(self):
        """
        Initialises the energy advisor information source.
        """
        super().__init__()
        self.known_subsidies_by_hs = {}

    def data_search(self, agent, cost):
        """
        Simulates an agent consulting an energy advisor.
        This method models the agent finding and ordering a consultation from
        an energy advisor. The detailed information exchange is subsequently
        handled by the energy advisor agent's logic.

        Parameters
        ----------
        agent : Houseowner
            The agent seeking a consultation.
        cost : int
            The cognitive resource cost of contacting the advisor.
        """
        if agent.energy_advisor == None:
            agent.find_energy_advisor()
        
        if agent.cognitive_resource >= cost:
            agent.order_energy_advisor()
            # logger.info("I have ordered a consultation from my energy advisor!")
            agent.cognitive_resource = 0
        
def generate_imperfect_system(agent, system_name):
    """
    Create a perceived, imperfect representation of a heating system.

    This function simulates an agent's imperfect perception of a heating
    system. It takes a system name, creates an instance with its "true"
    attributes calculated for the agent's house, and then applies a random
    "pessimistic-only" distortion and an uncertainty range to its parameters.
    
    The distortion's upper bound is based on the system's market share.

    Parameters
    ----------
    agent : Houseowner
        The agent for whom the system perception is being generated.
    system_name : str
        The name of the heating system class to generate.

    Returns
    -------
    Heating_system
        The newly created `Heating_system` object with distorted and
        uncertain parameters.
    """
    # Get distortion bounds
    max_distortion = settings.information_source.distortion # e.g., 0.3
    min_distortion = 0.1 # This must match the value in Information_source.__init__
    
    # Get market distribution from the agent's model
    distribution = agent.model.heating_distribution
    total_houses = sum(distribution.values())

    # 1. Get market share for the chosen system
    market_share = 0.0
    if total_houses > 0:
        market_share = distribution.get(system_name, 0) / total_houses
    
    # 2. Calculate this system's dynamic *top* distortion
    # Linear interpolation: maps [0, 1] -> [max_distortion, min_distortion]
    dynamic_top_distortion = min_distortion + (1.0 - market_share) * (max_distortion - min_distortion)
    
    # 3. Set distortion range
    bot_distortion = -dynamic_top_distortion
    top_distortion = dynamic_top_distortion
            
    uncertainty_lower = settings.information_source.uncertainty_lower
    uncertainty_upper = settings.information_source.uncertainty_upper
    
    new_system = agent.generate_system(system_name)
    new_system.calculate_all_attributes(
        area=agent.house.area, energy_demand=agent.house.energy_demand,
        heat_load=agent.house.heat_load
    )
            
    for key in [
        "operation_effort",
        "fuel_cost",
        "emissions",
        "price",
        "installation_effort",
        "opex",
    ]:
        random_noise = rng_information_source_run().uniform(
            bot_distortion, top_distortion
            )
        distortion_factor = max(0.5, 1 + random_noise)
        # Multiply, then round up the value
        new_system.params[key][0] = new_system.params[key][0] * distortion_factor

    # Setting the uncertainty range (UNCHANGED)
    for key, value in new_system.params.items():
        value[1] = value[0] * rng_information_source_run().uniform(
            uncertainty_lower, uncertainty_upper
        )
    
    return new_system