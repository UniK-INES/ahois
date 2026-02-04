"""
Pytest unit tests for the `Houseowner` agent class.

This file contains a suite of unit tests that cover a wide range of the
`Houseowner` agent's behaviours and methods. It uses the `pytest` framework
and relies on fixtures defined in `conftest.py` to provide the necessary agent
instances and other objects for testing.

The tests are organised logically to follow the agent's decision-making
process, from evaluating its current situation to gathering information,
making choices, and finally installing a new heating system.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
from copy import deepcopy
import random

# testing of evaluate() method


def test_evaluation_of_current_hs_cognitive_resource_depleting(houseowner):
    """
    Tests that evaluating the current heating system 
    depletes cognitive resources.
    """
    initial_cognitive_resource = houseowner.cognitive_resource
    houseowner.evaluate()
    assert houseowner.cognitive_resource == initial_cognitive_resource - 1


def test_evaluation_of_current_hs_dissatisfied(houseowner):
    """
    Tests that the houseowner remains 'Satisfied' 
    if their heating system is relatively new.
    """
    
    
    houseowner.standard.lifetime = 5

    # housewoner still has a new heating system
    houseowner.house.current_heating.age = 2
    houseowner.house.current_heating.lifetime = 10

    houseowner.evaluate()

    assert houseowner.satisfaction == "Satisfied"


def test_evaluation_of_current_hs_satisfied(houseowner):
    """
    Tests that the houseowner becomes 'Dissatisfied' 
    when the heating system approaches the end of its lifetime.
    """
    houseowner.standard.lifetime = 5

    # the lifetime of the heating system is almost over
    houseowner.house.current_heating.age = 8
    houseowner.house.current_heating.lifetime = 10

    houseowner.evaluate()

    assert houseowner.satisfaction == "Dissatisfied"


# testing of get_data() method and its possible consequences


def test_exception_when_consultation_is_already_ordered(houseowner):
    """
    Tests that `get_data` depletes cognitive resources 
    if a consultation is already ordered.
    """
    houseowner.consultation_ordered = True
    houseowner.get_data()
    assert houseowner.cognitive_resource == 0


def test_ordered_consulation_after_breakdown(houseowner):
    """
    Tests that a consultation is ordered automatically 
    when the heating system breaks down.
    """
    houseowner.house.current_heating.breakdown = True

    houseowner.get_data()

    assert houseowner.consultation_ordered == True


# When get_data method will find neighbours as a valid source of information
# we should therefore test ask_neighbours method
# which after finding neighbours will share knowledge with them by invoke methods
# share_ratings, shate_knowledge, share_satisfaction


def test_share_rating(houseowner, neighbour, heating_system_oil):
    """
    Tests that two neighbours correctly share and store 
    each other's heating system ratings.
    """
    houseowner.known_hs = [heating_system_oil]
    neighbour.known_hs = [heating_system_oil]

    houseowner.known_hs[0].rating = 0.1

    houseowner.share_rating(neighbour)
    neighbour.share_rating(houseowner)

    assert houseowner.known_hs[0].neighbours_opinions[neighbour.unique_id] == 0.1
    assert neighbour.known_hs[0].neighbours_opinions[houseowner.unique_id] == 0.1


def test_share_knowledge_of_known_hs(
    houseowner, neighbour, heating_system_oil, heating_system_gas
):
    """
    Tests that a neighbour acquires knowledge of a new heating system 
    from another houseowner.
    """
    houseowner.known_hs = [heating_system_oil]
    neighbour.known_hs = [heating_system_gas]

    houseowner.share_knowledge(neighbour)

    assert len(neighbour.known_hs) == 2


def test_share_knowledge_of_same_known_hs(houseowner, neighbour, heating_system_oil):
    """
    Tests that redundant knowledge (of an already known heating system) 
    is not shared.
    """
    houseowner.known_hs = []
    neighbour.known_hs = []

    houseowner.known_hs.append(heating_system_oil)

    # assuring that we will not share the same object
    heating_system_oil_copy = deepcopy(heating_system_oil)
    neighbour.known_hs.append(heating_system_oil_copy)

    houseowner.share_knowledge(neighbour)

    # neighbour will not aquire any knowledge, because he already know the oil heating system
    assert len(neighbour.known_hs) == 1


def test_sharing_params_knowledge(houseowner, neighbour, heating_system_oil):
    """
    Tests that knowledge sharing updates the parameters 
    (e.g., operation effort) of a known heating system.
    """
    heterogenous_heating_system_oil = deepcopy(heating_system_oil)
    neighbour_initial_operation_effort = 15.0

    heterogenous_heating_system_oil.params["operation_effort"] = [
        neighbour_initial_operation_effort,
        10,
    ]
    # non-zero uncertainty
    heating_system_oil.params["operation_effort"] = [10, 1]

    houseowner.known_hs.append(heating_system_oil)
    neighbour.known_hs.append(heterogenous_heating_system_oil)

    houseowner.share_knowledge(neighbour)
    #
    assert (
        neighbour_initial_operation_effort
        != neighbour.known_hs[0].params["operation_effort"][0]
    )


def test_share_satisfaction(houseowner, neighbour, heating_system_oil):
    """
    Tests that a houseowner's satisfaction ratio for a heating system 
    is updated based on neighbours' opinions.
    """
    # assuring that we will not share the same object
    heating_system_oil_copy = deepcopy(heating_system_oil)

    houseowner.known_hs.append(heating_system_oil)
    neighbour.known_hs.append(heating_system_oil_copy)

    neighbour.neighbours_HS = {
        "Houseowner 1": {"Heating_system_oil": "Satisfied"},
        "Houseowner 2": {"Heating_system_oil": "Disatisfied"},
        "Houseowner 3": {"Heating_system_oil": "Satisfied"},
        "Houseowner 4": {"Heating_system_oil": "Disatisfied"},
        "Houseowner 5": {"Heating_system_oil": "Satisfied"},
    }

    houseowner.house.current_heating = heating_system_oil
    neighbour.house.current_heating = heating_system_oil_copy

    # 3 Satisfied opinion / 5 Disatisfied opinion = 0.6 Satisfied ration
    houseowner.share_satisfaction(neighbour)

    # initially was None, here tests prove that satisfied ratio has changed
    assert neighbour.known_hs[0].satisfied_ratio <= 1
    assert neighbour.known_hs[0].satisfied_ratio >= 0


# When get_data method will use internet and magazine as a source of information
# we need to test functionality with other logic compare to other sources of information


def test_gaining_information_about_hs(
    houseowner,
    information_source_internet,
    information_source_magazine,
    information_source_preference_cut,
):
    """
    Tests that a houseowner can gain knowledge 
    of new heating systems from media sources.
    """
    
    houseowner.known_hs = []

    houseowner.house.current_heating.rating = 0

    # assuring that houseowner will definetelly chose some of the resources provided above
    # because other possbile recources was already tested
    houseowner.source_preferences = information_source_preference_cut
    houseowner.model.list_of_sources = [
        information_source_internet,
        information_source_magazine,
    ]
    houseowner.get_data()

    assert len(houseowner.known_hs) >= 1


def test_gaining_information_about_hs_no_cognitive_resource(
    houseowner,
    information_source_preference_cut,
    information_source_internet,
    information_source_magazine,
):
    """
    Tests that a houseowner with zero cognitive resources 
    cannot gain new information.
    """
    
    houseowner.known_hs = []
    houseowner.cognitive_resource = 0

    houseowner.source_preferences = information_source_preference_cut

    houseowner.model.list_of_sources = [
        information_source_internet,
        information_source_magazine,
    ]

    houseowner.get_data()

    assert len(houseowner.known_hs) == 0


# to test define_choice method first we need to test calculate_attitude method


def test_calculate_attitude(
    houseowner, heating_system_gas, heating_system_oil, heating_system_heat_pump
):
    """
    Tests that the calculated attitude (rating) 
    for a heating system is within the expected bounds.
    """
    
    houseowner.known_hs = [
        heating_system_gas,
        heating_system_oil,
        heating_system_heat_pump,
    ]
    system = houseowner.known_hs[0]

    houseowner.calculate_attitude(system)

    assert system.rating >= 0
    assert system.rating <= len(system.params)


def test_define_choice(
    houseowner, heating_system_gas, heating_system_oil, heating_system_heat_pump
):
    """
    Tests that the houseowner identifies at least one suitable heating system 
    when budget is unlimited.
    """
    
    houseowner.hs_budget = float("inf")
    houseowner.income = float("inf")
    houseowner.risk_tolerance = 1.0 
    houseowner.uncertainty_factor = 0.5
    houseowner.infeasible = []

    houseowner.known_hs = [
        heating_system_gas,
        heating_system_oil,
        heating_system_heat_pump,
    ]

    houseowner.define_choice()

    # by current maximum standard all heating systems are suitable
    # taking into account that parameters of different heating systems can be changed and
    # set randomly
    assert len(houseowner.suitable_hs) > 0


def test_define_choice_when_infeasible(
    houseowner, heating_system_gas, heating_system_oil, heating_system_heat_pump
):
    """
    Tests that no suitable heating systems are chosen 
    if all known systems are marked as infeasible.
    """
    
    houseowner.known_hs = [
        heating_system_gas,
        heating_system_oil,
        heating_system_heat_pump,
    ]
    houseowner.suitable_hs = []
    houseowner.infeasible = [
        "Heating_system_heat_pump",
        "Heating_system_gas",
        "Heating_system_oil",
    ]
    houseowner.define_choice()

    # each heating system is infeasible
    assert houseowner.suitable_hs == []


def test_calculate_social_norm(houseowner, heating_system_gas):
    """
    Tests that the calculated social norm for a heating system 
    is a valid value between 0 and 1.
    """
    
    heating_system_gas.neighbours_opinions = {
        successor: random.uniform(0, 1) for successor in houseowner.model.grid.get_cell_list_contents(
            list(houseowner.model.grid.G.successors(houseowner.unique_id)))
    }

    houseowner.calculate_social_norm(heating_system_gas)

    assert heating_system_gas.social_norm >= 0
    assert heating_system_gas.social_norm <= 1


def test_calculate_social_norm_no_opinions(houseowner, heating_system_gas):
    """
    Tests that the social norm is 0 when there are no neighbours' opinions available.
    """
    
    heating_system_gas.neighbours_opinions = {
        successor: None for successor in houseowner.model.grid.get_cell_list_contents(
            list(houseowner.model.grid.G.successors(houseowner.unique_id)))
    }

    houseowner.neighbours_systems = {}
    houseowner.calculate_social_norm(heating_system_gas)

    assert heating_system_gas.social_norm == 0


def test_calculate_PBC(houseowner, heating_system_heat_pump):
    """
    Tests that the Perceived Behavioural Control (PBC) 
    is calculated as a value between 0 and 1.
    """
    
    houseowner.calculate_PBC(heating_system_heat_pump)

    assert heating_system_heat_pump.behavioural_control >= 0
    assert heating_system_heat_pump.behavioural_control <= 1


def test_calculate_integral_rating(
    houseowner, heating_system_gas, heating_system_heat_pump
):
    """
    Tests that the final integral rating of suitable heating systems 
    falls within the expected range.
    """
    
    heating_system_gas.rating = random.uniform(0, 1)
    heating_system_heat_pump.rating = random.uniform(0, 1)
    heating_system_gas.neighbours_opinions = {
        "Houseowner 65": random.uniform(0, 1),
        "Houseowner 182": random.uniform(0, 1),
        "Houseowner 97": None,
        "Houseowner 96": random.uniform(0, 1),
    }
    heating_system_heat_pump.neighbours_opinions = {"Plumber 23": random.uniform(0, 1)}

    houseowner.suitable_hs = [heating_system_gas, heating_system_heat_pump]

    system_rating = houseowner.calculate_integral_rating()

    for system in system_rating:
        assert system.rating >= 0
        assert system.rating <= 3


def test_compare_hs(houseowner, heating_system_heat_pump, heating_system_gas):
    """
    Tests that the houseowner selects a desired heating system 
    after comparing suitable options.
    """
    
    heating_system_gas.rating = random.uniform(0, 1)
    heating_system_heat_pump.rating = random.uniform(0, 1)
    heating_system_gas.neighbours_opinions = {
        "Houseowner 65": random.uniform(0, 1),
        "Houseowner 182": random.uniform(0, 1),
        "Houseowner 97": None,
        "Houseowner 96": random.uniform(0, 1),
    }
    heating_system_heat_pump.neighbours_opinions = {"Plumber 23": random.uniform(0, 1)}

    houseowner.suitable_hs = [heating_system_heat_pump, heating_system_gas]

    houseowner.compare_hs()

    assert houseowner.desired_hs != None


def test_compare_hs_quitting(houseowner):
    """
    Tests that the houseowner quits the decision process 
    if no suitable heating systems are found.
    """
    
    houseowner.suitable_hs = None
    houseowner.compare_hs()

    # housewner has no good option and he quits
    assert houseowner.current_stage == "None"


def test_install_no_money(houseowner, plumber, heating_system_heat_pump):
    """
    Tests that the installation process is halted if the houseowner lacks the budget.
    """
    
    houseowner.hs_budget = 0
    houseowner.plumber = plumber
    houseowner.desired_hs = heating_system_heat_pump

    houseowner.install()

    assert houseowner.consultation_ordered == False
    assert houseowner.installation_ordered == False


def test_install(houseowner, plumber, heating_system_heat_pump):
    """
    Tests that a plumber is correctly ordered when the houseowner decides 
    to install a heating system.
    """
    
    houseowner.hs_budget = float("inf")
    houseowner.plumber = plumber
    houseowner.desired_hs = heating_system_heat_pump

    houseowner.install()

    assert plumber.Services[0].job_queue[0].customer == houseowner


def test_install_return_to_compare_hs(
    houseowner, plumber, heating_system_heat_pump, heating_system_gas
):
    """
    Tests that the houseowner re-evaluates choices 
    if their first desired system is found to be infeasible.
    """
    
    houseowner.hs_budget = float("inf")
    houseowner.plumber = plumber
    plumber.Services[0].job_queue.clear()
    houseowner.desired_hs = heating_system_heat_pump
    houseowner.infeasible = ["Heating_system_heat_pump"]

    # Setup for the alternative system (Gas)
    heating_system_gas.rating = random.uniform(0, 1)
    heating_system_gas.neighbours_opinions = {
        "Houseowner 65": random.uniform(0, 1),
        # ... other opinions ...
    }
    
    heating_system_heat_pump.rating = random.uniform(0, 1)
    heating_system_heat_pump.neighbours_opinions = {"Plumber 23": random.uniform(0, 1)}

    houseowner.suitable_hs = [heating_system_heat_pump, heating_system_gas]

    # 1. First Install Attempt (Fails)
    houseowner.install()

    # Verify the infeasible option was dropped and desired_hs reset
    assert houseowner.suitable_hs == [heating_system_gas]
    assert houseowner.desired_hs == "No"

    # 2. INTERMEDIATE STEP: Select the new system
    # We must replenish cognitive resources because install() consumed them.
    houseowner.cognitive_resource = houseowner.initial_cognitive_resource
    houseowner.compare_hs()
    
    # 3. Verify a new system was chosen (Gas)
    assert type(houseowner.desired_hs) == type(heating_system_gas)

    # 4. Second Install Attempt (Succeeds)
    houseowner.install()
    
    # Check first service's (consultation) job queue list:
    assert plumber.Services[0].job_queue[0].customer == houseowner


def test_system_has_been_installed(houseowner, heating_system_heat_pump):
    """
    Tests that the houseowner's state progresses after a successful installation.
    """
    
    houseowner.desired_hs = heating_system_heat_pump
    houseowner.house.current_heating = heating_system_heat_pump
    houseowner.house.current_heating.age = 0

    houseowner.install()

    # proceed to next stage
    assert houseowner.current_breakpoint == "Implementation"


def test_calculate_dissatisfaction(
    houseowner, heating_system_heat_pump, heating_system_gas, heating_system_oil
):
    """
    Tests that the houseowner becomes dissatisfied when their current system is
    significantly worse than other known options.

    Notes
    -----
    The test depends on default parameter settings and is therefore not
    reliable.
    """
    # length of params for heating system will be maximum rating value
    heating_system_gas.rating = len(heating_system_heat_pump.params)
    heating_system_oil.rating = len(heating_system_heat_pump.params)
    heating_system_heat_pump.rating = 0
    
    heating_system_gas.params["price"][0] = 1
    heating_system_oil.params["price"][0] = 1 
    heating_system_heat_pump.params["price"][0] = 99999
    
    heating_system_gas.params["fuel_cost"][0] = 1
    heating_system_oil.params["fuel_cost"][0] = 1 
    heating_system_heat_pump.params["fuel_cost"][0] = 99999
    
    houseowner.desired_hs = heating_system_heat_pump
    houseowner.house.current_heating = heating_system_heat_pump

    houseowner.suitable_hs = [
        heating_system_heat_pump,
        heating_system_gas,
        heating_system_oil,
    ]
    houseowner.known_hs = [
        heating_system_heat_pump,
        heating_system_gas,
        heating_system_oil,
    ]

    houseowner.calculate_satisfaction()

    # houseowner will be always dissatisfied
    # because other current systems has a maximum possible rating
    assert houseowner.satisfaction == "Dissatisfied"


def test_calculate_satisfaction(houseowner, heating_system_heat_pump):
    """
    Tests that the houseowner is satisfied when their current system 
    is the only known/suitable option.
    """
    
    houseowner.desired_hs = heating_system_heat_pump
    houseowner.house.current_heating = heating_system_heat_pump

    houseowner.suitable_hs = [heating_system_heat_pump]
    houseowner.known_hs = [heating_system_heat_pump]

    houseowner.calculate_satisfaction()

    # houseowner will be always satisfied
    # because he has only one suitable heating system
    assert houseowner.satisfaction == "Satisfied"


# TODO uncomment after mileu implementation wil be added to main branch

# def test_step_neighbour_jealousy(houseowner, neighbour, house, heating_system_gas, heating_system_oil, trigger_neighbour_jealousy, trigger_none):
#     neighbour.satisfaction = "Satisfied"

#     neighbour.house.current_heating = heating_system_gas
#     houseowner.house.current_heating = heating_system_oil

#     house.houseowner = neighbour

#     houseowner.model.space.add_agents(house)

#     # houseowner has new installed heating system
#     # therefore triggers like "Trigger_breakdown", "Trigger_lifetime" will not append to the active_trigger list
#     houseowner.house.current_heating.age = 0

#     houseowner.step()

#     assert type(houseowner.active_trigger).__name__ == type(trigger_neighbour_jealousy).__name__

#     neighbour.satisfaction = "Dissatisfied"

#     houseowner.step()

#     assert type(houseowner.active_trigger).__name__ == type(trigger_none).__name__


def test_step_breakdown(houseowner, trigger_none):
    """
    Tests that a heating system breakdown correctly 
    triggers the goal-setting breakpoint.
    """

    # will force houseowner be triggered by breakdown
    # and it should switch his breakpoint to "goal"
    houseowner.house.current_heating.breakdown = True

    houseowner.step()

    assert houseowner.current_breakpoint == "Goal"
    assert houseowner.consultation_ordered == True
    # active trigger should be set to None
    assert type(houseowner.active_trigger).__name__ == type(trigger_none).__name__


def test_step_lifetime(houseowner, trigger_none):
    """
    Tests that an expired heating system lifetime 
    correctly triggers the goal-setting breakpoint.
    """
    # will force houseowner be triggered by lifetime
    # and it should switch his breakpoint to "goal"
    houseowner.house.current_heating.lifetime = 0

    houseowner.step()

    assert houseowner.current_breakpoint == "Goal"
    # active trigger should be set to None
    assert type(houseowner.active_trigger).__name__ == type(trigger_none).__name__

