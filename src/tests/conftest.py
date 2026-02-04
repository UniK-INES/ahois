"""
Pytest fixtures and configuration for testing the agent-based model.

This file defines shared fixtures for the test suite, making it easier to write
and maintain tests. A fixture provides a fixed baseline state or data for
tests.

This `conftest.py` initialises a single `Prototype_Model` instance when the
test session starts. The various fixtures then provide copies of agents (e.g.,
Houseowner, Plumber) and other objects (e.g., Heating_system instances) from
this pre-initialised model. Using copies (`copy` or `deepcopy`) is crucial as
it ensures that tests are isolated and do not interfere with one another by
modifying the original model's state.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
from dotenv import load_dotenv
load_dotenv()
from helpers.config import settings
import pytest
from copy import deepcopy, copy
from agents.Houseowner import Houseowner
from agents.Plumber import Plumber
from modules.Heating_systems import (
    init_param_table,
    Heating_system_oil,
    Heating_system_gas,
    Heating_system_heat_pump,
    Heating_system_electricity,
)
from modules.Information_sources import (
    Information_source,
    Information_source_internet,
    Information_source_magazine,
)
import numpy as np
from modules.Triggers import (
    Trigger_none,
    Trigger_neighbour_jealousy,
)
from Model import Prototype_Model


init_param_table()
model = Prototype_Model(
    P=settings.main.number_of_plumbers,
    E=settings.main.number_of_energy_advisors,
    scenario=settings.main.current_scenario,
    #geojson_path=f"../{settings.geo.geojson_file_path}",
    verbose=False,
)


@pytest.fixture
def houseowner():
    """
    Provides a copy of a `Houseowner` agent from the global model.

    Returns
    -------
    Houseowner
        A shallow copy of the first Houseowner agent found in the model's
        schedule.
    """
    for agent in model.schedule.agents:
        if isinstance(agent, Houseowner):
            return copy(agent)


@pytest.fixture
def neighbour():
    """
    Provides a copy of a second `Houseowner` agent to act as a neighbour.

    This allows for testing interactions between two distinct houseowner agents.

    Returns
    -------
    Houseowner
        A shallow copy of the second Houseowner agent found in the model's
        schedule.
    """
    houseowner_count = 0

    for agent in model.schedule.agents:
        if isinstance(agent, Houseowner):
            houseowner_count += 1
            if houseowner_count == 2:
                return copy(agent)


@pytest.fixture
def plumber():
    """
    Provides a copy of a `Plumber` agent from the global model.

    Returns
    -------
    Plumber
        A shallow copy of the first Plumber agent found in the model's
        schedule.
    """
    for agent in model.schedule.agents:
        if isinstance(agent, Plumber):
            return copy(agent)


class Information_source_preference_cut:
    """
    A helper class to represent a simple distribution of source preferences.

    This class is used in tests to assign a random, normalised preference
    between 'internet' and 'magazine' information sources. The values are
    drawn from a Dirichlet distribution, ensuring they sum to 1.
    """
    def __init__(self):
        randomizer = np.random.dirichlet(np.ones(2), size=1)
        self.internet = randomizer[0][0]
        self.magazine = randomizer[0][1]


@pytest.fixture
def heating_system_oil():
    """
    Provides a deep copy of an `Heating_system_oil` instance.

    A deep copy is used to ensure that any modifications to the heating system
    object within a test do not affect other tests.

    Returns
    -------
    Heating_system_oil
        A deep copy of the first oil heating system found in the model.
    """
    for house in model.space.agents:
        if isinstance(house.current_heating, Heating_system_oil):
            return deepcopy(house.current_heating)


@pytest.fixture
def heating_system_gas():
    """
    Provides a deep copy of a `Heating_system_gas` instance.

    Returns
    -------
    Heating_system_gas
        A deep copy of the first gas heating system found in the model.
    """
    for house in model.space.agents:
        if isinstance(house.current_heating, Heating_system_gas):
            return deepcopy(house.current_heating)


@pytest.fixture
def heating_system_heat_pump():
    """
    Provides a deep copy of a `Heating_system_heat_pump` instance.

    Returns
    -------
    Heating_system_heat_pump
        A deep copy of the first heat pump system found in the model.
    """
    for house in model.space.agents:
        if isinstance(house.current_heating, Heating_system_heat_pump):
            return deepcopy(house.current_heating)


@pytest.fixture
def heating_system_eletricity():
    """
    Provides a deep copy of an `Heating_system_electricity` instance.

    Returns
    -------
    Heating_system_electricity
        A deep copy of the first electric heating system found in the model.
    """
    for house in model.space.agents:
        if isinstance(house.current_heating, Heating_system_electricity):
            return deepcopy(house.current_heating)


@pytest.fixture
def information_source_internet():
    """
    Provides a new instance of `Information_source_internet`.

    Returns
    -------
    Information_source_internet
        A new, standard instance of the information source.
    """
    return Information_source_internet()


@pytest.fixture
def information_source_magazine():
    """
    Provides a new instance of `Information_source_magazine`.

    Returns
    -------
    Information_source_magazine
        A new, standard instance of the information source.
    """
    return Information_source_magazine()


@pytest.fixture
def information_source_preference_cut():
    """
    Provides an instance of the helper class `Information_source_preference_cut`.

    Returns
    -------
    Information_source_preference_cut
        An instance with randomised preference values for information sources.
    """
    return Information_source_preference_cut()


@pytest.fixture
def information_source():
    """
    Provides a new instance of the base `Information_source` class.

    Returns
    -------
    Information_source
        A new, standard instance of the base information source.
    """
    return Information_source()


@pytest.fixture
def trigger_neighbour_jealousy():
    """
    Provides a new instance of `Trigger_neighbour_jealousy`.

    Returns
    -------
    Trigger_neighbour_jealousy
        A new instance of the trigger.
    """
    return Trigger_neighbour_jealousy()


@pytest.fixture
def trigger_none():
    """
    Provides a new instance of `Trigger_none`.

    Returns
    -------
    Trigger_none
        A new instance of the default 'None' trigger.
    """
    return Trigger_none()
