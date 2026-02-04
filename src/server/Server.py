"""
Configuration and instantiation of the Mesa visualisation server.

This script sets up the interactive web server for the agent-based model
using Mesa's visualisation tools. It defines the user-configurable model
parameters, such as sliders for the number of agents and dropdowns for
scenario selection. It also links the visualisation modules (like the map
and charts) to the main model, creating the complete server instance that
is launched by `Launch.py`.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import mesa
from Model import Prototype_Model
from server.Visualization import scenario_fulfilment_chart
from helpers.config import settings

options = {
    "subsidy_to_observe": mesa.visualization.Choice(
        "Subsidy",
        choices=settings.information_overspread.subsidies_list,
        value=settings.information_overspread.subsidies_current,
    ),
    "known_hs_to_observe": mesa.visualization.Choice(
        "Known heating systems",
        choices=settings.information_overspread.known_hs_list,
        value=settings.information_overspread.known_hs_current,
    ),
}

# Model params
model_params = {
    "P": mesa.visualization.Slider(
        "Number of plumbers",
        value=settings.main.number_of_plumbers,
        min_value=1,
        max_value=50,
        step=1,
    ),
    "E": mesa.visualization.Slider(
        "Number of energy advisors",
        value=settings.main.number_of_energy_advisors,
        min_value=1,
        max_value=50,
        step=1,
    ),
    "scenario": mesa.visualization.Choice(
        "Scenario",
        choices=list(settings.heating_systems.compare_scenario.keys()),
        value=settings.main.current_scenario,
    ),
}

selected_option = settings.information_overspread.selected_option

# Adding the selected parameter to the model_params dictionary
if selected_option in options:
    model_params[selected_option] = options[selected_option]
else:
    raise ValueError(f"Incorrect selected option: {selected_option}")


# Server to be used without dynamic charts
server = mesa.visualization.ModularServer(
    Prototype_Model,
    [scenario_fulfilment_chart],
    name="Prototype Model",
    model_params=model_params,
)
