"""
Defines the experimental scenarios for the simulation.

This module contains the classes that control the specific conditions and
interventions for different simulation experiments. It features a base `Scenario`
class that provides the core structure and default behaviours.

Various subclasses inherit from this base class to implement specific future
pathways or policy interventions. Each scenario can modify the model's initial
state (via the `setup` method) and introduce dynamic events during the
simulation (via the `impact` method).

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""
from copy import deepcopy
from helpers.config import settings
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
)
from interventions.Subsidy import *
from modules.Rng import rng_model_init, rng_model_run
from modules.Triggers import *
from modules.Information_sources import generate_imperfect_system


class Scenario:
    """
    A base class for defining an experimental scenario.

    This class provides the fundamental structure (`setup` and `impact` methods)
    and default behaviours that can be inherited and extended by specific
    scenario subclasses. It also contains the logic for common, optional
    interventions like plumber training or information campaigns, which can be
    activated via the global settings.

    Attributes
    ----------
    id : str
        The unique identifier for the scenario.
    hs_targets : dict
        A dictionary defining the target market shares for heating systems in this scenario.
    visited_agents : list
        A list to keep track of agents who have been targeted by an intervention.
    """
    id = "00"

    def __init__(self):
        """
        Initializes the scenario's state-tracking attributes.
        """
        self.hs_targets = {}
        self.visited_agents = []

    def setup(self, model):
        """
        Applies initial, one-time modifications to the model.

        This method is called once at the beginning of a simulation (step 0)
        to set up the specific conditions of the scenario. The default behaviour
        gives agents who already own a heat pump a head start in knowledge
        about various systems and subsidies. Subclasses can extend this to
        implement their unique starting conditions.

        Parameters
        ----------
        model : Model
            The main model instance.
        """
        plumbers_list = []
        for agent in model.schedule.agents:
            if type(agent).__name__ == "Houseowner":
                #Heat pump users know more about systems and subsidies
                if type(agent.house.current_heating).__name__ == "Heating_system_heat_pump":
                    #First, populate known_hs
                    systems_to_generate = settings.information_overspread.known_hs_list
                    for system_name in systems_to_generate:
                        new_system = generate_imperfect_system(agent, system_name)
                        agent.known_hs.append(new_system)
                    #Second, organize and apply subsidies
                    organize_subsidies(agent)
                    if (type(agent.house.current_heating).__name__ 
                        in agent.known_subsidies_by_hs):
                        apply_subsidies(agent, agent.house.current_heating)
                    
                    for system in agent.known_hs:
                        if type(system).__name__ in agent.known_subsidies_by_hs:
                            apply_subsidies(agent, system)
                    
                    for i, system in enumerate(agent.known_hs):
                        agent.calculate_attitude(system)
                        if type(system) == type(agent.house.current_heating):
                            agent.known_hs[i] = deepcopy(agent.house.current_heating)
        
        for agent in model.schedule.agents:
            if type(agent).__name__ == "Houseowner":
                model.initial_meetings(agent = agent,
                                       share = 1.0)
                  
    def impact(self, model):
        """
        Applies dynamic interventions or events during the simulation.

        This method is called at each step of the simulation to introduce
        changes or trigger events. It serves as the entry point for various
        policy interventions that can be enabled in the settings, such as
        plumber training programs, information campaigns, technology bans, or
        replacement mandates.

        Parameters
        ----------
        model : Model
            The main model instance.
        """
        if settings.experiments.plumber_training == True:
            plumber_training_program(model = model,
                                     system_name = settings.experiments.plumber_training_system)
        if (settings.experiments.information_campaign == True
            and model.schedule.steps in settings.experiments.inf_campaign_duration):
            information_campaign(model = model,
                                 system_names = settings.experiments.inf_campaign_systems,
                                 mode = settings.experiments.inf_campaign_mode,
                                 scenario = self)  
        if settings.experiments.enforcement == True:
            enforce_heating_systems(model = model, systems_names = settings.experiments.enforcement_systems)
        if settings.experiments.replacement_mandates == True:
            issue_replacement_mandates(model = model)
        if settings.experiments.open_house_measure == True:
            open_house_measure(model = model, 
                               system_names = settings.experiments.open_house_systems, 
                               milieus = settings.experiments.open_house_milieus,
                               freq = settings.experiments.open_house_freq)
    
class Scenario_none(Scenario):
    """
    A default scenario with no specific modifications.

    This scenario serves as a baseline or control, applying only the default
    setup and impact logic from the base `Scenario` class.
    """

    id = "01"

    def __init__(self):
        super().__init__()

    def setup(self, model):
        """Scenario specific model adjustments"""
        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_perfect(Scenario):
    """
    A scenario with perfect information and no feasibility constraints.

    In this idealised scenario, all agents start with complete and perfect
    knowledge of all available heating systems. Information is not distorted,
    and all systems are considered feasible options from the beginning.
    """

    id = "02"

    def __init__(self):
        super().__init__()
        self.references = {
            "Scenario_network_district": {"Heating_system_network": 100},
            "Scenario_network_local_hot": {"Heating_system_network": 100},
            "Scenario_network_local_cold": {"Heating_system_heat_pump_brine": 100},
            "Scenario_mix_pellet_heat_pump": {
                "Heating_system_heat_pump": 80,
                "Heating_system_pellet": 20,
            },
            "Scenario_mix_pellet_heat_pump_network": {
                "Heating_system_heat_pump": 9,
                "Heating_system_pellet": 29,
                "Heating_system_network_local": 62,
            },
        }

    def setup(self, model):
        """Scenario specific model adjustments"""
        super().setup(model)
        
        known_hs = [
            Heating_system_oil(),
            Heating_system_gas(),
            Heating_system_heat_pump(),
            Heating_system_electricity(),
            Heating_system_pellet(),
            Heating_system_network_district(),
            Heating_system_network_local(),
            Heating_system_heat_pump_brine(),
            Heating_system_GP_Joule(),
        ]
        for agent in model.schedule.agents:
            agent.known_hs = deepcopy(known_hs)
            for system in agent.known_hs:
                if agent.__class__.__name__ == "Houseowner":
                    system.calculate_all_attributes(
                        area=agent.house.area, energy_demand=agent.house.energy_demand,
                        heat_load=agent.house.heat_load
                    )
            if agent.__class__.__name__ == "Houseowner":
                agent.house.current_heating.calculate_all_attributes(
                    area=agent.house.area, energy_demand=agent.house.energy_demand,
                    heat_load=agent.house.heat_load
                )
            agent.initial_aspiration_value = 0
            agent.aspiration_value = 0
        
        
    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_network_district(Scenario):
    """
    A scenario where district heating is the sole targeted technology.

    This scenario models a future where policy and infrastructure are focused
    exclusively on district heating. Competing network-based technologies are
    made infeasible for all agents from the start of the simulation.
    """

    id = "03"

    def __init__(self):
        super().__init__()
        self.hs_targets = {"Heating_system_network_district": 100}  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_local",
                            "Heating_system_heat_pump_brine",
                            "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_local")
            agent.infeasible.append("Heating_system_heat_pump_brine")
            agent.infeasible.append("Heating_system_GP_Joule")
            
        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_network_local_hot(Scenario):
    """
    A scenario where local 'hot' network heating is the sole targeted technology.

    This scenario models a future focused exclusively on local 'hot' heating
    networks. It makes district networks and other system-based
    options (brine heat pumps, GP Joule) infeasible for all agents from the
    start of the simulation.
    """

    id = "04"

    def __init__(self):
        super().__init__()
        self.hs_targets = {"Heating_system_network_local": 100}  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_district")
            agent.infeasible.append("Heating_system_heat_pump_brine")
            agent.infeasible.append("Heating_system_GP_Joule")

        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_network_local_cold(Scenario):
    """
    A scenario where brine heat pumps (cold network) are the sole targeted technology.

    This scenario models a future pathway centered on local "cold" networks that rely on
    brine heat pumps. Competing centralised network options are made
    infeasible for all agents.
    """

    id = "05"

    def __init__(self):
        super().__init__()
        self.hs_targets = {"Heating_system_heat_pump_brine": 100}  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_network_local",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_district")
            agent.infeasible.append("Heating_system_network_local")
            agent.infeasible.append("Heating_system_GP_Joule")
        
        super().setup(model)
        
    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_heat_pumps(Scenario):
    """
    A scenario where air-source heat pumps are the sole targeted technology.

    This scenario simulates a strong policy push towards electrification of
    heating via individual air-source heat pumps. All network-based heating
    options are made infeasible.
    """

    id = "06"

    def __init__(self):
        super().__init__()
        self.hs_targets = {"Heating_system_heat_pump": 100}  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_network_local",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_district")
            agent.infeasible.append("Heating_system_network_local")
            agent.infeasible.append("Heating_system_heat_pump_brine")
            agent.infeasible.append("Heating_system_GP_Joule")

        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)
        

class Scenario_mix_pellet_heat_pump(Scenario):
    """
    A scenario targeting a mix of heat pumps and pellet systems.

    This scenario explores a future with two desired renewable, decentralised
    heating options. It assumes no large-scale heating networks are built,
    making those options infeasible for all agents. The target market share
    is 80% heat pumps and 20% pellet systems.
    """

    id = "07"

    def __init__(self):
        super().__init__()
        self.hs_targets = {
            "Heating_system_heat_pump": 80,
            "Heating_system_pellet": 20,
        }  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_network_local",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_district")
            agent.infeasible.append("Heating_system_network_local")
            agent.infeasible.append("Heating_system_heat_pump_brine")
            agent.infeasible.append("Heating_system_GP_Joule")

        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)


class Scenario_mix_pellet_heat_pump_network(Scenario):
    """
    A scenario targeting a mix of a local hot network, heat pumps, 
    and pellet systems.

    This complex scenario models a spatially differentiated energy transition.
    A local 'hot' heating network is available, but only for agents outside
    the 'Sued' subarea. All agents can choose between heat pumps and pellet
    systems. Other network types are globally infeasible.
    """

    id = "08"

    def __init__(self):
        super().__init__()
        self.hs_targets = {
            "Heating_system_heat_pump": 10,
            "Heating_system_pellet": 30,
            "Heating_system_network_local": 60,
        }  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        super().setup(model)
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                agent.infeasible.append("Heating_system_network_district")
                agent.infeasible.append("Heating_system_heat_pump_brine")
                agent.infeasible.append("Heating_system_GP_Joule")
                if agent.house.subarea == "Sued":
                    agent.infeasible.append("Heating_system_network_local")

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)
              
                
class Scenario_pellets(Scenario):
    """
    A scenario where pellet heating systems are the sole targeted technology.

    This scenario models a future pathway focused on biomass as the primary
    renewable heating source. All network-based heating options and heat pumps
    that require significant grid infrastructure are made infeasible.
    """

    id = "09"

    def __init__(self):
        super().__init__()
        self.hs_targets = {
            "Heating_system_pellet": 100,
        }  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_network_local",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            agent.infeasible.append("Heating_system_network_district")
            agent.infeasible.append("Heating_system_network_local")
            agent.infeasible.append("Heating_system_heat_pump_brine")
            agent.infeasible.append("Heating_system_GP_Joule")

        super().setup(model)

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)

class Scenario_mix_heat_pump_network_cold(Scenario):
    """
    A scenario targeting a mix of air-source and local cold network based on
    brine-source heat pumps.

    This scenario simulates a future focused entirely on different types of
    heat pump technology, representing a full electrification pathway. All
    other centralised heating network options are made infeasible.
    """

    id = "10"

    def __init__(self):
        super().__init__()
        self.hs_targets = {
            "Heating_system_heat_pump": 40,
            "Heating_system_heat_pump_brine": 60,
        }  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        super().setup(model)
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_network_local",
                           "Heating_system_GP_Joule"]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                agent.infeasible.append("Heating_system_network_district")
                agent.infeasible.append("Heating_system_network_local")
                agent.infeasible.append("Heating_system_GP_Joule")
                    

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)

class Scenario_mix_GP_Joule(Scenario):
    """
    A scenario targeting a mix of a local hot network, heat pumps, 
    and pellet systems.
    The default hot network is replaced with the option provided
    by the firm GP Joule.

    It assumes no other large-scale heating networks are built,
    making those options infeasible for all agents.
    
    """

    id = "11"

    def __init__(self):
        super().__init__()
        self.hs_targets = {
            "Heating_system_heat_pump": 20,
            "Heating_system_pellet": 30,
            "Heating_system_GP_Joule": 50,
        }  # Percentage

    def setup(self, model):
        """Scenario specific model adjustments"""
        super().setup(model)
        blocked_systems = ["Heating_system_network_district",
                           "Heating_system_heat_pump_brine",
                           "Heating_system_network_local",]
        model.global_infeasibles.extend(blocked_systems)
        
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                agent.infeasible.append("Heating_system_network_district")
                agent.infeasible.append("Heating_system_heat_pump_brine")
                agent.infeasible.append("Heating_system_network_local")

    def impact(self, model):
        """Scenario specific impacts during model runs"""
        super().impact(model)

#Helper methods for the default set-up 
def apply_subsidies(agent, system):
    """
    Applies all known and applicable subsidies to a given heating system.

    Parameters
    ----------
    agent : Houseowner
        The agent considering the system.
    system : Heating_system
        The heating system to which subsidies will be applied.
    """
    system_name = type(system).__name__
    
    subsidies_by_hs = agent.known_subsidies_by_hs[system_name]
    
    current_price = system.params["price"][0]
    total_subsidy = 0
    
    # Pre-calculate the maximum allowed subsidy (70% of price OR 21,000)
    subsidy_cap = min(current_price * 0.7, 21000)

    for subsidy_rule in subsidies_by_hs:
        # Check if subsidy applies (unconditional OR condition met)
        if subsidy_rule.target is None:
            subsidy_amount = current_price * subsidy_rule.subsidy
            total_subsidy += subsidy_amount
        elif subsidy_rule.check_condition(system=system, agent=agent):
            subsidy_amount = current_price * subsidy_rule.subsidy
            total_subsidy += subsidy_amount

        # Enforce the cap
        if total_subsidy >= subsidy_cap:
            total_subsidy = subsidy_cap
            break

    if total_subsidy > 0:
        system.subsidised = True
        system.params["price"][0] -= total_subsidy
        system.params["price"][1] = 0
    
def organize_subsidies(agent):
    """
    Populates an agent's knowledge base with available subsidies.

    This function simulates an agent learning about the various subsidies
    available for the heating systems they know. It populates the agent's
    `known_subsidies_by_hs` dictionary.

    Parameters
    ----------
    agent : Houseowner
        The agent who is learning about subsidies.
    """
    subsidies_list = [Subsidy_pellet(),
                      Subsidy_heat_pump(),
                      Subsidy_heat_pump_brine(),
                      Subsidy_climate_speed(),
                      Subsidy_income(),
                      Subsidy_network_local(),
                      Subsidy_GP_Joule(),
                      Subsidy_efficiency()]
    for subsidy in subsidies_list:
        if isinstance(subsidy.heating_system, tuple):
                for hs in agent.known_hs:
                    hs_name = type(hs).__name__
                    if hs_name in subsidy.heating_system:
                        agent.known_subsidies_by_hs.setdefault(hs_name, []).append(
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
            for hs in agent.known_hs:
                hs_name = type(hs).__name__
                agent.known_subsidies_by_hs.setdefault(hs_name, []).append(
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
            agent.known_subsidies_by_hs.setdefault(subsidy.heating_system, []).append(
                deepcopy(subsidy)
            )

    
def plumber_training_program(model, system_name: str):
    """
    Simulates a training program for plumbers.
    This function identifies all plumber agents in the model who do not yet
    have knowledge of a specific heating system and makes them "trained" in it,
    adding it to their knowledge base.

    Parameters
    ----------
    model : Model
        The main model instance.
    system_name : str
        The name of the heating system for the training program.
    """
    plumbers_list = []
    for agent in model.schedule.agents:
        if type(agent).__name__ == "Plumber":
            names_known_hs = [type(system).__name__ for system in agent.known_hs]
            if system_name not in names_known_hs:
                plumbers_list.append(agent)
    if plumbers_list:
        for plumber in plumbers_list:
            if system_name not in [type(system).__name__ for system in agent.known_hs]:
                plumber.training(system = system_name)
                
def information_campaign(model, system_names: list, mode: str, scenario):
    """
    Simulates a large-scale information campaign intervention.

    This function models different types of information campaigns designed to
    influence houseowners. The behaviour depends on the specified `mode`:
    - 'Direct_informing': A set number of agents receive direct information.
    - 'Energy_advisor': A set number of agents are prompted to consult an energy advisor.
    - 'Risk_targeting': A campaign designed to mitigate the perceived risk of certain technologies.

    Parameters
    ----------
    model : Model
        The main model instance.
    system_names : list
        A list of heating systems to be promoted in the campaign.
    mode : str
        The type of campaign to run ('Direct_informing', 'Energy_advisor', or 'Risk_targeting').
    scenario : Scenario
        The currently active scenario instance, used to track visited agents.
    """
    if mode == "None":
        print("No mode was chosen for the information campaign!")
    
    elif mode == "Direct_informing":
        all_agents = [
            agent for agent in model.schedule.agents
            if type(agent).__name__ == "Houseowner"
            and agent not in scenario.visited_agents  # Ensure agent was not previously visited
        ]
    
        if all_agents:
            agents_to_propagate = []
            reach = settings.experiments.inf_campaign_reach
    
            while reach > 0 and all_agents:  # Avoid empty sampling
                agent_to_propagate = rng_model_run().choice(all_agents, replace=False)
                agents_to_propagate.append(agent_to_propagate)
                all_agents.remove(agent_to_propagate)  # Prevent duplicates
                reach -= 1
    
            scenario.visited_agents.extend(agents_to_propagate)  # Add drawn agents to visited set
    
            for agent in agents_to_propagate:
                organize_subsidies(agent)
                trigger = Trigger_information_campaign(system_names=system_names)
                agent.active_trigger = trigger
    
    elif mode == "Energy_advisor":
        all_houseowners = [
            agent for agent in model.schedule.agents
            if type(agent).__name__ == "Houseowner"
            and agent not in scenario.visited_agents  # Ensure agent was not previously visited
            and agent.current_stage not in ["Stage 3", "Stage 4"]
        ]
    
        all_advisors = [agent for agent in model.schedule.agents if type(agent).__name__ == "EnergyAdvisor"]
    
        if all_houseowners and all_advisors:
            reach = settings.experiments.inf_campaign_reach
            agents_to_consult = []
    
            while reach > 0 and all_houseowners:  # Ensure there are available agents to select
                agent_to_consult = rng_model_run().choice(all_houseowners, replace=False)
                advisor = rng_model_run().choice(all_advisors, replace=False)
                advisor.Services[0].queue_job(agent_to_consult)
                agent_to_consult.consulted_by_energy_advisor = True
                agent_to_consult.consultation_ordered = True
                
                agents_to_consult.append(agent_to_consult)
                all_houseowners.remove(agent_to_consult)  # Prevent duplicate selection
                reach -= 1
    
            scenario.visited_agents.extend(agents_to_consult)  # Add consulted agents to visited set
    
    elif mode == "Risk_targeting":
        all_agents = [agent for agent in model.schedule.agents 
                      if type(agent).__name__ == "Houseowner" and agent not in scenario.visited_agents]
        if all_agents:
            agents_to_propagate = []
            reach = settings.experiments.inf_campaign_reach
        
            while reach > 0 and all_agents:  # Ensure we do not try to sample from an empty list
                agent_to_propagate = rng_model_run().choice(all_agents, replace=False)
                agents_to_propagate.append(agent_to_propagate)
                all_agents.remove(agent_to_propagate)  # Prevent duplicate selection
                reach -= 1
        
            scenario.visited_agents.extend(agents_to_propagate)  # Update visited agents
        
            for agent in agents_to_propagate:
                agent.risk_tolerance = min(1, agent.risk_tolerance + 0.1)
                trigger = Trigger_risk_targeting_campaign(system_names=system_names)
                agent.active_trigger = trigger
        
def enforce_heating_systems(model, systems_names: list):
    """
    Enforces a limited set of allowed heating systems.

    This function models a regulatory policy where only a specific list of
    heating systems are allowed for new installations. All other systems are
    made infeasible for all agents.

    Parameters
    ----------
    model : Model
        The main model instance.
    systems_names : list
        A list of the only heating system names that are allowed.
    """
    if model.schedule.steps == 0:
        all_systems = settings.heating_systems.list
        enforced_systems = systems_names
        banned_systems = list(set(all_systems) - set(enforced_systems))
        print("Agents can only install: ", enforced_systems)
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                if set(enforced_systems).issubset(set(agent.infeasible)):
                    pass
                else:
                    for system_name in banned_systems:
                        agent.infeasible.append(system_name)
                

def issue_replacement_mandates(model):
    """
    Simulates the policy of mandating the replacement of inefficient systems.

    This function models two types of mandates:
    1. Performance-based: A fraction of systems exceeding a certain emissions
       threshold are forced into a 'breakdown' state each year.
    2. Technology-based: Any systems of a specific type (e.g., oil boilers)
       are forced into a 'breakdown' state.

    Parameters
    ----------
    model : Model
        The main model instance.
    """
    params_conditions = {"emissions": settings.experiments.emissions_mandate}
    systems_to_replace = settings.experiments.systems_mandate
    if params_conditions and model.schedule.steps % 52 == 0:
        eligible_agents = []
        # Loop over agents to find eligible ones
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                for condition in params_conditions:
                    if (agent.house.current_heating.params[condition][0] > params_conditions[condition]
                        and not agent.house.current_heating.breakdown):
                        # Compute a "badness" score: the amount by which the parameter exceeds the condition
                        score = agent.house.current_heating.params[condition][0] - params_conditions[condition]
                        eligible_agents.append((score, agent))
                        # Only add the agent once, even if they violate multiple conditions
                        break
    
        # Only proceed if there are any eligible agents
        if eligible_agents:
            # Sort the agents in descending order by their score (worst first)
            eligible_agents.sort(key=lambda x: x[0], reverse=True)
            total = len(eligible_agents)
            # Select 10% of agents (rounding down, but ensure at least one agent is selected)
            num_to_select = max(1, int(total * 0.1))
            # Process the selected worst agents
            for score, agent in eligible_agents[:num_to_select]:
                agent.house.current_heating.breakdown = True  # Note: using assignment (=) here
                agent.infeasible.append(type(agent.house.current_heating).__name__)
    
    if (not "None" in systems_to_replace
        and systems_to_replace):
        for agent in model.schedule.agents:
            if agent.__class__.__name__ == "Houseowner":
                agent.infeasible.extend(systems_to_replace)
                if (type(agent.house.current_heating).__name__ in systems_to_replace
                    and agent.house.current_heating.breakdown != True):
                    agent.house.current_heating.breakdown == True
                    agent.infeasible.append(type(agent.house.current_heating).__name__)
                    
def open_house_measure(model, 
                       system_names = ["Heating_system_heat_pump"], 
                       milieus = ["Leading"],
                       freq = 0):
    """
    Asks Heat pump users to share their satisfaction and knowledge with their neighbours
    Based on 'Woche der Wärmepumpe' launched by BMWK and dena.
    
    Parameters
    ----------
    model : Model
        The main model instance.
    system_names : list
        A list of heating systems to be promoted in the campaign.
    milieus: list
        A list of milieus that would actively participate as promoters
    """
    current_step = model.schedule.steps

    # 1. Safety check for frequency: skips execution if freq is 0
    if freq > 0:
        # 2. Check if the current step falls within the sequence
        if current_step in range(0, 520, freq):
            for agent in model.schedule.agents:
                # Check all conditions for agent sharing
                if (agent.__class__.__name__ == "Houseowner" and 
                    type(agent.house.current_heating).__name__ in system_names and 
                    agent.milieu in milieus and 
                    agent.satisfaction == "Satisfied"):
                    
                    agent.share_decision(iterations=agent.cognitive_resource)
                    