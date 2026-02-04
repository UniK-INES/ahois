"""
Defines the House agent for the simulation.

This module contains the `House` class, a GeoAgent that represents a physical 
building in the model. It holds attributes like construction year, area, and 
energy demand, and is directly linked to a `Houseowner` agent and a 
`Heating_system`. It also includes an Enum for different heating terminal types.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""
import mesa_geo as mg
import numpy as np
import pandas as pd
import logging
from modules.Rng import rng_house_init
from enum import Enum, auto
from modules.Excel_input_read import Milieu_table
from helpers.config import settings

logger = logging.getLogger("ahoi")
logger.setLevel(logging.INFO)

class House(mg.GeoAgent):
    """A GeoAgent representing a single residential building in the model.

    This agent models the physical characteristics of a building, including its
    geographical footprint, age, size, and energy requirements. Each house is
    associated with a `Houseowner` agent and contains the currently installed
    heating system.

    Attributes
    ----------
    milieu_table : Milieu_table
        A table containing parameters for different socio-economic milieus.
    milieu : Milieu
        The milieu associated with the house's owner.
    year : int
        The year the house was constructed.
    area : float
        The living area of the house in square meters.
    energy_demand : float
        The annual energy demand for heating in kWh per sq.m. per year.
    current_heating : Heating_system
        The heating system currently installed in the house.
    houseowner : Houseowner
        The `Houseowner` agent who owns and lives in the house.
    subarea : str
        The name of the geographical subarea where the house is located.
    heat_load : float
        The heating load of the house in kW.
    """

    def __init__(self, unique_id, model, geometry, crs, current_heating=None):
        """Initializes a House agent.

        Parameters
        ----------
        unique_id : int
            A unique identifier for the agent, typically provided by MESA-Geo.
        model : mesa.Model
            The main model instance.
        geometry : shapely.geometry.BaseGeometry
            A Shapely object representing the house's geographical footprint.
        crs : str or pyproj.CRS
            The coordinate reference system of the geometry.
        current_heating : Heating_system, optional
            The heating system to be installed initially. Defaults to None.
        """
        
        super().__init__(unique_id, model, geometry, crs)
        self.milieu_table = Milieu_table()
        self.milieu = None
        self.year = None
        self.area = None
        self.energy_demand = None  
        self.current_heating = current_heating
        self.houseowner = None
        self.subarea = None
        self.heat_load = None

    def set_house_owner(self, houseowner):
        """Assigns a Houseowner agent to this house.

        Parameters
        ----------
        houseowner : Houseowner
            The `Houseowner` agent to be linked to this house.
        """
        self.houseowner = houseowner

    def knockknock(self):
        """Returns the owner of the house.

        Returns
        -------
        Houseowner
            The `Houseowner` agent associated with this house.
        """
        return self.houseowner

    def generate_area_distribution(self, mean, deviation):
        """Generates a living area value from a normal distribution.

        This method is used for initializing house areas when specific data is
        not available.

        Parameters
        ----------
        mean : float
            The mean living area in square meters.
        deviation : float
            The standard deviation from the mean in square meters.

        Returns
        -------
        float
            A randomly generated value for the living area.
        """
        return rng_house_init().normal(mean, deviation)

    def generate_energy_demand_distribution(self, mean, deviation):
        """Generates an energy demand value from a normal distribution.

        This method is used for initializing energy demand when specific data
        is not available.

        Parameters
        ----------
        mean : float
            The mean energy demand in kWh per square meter per year.
        deviation : float
            The standard deviation from the mean.

        Returns
        -------
        float
            A randomly generated value for the energy demand.
        """
        return rng_house_init().normal(mean, deviation)

    def define_energy_demand(self, year, heat_demand):
        """Sets the specific energy demand based on construction year 
        and data source.

        This method calculates the energy demand (in kWh/m²/a) based on one of
        two modes defined in the model settings:
        - 'eqcity': Uses a predefined lookup table based on building age classes.
        - 'ubem': Calculates the demand by dividing the total annual heat demand
                  by the house's area.

        Parameters
        ----------
        year : int
            The construction year of the house.
        heat_demand : float
            The total annual heat demand of the house in kWh, used in 'ubem' mode.

        Returns
        -------
        float
            The calculated specific energy demand in kWh per square meter per year.
        """
        if settings.data.heat_demand == "eqcity":
            classes_df = pd.DataFrame(
                {
                    "Start": [
                        1860,
                        1919,
                        1949,
                        1958,
                        1969,
                        1979,
                        1984,
                        1995,
                        2002,
                        2010,
                    ],
                    "End": [1918, 1948, 1957, 1968, 1978, 1983, 1994, 2001, 2009, 2050],
                    "Demand": [181, 164, 182, 180, 153, 120, 132, 122, 87, 50],
                }
            )
            for _, row in classes_df.iterrows():
                if row["Start"] <= year <= row["End"]:
                    return row["Demand"]
                    break
        elif settings.data.heat_demand == "ubem":
            demand = heat_demand / self.area
            return demand
