"""
Defines the trigger events that initiate an agent's decision-making process.

This module contains the classes that represent various events or conditions,
known as "triggers," which can prompt a `Houseowner` agent to reconsider their
current heating system. It includes a generic `Trigger` base class and numerous
subclasses, each modelling a specific event such as a system breakdown, a fuel
price shock, or social influence from a neighbour.

When a trigger becomes active for an agent, its `impact` method is executed,
typically moving the agent from a passive state into the first stage of the
decision-making model.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>

"""
from copy import deepcopy
from helpers.config import settings
from modules.Information_sources import generate_imperfect_system
import logging
from modules.Rng import rng_model_run
from click.decorators import option

logger_rng = logging.getLogger("ahoi.rng")

class Trigger:
    """
    A base class for an event that can trigger an agent's decision process.

    This class provides the structure for all triggers. Its primary
    role is to define the `impact` method, which is called when the trigger
    affects an agent. The base `impact` method handles data collection and
    ensures an agent is not re-triggered if they are already in an active
    decision process.
    """

    def __init__(self):
        """
        Initialises a new Trigger instance.
        """
        pass

    def impact(self, agent):
        """
        Applies the trigger's effect to an agent.

        This base method logs the trigger's activation for data collection and
        contains a guard clause to prevent the trigger from affecting an agent
        who is already in an active decision-making stage.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        agent.model.trigger_types_counter[type(self).__name__] = agent.model.trigger_types_counter.get(type(self).__name__, 0) + 1
        if agent.current_stage != "None":
            return

    def __repr__(self):
        return f"{type(self)}"

    def __str__(self):
        return self.__repr__()
    

class Trigger_none(Trigger):
    """
    A null trigger that has no effect.
    """
    def __init__(self):
        """
        Initialises a new Trigger_none instance.
        """
        pass

    def impact(self, agent):
        """
        Applies only the impact from the superclass.
        """
        super().impact(agent)


class Trigger_price_shock(Trigger):
    """
    A trigger representing a sudden, significant increase in fuel price.
    """
    def __init__(
        self,
        factor: float = 1,
    ):
        """
        Initialises the price shock trigger.

        Parameters
        ----------
        factor : float, optional
            The multiplication factor to apply to the agent's current fuel cost,
            by default 1.
        """
        self.factor = factor
        pass

    def impact(self, agent):
        """
        Increases the agent's perceived fuel cost 
        and starts the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.house.current_heating.fuel_cost *= self.factor
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1


class Trigger_lifetime(Trigger):
    """
    A trigger representing the agent's awareness 
    that their system is nearing its end of life.
    """
    def __init__(self):
        """
        Initializes a new Trigger_lifetime instance.
        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = (
            "Stage 1"  
        )
        agent.model.trigger_counter += 1


class Trigger_neighbour_jealousy(Trigger):
    """
    A trigger representing social influence 
    from a neighbor's new heating system.
    """
    def __init__(self):
        """
        Initializes a new Trigger_neighbour_jealousy instance.
        """
        pass

    def impact(self, agent):
        """Moves the agent into the first stage of the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1

class Trigger_adoptive_comparsion(Trigger):
    """
    A trigger representing an invitation 
    from a neighbour to adopt a heating system of the same type.

    This trigger occurs when a neighbour installs a new heating system
    and proposes to install one of the same type to the agent.
    """
    def __init__(self):
        """Initialises the adoptive comparison trigger.

        """

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        This trigger simulates the effect of being prompted to think about one's
        own heating system after a neighbour asks for advice.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = (
            "Stage 1"  
        )
        agent.model.trigger_counter += 1

                
class Trigger_asked_by_neighbour(Trigger):
    """
    A trigger representing being asked for an opinion by a neighbour.
    """
    def __init__(self):
        """
        Initialises a new Trigger_asked_by_neighbour instance.
        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        This trigger simulates the effect of being prompted to think about one's
        own heating system after a neighbour asks for advice.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = (
            "Stage 1"  
        )
        agent.model.trigger_counter += 1

class Trigger_breakdown(Trigger):
    """
    A trigger representing a critical failure 
    of the agent's heating system.
    """
    def __init__(self):
        """
        Initializes a new Trigger_breakdown instance.
        """
        pass

    def impact(self, agent):
        """
        Forces the agent directly into the second stage of the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_breakpoint = "Goal"
        agent.current_stage = "Stage 2"
        agent.model.trigger_counter += 1

class Trigger_information_campaign(Trigger):
    """A trigger representing an agent being targeted 
    by an information campaign."""
    
    def __init__(self, system_names):
        """Initializes the information campaign trigger.

        Parameters
        ----------
        system_names : list[str]
            A list of heating system names being promoted by the campaign.
        """
        self.system_names = system_names

    def impact(self, agent):
        """Introduces idealised versions of promoted systems 
        to the agent's knowledge.

        This trigger adds perfected versions of the
        promoted heating systems to the agent's set of known alternatives,
        then moves the agent into the first stage of the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        if all(name in agent.infeasible for name in self.system_names):
            pass
        else:
            for system_name in self.system_names:
                advertised_system = agent.generate_system(system_name)
                advertised_system.calculate_all_attributes(area = 106, 
                                                           energy_demand = 147, 
                                                           heat_load = 19)
                advertised_system.source = "Campaign"
                
                source = None 
                for option in agent.model.list_of_sources:
                    if type(option).__name__ == "Information_source_internet":
                        source = option
                        break
                if system_name in source.known_subsidies_by_hs:
                    agent.known_subsidies_by_hs[system_name] = deepcopy(source.known_subsidies_by_hs[system_name])
                    agent.apply_subsidies(system = advertised_system)
                
                for key, value in advertised_system.params.items():
                    value[1] = value[0] * settings.information_source.uncertainty_upper
                    
                if not any(type(i).__name__ == system_name for i in agent.known_hs):
                    agent.known_hs.append(deepcopy(advertised_system))
                    for system in agent.known_hs:
                        agent.calculate_attitude(system)
    
                else:
                    agent.relative_agreement(new_system = advertised_system)
                    for system in agent.known_hs:
                        agent.calculate_attitude(system)
                
            agent.current_stage = ("Stage 1")
            
        agent.model.trigger_counter += 1
        
class Trigger_consulted(Trigger):
    """
    A trigger representing an agent being nudged to thinking about the replacement 
    by a consultation.
    """
    def __init__(self):
        """
        Initialises a new Trigger_consulted instance.
        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        This trigger is typically activated by an external intervention, like an
        information campaign that encourages houseowners to think about the replacement.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1
        
class Trigger_risk_targeting_campaign(Trigger):
    """
    A trigger from a campaign designed to mitigate perceived technology risk.
    """
    def __init__(self):
        """
        Initializes the risk-targeting campaign trigger.

        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = ("Stage 1")
        agent.model.trigger_counter += 1
        
class Trigger_availability(Trigger):
    """
    A trigger representing a change in the availability of a heating system.
    """
    def __init__(self):
        """
        Initialises a new Trigger_availability instance.
        """
        pass

    def impact(self, agent):
        """
        Forces the agent directly into the second stage of the decision process.

        This trigger models an external event where an agent finds out that 
        their current heating type will be no longer available for the installation
        in some (near) future, forcing them to think about installing a new one
        of the same type to avoid the "forced" switch to another heating technology.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1
        
class Trigger_fuel_price(Trigger):
    """
    A trigger representing general awareness of changing fuel prices.
    """
    def __init__(self):
        """
        Initialises a new Trigger_fuel_price instance.
        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        This trigger models a non-shock-based response to fuel price volatility,
        prompting the agent to begin considering their heating options.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1
        
class Trigger_owner_change(Trigger):
    """
    A trigger representing general awareness of changing fuel prices.
    """
    def __init__(self):
        """
        Initialises a new Trigger_fuel_price instance.
        """
        pass

    def impact(self, agent):
        """
        Moves the agent into the first stage of the decision process.

        This trigger models a non-shock-based response to fuel price volatility,
        prompting the agent to begin considering their heating options.

        Parameters
        ----------
        agent : Houseowner
            The agent to be impacted by the trigger.
        """
        super().impact(agent)
        agent.current_stage = "Stage 1"
        agent.model.trigger_counter += 1