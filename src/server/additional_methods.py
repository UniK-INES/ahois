"""
Helper functions for Mesa server visualisation.

This module provides utility functions used by the main visualisation components.
It includes a colour converter and specific agent portrayal methods for
visualising the spread of information (subsidies and heating system knowledge)
on the simulation map.

:Authors:
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
def rgb_to_hex(rgb):
    """
    Converts an RGB colour tuple to a hexadecimal string.

    This function takes an RGB colour, represented as a list or tuple of three
    integers, and converts it into the standard hexadecimal colour format
    used in web and visualisation contexts.

    Parameters
    ----------
    rgb : list or tuple of int
        An iterable containing three integer values (Red, Green, Blue)
        ranging from 0 to 255.

    Returns
    -------
    str
        The hexadecimal color representation (e.g., '#RRGGBB').

    Examples
    --------
    >>> rgb_to_hex([255, 0, 0])
    '#ff0000'
    >>> rgb_to_hex((0, 128, 255))
    '#0080ff'
    """
    return "#" + "".join(f"{int(c):02x}" for c in rgb)


def subsidy_overspread_portrayal(agent):
    """
    Defines the agent portrayal for visualising subsidy knowledge.

    This Mesa portrayal function determines how a House agent is displayed on
    the map. If the agent's associated houseowner knows about the specific
    subsidy being observed in the model (`agent.model.subsidy_to_observe`),
    the agent is coloured green. Otherwise, it is white. The portrayal's
    description tooltip lists all subsidies known by the agent.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed. It is expected to have a `houseowner`
        attribute with subsidy information.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'color' and 'description'
        for the visualisation.
    """
    portrayal = {}
    color = "white"
    known_subsidies = []

    for subsidy_list in agent.houseowner.known_subsidies.values():
        for subsidy in subsidy_list:
            known_subsidies.append(subsidy.name)
            if agent.model.subsidy_to_observe == subsidy.name:
                color = "green"

    portrayal["description"] = {
        "Person:": agent.unique_id,
        "Known subsidies:": ", ".join(known_subsidies) if known_subsidies else "None",
    }
    portrayal["color"] = color
    return portrayal


def heating_system_overspread_portrayal(agent):
    """
    Defines the agent portrayal for visualising heating system knowledge.

    This Mesa portrayal function determines how a House agent is displayed on
    the map. If the agent's associated houseowner knows about the specific
    heating system being observed in the model (`agent.model.known_hs_to_observe`),
    the agent is coloured green. Otherwise, it is white. The portrayal's
    description tooltip lists all heating systems known by the agent.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed. It is expected to have a `houseowner`
        attribute with heating system information.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'color' and 'description'
        for the visualisation.
    """
    portrayal = {}
    color = "white"
    known_hs = []

    for hs in agent.houseowner.known_hs:
        known_hs.append(hs.__class__.__name__)
        if agent.model.known_hs_to_observe == hs.__class__.__name__:
            color = "green"

    portrayal["description"] = {
        "Person:": agent.unique_id,
        "Known heating systems:": ", ".join(known_hs) if known_hs else "None",
    }
    portrayal["color"] = color
    return portrayal
