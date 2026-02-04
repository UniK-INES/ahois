"""
Defines the classes and methods for all heating systems in the simulation.

This module provides the core data structures for representing heating systems.
It includes a generic `Heating_system` base class that defines the common
attributes and functionalities shared by all systems.

Specific heating technologies are implemented as subclasses. 
These subclasses inherit the common framework from the base class 
but are initialised with their own unique parameters 
loaded from external data files.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
import sys
import os
import pandas as pd
import ast
import uuid
import math
from modules.Rng import rng_heating_init
from modules.Excel_input_read import Heating_params_table
#from statsmodels.discrete.tests.results.results_count_robust_cluster import params_table
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
from helpers.config import settings

params_table = None

def init_param_table():
    """
    Initialises the global heating system parameter table.
    This function must be called once at the beginning of a simulation run
    before any `Heating_system` objects are created. It creates an instance of
    `Heating_params_table`, loading the data from the input file and making it
    globally accessible for all heating system instances.
    """
    global params_table 
    params_table = Heating_params_table()

class Heating_system:
    """
    A base class representing a generic heating system.
    This class serves as the blueprint for all heating system types in the
    model. It defines the core attributes and perceived characteristics. 
    It also contains the methods for calculating key performance and cost indicators,
    including installation costs, fuel costs, operating costs, and emissions.

    Attributes
    ----------
    unique_id : uuid.UUID
        A unique identifier for the system instance.
    table : pandas.Series
        The row from the parameters table corresponding to the system type.
    age : int
        The number of steps (weeks) since the system was installed.
    breakdown : bool
        A flag indicating if the system has broken down.
    investment : float or None
        The remaining investment cost to be paid back.
    rating : float or None
        An agent's calculated attitude (rating) towards this system.
    params : dict
        A dictionary holding the core parameters of the system. Each key maps
        to a list of two values: the parameter's point value and its
        associated uncertainty (e.g., `[value, uncertainty]`).
    riskiness : float
        A calculated score from 0 to 1 representing the perceived riskiness
        of installing this system.
    weibull_lifetime : bool
        Defines whether the lifetime will be calculated using Weibull or Uniform
    """

    def __init__(self):
        """
        Initializes a new Heating_system instance with default values.
        """
        # Seed control part
        self.unique_id = uuid.uuid4()
        # Data table
        self.table = None
        # Other params
        self.age = 0  # Counter of HS's lifetime after installation
        self.breakdown = False  # Marks a broken system
        self.total_energy_demand = None  # House and system-specific demand
        self.investment = None
        self.payback = None
        self.subsidised = False
        self.loan = None
        self.availability = None
        self.power = None
        self.fuel_price_contract_term = None
        self.heat_delivery_contract = None
        # The part used for the Theory of Planned Behaviour
        self.rating = None  # Attitude of a houseowner towards certain HS
        self.neighbours_opinions = {}  # Storage of neighbours' opinions
        self.social_norm = None  # Perceived social "norm", mean of the opinions
        self.behavioural_control = None  # PERCEIVED behavioural control
        self.weibull_lifetime = None
        self.source = None
        

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [None, None],  # Operational effort, hours per year
            "fuel_cost": [None, None],  # Fuel/energy cost, EUR per year
            "emissions": [None, None],  # Emissions, grams of CO2 equivalent per kWh
            "price": [None, None],  # Installation price, EUR
            "installation_effort": [None, None],  # Working hours
            "opex": [None, None],  # Operating expenses, EUR per Year
        }
        self.riskiness = 0 #The higher, the worse [0, 1]


    # Methods part
    def generate_lifetime(self, min_weeks, max_weeks, shape=None, scale=None):
        """
        Generates a random lifetime for the system, using one of two modes.
    
        Mode 1: Uniform (Default)
            If 'shape' and 'scale' are NOT provided (or are None), this
            generates a uniform random integer between 'min_weeks' and 
            'max_weeks' (inclusive).
    
        Mode 2: Weibull
            If 'shape' and 'scale' ARE provided, this generates a random
            lifetime from a Weibull distribution. In this mode, 
            'min_weeks' and 'max_weeks' are IGNORED.
        
        The final lifetime is rounded to the nearest integer.
    
        Parameters
        ----------
        min_weeks : int
            The minimum possible lifetime (inclusive) for the uniform distribution.
            Ignored if 'shape' and 'scale' are provided.
        max_weeks : int
            The maximum possible lifetime (inclusive) for the uniform distribution.
            Ignored if 'shape' and 'scale' are provided.
        shape : float, optional
            The shape parameter (k) for the Weibull distribution.
            If provided, 'scale' must also be provided.
        scale : float, optional
            The scale parameter (lambda) for the Weibull distribution.
            If provided, 'shape' must also be provided.
    
        Returns
        -------
        int
            The generated lifetime in weeks.
        """
        
        rng = rng_heating_init() # Get the random number generator
    
        if self.weibull_lifetime:
            # --- Mode 1: Unrestricted Weibull Distribution ---
            # 'min_weeks' and 'max_weeks' are ignored, as requested.

            lifetime = max(min_weeks, scale * rng.weibull(shape))
            
        else:
            # --- Mode 2: Uniform Integer Distribution ---
            # We use 'max_weeks + 1' because rng.integers is exclusive 
            # of the upper bound (i.e., [low, high) )
            lifetime = rng.integers(min_weeks, max_weeks + 1)
    
        # Round to the nearest integer for both cases
        return round(lifetime)

    def get_name(self):
        """
        Returns the name of the heating system class.

        Returns
        -------
        str
            The class name as a string.
        """
        return type(self).__name__

    def breakdown_check(self):
        """
        Check if the system's age has exceeded its lifetime.

        If the age is greater than the system's generated lifetime, 
        the `breakdown` flag is set to True.
        """
        if self.lifetime < self.age:
            self.breakdown = True
            self.investment = 0

    def payback_check(self):
        """
        Reduce the remaining investment value.

        This method is called periodically to simulate the payback of the
        initial investment.
        """
        if self.investment != 0:
            leftovers = self.investment - self.payback
            self.investment = leftovers if leftovers >= 0 else 0

    def calculate_all_attributes(self, area=None, energy_demand=None, house=None, heat_load = None):
        """
        Calculates all cost and performance attributes for the system.

        This is a convenience method that runs all individual calculation
        methods to populate the system's `params` dictionary 
        based on the properties of a given house.

        Parameters
        ----------
        area : float, optional
            The living area of the house in square meters.
        energy_demand : float, optional
            The specific energy demand of the house in kWh per square meter per year.
        house : House, optional
            A House object from which to derive area, energy_demand, and heat_load.
            If provided, it overrides other parameters.
        heat_load : float, optional
            The heat load of the house in kW.
        """
        if house:
            area = house.area
            energy_demand=house.energy_demand
            heat_load=house.heat_load
            
        """Perform all calculations in one method"""
        self.total_energy_demand = self.calculate_energy_demand(
            energy_demand=energy_demand, area=area
        )
        self.params["price"][0] = self.calculate_installation_costs(area=area,
                                                                    heat_load=heat_load)
        self.params["fuel_cost"][0] = self.calculate_fuel_costs(
            energy_demand=self.total_energy_demand
        )
        self.params["opex"][0] = self.calculate_operating_costs(area = area,
                                                                heat_load=heat_load)
        self.params["emissions"][0] = self.calculate_emissions(
            energy_demand=self.total_energy_demand
        )

    def calculate_installation_costs(self, area=None, heat_load=None):
        """
        Calculates the installation cost for the heating system.

        The calculation logic depends on the system type. 
        Some systems are priced based on the house's area, 
        while others are priced based on the required heat load.

        Parameters
        ----------
        area : float, optional
            The living area of the house in square meters.
        heat_load : float, optional
            The heat load of the house in kW.

        Returns
        -------
        float
            The total installation cost in EUR.
        """
        area_based = ["Heating_system_network_local",
                      "Heating_system_GP_Joule",
                      "Heating_system_district"]
        
        if self.heat_delivery_contract:
            return 0
        
        elif type(self).__name__ == "Heating_system_electricity":
            price = self.table["price"]
            factor_area = self.table["factor_area"]
            factor_oppendorf = self.table["factor_oppendorf"]
            price_index = self.table["price_index"]
            sidecosts_index = self.table["sidecosts_index"]
    
            cost = (
                price
                * area**factor_area
                * area
                * factor_oppendorf
                * price_index
                * sidecosts_index
            )
    
            return math.floor(cost)
        
        elif type(self).__name__ in area_based:
            price = self.table["price"]
            factor_area = self.table["factor_area"]
            factor_oppendorf = self.table["factor_oppendorf"]
            price_index = self.table["price_index"]
            sidecosts_index = self.table["sidecosts_index"]
            correction_factor = self.table["heat_load_correction"]
    
            cost = (
                price
                * area**factor_area
                * area
                * factor_oppendorf
                * price_index
                * sidecosts_index
                * correction_factor
            )
    
            return math.floor(cost)
        
        else:
            price = float(self.table["heat_load_price"])
            factor = float(self.table["heat_load_factor"])
            correction_factor = float(self.table["heat_load_correction"])
    
            cost = (
                price
                * ((heat_load)**factor)
                * heat_load
            )
            
            #Adjustments for network options, the same otherwise
            cost = cost * correction_factor
            
            return math.floor(cost)

    def calculate_operating_costs(self, area, heat_load):
        """
        Calculates the annual operating and maintenance costs (OPEX).

        Calculates the OPEX as a fraction of the initial installation cost.
        For systems with a heat delivery contract, the amortised installation
        cost is included in the annual OPEX.

        Parameters
        ----------
        area : float
            The living area of the house in square meters.
        heat_load : float
            The heat load of the house in kW.

        Returns
        -------
        float
            The total annual operating costs in EUR.
        """
        price = self.calculate_installation_costs(area = area, 
                                                  heat_load = heat_load)
        
        if self.heat_delivery_contract:
            price_distributed = 52*(price / self.lifetime)
            
            factor_opex = self.table["factor_opex"]
            opex = price * factor_opex
            
            total_opex = opex + price_distributed
            
            return math.floor(total_opex)      
            
        else:
            factor_opex = float(self.table["factor_opex"])
            cost = price * factor_opex
         
            return math.floor(cost)

    def calculate_fuel_costs(self, energy_demand):
        """
        Calculates the annual energy costs.

        Parameters
        ----------
        energy_demand : float
            The total final energy demand of the house in kWh per year.

        Returns
        -------
        float
            The total annual fuel costs in EUR.
        """
        fuel_cost = self.table["fuel_cost"]
        cost = fuel_cost * energy_demand

        return math.floor(cost)

    def calculate_emissions(self, energy_demand):
        """
        Calculate the annual CO2 equivalent emissions.

        Parameters
        ----------
        energy_demand : float
            The total final energy demand of the house in kWh per year.

        Returns
        -------
        float
            The total annual emissions in grams of CO2 equivalent.
        """
        emissions = self.table["emissions"]
        total_emissions = emissions * energy_demand

        return math.floor(total_emissions)

    def calculate_energy_demand(self, energy_demand, area):
        """
        Calculates the final energy demand.

        This method adjusts a house's specific energy demand by applying a
        system-specific efficiency factor. The factor is chosen from a list
        based on which predefined energy demand class is closest to the
        house's demand.

        Parameters
        ----------
        energy_demand : float
            The specific energy demand of the house in kWh per square meter per year.
        area : float
            The living area of the house in square meters.

        Returns
        -------
        float
            The total final energy demand in kWh per year.
        """
    
        # Create a DataFrame of demand and factor classes
        demand_classes = [50, 100, 150, 200, 250]
        factor_classes = ast.literal_eval(self.table["factor_energy"])
        classes_df = pd.DataFrame({
            "Demand": demand_classes,
            "Factor": factor_classes,
        })
    
        # Identify the factor corresponding to the closest demand class
        factor = classes_df.loc[(classes_df["Demand"] - energy_demand).abs().idxmin(), "Factor"]
    
        # Calculate the processed area with a fixed scaling formula
        processed_area = area * (2.3 * 1.5 + 0.75) * 0.32
    
        # Compute total energy demand
        total_demand = processed_area * energy_demand * factor
        return math.floor(total_demand)

    def calculate_risk(self, agent):
        """
        This method computes a 'riskiness' score between 0 and 1. The score
        is an average of several factors, including the financial risk from
        a potential loan and the system-specific uncertainty mitigated by
        the share of neighbours that have adopted the same system.

        Parameters
        ----------
        agent : Houseowner
            The agent for whom the risk is being calculated.
        """

        factors = {}

        # --- 1. Loan Risk ---
        price = self.params["price"][0]
        
        if self.loan and price > 0:
            loan_risk = min(1, self.loan.loan_amount / price)
            factors["loan_risk"] = loan_risk
        else:
            factors["loan_risk"] = 0
        
        """
        if self.fuel_price_contract_term:
            price_ratio = min(self.fuel_price_contract_term / self.lifetime, 1)
            price_risk = 1 - price_ratio
            factors["price_risk"] = price_risk
        else:
            factors["price_risk"] = 1
        """
    
        # --- 2. Uncertainty Risk ---
        
        graph = agent.model.grid.G
        
        successors_ids = set(graph.successors(agent.unique_id))
        
        n_total_neighbors = len(successors_ids)
        
        n_dissatisfied = 0
        n_known = 0
        target_system_name = self.get_name()
    
        for neighbour_id, opinion_data in agent.neighbours_satisfaction.items():
            if neighbour_id in successors_ids:
                if target_system_name in opinion_data:
                    n_known += 1
                    if opinion_data[target_system_name] == "Dissatisfied":
                        n_dissatisfied += 1
                        
        n_unknown = n_total_neighbors - n_known
    
        weight = agent.uncertainty_factor
        weighted_dissatisfaction = n_dissatisfied + (weight * n_unknown)
        
        """
        if n_dissatisfied > 0:
            factors["uncertainty_risk"] = 1 - n_known / n_total_neighbors)
        else:
            factors["uncertainty_risk"] = 0"""
        
        factors["uncertainty_risk"] = weighted_dissatisfaction / n_total_neighbors
        
        final_risk = sum(factors.values()) / int(len(factors))
        self.riskiness = final_risk
        
    def count_neighbours(self, agent):
        """
        This helper method counts the fraction of an agent's neighbours who
        have installed the same type of heating system. It returns a value
        representing the inverse of this fraction, where 1 indicates maximum
        uncertainty (no neighbours have the system) and 0 indicates minimum
        uncertainty (all neighbours have the system).

        Parameters
        ----------
        agent : Houseowner
            The agent whose neighbours are being checked.

        Returns
        -------
        float
            A value between 0 and 1 representing social uncertainty.
        """
        total_systems = 0
        target_systems = 0
        for neighbour_system in agent.neighbours_systems.values():
            total_systems += 1
            if self.get_name() == neighbour_system:
                target_systems += 1
        
        if total_systems != 0:     
            target_share = target_systems / total_systems
            return 1 - target_share
        else:
            return 1
    
    
    def __repr__(self):
        return f"{self.number}: {type(self)} | Price: {self.params['price']} | Rating: {self.rating}\n"


    def __str__(self):
        return self.__repr__()
    
class Heating_system_oil(Heating_system):
    """
    Represents an oil-fired heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the oil heating system with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 0
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [
                self.table["operation_effort"],
                0,
            ],  # Operational effort, hours per year
            "fuel_cost": [None, 0],  # Fuel/energy cost, EUR per year
            "emissions": [None, 0],  # Emissions, grams of CO2 equivalent per kWh
            "price": [None, 0],  # Installation price, EUR
            "installation_effort": [
                self.table["installation_effort"],
                0,
            ],  # Working hours
            "opex": [None, 0],  # Operating price, EUR per Year
        }

        # The part used by AHID
        self.conversion_params = {
            "es": "oil",
            "heat_sys": "cond_boiler",
            "ht": "flat",
            "ns": "no",
        }


class Heating_system_gas(Heating_system):
    """
    Represents a gas-fired heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for a gas heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the gas heating system with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 1
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "gas",
            "heat_sys": "cond_boiler",
            "ht": "flat",
            "ns": "no",
        }
        

class Heating_system_heat_pump(Heating_system):
    """
    Represents an independent heat pump.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the heat pump heating system with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 2
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "heat_re",
            "heat_sys": "hp_air",
            "ht": "flat",
            "ns": "no",
        }


class Heating_system_electricity(Heating_system):
    """
    Represents an electricity-based heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the electricity-based heating with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 3
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "electricity",
            "heat_sys": "cond_boiler_sol",
            "ht": "flat",
            "ns": "no",
        }


class Heating_system_pellet(Heating_system):
    """
    Represents a pellet heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the pellet heating system with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 4
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "wood",
            "heat_sys": "cond_boiler_sol",
            "ht": "flat",
            "ns": "no",
        }


class Heating_system_network_district(Heating_system):
    """
    Represents a district grid-based heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the district heating with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 5
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "wood",
            "heat_sys": "cond_boiler_sol",
            "ht": "dh",
            "ns": "no",
        }


class Heating_system_network_local(Heating_system):
    """
    Represents a hot local network heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the hot local network heating with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 6
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "wood",
            "heat_sys": "cond_boiler_sol",
            "ht": "dh",
            "ns": "no",
        }


class Heating_system_heat_pump_brine(Heating_system):
    """
    Represents a heat pump-based cold local network heating system.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the heat pump-based cold local network with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 7
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "heat_re",
            "heat_sys": "hp_brine",
            "ht": "flat",
            "ns": "no",
        }


class Heating_system_GP_Joule(Heating_system):
    """
    Represents a hot local network heating system provided by the firm "GP Joule".

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the hot local network provided by the firm GP Joule 
        with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 6
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [None, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "wood",
            "heat_sys": "cond_boiler_sol",
            "ht": "dh",
            "ns": "no",
        }
        

class Heating_system_vacuum_tube(Heating_system):
    """
    Represents a vacuum tube heating system. Not actually a heating system and
    is not used anywhere in the model.

    This class inherits from `Heating_system` and sets the specific parameters
    for an oil heating system by loading them from the global `params_table`.
    """
    def __init__(self, table = None):
        """
        Initialises the vacuum tube heating system with its specific parameters.

        Parameters
        ----------
        table : Heating_params_table, optional
            The parameter table to use. If None, the global `params_table`
            is used, by default None.
        """
        super().__init__()
        # Data table
        if table is None:
            table = params_table
        self.table = table.content.loc[type(self).__name__]
        # Used for the data collection and visualization
        self.number = 8
        # Expected lifetime of a system
        self.weibull_lifetime = settings.data.heat_sys_weibull_generation
        self.lifetime = self.generate_lifetime(
            min_weeks = self.table["lifetime_lower"], max_weeks = self.table["lifetime_upper"],
            shape = self.table["weibull_shape"], scale = self.table["weibull_scale"]
        )
        self.availability = self.table["availability"]
        # Used by plumber to install
        self.installation_time = self.table["installation_time"]
        # Satisfied/dissatisfied known neighbour owners ratio
        self.satisfied_ratio = None
        self.power = self.table["power"]
        self.fuel_price_contract_term = self.table["contract"]
        self.heat_delivery_contract = True if self.table["heat_delivery"] == 1 else False

        # The part used for the rating calculation
        self.params = {
            "operation_effort": [self.table["operation_effort"], 0],
            "fuel_cost": [None, 0],
            "emissions": [0, 0],
            "price": [None, 0],
            "installation_effort": [self.table["installation_effort"], 0],
            "opex": [None, 0],
        }

        self.conversion_params = {
            "es": "heat_re",
            "heat_sys": "cond_boiler_sol",
            "ht": "flat",
            "ns": "no",
        }


"""AHID Compatibility parameters
es = energy source("gas", "oil", "wood", "electricity", "heat_re", "district_chp_mix", "district_steam_mix")
heat_sys = heating system ("cond_boiler", "cond_boiler_sol", "low_temp_boiler", 
                           "low_temp_boiler_sol", "const_temp_boiler", "const_temp_boiler_sol", 
                           "pellet, pellet_sol", "hp_air", "hp_air_vent", "hp_brine", "hp_brine_vent", "dh")
ht = heating type ("district", "central", "flat")
ns = night setback ("yes", "no")
"""
