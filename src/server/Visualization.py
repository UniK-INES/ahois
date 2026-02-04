"""
Defines the visualisation components for the Mesa server.

This module creates all the necessary elements for the browser-based
visualisation of the simulation. It includes several agent portrayal functions
that define how agents are coloured and described on the map based on their
current state (e.g., heating system type, energy demand, knowledge). It
also sets up chart modules for plotting time-series data and configures
the main map visualisation.

Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import mesa
from helpers.config import settings
from server.additional_methods import rgb_to_hex, subsidy_overspread_portrayal, heating_system_overspread_portrayal



# Create agent portrayals
def HS_portrayal(agent):
    """
    Defines the portrayal for visualising the distribution of heating systems.

    This function colours agents on the map based on the type of heating
    system currently installed in their house. Colours are defined in the
    global settings file.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'size' and 'color'.
    """
    size = 1
    heating_systems_colors = settings.heating_systems_colors
    heating_system_type = type(agent.current_heating).__name__
    color = heating_systems_colors.get(heating_system_type, None)

    return {"size": size, "color": color}


def energy_demand_portrayal(agent):
    """
    Defines the portrayal for visualising the distribution of energy demand.

    This function colours agents on a yellow-to-red gradient based on their
    total energy demand. The colour intensity is scaled relative to the
    maximum energy demand observed in the model for normalisation.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'size' and 'color'.
    """
    size = 1
    total_energy_demand = (
        agent.current_heating.total_energy_demand
    )  # Total demand of a house
    max_demand = agent.model.max_total_energy_demand  # Max possible demand for scaling
    color_intensity = min(
        total_energy_demand / max_demand, 1
    )  # Define colour intensity depending on the energy demand
    color = rgb_to_hex([255, 255 * (1 - color_intensity), 0])
    return {"size": size, "color": color}


def emissions_portrayal(agent):
    """
    Defines the portrayal for visualizing the distribution of CO2 emissions.

    This function colours agents on a green-to-red gradient based on their
    annual CO2 emissions. The colour intensity is scaled relative to the
    maximum emissions observed in the model for normalisation.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'size' and 'color'.
    """
    size = 1
    emissions = agent.current_heating.params["emissions"][
        0
    ]  # Total emissions of a house
    max_emissions = agent.model.max_emissions  # Max possible demand for scaling
    color_intensity = min(
        emissions / max_emissions, 1
    )  # Define colour intensity depending on the energy demand
    color = rgb_to_hex([255 * color_intensity, 255 * (1 - color_intensity), 0])
    return {"size": size, "color": color}


def information_overspread_middleware(agent):
    """
    Acts as a dispatcher to select the active information-spread portrayal.

    Based on a global setting, this function calls the appropriate portrayal
    method to visualise either the spread of subsidy knowledge, heating
    system knowledge, or the probability of installing a target system.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        The portrayal dictionary from the selected function.
    """
    selected_option = settings.information_overspread.selected_option
    if selected_option == "subsidy_to_observe":
        return subsidy_overspread_portrayal(agent)
    elif selected_option == "known_hs_to_observe":
        return heating_system_overspread_portrayal(agent)
    else:
        return probability_of_installing_portrayal(agent)

def probability_of_installing_portrayal(agent):
    """
    Defines the portrayal for visualising the likelihood of installing a target system.

    This function colours an agent based on the comparison between the rating
    of their current heating system and their rating for a scenario-defined
    target system. The colour indicates how favourably the agent views the
    target system relative to their own.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'color' and 'description' (tooltip).
    """
    portrayal = {}
    current_heating_rating = agent.current_heating.rating
    current_heating = agent.current_heating.__class__.__name__
    target_heatings = settings.heating_systems.compare_scenario[
        agent.model.scenario.__class__.__name__
    ]
    target_heating_ratings = {}
    color = "white"

    for hs in agent.houseowner.known_hs:
        for target_heating in target_heatings:
            if hs.__class__.__name__ == target_heating and hs.rating != None:
                target_heating_ratings[target_heating] = hs.rating

    if len(target_heatings) == 1 and len(target_heating_ratings.keys()) == 1 and current_heating_rating is not None:
        color_intensity = min(
            current_heating_rating / target_heating_ratings[target_heatings[0]], 1
        )
        color = rgb_to_hex([255 * (1 - color_intensity), 255 * color_intensity, 0])

    target_heating_ratings = (
        ", ".join([f"{k}: {v}" for k, v in target_heating_ratings.items()])
        if len(target_heating_ratings) > 0
        else "Unknown"
    )

    # If there are multiple target heatings everything is white, but we want to see
    # changes in the color of the agents when they are get some rating information
    if len(target_heatings) > 1 and target_heating_ratings != "Unknown":
        color = "purple"

    # If the agent has the target heating, it will be purple
    if len(target_heatings) == 1 and current_heating == target_heatings[0]:
        color = "purple"
    
    portrayal["color"] = color
    portrayal["description"] = {
        "Person": agent.unique_id,
        "Current heating": current_heating,
        "Rating": current_heating_rating if current_heating_rating is not None else "Unknown",
        "Target heating": ", ".join(
            [target_heating for target_heating in target_heatings]
        ),
        "Target heating ratings": target_heating_ratings,
    }

    return portrayal

def best_system_rating(agent):
    """
    Defines the portrayal for visualising the rating of the target system vs. 
    the best-known alternative.

    This function colours an agent based on the ratio between their rating for a
    target heating system and the rating of the best alternative system they know.
    This helps to visualise the competitiveness of the target system from the
    agent's perspective.

    Parameters
    ----------
    agent : mesa_geo.GeoAgent
        The House agent to be portrayed.

    Returns
    -------
    dict
        A dictionary specifying the agent's 'color' and 'description' (tooltip).
    """
    portrayal = {}
    current_heating = agent.current_heating.__class__.__name__
    target_heatings = settings.heating_systems.compare_scenario[
        agent.model.scenario.__class__.__name__
    ]
    target_heating_ratings = {}
    color = "white"
    best_heating_rating = 0
    best_heating_system = None

    for hs in agent.houseowner.known_hs:
        for target_heating in target_heatings:
            if hs.rating != None:
                if hs.__class__.__name__ == target_heating:
                    target_heating_ratings[target_heating] = hs.rating
                else:
                    if hs.rating > best_heating_rating:
                        best_heating_rating = hs.rating
                        best_heating_system = hs.__class__.__name__

    if len(target_heatings) == 1 and len(target_heating_ratings.keys()) == 1 and best_heating_system is not None:
        color_intensity = min(
            target_heating_ratings[target_heatings[0]] / best_heating_rating, 1
        )
        color = rgb_to_hex([255 * (1 - color_intensity), 255 * color_intensity, 0])
    
    target_heating_ratings = (
        ", ".join([f"{k}: {v}" for k, v in target_heating_ratings.items()])
        if len(target_heating_ratings) > 0
        else "Unknown"
    )
    
    # If there are multiple target heatings everything is white, but we want to see
    # changes in the color of the agents when they are get some rating information
    if len(target_heatings) > 1 and target_heating_ratings != "Unknown":
        color = "purple"

    # If the agent has the target heating, it will be purple
    if len(target_heatings) == 1 and best_heating_system == target_heatings[0]:
        color = "purple"

    portrayal["color"] = color
    portrayal["description"] = {
        "Person": agent.unique_id,
        "Current heating": current_heating,
        "Best heating": best_heating_system if best_heating_system != None else "Unknown",
        "Best Rating": best_heating_rating if best_heating_rating != 0 else "Unknown",
        "Target heating": ", ".join(
            [target_heating for target_heating in target_heatings]
        ),
        "Target heating ratings": target_heating_ratings,
    }
    return portrayal


# Data charts
replacements_chart = mesa.visualization.ChartModule(
    [{"Label": "Replacements", "Color": "#0000FF"}], data_collector_name="datacollector"
)

emissions_chart = mesa.visualization.ChartModule(
    [{"Label": "Emissions", "Color": "#00FF00"}], data_collector_name="datacollector"
)

scenario_fulfilment_chart = mesa.visualization.ChartModule(
    [{"Label": "Scenario fulfilment", "Color": "#00FF88"}],
    data_collector_name="datacollector",
)

# Create the map (insert HS_portrayal, energy_demand_portrayal, or emissions_portrayal)
# map_visualization = MapModule(
#     portrayal_method=information_overspread_middleware,
#     view=None,
#     zoom=None,
#     map_width=800,
#     map_height=800,
#     scale_options=None,
# )
