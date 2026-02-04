********
ODD
********
.. toctree::
   :maxdepth: 3

This section follows the ODD (Overview/Design principles/Details) protocol. See [1] for a motivation and further information.

[1]  Grimm, Volker, Railsback, Steven F., Vincenot, Christian E., Berger, Uta, Gallagher, Cara, DeAngelis, Donald L., Edmonds, Bruce, 
Ge, Jiaqi, Giske, Jarl, Groeneveld, Jürgen, Johnston, Alice S.A., Milles, Alexander, Nabe-Nielsen, Jacob, Polhill, J. Gareth,
Radchuk, Viktoriia, Rohwäder, Marie-Sophie, Stillman, Richard A., Thiele, Jan C. and Ayllón, Daniel (2020)
'The ODD Protocol for Describing Agent-Based and Other Simulation Models: A Second Update to Improve Clarity, Replication, and 
Structural Realism'. Journal of Artificial Societies and Social Simulation 23 (2) 7
http://jasss.soc.surrey.ac.uk/23/2/7.html. doi: 10.18564/jasss.4259
		

Overview
========

Purpose
-------

The purpose of the AHOIS (Agent-based Homeowner decisions on Heating System replacement) model is to simulate the decision-making processes of homeowners when replacing residential heating systems. The primary goal is to understand how the aggregation of these individual choices influences broader, system-wide outcomes such as technology diffusion rates, overall energy demand, and carbon emissions over time.

To achieve this, the model investigates how homeowner decisions are driven by a combination of factors:

* Personal financial situations, risk perceptions, and individual preferences of homeowners.
* External stimuli such as policy interventions, available information and infrastructure.
* Social networks and peer influence.

AHOIS serves as a virtual laboratory to explore the effects of different scenarios. It is designed to assess the effectiveness of various policy interventions and communication strategies aimed at accelerating the transition towards sustainable residential heating systems.

Entities, state variables, scales
---------------------------------

.. csv-table:: Building
    :file: odd/AHOI_ODD_StateVariables.csv
    :quote: "
    :header-rows: 1
    :stub-columns: 1
    :align: left
    :widths: 10, 15, 15, 10, 25, 25
    :width: 100%


Process Overview and Scheduling
-------------------------------

Main processes
^^^^^^^^^^^^^^

* **Triggers.** Houseowners may experience triggers, such as system breakdowns or neighbour influence, prompting them to initiate the decision-making process.

* **Houseowner decision-making.** Houseowners follow a multi-stage decision-making process regarding their heating systems.

  At the beginning of the simulation every agent is at the stage 0, i.e. is not participating in any decision-making.

  If they are triggered, they enter the stage 1 of the decision-making - evaluation. During evaluation, houseowners evaluate their satisfaction with their current heating system. If they are satisfied, no further actions are taken.

  If dissatisfied, they enter stage 2 - data gathering and choice. This stage includes three subsequent actions:
  
 * **data gathering** adds more options to their knowledge

 * **filtering** formulates a list of subjectively suitable options according to feasibility, affordability and riskiness
 
 * **comparison** allows to choose the desired system via attribute-wise comparison.


  If houseowners are not overwhelmed by options and have at least one suitable system that they desire, they proceed to stage 3 - planning and installation. They schedule a consultation with a plumber about the installation of the chosen systems. The rest of this stage is performed by the plumber. The installation may fail for different reasons, and then the houseowners try to choose an alternative or leaves the decision-making.

  If the desired system is installed, the houseonwers enter the last stage - assessment. They compare the actual performance of their new HS and check, whether the system is still the best among those known to them. If it is, they become satisfied, if not - they become dissatisfied. Satisfaction defines whether houseowners would try to propagate their decision to other houseowners, in case this system type is relatively new to the district.

* **Intermediary consultation.** Plumbers can advise Houseowners on two matters.

 * First, plumbers offer consultations regarding the available heating systems, their characteristics, and subsidies. They can recommend heating systems. Their consultations are based on averaged values for attributes, and recommendations consider their own preferences.
 
 * Second, they evaluate the feasibility of installation of the desired heating systems and the final installation price. If the systems are not feasible or the final installation costs more than the Houseowners can afford, the Houseowners are forced to reconsider.

  Energy advisors provide one type of consultations - about heating system options and subsidies, but their consultations are tailored to the characteristics of the houses and preferences of Houseowners, i.e. they are much more precise. They make recommendations, but also define the list of suitable options for Houseowners such that they do not have to do it on their own.

* **Heating system installation.** Houseowners order an installation of the desired heating system from their plumber. The plumber generate new instances of the desired heating and replace the existing system in the houses with the newly generated ones. After that they subtract the installation price from the budget of the Houseowners, and adjust their weekly expences according to the attributes of the new heating system.

* **Houseonwer interactions.** Houseowners interact with each other either when they are not in the decision-making, or when they are gathering information. Both types of interactions lead to information and opinion exchange. The difference is the amount of contacts - for the former it is one contact per week maximum, for the latter it depends on the cognitive resources of Houseowners.

* **Scenario-defined impacts.** Scenarios may have specific impacts affecting the entire model or only some agents. Several examples: 
 
 * Information campaign that spreads knowledge about systems among agents;
 
 * Changes in availability of heating technologies
 
 * Energy price increase.

Scheduling
^^^^^^^^^^

* The time is discrete, each step represents one week in real life.
* State variables can be separated into two groups - those that are updated at the beginning of the step, and those that are updated during the step.
* Actions on fixed schedule - scenario and model related actions, i.e. updates in model-level variables, global events that represent changes in the environment. These update state variables at the beginning of the step.
* Actions on random schedule - agents' actions, i.e. agents being activated randomly represent real-life uncertainty and simultaneity of human actions. These update state variables during the step. The exact time depends on the order of actions of agents at that step.
* Each step starts with the model updating global variables (HS and subsidies availability, heat delivery contract terms, emissions from HS, energy prices). Then scenario-defined impacts happen. After that agents are activated. The RandomActivationByType scheduler divides the agents into groups (e.g., houseowners, plumbers, energy advisors) and activates them in a random order within their group during each time step. The order of activation for groups is - Houseowners, Plumbers, Energy Advisors. Then the model collects data.

The simulation ends when the amount of steps reaches a pre-defined threshold.


Design Concepts
===============


Basic Principles
----------------

* **Bamberg's stage model of self-regulated behavioural change.**
  The model frames the decision-making of Houseowners. The process consists of four stages. Each stage has its unique aims, sub-processes and conditions of transfer to other stages or of abandoning the decision-making entirely. Houseowners start at the stage 1 after they encounter a trigger, and then try to sequentially move to the next stages. However, it is possible for them to go backwards or leave the decision-making entirely. The outcome depends on the events happening during the decision-making.

  1. **Stage 1 (predecisional)** aims to define whether Houseowners are still satisfied with their current heating system.
  2. **Stage 2 (preactional)** is dedicated to the data gathering, option filtering and the choice of a single desired option.
  3. **Stage 3 (actional)** revolves around the planning and installation of the desired heating system.
  4. **Stage 4 (postactional)** has a goal to evaluate satisfaction with the newly installed system and propagate its technology among peers.

* **Triggers.**
  Decision-making is triggered by events with different requirements to occur.

* **Ajzen’s Theory of Planned Behaviour.**
  The three factors of the Theory of Planned Behaviour are used by agents to evaluate options and make a choice.

  * **Attitude** corresponds to the individual preferences of agents tied to the characteristics of heating systems.
  * **Subjective norm** corresponds to the opinions of contacted agents about heting systems and the popularity of a certain heating technology among houseowners.
  * **Perceived behavioural control** corresponds to the perceptions of financial burden laid by the installation and maintenance of each option.
  
  The theory is integrated into the second stage of Bamberg's SSRB to represent reasoning behind the system evaluations.

* **Sinus Milieus.**
  Each Houseowner has one of the four lifestyles attached to it (so called Sinus Milieus) - Leading, Mainstream, Traditionals, Hedonists. The Milieus define all socio-economic and psychological variables of Houseowners; the structure of the network, to which they belong; and some of their behaviour during the decision-making.

* **Social networks and neighbourhood.**
  Each Houseowner is a part of a social network that consists of its immediate geographic neighbours and of Houseowners with the same lifestyle regardless of their location. The network links can be uni- and bi-directional. The character of the link is defined by the milieus of the linked agents. The links define the direction of information exchange between agents during agent interactions.

* **Social influence.**
  Houseowners' decisions are affected by the information they know from and about their neighbours. They store information about the opinions of their neighbours about different heating systems, about the systems installed into their neighbours' houses, and whether their neighbours are satisfied with their current heating system. This information affects the decision-making during the information gathering, filtering and choice. Social interaction can also cause triggers - when one agent finds out that their interlocutor has installed a new heating or when one agent decides to propagate a newly obtained technology among its peers.

* **Cognitive effort.**
  Each Houseowner has a limited stock of abstract cognitive resource for each step, which they must spend on actions during decision-making. The stock size depends on the milieu group	. The action cost depends on the action.

* **Imperfect information.**
  Houseowners do not posess precise values of heating systems' characteristics. They have expected values formed by informations sources (Internet shifts values, neighbours share their knowledge, plumbers share averaged values). These values have uncertainty boundaries, which are defined and changed during data gathering, information exchange and installation. Moreover, Houseowners have to contact other Houseowners in order to obtain information about their installed heating systems, how satisfied they are with them, and also their opinions about all known heating systems. This knowledge is only updated if the same Houseowners are contacted again.
  
  Plumbers also posess imperfect information, but theirs cannot be changed. Its imperfection is represented via averaged values of heating systems' characteristics to represent broader expertise, with lack of tailored consultation. The only characteristic that they always know precisely tailored to the installation case is the installation price.
  
  Energy Advisors are the only agents that always have perfect knowledge tailored to the specific consultation case.

* **Bounded rationality.**
  Houweowners cannot have and analyse all the knowledge to make the best possible decision. They are intended to choose the best system to their estimation, but this estimation is limited by incomplete and distorted knowledge, limited cognitive resource, aspiration, cognitive overload, risk tolerance, and decision fatigue.

* **Satisficing, cognitive overload and decision fatigue.**
  These concepts represent the obstacles related to the information search and the choice. Houseowners try to gather information untill they either reach the aspiration level or the overload threshold. The aspiration level is reached when they find options during the information search that are better than their current heating systems. The overload happens when the Houseowners find systems that are the same or worse according to their estimations than their current heating systems. Each such system adds to the overload level. When a certain level is reached, they drop the decision-making.
  
  The decision fatigue happens when Houseowners have to choose among two systems that are too similar according to their estimations. When this happens, they have to spend additional cognitive resource on the choice, and the nest system will be defined randomly among these two.

* **Risk tolerance.**
  Each Houseonwer has its unique value of risk tolerance, which they use to filter out options before they make the final choice.

* **Budget constraints and loans.**
  Each Houseonwer has its unique budget, which is defined by a certain amount of their weekly net income. They consider their budget during decision-making and filter out options that are not affordable before making the choice. They can take loans to cover the difference between the budget and the price of installation. Depending on their milieu group, some Houseowners are loan avoidant and do not take loans if not absolutely necessary (e.g. the current heating is broken).

* **Relative agreement.**
  The knowledge exchange is implemented as an adaptation of the Relative Agreement algorithm. Houseowners posess knowledge about heating system characteristics with uncertainty ranges attached. Whenever two Houseowners interact and both have their own knowledge about the same heating technology, this two piece of knowledge interact. Depending on the distance between values of the same characteristic and the uncertainty range, each piece of knowledge may change.

* **Priority of empirical grounding.**
  For each model variable and parameter, there was an effort to find a representation in empirical literature, own surveys, workshops or technical data. For those without such justification, values were defined based on theories or sensitivity analysis. For each variable, there is a note stating the validation source.


Emergence
---------

Emergent phenomena arise from the individual decisions and interactions of houseowners, plumbers, and energy advisors within the model.

* The adoption pattern of different heating systems within the population emerge as a result of individual decisions of Houseowners.
* The interactions between houseowners contribute to emergent localised clusters of heating systems. If a houseowner observes a neighbour adopting a new heating system, this may trigger social pressure, motivating other houseowners to consider replacement.
* Over time, the model may show the emergence of technology lock-in, where certain heating systems dominate the market due to early adoption patterns, social influence, or economic incentives. This can lead to market saturation, where alternative technologies struggle to gain traction even if they offer superior performance.


Adaptation
----------

Adaptation refers to how agents modify their behaviour and decision-making processes in response to changes in their environment, internal states, or interactions with other agents.

* **Houseowner Adaptation.**
  Houseowners adapt their decision-making based on several factors. External triggers cause houseowners to reassess their situation and adapt their behaviour by speeding up or delaying their decision-making.

  * Houseowners adapt to new information they receive. Their perception of heating systems evolves as they gather more data, which influences their choice of suitable and desired systems.
  * Houseowners adapt their actions based on their cognitive resources, which limit the number of decisions they can make in each time step.
  * Houseowners learn from their neighbours’ experiences and opinions. Through interactions with nearby houseowners, they gather information about the performance and satisfaction associated with different heating systems.

* **Plumber Adaptation.**
  Plumbers adapt their knowledge base over time, learning about new heating systems through training. They expand their service offerings as they acquire expertise in installing and consulting on new heating technologies.

* **Energy Advisor Adaptation.**
  Based on houseowner preferences and financial situations, energy advisors adapt their recommendations to align with the suitability and feasibility of different heating systems.


Objectives
----------

* Houseowner Objectives:
   * The primary objective of houseowners is to ensure that their heating system satisfies them. When houseowners become dissatisfied, their objective shifts toward identifying and installing a satisfactory replacement system.
   * Houseowners aim to stay under their financial constraints. This involves seeking systems that are within their budget, considering subsidies or loans.
   * Houseowners differ in their degree of risks aversion. They may filter out systems they deem to risky during options consideration.
   * Houseowners prioritize systems that have the best score according to their preferences. 
   * Houseowners consider the opinions and decisions of their social peers.


* Plumber Objectives:
   * Plumbers aim to provide consultation and installation services to houseowners.  Their objective is to successfully complete consultations and installations within the constraints of their workload.
   * Plumbers seek to expand their knowledge of different heating systems through training, enabling them to offer a wider range of services.

* Energy Advisor Objectives:
   * Energy advisors aim to recommend heating systems that align with houseowners' preferences, budgets, and the latest available subsidies. 
   * Energy advisors seek to share their expertise on heating systems. Their objective is to help houseowners understand the long-term advantages of different systems.


Learning
--------

There is no learning in AHOIS at the moment.


Prediction
----------

Agents make decisions based on limited information and cognitive resources, which means their ability to predict future outcomes is constrained. 

* Agents attempt to predict the long-term financial impacts of their heating system choices. When evaluating different systems, they estimate future operational expenses and potential savings from more energy-efficient technologies. These predictions are based on information provided by information sources, though they are subject to imperfect information.


Sensing
-------

The information agents can sense or perceive is limited by their cognitive capacities and the availability of information sources.

* Houseowner Sensing:

  * Houseowners are aware of their neighbours within their social network.
  * Houseowners are fully aware of the attributes of their current heating system.
  * Houseowners have complete information about their own income and budget.
  * Houseowners can sense external triggers, such as heating system breakdowns or price shocks.
  * Houseowners can sense and gather information from various information sources. This includes the technical feasibility of installing different heating systems, system characteristics, and the availability of subsidies. The amount of this sensed information is limited by the houseowner's cognitive resources and the extent of the advice they seek.
  * Houseowners can sense the heating systems adopted by their social network partners through social interactions. They can also observe their neighbours' satisfaction with these systems, their opinion about them.

* Plumber Sensing:

  * Plumbers are aware of the technical feasibility of installing various heating systems in different house types. 
  * Plumbers sense their current workload, including the length of their consultation and installation queues.

* Energy Advisor Sensing:

  * Energy advisors are fully aware of the current financial incentives available for different heating systems. 
  * Energy advisors can sense the financial constraints and preferences of houseowners during consultations. This information enables them to recommend systems that align with houseowner budgets while maximizing potential cost savings through subsidies.
  * Energy advisors are aware of the technical specifications and performance of different heating systems, allowing them to evaluate which systems are most suitable for houseowners based the properties of their houses.


Interaction
-----------

Agents interact through consultations and service provisions, and through social influence and information exchange.

1.	Houseowner-Plumber Interaction:
   * Houseowners interact with plumbers through consultations. When a houseowner requires advice on replacing their heating system, they can consult a plumber.  During the consultation, the plumber provides information about available heating systems,  assesses the technical feasibility of installing specific systems, and offers recommendations based on their general experience.
   * Once a houseowner decides on a heating system, plumbers provide installation services. The interaction involves scheduling the installation, and completing the work.  Plumbers manage their workload and can interact with multiple houseowners simultaneously, prioritizing installations based on their queues.
2.	Houseowner-Energy Advisor Interaction:
   * Houseowners consult energy advisors to learn about available subsidies and financial incentives for heating system replacements. Energy advisors provide advice on which systems qualify for subsidies. 
   * Energy advisors share their knowledge of system performance, energy efficiency, and environmental benefits with houseowners. 
3.	Houseowner-Houseowner Interaction:
   * Houseowners interact socially with their neighbours, exchanging opinions, satisfaction and knowledge regarding heating systems. 
4.	Houseowner-Environment Interaction:
   * Houseowners interact with their environment through external triggers, such as heating system breakdowns or price shocks. 


Stochasticity
-------------


Stochasticity is incorporated into various aspects of model initialization, agent behaviour, interactions, 
and environmental events to simulate the unpredictable nature of human choices, external triggers, and market conditions. 
There are two main stochastic parts in the model – one related to the model initialisation, 
and the one related to the processes happening during a model run.

.. excel-table::
	:file: concepts/AHOISpro_RandomProcesses.xlsx
	:colwidths: 20, 20, 30, 30
	:row_header: true
	:col_header: true

Collectives
-----------

Each Houseowner is a part of its own social network.


Initialisation
==============

Model Initialisation
--------------------
* The model initialises the spatial environment by reading a geoJSON file that contains geospatial data about the houses. 
* Houses are created using the MESA-GEO framework's AgentCreator tool, which generates house agents from the geospatial data. 
* Each house is assigned geospatial coordinates, along with attributes of area, year of construction, energy demand, Milieu code, heat load. 
* Each house is assigned to a specific milieu group, using a mapping function based on Milieu codes. 
* The model distributes different heating systems among the houses based on a probabilistic approach. Each house is assigned a heating system according to a custom distribution defined by the model’s parameters.
* For each house, the model initialises a Houseowner agent.
* After all Houseowners are initialised, they are added to the social network. Their network connections depend on the spatial proximity and milieus.
* The model initialises the intermediaries - Plumbers and Energy Advisors.
* The model initialises the selected scenario and performs its set-up.
* The model’s DataCollector is initialised to track key metrics throughout the simulation.


Houseowners Initialisation
--------------------------
* Each agent is initialised with a unique set of state variables that define its identity, socio-demographic context,  psychological profile, and initial state within the decision-making process.
* Each agent is assigned a unique_id and linked to a specific house object, which provides its geographical geometry and coordinate reference system (crs). The latter are used by the network generator. 
* A crucial part of the agent's identity is its milieu group, a composite object that encapsulates a cluster of socio-psychological attributes,  including income, preferences and behavioral tendencies based on empirical data. The following is derived form the milieu group:
   * Preferences: heating system preferences (the importance placed on attributes like cost, environmental impact, etc.) and information source preferences (preferability of different information sources) are derived directly from the agent's assigned milieu.
   * Cognitive Resources: each agent starts with an initial_cognitive_resource, representing the mental effort available for decision-making tasks, an aspiration_value, which sets the threshold for how much information is needed to feel satisfied, and an overload_value, which defines maximum information overload.
   * Behavioral Theories: Weights for the Theory of Planned Behavior (tpb_weights)  and exposure levels for the Relative Agreement model (ra_exposure) are also initialized from the milieu.
   * Perceptions: The perceived_uncertainty associated with different heating technologies is initialized to a set of fixed, default values for all agents.
* Agents can be initialized at different points in their decision-making.  The current_stage and current_breakpoint are set to "Stage 0" and "None" by default. 
* The agent’s knowledge base, including known_hs (known heating systems), suitable_hs (systems considered acceptable), and a desired_hs (the single desired system) can be initialised from an empty list or with pre-existing knowledge depending on the model setup.
* All other state variables are initialized to a neutral or "zero" state.  Lists tracking interactions (e.g., visited_neighbours, unqualified_plumbers) are empty.  Boolean flags indicating process steps (e.g., consultation_ordered, installation_ordered) are set to False. Counters like waiting time and stage_counter are set to 0.
* Agent data collection attributes are set up last.


Plumbers Initialisation
-----------------------
* Each Plumber agent is initialized as a non-spatial intermediary with a distinct knowledge base, service capacity, and job management system.
* Each agent is assigned a unique_id and is registered with the main model instance.
* Their knowledge base is initialized with a list of known_hs (heating systems) and known_subsidies.
* Upon creation, the Plumber immediately performs two key actions to establish their baseline knowledge:
   * They calculate the performance attributes for each known system based on a standardized "average house" configuration to formulate their general expertise.
   * They evaluate all known_hs against their personal heating_preferences to form an initial professional opinion on each system.
* The Plumber's operational capacity is set. Consultation_power and installation_power define how many tasks they can process per step.  Their job management system (active_jobs, completed_jobs, max_concurrent_jobs) is initialized to a neutral state, ready to accept work from Houseowners.
* Key functionalities are established by creating ConsultationService and InstallationService objects, which manage the agent's interaction queues.
* Other attributes are inherited from a parent class. These are not used in the Plumber's logic but are included for compatibility with the model's data collector.


Energy Advisors Initialisation
------------------------------
* Each EnergyAdvisor agent is initialized as a non-spatial intermediary focused on providing expert information to Houseowners.
* Each agent is assigned a unique_id and registered with the main model instance.
* The agent's knowledge base is its primary attribute and is defined at creation. This includes:
	* A comprehensive list of known_hs (heating systems) and known_subsidies (financial incentives).
	* A set of heating_preferences used to evaluate and compare different technologies from an expert standpoint.
* Immediately upon initialization, the agent processes its list of subsidies using an _organize_subsidies function.  This creates a structured dictionary that maps each known heating system to all of its applicable subsidies, allowing for rapid information retrieval during consultations.
* The agent's core function is established by creating a ConsultationServiceEnergyAdvisor object, which manages its queue of consultation requests from Houseowners.
* Other attributes are inherited from a parent class. These are not used in the Energy Advisors's logic but are included for compatibility with the model's data collector.


Input Data
==========

The model relies on various external data inputs to initialize agents, houses, and the environment. 
These data sources provide the parameters necessary for agent decision-making, heating system evaluation, 
and the simulation of social dynamics and energy use.


.. csv-table:: Inputs
    :file: odd/AHOI_ODD_Inputs.csv
    :header-rows: 1
    :stub-columns: 1
    :align: left
    :widths: 20, 15, 20, 30, 15
    :width: 100%


Submodels
=========

Scenarios
---------
A Scenario is a set of additional rules applied to the default model state. These rules are separated into 3 groups:

* Target state defines the desired heating technologies and their market shares (e.g. 100% of heat pumps). These are used to analyse the achievement of the district planning goal.
* Rules altering the initial set-up. For example, they might change knowledge distribution or available subsidies.
* Rules that change the model state during the runs. For example, it might define an information campaign during a run.

A Scenario might contain only some of the rules, i.e. only alter the set-up.

Houseowner decision-making
--------------------------
This submodel describes the core behavioral logic of the :py:class:`agents.Houseowner.Houseowner` agent. It follows a structured, multi-stage process for evaluating, choosing, and installing a new heating system. An agent can be in one of two primary modes: an "inactive" state characterized by passive social interaction, or an "active" decision-making state. The transition between stages in the active state is governed by the agent's ``cognitive_resource`` and a series of breakpoints that mark the completion of key milestones.
The entire active decision-making process occurs within a loop that persists as long as the agent has ``cognitive_resource`` remaining for the current time step. This means an agent can progress through multiple stages or actions in a single step if the tasks are not cognitively demanding. If resources are depleted, the process is paused at its current breakpoint and will resume in the next time step.

Stage 0: Inactive State
^^^^^^^^^^^^^^^^^^^^^^^

This is the default state for agents who are not actively considering a change to their heating system.

* **Condition for State:** An agent is in this state if its ``current_stage`` is "None", which occurs either at the start of the simulation or after successfully completing (or abandoning) the full decision-making cycle.
* **Behavior:** Instead of evaluating their heating system, agents in the inactive state may engage in social behavior. With a 57% probability each time step, the agent will initiate a meeting with another agent (:py:mod:`agents.Houseowner.Houseowner.meet_agent`) to exchange information and opinions. Otherwise, the agent takes no action.

Stage 1: Predecisional
^^^^^^^^^^^^^^^^^^^^^^

This is the entry point into the active decision-making process, where the agent assesses its current situation.

* **Trigger:** An agent is triggered to enter Stage 1, typically by external factors or internal dissatisfaction accumulating over time. In the model, this is represented by the agent having a ``current_stage`` but its ``current_breakpoint`` being "None".
* **Action:** The agent executes the ``evaluate()`` submodel (see :ref:`application/odd:Heating system evaluation`). This involves assessing its ``satisfaction`` with its current heating system based on various performance and cost metrics.
* **Outcomes:**
    * **Satisfied:** If the evaluation results in a "Satisfied" state, the decision-making process terminates immediately. The agent expends the cognitive resource for the evaluation but takes no further action, returning to the inactive state.
    * **Dissatisfied:** If the agent is dissatisfied, it forms the intention to change its situation. The model sets the ``current_breakpoint`` to "Goal", advancing the agent to the next stage.

Stage 2: Preactional
^^^^^^^^^^^^^^^^^^^^

Triggered by dissatisfaction, this stage involves a sequence of information processing and deliberation to select a preferred heating system.

* **Trigger:** The agent's ``current_breakpoint`` is "Goal".
* **Actions:** The agent performs a series of three distinct sub-processes, conditional on having sufficient ``cognitive_resource`` to proceed from one to the next:
    1. **Data Gathering (``get_data()``):** The agent actively seeks information to learn about new heating system options and update its knowledge on existing ones. This can involve consulting intermediaries or interacting with peers.
    2. **Choice Set Formulation (``define_choice()``):** The agent filters its expanded list of ``known_hs`` to produce a smaller, more manageable ``suitable_hs`` list. This filtering is based on personal criteria for technical feasibility, affordability (with and without loans), and risk tolerance.
    3. **Comparison and Selection (``compare_hs()``):** The agent performs a detailed comparison of the options within its ``suitable_hs`` list. If this comparison yields a clear winner, that system is chosen as the ``desired_hs``.
* **Outcomes:**
    * **Success:** If the agent successfully identifies a ``desired_hs`` and still has cognitive resources, its ``current_breakpoint`` is set to "Behaviour", advancing it to Stage 3.
    * **Failure or Pause:** If the agent runs out of cognitive resources, the process pauses and will resume from the same point in the next time step. If the process fails (e.g., no suitable options are found, or no option is clearly superior), the agent may exit the decision cycle and return to the inactive state.

Stage 3: Actional
^^^^^^^^^^^^^^^^^

In this stage, the agent acts on its decision by arranging the installation of its chosen heating system.

* **Trigger:** The agent has a ``desired_hs`` and its ``current_breakpoint`` is "Behaviour".
* **Action:** The agent executes the ``install()`` submodel. This is a complex, multi-step process that involves finding and scheduling a consultation with a qualified ``Plumber``, undergoing final feasibility and affordability checks, and waiting for the installation to be completed. Much of the action in this stage is handled by the ``Plumber`` agent.
* **Outcomes:**
    * **Installation Scheduled:** If the consultation is successful and all checks pass, an installation is queued. The agent enters a waiting period.
    * **Installation Complete:** Once the ``Plumber`` completes the job, the agent's ``current_breakpoint`` is set to "Implementation", advancing it to the final stage.
    * **Failure:** If the installation fails at any point (e.g., the plumber deems it infeasible, the final price is unaffordable), the agent may revert to Stage 2 to select an alternative from its ``suitable_hs`` list, or abandon the process entirely.

Stage 4: Postactional
^^^^^^^^^^^^^^^^^^^^^

After the new system is installed, the agent assesses the outcome of its decision.

* **Trigger:** The new heating system has been installed, and the agent's ``current_breakpoint`` is "Implementation".
* **Action:** The agent executes the ``calculate_satisfaction()`` submodel. This involves comparing the real-world performance and costs of the new system against the expectations the agent had formed during Stage 2.
* **Outcomes:** The agent's ``satisfaction`` attribute is updated to "Satisfied" or "Dissatisfied". This new state influences its willingness to recommend its choice to peers in future social interactions. After this final assessment, the active decision-making cycle is complete, and the agent's ``current_stage`` is reset, returning it to the inactive state (Stage 0).

Houseowner interactions
-----------------------
Houseowners interact in two distinct ways:

* **Passive Interaction:** This occurs when a Houseowner is not actively in the decision-making process. They may randomly choose to contact **one** of the other Houseowners in their network and exchange information.

* **Active Interaction:** This happens during Stage 2 of the decision-making process. If the Houseowner chooses "Neighbours" as their information source, they will contact all neighbours with connections pointing towards them (i.e., incoming links) and perform an information exchange.

The information exchange process consists of the following steps:

1.  **Sharing Knowledge of New Technologies:**
    The contacted neighbour shares information about technologies and their characteristics, but only for those not already known to the asking Houseowner. This information includes the parameter values and their associated uncertainty. The asking Houseowner then stores each new piece of information.

2.  **Updating Knowledge of Known Technologies:**
    For technologies that are familiar to both agents, they perform the relative agreement algorithm to update their mutual understanding. This process is applied to each parameter (e.g., cost, efficiency) of the shared technology.

    The algorithm is detailed below:

    Let the target agent be :math:`i` and the source agent be :math:`j`. For a given parameter of the technology, their knowledge is represented by an opinion (mean value) and an uncertainty (half the width of the confidence interval).

    * Target agent's opinion: :math:`o_i`
    * Target agent's uncertainty: :math:`u_i`
    * Source agent's opinion: :math:`o_j`
    * Source agent's uncertainty: :math:`u_j`

    The update process for the target agent :math:`i` follows these steps:

    a.  **Calculate the Overlap of Uncertainty Intervals:** The model first determines the degree of overlap, :math:`v`, between the uncertainty intervals of the two agents. The uncertainty interval for an agent :math:`k` is defined as :math:`[o_k - u_k, o_k + u_k]`. The overlap is calculated as:

        .. math::
           v = \min(o_i + u_i, o_j + u_j) - \max(o_i - u_i, o_j - u_j)

        If :math:`v \le 0`, there is no overlap, and no opinion exchange occurs.

    b.  **Calculate the Agreement Kernel:** If there is an overlap (:math:`v > 0`), a dimensionless agreement kernel, :math:`h`, is calculated. This kernel represents the degree of agreement, normalized by the source agent's uncertainty. It is defined as the ratio of the overlap length to the total width of the source agent's uncertainty interval (:math:`2u_j`):

        .. math::
           h = \frac{v}{2u_j}

        The value of :math:`h` ranges from 0 (no overlap) to 1.

    c.  **Update Opinion and Uncertainty:** The target agent's opinion and uncertainty are updated based on the agreement kernel :math:`h`, the difference in their initial values, and an ``exposure`` parameter, :math:`\mu`, which acts as a learning rate. The updated values at time :math:`t+1` are:

        .. math::
           o_i(t+1) = o_i(t) + \mu \cdot h \cdot (o_j(t) - o_i(t))
           
           u_i(t+1) = u_i(t) + \mu \cdot h \cdot (u_j(t) - u_i(t))

        This formulation ensures that the agent's opinion and uncertainty shift towards those of the source, with the magnitude of the shift being proportional to their existing agreement. Finally, to ensure numerical stability, the updated values are floored at a small positive number (:math:`1 \times 10^{-6}`).

3.  **Sharing Final Ratings:**
    The contacted neighbour shares its final rating for each heating system it know. The asking Houseowner stores these ratings in a dedicated dictionary, mapping them to the technology's name.

4.  **Sharing Installed System:**
    The neighbour shares the name of its currently installed heating system. The asking Houseowner stores this information, linking the neighbour's unique ID to their installed technology.

5.  **Sharing Satisfaction:**
    Finally, the contacted neighbour shares its satisfaction level with its currently installed system. The asking Houseowner stores this, associating the neighbour's ID and technology type with the satisfaction state.

Triggers
--------

A trigger is a distinct event that happens to a ``Houseowner`` and activates their decision-making process, moving them from an inactive state (Stage 0) into an active evaluation. Different triggers represent different real-world events, have unique conditions to occur, and can have different impacts on the ``Houseowner``'s knowledge and state.

A trigger can only affect an agent who is not already in an active decision-making cycle (i.e., their ``current_stage`` must be "None").

The following triggers are implemented in the model:

* **Blanc (None)**

  * **Description:** A null trigger that has no effect.  
  * **Impact:** It serves as a marker indicating no triggers at a step.
  * **Decision Stage:** The agent remains in the inactive state.

* **Breakdown**

  * **Description:** A critical failure of the agent's current heating system. This is an emergency trigger that forces immediate action.
  * **Impact:** This trigger bypasses the initial evaluation stage.
  * **Decision Stage:** Sends the agent directly to **Stage 2** (Goal Formation and Choice).

* **Lifetime**

  * **Description:** The agent becomes aware that their current heating system is approaching the end of its expected operational lifetime.
  * **Impact:** Prompts a non-urgent re-evaluation of the system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Availability**

  * **Description:** The agent learns that their current heating system technology will soon become unavailable for new installations or repairs, prompting them to consider a replacement before being forced to switch.
  * **Impact:** Creates a sense of urgency to evaluate the current system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Price shock**

  * **Description:** A sudden and significant increase in the price of fuel for the agent's current heating system, representing a major external economic shock.
  * **Impact:** The agent's perceived ``fuel_cost`` for their current system is multiplied by a scenario-defined factor, making it seem much more expensive.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Fuel price**

  * **Description:** Represents a general, non-shock-based awareness of changing or volatile fuel prices, prompting the agent to reconsider their heating costs.
  * **Impact:** Prompts a re-evaluation of the current system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Owner change**

  * **Description:** Represents the re-evaluation of a home's heating system that typically occurs when a new owner moves in.
  * **Impact:** Prompts a standard re-evaluation of the existing system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Neighbour jealousy**

  * **Description:** A social trigger that occurs when an agent observes a neighbour installing a new, potentially superior, heating system.
  * **Impact:** Prompts a social comparison and re-evaluation of the agent's own system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Adoptive comparison**

  * **Description:** A direct social trigger where a neighbour who has recently installed a new system actively encourages the agent to consider adopting the same technology.
  * **Impact:** Prompts a re-evaluation spurred by direct social influence.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Asked by neighbour**

  * **Description:** A subtle social trigger where being asked for an opinion by a neighbour who is in the decision-making process causes the agent to reflect on their own heating system.
  * **Impact:** Prompts a re-evaluation based on incidental social interaction.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Information campaign**

  * **Description:** The agent is targeted by a scenario-defined information campaign promoting one or more specific heating technologies.
  * **Impact:** The agent's knowledge is directly altered. Idealised, low-uncertainty versions of the promoted systems (with subsidies already applied) are added to the agent's ``known_hs`` list.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Risk targeting campaign**

  * **Description:** A specialised information campaign designed to alleviate common fears or perceived risks associated with specific, often newer, technologies.
  * **Impact:** The agent's ``perceived_uncertainty`` for the targeted heating systems is directly reduced, making them appear less risky.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).

* **Consultation**

  * **Description:** Represents a general nudge from an external campaign or policy that encourages houseowners to seek professional advice, prompting them to think about their heating system.
  * **Impact:** Prompts a re-evaluation of the current system.
  * **Decision Stage:** Sends the agent to **Stage 1** (Evaluation).


Current heating system evaluation
---------------------------------
This submodel corresponds to Stage 1 of the ``Houseowner`` decision-making process. It is the critical first step that determines whether an agent is content with their current situation or is triggered to actively seek a new heating system. The evaluation is performed by comparing the agent's ``current_heating`` system against a set of personal and milieu-specific standards.

The process unfolds as follows:

Initiation and Pre-condition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The evaluation begins when an agent enters Stage 1 of the decision cycle. The process requires a small amount of ``cognitive_resource``; if the agent is "tired" (has insufficient resources), the evaluation is skipped for the current time step.

The Standard Check
^^^^^^^^^^^^^^^^^^

The core of the evaluation is a call to the :py:mod:`agents.Houseowner.Houseowner.check_standard` function, which assesses the agent's current heating system against a list of criteria. For the system to be considered satisfactory, it must pass **all** applicable criteria. If even one criterion fails, the entire check fails.

Evaluation Criteria
^^^^^^^^^^^^^^^^^^^

The criteria are composed of a universal standard that applies to all agents, plus a specific standard that is determined by the agent's milieu group.

    a. **Universal Criterion (Remaining Lifetime)**
       This check applies to all agents, regardless of their milieu. The agent becomes dissatisfied if their current heating system is nearing the end of its operational lifetime. Specifically, the system's current ``age`` must be less than its total ``lifetime`` minus a personal tolerance threshold (``self.standard.lifetime``).

    b. **Milieu-Specific Criteria**
       In addition to the lifetime check, agents apply a unique standard based on the values of their milieu group:

       * **Leading milieu group (Environmental Performance):** These agents prioritize environmental protection. They are only satisfied if their current system has the lowest CO2 emissions among all heating systems they know of (``known_hs``). This check is only triggered if the agent has a sufficient budget to realistically consider an upgrade, preventing dissatisfaction when change is not financially viable.
       * **Mainstream milieu group (Social Conformity):** These agents are strongly influenced by social norms. They are satisfied only if their current heating system is the most popular (or tied for the most popular) type within their immediate social network (``neighbours_systems``). Like the Leading milieu group, this check is conditional on the agent having a sufficient budget to act on their dissatisfaction.
       * **Traditional milieu group (Risk Aversion):** These agents prioritize reliability and avoiding future crises. They become dissatisfied if their heating system enters a "danger zone," which occurs if two conditions are met simultaneously: 1) the technology is being phased out of the market (less than 2 years of market ``availability`` remaining), and 2) the physical unit has less than 4 years of ``remaining_lifetime``. This reflects a desire to replace the system proactively before it fails and becomes difficult to repair.
       * **Hedonist milieu group (Pragmatism):** This group has a more pragmatic approach. They do not apply any additional, specific criteria. As long as their system passes the universal remaining lifetime check, they remain satisfied.

Outcome and State Transition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The result of the standard check determines the agent's next action:

    * **Satisfaction:** If the ``current_heating`` system passes all applicable criteria, the agent's state is set to "Satisfied". The decision-making process concludes for the time being, and the agent's ``current_stage`` is reset to "None", returning them to the inactive state.
    * **Dissatisfaction:** If the system fails even one criterion, the agent's state is set to "Dissatisfied". This dissatisfaction serves as the trigger for the active decision-making process. The agent's ``current_breakpoint`` is set to "Goal", and their ``current_stage`` is advanced to "Stage 2", initiating the search for a new heating system.


Information search
------------------

This submodel describes the process by which a ``Houseowner`` agent actively gathers information about alternative heating systems. It corresponds to the initial part of Stage 2 in the decision-making cycle. The goal is to expand the agent's knowledge base (``known_hs``) and form (imperfect) expectations about the attributes of different options.

The search process is governed by the agent's cognitive resources and personal preferences for different information channels.

1.  **Initiation and Pre-conditions**
    The information search begins when an agent enters Stage 2 with an unmet need for information (represented by ``aspiration_value > 0``) and is not already waiting for a previously scheduled consultation (``consultation_ordered = False``).

2.  **Baseline Social Search**
    Before consulting any primary information source, the agent **always** performs an initial search within their social network by executing the ``ask_neighbours()`` method. This establishes a baseline of socially-derived information.

3.  **Primary Information Source Selection**
    After the initial neighbor search, the agent chooses **one** primary information source (see below) to consult for the current time step. This choice is probabilistic, determined by the agent's milieu-specific preferences (``source_preferences``), which act as weights for the selection.

    * **Emergency Condition:** A special rule applies if the agent's current heating system is broken. In this emergency scenario, the agent is forced to seek professional help, and the choice of information source is restricted to only a ``plumber`` or an ``energy_advisor``.

Once a source is chosen, the agent executes that source's specific ``data_search()`` method. The mechanism of the search depends on the type of source selected.

Information Sources and Mechanisms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are two primary categories of information sources, each with a distinct search mechanism: impersonal sources that provide distorted information, and intermediary sources that trigger direct agent-to-agent consultations.

Impersonal Sources (Internet, Magazines)
""""""""""""""""""""""""""""""""""""""""

These sources represent channels that provide generic, non-personalized information. They are characterized by the limited scope of their content (e.g., a magazine may only cover a few system types) and the inherent imperfection of the information provided. The search process is iterative:

1.  **Iterative Search:** The agent repeatedly queries the source in a loop, with each query consuming ``cognitive_resource``.
2.  **Information Discovery:** In each iteration, the source provides information on one randomly selected heating system from its ``content``.
3.  **Perception Modeling:** The information received is not perfect. It is shaped by a multi-step perception model to form the agent's subjective "expectations":
   
  a. First, the "true" attributes of the system are calculated for a generic, average house.
  b. A ``distortion_factor`` is then applied to these true values. This factor combines a general distortion level, the source's specific bias for or against that technology (``system_skewedness``), and a random element. This creates a *perceived* central value for each attribute (e.g., price, emissions).
  c. Finally, an ``uncertainty`` range is assigned to each perceived value, representing the agent's lack of confidence in the information.

4.  **Knowledge Integration:**
  
  * **New System:** If the agent learns of a system for the first time, the new perceived version is added to its ``known_hs`` list. The agent then evaluates if this new option is better than their current system. If it is, their ``aspiration_value`` decreases (getting closer to their goal). If not, their ``overload_value`` decreases (effort spent for little gain).
  * **Known System:** If the agent already knew about the system, the new perceived information is integrated with their existing beliefs using a relative agreement mechanism.

5.  **Search Termination:** The iterative search loop terminates under one of three conditions:

  * The agent runs out of ``cognitive_resource``.
  * The agent's ``aspiration_value`` reaches zero, indicating they have found a sufficient number of promising alternatives.
  * The agent's ``overload_value`` reaches zero, indicating they have processed too much information without finding good options and will abandon the search for now.

Intermediary and Social Sources (Plumbers, Energy Advisors, Neighbours)
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

These sources represent direct interactions with other agents in the model. Their ``data_search()`` methods work differently:

* **Function:** Instead of providing chunks of distorted information, selecting one of these sources acts as a trigger to initiate a consultation or social interaction.
* **Process:** The method is responsible for finding a relevant agent (e.g., ``find_plumber()``) and scheduling an interaction (e.g., ``order_plumber()``). The ``Neighbours`` source simply calls the agent's own ``ask_neighbours()`` method.
* **Outcome:** After scheduling the interaction, the agent's ``cognitive_resource`` for the current time step is immediately depleted. This ends the information search and puts the agent into a passive, waiting state until the consultation or interaction is formally carried out by the other agent in a subsequent step (as described in the "Intermediary Consultation" submodel).


Formulating a list of suitable heating systems
----------------------------------------------

This submodel describes the process by which a Houseowner agent filters its list of *known* heating systems (``known_hs``) to produce a shorter *choice set* of options (``suitable_hs``) that are deemed suitable for further consideration.

Pre-condition check
^^^^^^^^^^^^^^^^^^^	

* **Prior Consultation Check:** If the agent has already consulted an energy advisor and has a pre-existing list of suitable systems, this filtering process is skipped to avoid re-evaluating the options.

Filtering
^^^^^^^^^

If this check passes, the agent iterates through every heating system in its ``known_hs`` list and subjects each one to a sequential filtering process. A system must pass all of the following checks in order to be considered suitable:

1.  **Technical Feasibility Filter:**
    The system must not be on the agent's personal list of technically infeasible options (``infeasible``). This list may be populated by an energy advisor's recommendations.

2.  **Installation Affordability Filter:**
    The agent must be able to afford the installation cost. This is checked in two ways:
    
    a. **Direct Affordability:** The system's price is checked directly against the agent's dedicated heating system budget (``hs_budget``).
    b. **Loan-Assisted Affordability:** If the system is not directly affordable, the agent attempts to find a suitable loan. If a loan is found, affordability is re-checked against the budget plus the loan amount.

3.  **Operational Affordability Filter:**
    The ongoing running costs of the new system must be affordable relative to the agent's income. The model calculates the *change* in weekly household expenses, which includes:
    
    * The difference in fuel and operational costs between the new system and the agent's current one.
    * The weekly repayment cost of any new loan taken for the installation.
    * Any existing financial burdens, such as a loan on the current heating system.
    
    The system is considered affordable only if the agent's income can cover these changes in expenses.

4.  **Risk Tolerance Filter:**
    All systems that pass the feasibility and affordability checks are added to a preliminary list. This list then undergoes a final filtering based on the agent's risk perception:
    
    a. First, a perceived risk score is calculated for each system on the list.
    b. The list is sorted from most to least risky.
    c. The agent iteratively removes the most risky system from the list until all remaining options have a risk score at or below the agent's personal ``risk_tolerance`` threshold.

Submodel Outcome and Special Conditions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After the filtering process is complete, one of the following outcomes occurs:

* **Suitable Options Found:** If the final ``suitable_hs`` list contains one or more heating systems, the agent successfully forms its choice set and proceeds to the next stage of the decision-making process.

* **No Suitable Options Found (Standard Case):** If the ``suitable_hs`` list is empty, the agent abandons the decision-making process for the time being, resetting its aspiration values and depleting its cognitive resources.

* **No Suitable Options Found (Emergency in case of broken heating):**The agent is forced to reconsider its options, potentially triggering a search for subsidies (by becoming ``subsidy_curious``) or attempting to secure a loan for a previously recommended system, even if it requires bypassing their normal risk avoidance. If all financing options are exhausted and still no system is affordable, the agent will default to the highest-rated system it can afford, regardless of other preferences.


Heating system evaluation
-------------------------

Once an agent has formulated a choice set of suitable heating systems (``suitable_hs``), this submodel evaluates each option to produce a final utility score, referred to as the "integral rating". This evaluation is based on the **Theory of Planned Behavior (TPB)**, which combines three key components to determine behavioural intention: the agent's personal attitude, the perceived social norm, and the perceived behavioural control.

The evaluation proceeds in the following steps for each system in the ``suitable_hs`` list.

1.  **Calculating Attitude (Personal Preference)**
    The agent's attitude represents how personally favourable they find each system. It is calculated by comparing a system's attributes against the agent's personal preferences (``heating_preferences``). The process is as follows:
    
    a. First, the attributes of all systems *known* to the agent (not just those in the choice set) are normalized relative to each other. This creates a rescaled attribute score between 0 and 1.
    b. For attributes where lower values are better (e.g., cost, emissions), this score is inverted (1 - normalized value).
    c. The corresponding rescaled attribute scores are then multiplied by the agent's personal preference weights for each attribute.
    d. Finally, these weighted scores are summed and averaged to produce a single ``rating`` for the system, which represents the agent's overall attitude towards it.

    The final ``rating`` score is a value between 0 and 1.

2.  **Calculating Social Norm (Peer Influence)**
    The social norm captures the perceived social pressure and influence from the agent's network. It is calculated as the average of two distinct factors:
    
    a. **Neighbour Opinion:** The average of all known opinions (i.e. attitudes) that the agent's neighbours have for that specific system.
    b. **System Prevalence:** The fraction of known neighbours in the agent's network who have that same type of heating system currently installed.
    
    The final ``social_norm`` score is a value between 0 and 1.

3.  **Calculating Perceived Behavioural Control (PBC)**
    Perceived Behavioural Control reflects the agent's confidence in their ability to perform the behaviour (i.e., install the system), primarily based on its affordability. It is calculated as the average of two financial ratios:
    
    a. **Installation Affordability:** The ratio of the agent's heating system budget (``hs_budget``) to the system's installation price, capped at 1. A value of 1 means the agent can fully afford the upfront cost.
    b. **Operational Affordability:** A measure of how the change in running costs (fuel and opex) compares to the agent's income. If the new system is cheaper or the same price to run, this value is 1. If it is more expensive, the value is reduced proportionally to the new financial burden.
    
    The resulting ``behavioural_control`` score is a value between 0 and 1.

4.  **Calculating the Integral Rating (Final Utility)**
    In the final step, the three calculated TPB components are combined into a single utility score for each system in the choice set. This is a multi-step process:
    
    a. **Relative Normalization:** The raw scores for Attitude (``rating``), ``social_norm``, and ``behavioural_control`` are normalized across all options *within the choice set*. For example, the system with the highest attitude score gets a normalized attitude of 1.
    b. **Weighting:** These newly normalized scores are then multiplied by the agent's personal TPB weights (``tpb_weights``), which define how much the agent cares about personal preference vs. social norms vs. affordability.
    c. **Summation:** The three weighted, normalized scores are summed to produce the final ``integral_rating`` for each system.

Submodel Outcome
^^^^^^^^^^^^^^^^

The output of this submodel is a dictionary mapping each ``Heating_system`` instance in the choice set to its final integral rating. This ranked list is then passed to the next submodel to make the final installation decision.


Heating system installation
---------------------------
This submodel describes the installation phase of the decision-making process, where a ``Houseowner`` agent, having already selected a ``desired_hs``, proceeds to have it installed. This process is a multi-step interaction between the ``Houseowner`` and a ``Plumber`` agent.

The process is initiated by the ``Houseowner`` agent and unfolds through a series of sequential checks and actions:

1.  **Pre-Condition and State Checks:**
    Before taking any action, the agent first evaluates its current state. This step determines whether the agent needs to act, wait, or has already completed the process.

    * **Installation Already Complete:** The agent checks if the ``desired_hs`` is already installed by verifying that its age is 0. If so, the process is considered complete. The agent's state is set to "Stage 4: Implementation", its ``waiting`` counter is reset, and relevant model-level obstacle trackers are updated to reflect the successful installation.
    * **Agent is Waiting:** If the agent has already ordered a consultation (``consultation_ordered == True``) or an installation (``installation_ordered == True``), it takes no new action. Instead, it enters a passive waiting state, depleting its ``cognitive_resource`` for the timestep and incrementing its ``waiting`` counter.
    * **Insufficient Cognitive Resources:** The agent must have a minimum amount of ``cognitive_resource`` to proceed with planning the installation. If its resources are below this threshold, it does nothing in the current timestep.

2.  **Internal Feasibility and Plumber Search:**
    If the agent is not waiting and has sufficient resources, it proceeds with the active planning steps.

    * **Check for Known Infeasibility:** The agent first checks if the ``desired_hs`` is on its personal list of infeasible systems (``infeasible``). This list may have been changed by a prior consultation. If it is infeasible:
        * The system is removed from the list of ``suitable_hs``, and the ``desired_hs`` is reset.
        * If other options remain in the ``suitable_hs`` list, the agent replenishes its cognitive resources and re-runs the comparison submodel (``compare_hs()``) to select a new desired system.
        * If no other suitable options exist, the agent abandons the implementation stage and reverts to "Stage 2: Goal" to search for new information.
    * **Finding a Qualified Plumber:** If the system is still considered feasible, the agent searches for a ``Plumber`` agent who is qualified to install the ``desired_hs``. It may be the same plumber from the previous consultation. If no such plumber can be found in the model, the agent's decision-making process fails for this cycle. It resets its ``suitable_hs`` and ``desired_hs``, and its decision stage is set to "None".
    * **Timeline Feasibility Check:** After successfully finding a plumber, the agent estimates the total time until installation is complete. This is the sum of the plumber's current queue time and the installation duration itself. If this total time exceeds 52 weeks (one year), the agent considers the delay unacceptable, unless the system was specifically recommended. In case of an unacceptable delay, the current ``desired_hs`` is removed from the ``suitable_hs`` list, and the agent attempts to re-evaluate and choose an alternative from the remaining suitable options. If none are left, the agent exits the decision-making process for the time being.

3.  **Plumber Consultation and Final Verification:**
    Once a plumber has been selected and the timeline is acceptable, the ``Houseowner`` orders a consultation. The ``Plumber`` agent then performs its own set of checks.

    * **Plumber Qualification Check:** The plumber verifies that the requested system is one they are familiar with and can install. If not, they reject the job, and the ``Houseowner`` adds them to a list of ``unqualified_plumbers`` and must restart the planning, potentially trying to find a qualified plumber.
    * **Technical Feasibility Assessment:** The plumber conducts a technical check. For certain heating systems (e.g., heat pumps), this involves verifying that the house's energy demand is below a specific threshold (i.e., the house is sufficiently insulated). If the house fails this check, the system is declared infeasible. The ``Houseowner`` is notified, adds the system to their ``infeasible`` list, and the installation is cancelled.
    * **Precise Cost Calculation:** If the system is deemed feasible, the plumber calculates the precise, house-specific installation (``price``) and operational (``opex``) costs. These calculated costs replace the agent's initial, potentially uncertain estimates. The plumber may also apply available ``subsidies`` at this stage.
    * **Final Affordability Check:** With the precise costs known, the ``Houseowner`` agent performs a final, definitive affordability check. If the new price is higher than anticipated, the agent will attempt to secure a new or larger loan (``find_loan()``) to cover the difference, bypassing its usual loan avoidance rules if necessary.

4.  **Ordering and Queuing the Installation:**
    This is the final step before the physical installation.

    * **Successful Order:** If the final affordability check passes, the consultation is considered successful. The ``Plumber`` adds the installation job to their work queue. The ``Houseowner``'s state is updated to reflect that an installation has been ordered (``installation_ordered = True``), and they enter the passive waiting state described in step 1.
    * **Failed Order:** If the final affordability check fails even after attempting to secure a loan, the installation cannot proceed. The agent abandons the choice, resets its ``desired_hs`` and ``suitable_hs``, and reverts to "Stage 2: Goal" to reconsider its options from an earlier point.

5.  **Physical Installation and State Update:**
    When the ``Houseowner``'s job reaches the front of the ``Plumber``'s queue, the ``installation`` is executed by the ``Plumber``.

    * **Financial Transaction:** The final installation ``price`` is deducted from the ``Houseowner`` agent's ``hs_budget``.
    * **System Swap:** The ``Houseowner``'s ``current_heating`` object is replaced with a new object representing the installed system. Key properties from the decision process, such as whether it was subsidised or financed with a loan, are transferred to this new object.
    * **Income Adjustment:** The agent's weekly income is permanently modified to reflect the change in operational costs and any new loan repayments.
    * **Final State Change:** The ``Houseowner``'s ``installation_ordered`` flag is set to ``False``, and they are marked as having ``installed_once``. They have now successfully completed the installation process.

Post-installation assessment
----------------------------
This submodel represents the final stage of the ``Houseowner``'s decision-making process, executed after a new heating system has been successfully installed. The primary purpose is for the agent to reflect on the outcome of its decision by comparing the actual performance of the new system against its prior expectations and other known alternatives. This assessment determines the agent's new ``satisfaction`` state, which in turn influences its future social interactions.

The process is executed as follows:

1.  **Pre-condition Check**
    The agent must have a sufficient amount of ``cognitive_resource`` to perform the assessment. If its resources are below the required threshold, the process is paused and deferred to the next time step.

2.  **Knowledge Update: Replacing Expectations with Reality**
    To perform a fair assessment, the agent first updates its internal knowledge base. This is a critical step:
    The agent replaces in its ``known_hs`` list the instance of the chosen heating system (which still holds *expected* attributes and the rating calculated *before* the installation) by a copy of its ``house.current_heating`` object. This new instance contains the *actual*, real-world attributes and performance data of the newly installed system.

3.  **Re-evaluation of All Known Options**
    With its knowledge base updated, the agent recalculates its personal attitude (``rating``) for every system in its ``known_hs`` list. This ensures that the comparison is based on the agent's most current perspective. The newly calculated rating for the installed system is considered its final, "true" rating.

4.  **Choice Optimality Assessment**
    The core of the satisfaction calculation lies in determining if the agent made the best possible choice from the options it had previously considered suitable.

    * The agent checks its ``suitable_hs`` list, which was formulated during the choice phase (Stage 2).
    
    * If there were **no other alternatives** in the ``suitable_hs`` list, the agent could not have made a better choice. Therefore, its ``satisfaction`` is automatically set to "Satisfied".
    * **In case of multiple options**, the agent compares the "true" rating of its newly installed system against the rating of the **second-best** alternative from that list.
        * **Optimal Choice (Satisfaction):** If the installed system's rating is greater than or equal to the second-best alternative's, the agent's choice is confirmed, and its ``satisfaction`` is set to "Satisfied".
        * **Suboptimal Choice (Dissatisfaction):** If the rating of the second-best alternative is higher than the rating of the installed system, the agent concludes it made a suboptimal decision and its ``satisfaction`` is set to "Dissatisfied".


5.  **Consequential Actions**
    The agent's new satisfaction state determines its immediate follow-up actions:

    * **If Satisfied:** The agent will attempt to propagate its successful decision by calling the ``share_decision()`` submodel. This allows it to influence its peers. The number of peers it attempts to influence is determined by its remaining ``cognitive_resource``.
    * **If Dissatisfied:** The agent does not share its decision, preventing the spread of a suboptimal choice.

6.  **State Reset and Cycle Conclusion**
    Regardless of the outcome, the agent performs a comprehensive state reset to formally conclude the entire decision-making cycle. This cleanup involves:

    * Clearing all temporary decision-making lists (``suitable_hs``).
    * Resetting choice variables (``desired_hs``, ``recommended_hs``).
    * Clearing its memory of interactions from the completed cycle (e.g., ``visited_neighbours``, ``unqualified_plumbers``).
    * Resetting its list of ``infeasible`` systems to the global default.

After this cleanup, the agent's ``current_stage`` and ``current_breakpoint`` are reset to "None", returning it to the inactive state (Stage 0).

Intermediary consultation
-------------------------

Plumber consultation
^^^^^^^^^^^^^^^^^^^^

When a ``Houseowner`` consults a ``Plumber`` for general advice, the ``Plumber`` executes a sequence of actions designed to expand and refine the ``Houseowner``'s knowledge base, ultimately providing a concrete recommendation.

The consultation process consists of the following steps:

1.  **Knowledge and Attribute Sharing (``share_knowledge``):**
    The ``Plumber`` first updates the ``Houseowner``'s understanding of various heating systems. This is a multi-faceted information transfer:

    * **House-Specific Cost Calculation:** The ``Plumber`` calculates the precise installation (``price``) and operational (``opex``) costs for every heating system it knows, tailored specifically to the ``Houseowner``'s house characteristics (e.g., ``area``, ``heat_load``).
    * **Updating Existing Knowledge:** For heating systems that the ``Houseowner`` already knows about, the ``Plumber``'s house-specific attribute data is used to influence the ``Houseowner``'s existing beliefs. This is handled via a Relative Agreement mechanism, which adjusts the ``Houseowner``'s (potentially uncertain) parameter estimates to align more closely with the ``Plumber``'s expert assessment.
    * **Introducing New Systems:** If the ``Plumber`` knows about heating systems that are not in the ``Houseowner``'s ``known_hs`` list, these new systems are added to the list. The ``Houseowner``'s subjective perception of social opinions for these newly learned systems is initialized as neutral.
    * **Sharing Subsidy Information:** The ``Plumber`` shares its entire portfolio of known subsidies (``known_subsidies_by_hs``) with the ``Houseowner``.

2.  **Opinion Sharing (``share_rating``):**
    The ``Plumber`` shares its personal professional rating for each heating system it knows. This rating is added to the ``Houseowner``'s ``neighbours_opinions`` dictionary for the corresponding system, treating the ``Plumber`` as a trusted source of opinion.

3.  **Formal Recommendation (``recommend``):**
    The ``Plumber`` provides a single, formal recommendation. This is determined through a filtering process:

    a. First, the ``Plumber`` creates a **list of all systems** it can install, sorted by its personal ``rating``.
    b. **Technical Feasibility Filter:** The list is filtered to remove systems that are technically unsuitable for the ``Houseowner``'s house (e.g., heat pumps in a poorly insulated building, as determined by the ``insulation_threshold``).
    c. **Agent Infeasibility Filter:** The list is filtered again to remove any systems the ``Houseowner`` has previously identified as being on their personal ``infeasible`` list.
    d. The highest-rated system remaining after these filters are applied is then designated as the ``Houseowner``'s ``recommended_hs``.

4.  **Sharing Social Context (``share_systems``):**
    If the corresponding model parameter (``settings.plumber.share_systems``) is enabled, the ``Plumber`` provides the ``Houseowner`` with information about which heating systems are installed in the homes of their social network neighbors, but only for those neighbors who are also clients of this specific ``Plumber``. This updates the ``Houseowner``'s ``neighbours_systems`` attribute.


Plumber Consultation Outcome
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

After all information has been shared and the recommendation has been made, the consultation concludes. The ``Houseowner``'s ``consultation_ordered`` flag is set to ``False``, and their ``aspiration_value`` is reset to 0. This reset prompts the agent to re-evaluate their goals and options in light of the new, expert information they have just received.

Energy Advisor Consultation
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The consultation with an ``Energy Advisor`` provides the ``Houseowner`` with a comprehensive and financially-focused analysis of heating options. The primary goal of this submodel is to transform the advisor's general knowledge into a concrete, curated list of technically feasible and financially affordable heating systems (``suitable_hs``) for the agent, completed	 with a formal recommendation.

The consultation process unfolds as follows:

1.  **House-Specific Cost and Subsidy Analysis:**
    The advisor begins by assessing all heating systems within its knowledge base (``known_hs``). For each system, it performs two key calculations:

    * **Personalised Cost Calculation:** It first calculates the precise installation and operational costs based on the specific attributes of the ``Houseowner``'s house (``area``, ``energy_demand``, ``heat_load``).
    * **Detailed Subsidy Application:** It then meticulously applies all known subsidies for which the system or ``Houseowner`` is eligible. This involves:
        * Checking any specific conditions attached to a subsidy.
        * Calculating the subsidy amount, typically as a percentage of the installation cost.
        * Applying a cap to the total subsidy (the lower of 70% of the price or 21,000 currency units).
        * Adding a small additional premium (5% of the original price) to the total subsidy amount.
        * The final, aggregated subsidy is deducted from the system's installation cost, and the system is marked as ``subsidised``.

2.  **System Evaluation and Ranking:**
    Once the post-subsidy costs are determined, the advisor assigns a quantitative ``rating`` to each potential heating system. The systems are then sorted in a list from highest to lowest rating, creating a ranked order of preference from the advisor's perspective.

3.  **Multi-Stage Filtering and Financial Planning:**
    The advisor filters the ranked list of systems to determine which ones are viable for the ``Houseowner``. This is a multi-step process:

    a. **Initial Feasibility Filter:** The list is first filtered to exclude any system that the ``Houseowner`` has previously marked as being on their personal ``infeasible`` list.
    b. **Proactive Loan Assessment:** The advisor then iterates through the remaining systems. For any option that is still not affordable with the agent's dedicated budget (``hs_budget``), the advisor prompts the agent to proactively search for a loan (by calling ``find_loan()``) for that specific system.
    c. **Final Affordability Filter:** A final, definitive filter is applied. Only systems that are affordable—either directly from the agent's ``hs_budget`` or with the help of a successfully identified loan—are kept for the final list.

4.  **Formulating the Final Recommendations:**
    The systems that pass all filters constitute the final output of the consultation.

    * **Creation of a Suitable Set:** All systems that pass the final affordability filter are passed to the ``Houseowner`` to become their new ``suitable_hs`` list. This provides the agent with a pre-vetted choice set.
    * **Technical Check for Recommendation:** The advisor performs one last technical check on this suitable list, removing options that are incompatible with the house's insulation level (the ``insulation_threshold`` check).
    * **Formal Recommendation:** The highest-rated system from this final, technically viable list is formally designated as the ``Houseowner``'s ``recommended_hs``.

5.  **Final Knowledge Transfer:**
    To ensure the ``Houseowner``'s internal knowledge is up-to-date, the advisor shares its detailed, house-specific attributes and professional ratings for all systems, not just the suitable ones. It also shares the specific subsidy information relevant to the systems in the final ``suitable_hs`` list.

Energy Advisor Consultation Outcome
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The consultation concludes by updating the ``Houseowner``'s state. The agent now possesses a curated list of ``suitable_hs`` and a formal ``recommended_hs``. Their ``aspiration_value`` is reset to 0 to trigger a re-evaluation based on this new information, and their ``consultation_ordered`` and ``subsidy_curious`` flags are set to ``False``.


Heating system attribute calculations
-------------------------------------

This submodel details the set of procedures used to calculate the primary cost and performance attributes of all heating systems in the model. These are not agent-level behaviors but are foundational calculations performed at the beginning of the simulation for each existing system and dynamically during a simulation whenever an intermediary agent (a ``Plumber`` or ``Energy Advisor``) provides a house-specific consultation.

The calculations are dependent on the characteristics of the ``House`` for which the system is being evaluated, specifically its area :math:`A_{house}` (in :math:`m^2`), specific energy demand :math:`E_{specific}`(in :math:`kWh/m^2a`), and heat load :math:`L_{heat}` (in :math:`kW`). The master function ``calculate_all_attributes`` orchestrates the following sequence of calculations:

1. Final Energy Demand Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Before costs can be determined, the system's total final energy demand is calculated based on the house's specific energy demand and the system's efficiency.

* **Inputs:** House area (:math:`A_{house}`), house specific energy demand (:math:`E_{specific}`).
* **Process:**
    1. A system-specific efficiency factor (:math:`F_{efficiency}`) is determined. The model uses five predefined energy demand classes (50, 100, 150, 200, 250 :math:`kWh/m^2a`) each with a corresponding efficiency factor for the given heating system. The factor corresponding to the class closest to the house's :math:`E_{specific}` is selected.
    2. A ``processed_area`` is calculated using a fixed scaling formula to represent the building's heat-transferring surface area:
       
       .. math::
       
          A_{processed} = A_{house} \times (2.3 \times 1.5 + 0.75) \times 0.32
    
    3. The total final energy demand (:math:`E_{final}`) is then computed as:
    
       .. math::
    
          E_{final} = A_{processed} \times E_{specific} \times F_{efficiency}

* **Output:** Total final energy demand in :math:`kWh` per year.

2. Installation Cost Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The initial installation cost (``price``) is calculated based on the system type and house characteristics.

* **Inputs:** House area (:math:`A_{house}`), house heat load (:math:`L_{heat}`).
* **Process:** The calculation follows one of three paths:

    a. **Heat Delivery Contract:** For systems where the ``Houseowner`` pays for heat as a service (``heat_delivery_contract = True``), the direct installation cost to the agent is :math:`0`.
    b. **Heat Load-Based Cost:** For most heating systems (e.g., boilers, heat pumps), the cost is a function of the house's heat load. The formula uses several system-specific parameters from a lookup table:
    
       .. math::
       
          C_{install} = (P_{base} \times L_{heat}^{F_{load}} \times L_{heat}) \times F_{correction}
          
       Where :math:`P_{base}` is the base price, :math:`F_{load}` is a scaling factor for the heat load, and :math:`F_{correction}` is an adjustment factor.
       
    c. **Area-Based Cost:** For network-based systems (e.g., district heating), the cost is a function of the house's area. A similar formula applies:

       .. math::
       
          C_{install} = (P_{base} \times A_{house}^{F_{area}} \times A_{house} \times F_{oppendorf} \times I_{price} \times I_{sidecosts}) \times F_{correction}
          
       Where the parameters are system-specific values from a lookup table representing base price, area scaling factor, and various indices. A special case, ``Heating_system_electricity``, uses a similar area-based formula but without the final correction factor.

3. Operating Cost (OPEX) Calculation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The annual operating and maintenance costs (``opex``) - excluding fuel costs - are calculated as a fraction of the installation cost.

* **Inputs:** House area (:math:`A_{house}`), house heat load (:math:`L_{heat}`).
* **Process:**
    
    a. **Standard Systems:** For standard, owner-operated systems, the OPEX is a direct fraction of the installation cost:
    
       .. math::
       
          OPEX = C_{install} \times F_{opex}
          
       Where :math:`F_{opex}` is a system-specific factor.
       
    b. **Heat Delivery Contracts:** For these systems, the OPEX also includes the amortized installation cost, which is paid off over the system's lifetime (:math:`T_{lifetime}; in weeks`):
    
       .. math::
       
          OPEX = (C_{install} \times F_{opex}) + (52 \times \frac{C_{install}}{T_{lifetime}})

4. Fuel Cost Calculation
^^^^^^^^^^^^^^^^^^^^^^^^
The annual fuel cost (``fuel_cost``) is calculated based on the final energy demand.

* **Input:** Total final energy demand (:math:`E_{final}`).
* **Process:** This is a direct linear calculation:

    .. math::

       C_{fuel} = E_{final} \times P_{fuel}
       
    Where :math:`P_{fuel}` is the system-specific price of fuel per :math:`kWh`.

5. Emissions Calculation
^^^^^^^^^^^^^^^^^^^^^^^^
The annual CO2-equivalent emissions (``emissions``) are also calculated from the final energy demand.

* **Input:** Total final energy demand (:math:`E_{final}`).
* **Process:** This is a direct linear calculation:

    .. math::
    
       Emissions_{CO2eq} = E_{final} \times F_{emissions}

    Where :math:`F_{emissions}` is the system-specific emission factor in grams of CO2-equivalent per :math:`kWh`.

Integration and Financial Metrics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once these core attributes are calculated, they are used to define key financial metrics for the heating system object:

* **Investment:** The initial investment is set equal to the calculated installation cost (:math:`C_{install}`).
* **Annual Payback:** The amount of the investment that is paid back each year over the system's lifetime is calculated as:

    .. math::
    
       Payback_{annual} = \frac{C_{install}}{T_{lifetime}}

* **Depreciated Value:** For existing systems, the model also calculates the remaining value of the investment based on its current age (:math:`T_{age}`):

    .. math::
    
       Value_{remaining} = C_{install} - (Payback_{annual} \times T_{age})


Subsidies and Loans
-------------------

This submodel describes the financial instruments available to ``Houseowner`` agents to reduce the cost burden of a new heating system. It covers the structure and application of subsidies, which lower the initial installation cost, and the process by which agents secure loans to cover remaining costs.

Subsidies
^^^^^^^^^

Subsidies are financial grants that directly reduce the installation price of a heating system. They are defined by a flexible structure that allows for a variety of subsidy types, including unconditional grants for specific technologies and conditional bonuses based on agent or system characteristics.

Subsidy Structure
"""""""""""""""""

Each subsidy in the model is an object with the following attributes:

* ``heating_system``: The specific heating system or group of systems the subsidy applies to.
* ``subsidy``: The value of the subsidy, represented as a decimal fraction of the system's installation cost (e.g., 0.3 for a 30% subsidy).
* ``condition``: An optional logical rule that must be met for the subsidy to be applicable.
* ``target``: Specifies whether the ``condition`` applies to the ``Houseowner`` agent (e.g., their income) or the ``Heating_system`` itself (e.g., a specific technical property).

The model includes several types of subsidies, such as:

* **Base Technology Subsidies:** Unconditional grants for adopting specific technologies like heat pumps, pellet boilers, or district heating connections.
* **Conditional Bonus Subsidies:** Additional, stackable grants that are awarded only if certain conditions are met. Examples include:
    * An "Income Bonus" for households with an annual income below a set threshold.
    * A "Climate Speed Bonus" for agents who replace an existing oil or gas heating system early.
    * An "Efficiency Bonus" for installing particularly efficient models of certain technologies.

Application and Calculation Process
"""""""""""""""""""""""""""""""""""

Subsidies are calculated and applied by intermediary agents (primarily the ``Energy Advisor``) during a consultation. The process for a given heating system is as follows:

1.  **Eligibility Check:** The intermediary checks all subsidies associated with the heating system's type. For each one, it evaluates its ``condition`` (if one exists) against the specified ``target`` (the ``Houseowner`` or the ``Heating_system``).
2.  **Amount Calculation:** For every eligible subsidy, the monetary value is calculated as a percentage of the system's pre-subsidy installation cost.
3.  **Aggregation:** The values of all eligible subsidies are summed to produce a ``total_subsidy`` amount.
4.  **Subsidy Capping:** The aggregated ``total_subsidy`` is capped to prevent over-subsidization. The final amount cannot exceed the lesser of these two values: 70% of the original installation cost, or 21,000 EUR.
5.  **Premium Addition:** A final "premium," calculated as 5% of the original installation cost, is added to the capped subsidy amount.
6.  **Price Reduction:** This final, total subsidy amount is subtracted directly from the heating system's installation ``price``.

Loans
^^^^^

Loans provide a mechanism for ``Houseowner`` agents to finance an installation when their available budget (``hs_budget``) is insufficient to cover the post-subsidy price.

Loan Structure and Terms
""""""""""""""""""""""""

A ``Loan`` object is defined by its principal amount, interest rate, and term, from which repayment values are calculated.

* **Loan Amount Determination:** When an agent considers a loan, the principal amount is determined by a two-step process:
    a. **Required Amount:** The amount needed is calculated as:
    
       .. math::
       
          L_{required} = C_{install} - B_{agent}
          
       Where :math:`C_{install}` is the system's post-subsidy price and :math:`B_{agent}` is the agent's available budget.
       
    b. **Affordable Amount:** The agent's maximum borrowing capacity is determined by a Loan-to-Income (LTI) rule, capped at 5 times their annual income, and a Loan-to-Value (LTV) rule, capped at 100% of the system's price.
    
       .. math::
       
          L_{affordable} = \min(C_{install}, I_{annual} \times 5)
          
       Where :math:`I_{annual}` is the agent's annual income.
       
    The final ``loan_amount`` is the minimum of the required and affordable amounts: :math:`\min(L_{required}, L_{affordable})`.

* **Repayment Calculation:** Using the final ``loan_amount``, a standard annual interest rate (e.g., 2.21%), and a loan term (in years), the model calculates the ``monthly_payment`` using the standard loan amortization formula and the ``total_repayment`` including compound interest.

The Loan-Finding Process
""""""""""""""""""""""""

When a ``Houseowner`` has insufficient funds to finance a system, they execute the ``find_loan`` process, which includes the following steps:

1. **Pre-Condition Checks:** The agent will only attempt to find a loan if two conditions are met:

   * The agent has a general willingness to take on debt (``loan_taking = True``), unless this check is explicitly bypassed (e.g., during an emergency).
   * The agent's expected weekly income after accounting for the changes in fuel and operating costs from the new system is greater than zero.
2. **Initial Attempt:** The agent first calculates the terms of a standard 10-year loan.
3. **Loan Term Optimization:** If the initial weekly payment is higher than the agent's expected weekly income, the loan is considered unaffordable. The agent then enters an optimization loop:

   * It incrementally increases the loan term by one year.
   * It recalculates the loan terms, resulting in a lower weekly payment.
   * This process continues until the weekly payment is less than or equal to the agent's expected weekly income.
4. **Success and Failure Conditions:**

   * **Success:** If an affordable weekly payment is found, the resulting ``Loan`` object, with its optimized term, is successfully attached to the heating system being considered.
   * **Failure:** The search for a loan fails if the optimization loop terminates before finding an affordable payment. This occurs if the required loan term exceeds the heating system's technical lifetime, in which case no viable loan is found.
