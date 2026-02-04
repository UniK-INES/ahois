"""
Defines the data structures for subsidies applicable to heating systems.

This module uses Python's `dataclasses` to create a representation 
for various subsidies. It includes a base `Subsidy` class that
defines the common attributes, such as the subsidy amount and any application
conditions.

Several specific subclasses are defined for different types of subsidies. 
These objects are used throughout the model to calculate the final, 
subsidized price of a new heating system.

:Authors:
 - Sören Lohr
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
from dataclasses import dataclass, field
from typing import Callable, Optional, Any
from helpers.config import settings


@dataclass
class Subsidy:
    """
    A dataclass representing a generic subsidy for a heating system.

    This class serves as the primary data structure for all subsidies. It holds
    information about the subsidy's name, amount, and the system(s) it applies
    to. It also supports conditional application, allowing a subsidy to be
    contingent on specific properties of the agent or the heating system itself.

    Attributes
    ----------
    name : str
        The full name of the subsidy.
    abbr : str
        A short abbreviation for the subsidy.
    subsidy : float
        The subsidy amount, typically as a decimal fraction of the total cost
        (e.g., 0.3 for 30%).
    heating_system : str or tuple[str, ...]
        The name(s) of the heating system classes this subsidy can apply to.
    condition : Callable[[Any], bool], optional
        A callable (e.g., a lambda function) that returns True if the subsidy
        conditions are met, by default None.
    target : str, optional
        Specifies whether the `condition` should be applied to the 'System' or
        the 'Agent', by default None.
    """
    name: str
    abbr: str
    subsidy: float
    heating_system: str
    condition: Optional[Callable[[Any], bool]] = field(default=None)
    target: Optional[str] = field(default=None)

    def check_condition(self, system, agent):
        """
        Checks if the conditions for this subsidy are met.

        This method evaluates the `condition` function against the specified
        `target` (either the heating system or the agent). If no condition is
        defined, it automatically returns True.

        Parameters
        ----------
        system : Heating_system
            The heating system being considered for the subsidy.
        agent : Houseowner
            The agent applying for the subsidy.

        Returns
        -------
        bool
            True if the subsidy is applicable, False otherwise.
        """
        if self.condition is None:
            return True
        elif self.target == "System":
            return self.condition(system)
        elif self.target == "Agent":
            return self.condition(agent)
        return False


@dataclass
class Subsidy_district(Subsidy):
    """
    A subsidy specifically for district heating connections.
    """
    name: str = "District"
    abbr: str = "DSTR"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_network_district"
    condition: None
    target: str = None
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.district)

@dataclass
class Subsidy_heat_pump(Subsidy):
    """
    A subsidy specifically for air-source heat pumps.
    """
    name: str = "Heat_pump"
    abbr: str = "HTPMP"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_heat_pump"
    condition: None
    target: str = None
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.heat_pump)
    
@dataclass
class Subsidy_heat_pump_brine(Subsidy):
    """
    A subsidy specifically for heat pump-based 
    local cold network.
    """
    name: str = "Heat_pump_brine"
    abbr: str = "HTPMPBR"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_heat_pump_brine"
    condition: None
    target: str = None
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.heat_pump_brine)
    
@dataclass
class Subsidy_pellet(Subsidy):
    """
    A subsidy specifically for pellet heating.
    """
    name: str = "Pellet"
    abbr: str = "PLLT"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_pellet"
    condition: None
    target: str = None
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.pellet)

@dataclass
class Subsidy_network_local(Subsidy):
    """
    A subsidy specifically for local hot network.
    """
    name: str = "Hot_network"
    abbr: str = "HTNTWRK"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_network_local"
    condition: None
    target: str = None 
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.network_local_hot) 

@dataclass
class Subsidy_GP_Joule(Subsidy):
    """
    A subsidy specifically for local hot network
    provided by GP Joule.
    """
    name: str = "GP_Joule"
    abbr: str = "GPJL"
    subsidy: float = 0.3
    heating_system: str = "Heating_system_GP_Joule"
    condition: None
    target: str = None 
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.GP_Joule)
    
@dataclass
class Subsidy_climate_speed(Subsidy):
    """
    A bonus subsidy for replacing an oil or gas heating system.

    This subsidy acts as a bonus for houseowners who switch from a fossil-fuel
    system (oil or gas) to a renewable alternative.
    """
    name: str = "Climate_speed"
    abbr: str = "CLMSPD"
    subsidy: float = 0.2
    heating_system: tuple[str, ...] = (
        "Heating_system_heat_pump",
        "Heating_system_heat_pump_brine",
        "Heating_system_pellet"
        )
    condition: Callable[[Any], bool] = field(
        default_factory=lambda: lambda a: type(a.house.current_heating).__name__
        in ["Heating_system_oil", "Heating_system_gas"]
    )
    target: str = "Agent"
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.climate_speed)

@dataclass
class Subsidy_income(Subsidy):
    """
    A subsidy for low-income households.

    This subsidy can be applied to any heating system but is conditional on the
    agent's annual income being below a specific threshold.
    """
    name: str = "Income"
    abbr: str = "INC"
    subsidy: float = 0.3
    heating_system: tuple[str, ...] = (
        "Heating_system_heat_pump",
        "Heating_system_heat_pump_brine",
        "Heating_system_pellet"
        )
    condition: Callable[[Any], bool] = field(
        default_factory=lambda: lambda a: 52*a.income <= settings.subsidies.low_income_threshold
    )
    target: str = "Agent"
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.income)
    
@dataclass
class Subsidy_efficiency(Subsidy):
    """
    A bonus subsidy for highly efficient heat pump systems.
    """
    name: str = "Efficiency"
    abbr: str = "EFF"
    subsidy: float = 0.05
    heating_system: tuple[str, ...] = (
        "Heating_system_heat_pump",
        "Heating_system_heat_pump_brine"
        )
    condition: None
    target: str = None
    
    def __post_init__(self):
        """
        Update the subsidy amount from the global settings file.
        """
        self.subsidy = float(settings.subsidies.efficiency)
