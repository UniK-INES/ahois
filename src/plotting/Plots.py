"""
Generates a wide array of plots and analyses from a single simulation run.

This module provides the `Plots` class, a tool for post-processing
the output of a single simulation. It is responsible for loading the detailed
agent and model data from pickle files and generating a suite of
visualisations.

The generated plots cover various aspects of the simulation, including agent
decision-making stages, heating system distribution, economic metrics (costs,
budgets), environmental impacts (emissions), social dynamics (information
spread), and the effectiveness of intermediaries.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
 - Dmytro Mykhailiuk <dmytromykhailiuk6@gmail.com>
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import plotly.express as px
import math
import random
import logging
import yaml
from helpers.utils import get_images_name, get_file_name
from helpers.config import settings, get_output_path
from modules.Excel_input_read import Heating_params_table
from helpers.i18n import _

try:
    from analysis.analyse_by_ahid import getLabels
except (ModuleNotFoundError, ImportError):
    print("Cannot import a module from analysis.analyse_by_ahid")

params_table = Heating_params_table()

logger = logging.getLogger("ahoi.plots")

class Plots:
    """
    A class to generate all plots and analyses for a single simulation run.
    """
    def __init__(self, run_id, milieu: str | None = None):
        """
        Initialises the Plots class by loading all necessary data.

        This constructor loads the agent, model, and intermediary data from
        the pickle files corresponding to the specified `run_id`. It also
        initialises the plotting style from a YAML configuration file and
        sets up the input and output paths. An optional `milieu` filter can
        be provided to generate plots for a specific subset of agents.

        Parameters
        ----------
        run_id : int
            The identifier of the simulation run to be processed.
        milieu : str or None, optional
            If specified, filters the agent data to include only agents of this
            milieu type, by default None.
        """
        with open(settings.data.plt_settings, "r") as configfile:
            config = yaml.safe_load(configfile)
        if "Layout" in config:
            plt.rcParams.update(config["Layout"])
        else:
            raise ValueError("Invalid plotting configuration file: 'Layout' section missing.")
        
        self.milieu = milieu
        
        self.inpath = get_output_path(runid=run_id, subfolder='pickles')
        if settings.output.simplenames:
            self.outpath = get_output_path(runid=run_id, subfolder='plots')
        else:
            self.outpath = get_output_path(runid=run_id, subfolder= f"single_run_plots")
            if not os.path.exists(self.outpath):
                os.makedirs(self.outpath)
                
        try:
            self.agent_df = pd.read_pickle(f"{self.inpath}/agent_df_{get_file_name(run_id = run_id)}.pkl")
            self.agent_df = (
                self.agent_df[self.agent_df["Milieu"] == self.milieu]
                if self.milieu
                else self.agent_df
                )
            self.last_agents = self.agent_df.groupby("AgentID").last().reset_index()
            self.houseowner_df = self.agent_df[self.agent_df["Class"] == "Houseowner"]
        except FileNotFoundError:
            logger.warning("Agent data files were not found!")
        
        try:
            self.model_df = pd.read_pickle(f"{self.inpath}/model_df_{get_file_name(run_id = run_id)}.pkl")
        except FileNotFoundError:
            logger.warning(f"Model data files were not found {self.inpath}/{get_file_name(run_id = run_id)}!")
        
        try:
            self.intermediary_df = pd.read_pickle(f"{self.inpath}/intermediary_df_{get_file_name(run_id = run_id)}.pkl")
            self.intermediary_queue_df = pd.read_pickle(
                f"{self.inpath}/intermediary_queue_df_{get_file_name(run_id = run_id)}.pkl"
                )
        except FileNotFoundError:
            logger.warning(f"Some data files were not found (looking for at {self.inpath}!")
            
        self.params_table = params_table
        self.serialization_function = settings.main.serialization_function
        assert self.serialization_function in [
            "to_excel",
            "to_csv",
        ], "Choose 'to_excel' or 'to_csv' as an option for serialization_function"

        self.file_ext = ".xlsx" if self.serialization_function == "to_excel" else ".csv"
        self.rate_of_change = pd.DataFrame()
        # Create an empty DataFrame for expanded attributes with the necessary columns

    def process_all_outputs(self):
        """
        Generates and saves the complete standard set of plots.

        This is the main public method to be called after initialisation. It
        handles the creation of all standard plots by calling the
        individual plotting methods in a predefined sequence.
        """
        self.average_time_on_stage()
        self.deciding_agents_aggregated()
        self.stages_distribution()
        self.share_deciding_agents()
        self.heating_distribution()
        self.average_HS_age()
        self.average_HS_age_per_system()
        self.average_satisfaction()
        self.optimality()
        self.emissions()
        self.energy_demand()
        self.trigger_amount()
        self.trigger_types()
        self.area_trigger_types()
        self.stages_history()
        self.information_source_calls()
        self.changes_and_replacements()
        self.opex()
        self.preferences()
        self.compare_metrics()
        self.hs_budget()
        self.dropouts()
        self.information_outspreading_by_subsidies(["Climate_speed", 
                                                    "Heat_pump",
                                                    "Heat_pump_brine",
                                                    "Pellet", 
                                                    "Income"]) # District , Climate_speed, Income
        self.subsidised_hs()
        self.information_outspreading_by_heating_system(["Heating_system_heat_pump"])
        self.hs_budget_installation_ratios()
        self.hs_budget_affordability_counts()
        if settings.main.current_scenario != "Scenario_none":
            self.scenario_fulfilment()
        if settings.main.current_scenario != "Scenario_perfect":
            self.compare_attributes()
            self.compare_attributes_median()
        if settings.main.number_of_energy_advisors > 0:
            self.heating_distribution_advised()
            self.intermediary_job_progression()
            self.save_intermediary_progress()
            self.intermediary_queue_length()
        
        
    def individual_plots_by_ids(
        self,
        ids: list[int] = [0],
        intermediary_ids: list[int] = [0],
        intermediary_type: str = "Plumber",
    ):
        """
        Generates detailed plots for a specific list of agent IDs.

        This method is used for in-depth analysis or debugging. It creates a
        set of plots focusing on the behaviour and metrics of a few specified
        agents over time.

        Parameters
        ----------
        ids : list[int], optional
            A list of `Houseowner` agent IDs to plot, by default [0].
        intermediary_ids : list[int], optional
            A list of intermediary agent IDs to plot, by default [0].
        intermediary_type : str, optional
            The class name of the intermediary type, by default "Plumber".
        """
        self.call_plotting_function(
            self.indicator_plot_by_ids,
            [
                ("Suboptimality", 0, 1, _("ratio"), ids),
                ("Opex", None, None, _("Euro"), ids),
                ("Emissions", 0, None, _("tons of CO2 equivalent per year"), ids, 1000000),
                ("Energy demand", 0, None, _("MWh per year"), ids, 1000),
            ],
        )

        information_sources = [
            _(word[0].upper() + word[1:].replace("_", " "))
            for word in settings.information_source.list
        ]

        self.call_plotting_function(
            self.deciding_agents_by_ids,
            [
                (
                    "Stage",
                    ids,
                    [1, 2, 3, 4],
                    [_("Predecisional"), _("Preactional"), _("Actional"), _("Postactional")],
                ),
                ("Cognitive resource", ids),
                ("Budget", ids),
                (
                    "Information_sources",
                    ids,
                    settings.information_source.list,
                    information_sources,
                ),
            ],
        )

        self.intermediary_queue_length_by_ids(intermediary_ids, intermediary_type)
    
    def analyze_obstacles(self, target_step=settings.main.steps):
        """
        Analyses and plot the decision-making funnel for a target heating system.

        This method visualises the "leaky pipeline" of agent decision-making.
        It counts how many agents pass each sequential obstacle (e.g., being
        triggered, gaining knowledge, affording the system, liking it) on their
        way to installing the scenario's target heating system.
        Plots separately the absolute values and shares.

        Parameters
        ----------
        target_step : int, optional
            The simulation step at which to perform the analysis, by default
            the final step.
        """
        if hasattr(self,"agent_df"):
            # Filter data up to the target step using the MultiIndex level "Step"
            filtered_df = self.agent_df.loc[self.agent_df.index.get_level_values("Step") <= target_step].copy()
            
            # Additional filtering: Include only "Houseowner" and exclude rows where "Obstacles" is None
            filtered_df = filtered_df[
                (filtered_df["Class"] == "Houseowner") & 
                (filtered_df["Obstacles"].notna())
            ].copy()
            
            # Expand the "Obstacles" dictionary into separate columns
            obstacle_data = filtered_df["Obstacles"].apply(pd.Series)
            filtered_df = pd.concat([filtered_df, obstacle_data], axis=1)
            
            # Filter rows where "Deciding" is True
            deciding_df = filtered_df[filtered_df["Deciding"] == True]
            
            # Identify all unique AgentIDs
            all_agents = set(filtered_df.index.get_level_values("AgentID").unique())
            
            # Identify unique AgentIDs who have "Deciding" as True
            deciding_agents = set(deciding_df.index.get_level_values("AgentID").unique())
            
            # Identify agents who were never "Deciding"
            never_deciding_agents = all_agents - deciding_agents
            
            # Extract details of agents who never entered "Deciding"
            never_deciding_df = filtered_df.loc[
                filtered_df.index.get_level_values("AgentID").isin(never_deciding_agents)
            ].reset_index().drop_duplicates(subset=["AgentID"])
            
            # Save these agents to a CSV file
            never_deciding_df.to_csv(f"{self.outpath}/never_deciding_agents.csv", index=False)
            
            # Initialize a dictionary to store results
            summary = {"Deciding": 0, "Knowing": 0, "Can afford": 0, "Certain": 0, "Like": 0, "Installed": 0}
            
            # Start with "Deciding" agents
            summary["Deciding"] = deciding_df.groupby(level="AgentID").ngroups  # Count unique AgentIDs
        
            # Calculate progression through obstacles
            knowing_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Knowledge"].eq(True).any())
            summary["Knowing"] = knowing_agents.groupby(level="AgentID").ngroups
        
            can_afford_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Affordability"].eq(True).any())
            summary["Can afford"] = can_afford_agents.groupby(level="AgentID").ngroups
            
            certain_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Riskiness"].eq(True).any())
            summary["Certain"] = certain_agents.groupby(level="AgentID").ngroups
        
            like_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Evaluation"].eq(True).any())
            summary["Like"] = like_agents.groupby(level="AgentID").ngroups
        
            finished_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Feasibility"].eq(True).any())
            summary["Installed"] = finished_agents.groupby(level="AgentID").ngroups
        
            # Convert the summary dictionary into a DataFrame
            result_df = pd.DataFrame([summary])
            
            # Bar chart configuration
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
            
            # Create a bar chart
            obstacles = list(summary.keys())
            counts = list(summary.values())
            bars = ax.bar(obstacles, counts, color='skyblue', edgecolor='black')
            
            # Annotate each bar with its value
            for bar in bars:
                height = bar.get_height()  # Get the height of the bar
                ax.text(
                    bar.get_x() + bar.get_width() / 2,  # X-coordinate: Center of the bar
                    height + 0.5,                      # Y-coordinate: Slightly above the top of the bar
                    f"{int(height)}",                  # Text: Convert height to an integer
                    ha='center',                       # Horizontal alignment
                    va='bottom'                        # Vertical alignment
                )
            
            # Set title and labels
            system_name = settings.main.current_scenario[len("Scenario_"):]
            title = "{imagename}Obstacles in {year} years for {system}".format(
                imagename=get_images_name(),
                year = int(target_step / 52),
                system=system_name
                )
            ax.set_title(title)
            ax.set_xlabel(_("Obstacles"))
            ax.set_ylabel(_("Agents"))
            
            # Save the plot
            file_path = f"{self.outpath}/{get_images_name()}Obstacles_{int(target_step / 52)}_years for {system_name}.png"
            
            plt.savefig(file_path)
            plt.close()

    def analyze_obstacles_by_period(self):
        """
        NEEDS REFACTORING
        Analyses and plot the decision-making funnel across different time periods.

        This method extends `analyze_obstacles` by breaking the simulation
        down into four equal time periods. It generates grouped bar charts
        showing how the number and percentage of agents passing each obstacle
        changes over the course of the simulation.
        """
        if hasattr(self,"agent_df"):
            # Get total steps and define periods
            total_steps = self.agent_df.index.get_level_values("Step").max()
            period_boundaries = np.linspace(0, total_steps, 5, dtype=int)  # 4 equal periods
            # Define the starting year of the simulation
            starting_year = settings.main.start_year 
            
            # Convert step boundaries to calendar year ranges
            periods = [
                f"{starting_year + (start // 52)}-{starting_year + (end // 52) - 1}"
                for start, end in zip(period_boundaries[:-1], period_boundaries[1:])
            ]
                
            # Initialize DataFrame to store results for each period, including a new "Triggered" column
            period_summary = pd.DataFrame(
                columns=["Triggered", "Deciding", "Knowing", "Can afford", "Certain", "Like", "Installed"],
                index=periods
            )
        
            # Get the total number of unique agents in the data frame for share calculations
            total_agents = self.agent_df.index.get_level_values("AgentID").nunique()
        
            # Initialize a list to store unmatched "Deciding" agents for all periods
            unmatched_deciding_agents = []
        
            # Process each period
            for i, (start, end) in enumerate(zip(period_boundaries[:-1], period_boundaries[1:])):
                # Filter rows for the current period
                period_df = self.agent_df.loc[
                    (self.agent_df.index.get_level_values("Step") >= start) &
                    (self.agent_df.index.get_level_values("Step") < end)
                ].copy()
                
                # Additional filtering: Include only "Houseowner" and exclude rows where "Obstacles" is None
                period_df = period_df[
                    (period_df["Class"] == "Houseowner") & 
                    (period_df["Obstacles"].notna())
                ]
                
                # Expand the "Obstacles" dictionary into separate columns
                obstacle_data = period_df["Obstacles"].apply(pd.Series)
                period_df = pd.concat([period_df, obstacle_data], axis=1)
                
                # Filter rows where "Triggered" is True
                triggered_df = period_df[period_df["Triggered"] == True]
                triggered_agents = triggered_df.groupby(level="AgentID")
        
                # Initialize a dictionary to store results for this period
                summary = {"Triggered": 0, "Deciding": 0, "Knowing": 0, "Can afford": 0, "Certain": 0, "Like": 0, "Installed": 0}
        
                # Count the total number of triggered agents
                summary["Triggered"] = triggered_agents.ngroups  # Count unique AgentIDs
                
                # Filter rows where "Deciding" is True
                deciding_df = period_df[period_df["Deciding"] == True]
                deciding_agents = deciding_df.groupby(level="AgentID")
                summary["Deciding"] = deciding_agents.ngroups  # Count unique AgentIDs
        
                # Stage-wise progression
                knowing_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Knowledge"].eq(True).any())
                summary["Knowing"] = knowing_agents.groupby(level="AgentID").ngroups
        
                can_afford_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Affordability"].eq(True).any())
                summary["Can afford"] = can_afford_agents.groupby(level="AgentID").ngroups
                
                certain_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Riskiness"].eq(True).any())
                summary["Certain"] = certain_agents.groupby(level="AgentID").ngroups
        
                like_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Evaluation"].eq(True).any())
                summary["Like"] = like_agents.groupby(level="AgentID").ngroups
        
                finished_agents = deciding_df.groupby(level="AgentID").filter(lambda x: x["Feasibility"].eq(True).any())
                summary["Installed"] = finished_agents.groupby(level="AgentID").ngroups
                
                # Identify agents not progressing beyond "Deciding"
                unmatched_agents_df = deciding_df[
                    ~(
                        deciding_df["Knowledge"].fillna(False) |
                        deciding_df["Affordability"].fillna(False) |
                        deciding_df["Riskiness"].fillna(False) |
                        deciding_df["Evaluation"].fillna(False) |
                        deciding_df["Feasibility"].fillna(False)
                    )
                ].copy()
                
                # Add period information to unmatched agents for context
                unmatched_agents_df["Period"] = periods[i]
                
                # Append these agents to the list
                if not unmatched_agents_df.empty:
                    unmatched_deciding_agents.append(unmatched_agents_df)
                
                # Update the period summary
                period_summary.loc[periods[i]] = summary
        
            # Combine all unmatched agents into a single DataFrame
            if unmatched_deciding_agents:
                unmatched_agents_summary = pd.concat(unmatched_deciding_agents, axis=0)
                unmatched_agents_summary.to_csv(f"{self.outpath}/unmatched_deciding_agents.csv", index=False)
            else:
                print("No unmatched deciding agents found across all periods.")
            
            # Calculate shares
            reference_summary = period_summary.copy()
            shares_summary = period_summary.copy()
            shares_summary[_("Triggered")] = ((reference_summary["Triggered"] / total_agents) * 100)
            shares_summary[_("Deciding")] = ((reference_summary["Deciding"] / reference_summary["Triggered"]) * 100)
            shares_summary[_("Knowing")] = ((reference_summary["Knowing"] / reference_summary["Deciding"]) * 100)
            shares_summary[_("Can afford")] = ((reference_summary["Can afford"] / reference_summary["Knowing"]) * 100)
            shares_summary[_("Certain")] = ((reference_summary["Certain"] / reference_summary["Can afford"]) * 100)
            shares_summary[_("Like")] = ((reference_summary["Like"] / reference_summary["Certain"]) * 100)
            shares_summary[_("Installed")] = ((reference_summary["Installed"] / reference_summary["Like"]) * 100)
        
            # Plot absolute values
            fig_size = (12, 6)
            dpi = 1920 / fig_size[0]
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
        
            # Create a grouped bar chart for absolute values
            bar_width = 0.1
            x = np.arange(len(periods))  # Positions for the periods
            for i, column in enumerate(period_summary.columns):
                bars = ax.bar(
                    x + i * bar_width,
                    period_summary[column],
                    width=bar_width,
                    label=_(column)
                )
                # Annotate each bar with its value
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,  # Center of the bar
                        height + 0.5,                      # Slightly above the bar
                        f"{int(height)}",                  # Text to display
                        ha='center',                       # Horizontal alignment
                        va='bottom'                        # Vertical alignment
                    )
        
            # Add labels and legend
            system_name = settings.main.current_scenario[len("Scenario_"):]
            ax.set_title(_("{imagename} Decision conversion numbers while deciding for {system_name}").format(
                imagename=get_images_name(), system=system_name))
            ax.set_xlabel(_("Periods"))
            ax.set_ylabel(_("Counts"))
            ax.set_xticks(x + bar_width * (len(period_summary.columns) - 1) / 2)
            ax.set_xticklabels(periods)
            ax.legend()
        
            # Save the absolute values plot
            file_path_absolute = f"{self.outpath}/{get_images_name()}Decision_conversion_numbers_{system_name}.png"
            
            plt.savefig(file_path_absolute)
            plt.close()
            
            # Plot shares
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
        
            # Create a grouped bar chart for shares
            for i, column in enumerate(shares_summary.columns):
                bars = ax.bar(
                    x + i * bar_width,
                    shares_summary[column],
                    width=bar_width,
                    label=f"{_(column)} (%)"
                )
                # Annotate each bar with its value
                for bar in bars:
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,  # Center of the bar
                        height + 0.5,                      # Slightly above the bar
                        f"{height:.1f}",                   # Text to display
                        ha='center',                       # Horizontal alignment
                        va='bottom'                        # Vertical alignment
                    )
        
            # Add labels and legend
            if settings.eval.plot_title:
                ax.set_title(f"{get_images_name()}" + _("Decision conversion efficiency while deciding for") + f" {system_name}")
            ax.set_xlabel(_("Periods"))
            ax.set_ylabel(_("Shares (%)"))
            ax.set_xticks(x + bar_width * (len(shares_summary.columns) - 1) / 2)
            ax.set_xticklabels(periods)
            ax.legend()
        
            # Save the shares plot
            file_path_shares = f"{self.outpath}/{get_images_name()}Decision_conversion_efficiency_{system_name}.png"
            
            plt.savefig(file_path_shares)
            plt.close()
    
    def information_outspreading_by_subsidies(self, subsidies):
        """
        Plots how knowledge of specific subsidies spreads over time.

        This method creates a line chart showing the number of agents who
        are aware of the specified subsidies at each step of the simulation.

        Parameters
        ----------
        subsidies : list[str]
            A list of subsidy names to be plotted.
        """
        known_subsidies = self.model_df["Known subsidies"].dropna()
        # Normalize only the dictionary entries into a DataFrame
        if not known_subsidies.empty:
            known_subsidies_df = pd.json_normalize(known_subsidies)
        else:
            print("No data to plot for subsidies")
            return
        
        # Check if there is any data to plot after normalization
        if known_subsidies_df.empty:
            print("No data to plot for subsidies")
            return
        # Setting up the plot
        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)

        for subsidy in subsidies:
            if subsidy in known_subsidies_df.columns:
                aggregated_known_hs = known_subsidies_df[subsidy]

                # Plotting the data for each heating system
                ax.plot(aggregated_known_hs, label=_(subsidy))
            else:
                # The heating system does not exist in the DataFrame
                print(f"Subsidy {subsidy} does not exist in the DataFrame")

        # Customizing the plot
        ax.set_title(_("{imagename}Information overspreading of subsidies").format(
            imagename=get_images_name(self.milieu)))
        ax.set_xlabel(_("Weeks"))
        ax.set_ylabel(_("Number of agents"))
        ax.legend()
        ax.set_xlim(left=0)

        # Saving the figure
        fig.savefig(
            f"{self.outpath}/{get_images_name(self.milieu)}Information outspreading of subsidies.png",
            bbox_inches="tight",
        )

        plt.close()

    def information_outspreading_by_heating_system(self, heating_systems):
        """
        Plots how knowledge of specific heating systems spreads over time.

        This method generates a line chart showing the number of agents who
        have gained knowledge of the specified heating systems at each step.

        Parameters
        ----------
        heating_systems : list[str]
            A list of heating system class names to be plotted.
        """
        known_hs = self.model_df["Known heating systems"]
        known_hs_df = pd.DataFrame(known_hs.tolist())

        # Check if there is any data to plot across desired heating systems
        if known_hs_df[heating_systems].isna().all().all():
            print("No data to plot for heating systems")
            return

        # Setting up the plot
        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)

        for heating_system in heating_systems:
            if heating_system in known_hs_df.columns:
                aggregated_known_hs = known_hs_df[heating_system]

                # Plotting the data for each heating system
                ax.plot(aggregated_known_hs, label=_(heating_system))
            else:
                # The heating system does not exist in the DataFrame
                print(f"Heating system {heating_system} does not exist in the DataFrame")

        # Customizing the plot
        ax.set_title(_("{imagename}Information outspreading of heating systems").format(
            imagename=get_images_name(self.milieu)))
        ax.set_xlabel(_("Weeks"))
        ax.set_ylabel(_("Number of agents"))
        ax.legend()
        ax.set_xlim(left=0)

        # Saving the figure
        fig.savefig(
            f"{self.outpath}/{get_images_name(self.milieu)}Information overspreading of heating systems.png",
            bbox_inches="tight",
        )

        plt.close()

    def call_plotting_function(self, function_to_call, indicators):
        """
        A generic helper to call a plotting function multiple times.

        This utility method iterates through a list of argument tuples and calls
        a specified plotting function for each tuple. It is used to reduce
        code repetition when creating similar plots for different metrics.

        Parameters
        ----------
        function_to_call : Callable
            The plotting function to be executed.
        indicators : list[tuple]
            A list where each element is a tuple of arguments to be passed to
            the plotting function.
        """
        for args_tuple in indicators:
            function_to_call(*args_tuple)

    def hs_budget(self):
        """
        Plots the average agent budget and weekly expenses over time.

        This method creates a two-panel figure. The top panel shows the
        evolution of the average agent's savings (`Budget`), and the bottom
        panel shows their average `Weekly expenses`. Both plots include a
        shaded area representing one standard deviation.
        """

        if hasattr(self,"agent_df"):
            houseowner_df = self.agent_df[self.agent_df["Class"] == "Houseowner"].reset_index()
            budget_filtered = houseowner_df[["Step", "Budget", "Weekly expenses"]]
        
            # Check for non-positive budget values
            if budget_filtered["Budget"].min() < 0:
                print("Budget values must be non-negative, please check the data!")
        
            # Calculate the mean and standard deviation of Budget and Weekly expenses for each step
            df_avg = budget_filtered.groupby("Step").agg(
                Budget_mean=("Budget", "mean"),
                Budget_std=("Budget", "std"),
                Expenses_mean=("Weekly expenses", "mean"),
                Expenses_std=("Weekly expenses", "std")
            ).reset_index()
        
            # Create two subplots for Budget and Weekly expenses
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))
        
            # Plot the average Budget with standard deviation range
            ax1.plot(df_avg["Step"], df_avg["Budget_mean"], label=_("Avg Budget"))
            ax1.fill_between(
                df_avg["Step"],
                df_avg["Budget_mean"] - df_avg["Budget_std"],
                df_avg["Budget_mean"] + df_avg["Budget_std"],
                color="blue",
                alpha=0.2,
                label=_("Budget Range (±1 SD)")
            )
            ax1.set_title(_("Average Budget"))
            ax1.set_xlabel(_("Step"))
            ax1.set_ylabel(_("Average Budget"))
            ax1.legend()
        
            # Plot the average Weekly expenses with standard deviation range
            ax2.plot(df_avg["Step"], df_avg["Expenses_mean"], label=_("Avg Weekly Expenses"))
            ax2.fill_between(
                df_avg["Step"],
                df_avg["Expenses_mean"] - df_avg["Expenses_std"],
                df_avg["Expenses_mean"] + df_avg["Expenses_std"],
                color="green",
                alpha=0.2,
                label=_("Expenses Range (±1 SD)")
            )
            ax2.set_title(_("Average Weekly Expenses, EUR"))
            ax2.set_xlabel(_("Step"))
            ax2.set_ylabel(_("Average Weekly Expenses, EUR"))
            ax2.legend()
        
            # Adjust layout and save plot
            
            plt.savefig(f"{self.outpath}/{get_images_name()}Average Budget and Weekly Expenses with Ranges.png")
            plt.close()

    def average_time_on_stage(self):
        """
        Plots the average time agents spend in each decision-making stage.

        This method creates boxplots to visualise the distribution of time
        (in weeks) that agents typically spend in each stage before
        leaving it.
        """
           
        if hasattr(self,"houseowner_df"):
            # Define figure size and DPI
            fig_size = (15, 5.6)  # Adjusted width for three plots
            dpi = 1920 / fig_size[0]
        
            # Copy the DataFrame to avoid modifying the original
            houseowner_copy = self.houseowner_df.copy()
        
            # Calculate the time spent on each stage
            houseowner_copy["StageChange"] = self.houseowner_df.groupby(
                "AgentID", group_keys=False
            )["Stage"].apply(lambda x: x.ne(x.shift()).cumsum())
        
            # Group by AgentID, StageChange, and Stage and count the occurrences
            stage_counts = houseowner_copy.groupby(
                ["AgentID", "StageChange", "Stage"]
            ).size()
        
            # Reset index to manipulate the DataFrame
            stage_counts_df = stage_counts.reset_index(name="Count")
        
            # Calculate the average time spent on each stage
            average_stage_counts = stage_counts_df.groupby(["AgentID", "Stage"])["Count"].mean()
        
            # Separate data for stage 0 and other stages
            stage_0_data = average_stage_counts[average_stage_counts.index.get_level_values("Stage") == 0]
            other_stages_data = average_stage_counts[average_stage_counts.index.get_level_values("Stage") != 0]
        
            # Identify and filter out outliers using the IQR method for other stages
            q1 = other_stages_data.quantile(0.25)
            q3 = other_stages_data.quantile(0.75)
            iqr = q3 - q1
            filtered_other_stages_data = other_stages_data[
                (other_stages_data >= (q1 - 1.5 * iqr)) & (other_stages_data <= (q3 + 1.5 * iqr))
            ]
        
            # Set up a figure with three subplots
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=fig_size, dpi=dpi)
        
            # Plot for stage 0
            stage_0_data.unstack().plot(kind="box", ax=ax1)
            ax1.set_title(_("{imagename}Average time on stage 0").format(imagename=get_images_name(self.milieu)))
            ax1.set_xlabel(_("Stage 0"))
            ax1.set_ylabel(_("Week"))
        
            # Plot for other stages with outliers
            other_stages_data.unstack().plot(kind="box", ax=ax2)
            ax2.set_title(_("{imagename}Average time on other stages").format(imagename=get_images_name(self.milieu)))
            ax2.set_xlabel(_("Stage"))
            ax2.set_ylabel(_("Week"))
        
            # Plot for other stages without outliers
            filtered_other_stages_data.unstack().plot(kind="box", ax=ax3)
            ax3.set_title(_("{imagename}Average time on other stages (no outliers)").format(
                imagename=get_images_name(self.milieu)))
            ax3.set_xlabel(_("Stage"))
            ax3.set_ylabel(_("Week"))
        
            # Save the figure with all three plots in the same file
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average_time_spent_on_each_stage.png",
                bbox_inches="tight"
            )
            plt.close()

    def compare_attributes(self):
        """
        Creates boxplots comparing attribute ratings between system pairs.

        For each target heating system in a scenario, this method generates
        a series of boxplots. Each plot compares how owners of the target
        system rate their own system versus how they rate an alternative
        system, broken down by each individual attribute (e.g., cost, effort,
        emissions). This reveals detailed perceptual differences.
        """
        if hasattr(self, "agent_df"):
            # Filter DataFrame for the last step and Houseowner class
            filtered_df = self.agent_df[
                (self.agent_df["Class"] == "Houseowner")
                & (self.agent_df["Attribute ratings"].notnull())
            ]
    
            rows = []
            # Expand the attribute ratings to have a row for each system, heating, and category
            for agent_id, row in filtered_df.iterrows():
                owners_heating = row["Heating"]
                attribute_ratings = row["Attribute ratings"]
                owner_id = agent_id
    
                for system, rating in attribute_ratings.items():
                    for category, value in rating.items():
                        rows.append(
                            {
                                "Owner ID": owner_id,
                                "Owners Heating": owners_heating,
                                "System": system,
                                "Category": category,
                                "Value": value,
                            }
                        )
    
            attributes_expanded = pd.DataFrame(rows).set_index("Owner ID")
    
            if attributes_expanded.empty:
                print("Not enough data to compare attitudes")
                return
    
            compare_systems = settings.heating_systems.compare_scenario[
                settings.main.current_scenario
            ]
            labels = [_(label) for label in settings.heating_systems["parameters"]]
    
            # Generate random colors for each category
            bar_colors = ["#{:06x}".format(random.randint(0, 0xFFFFFF)) for _ in labels]
    
            save_dir = f"{self.outpath}/Attribute ratings"
            os.makedirs(save_dir, exist_ok=True)
            systems = settings.heating_systems.list
    
            for compare_system in compare_systems:
                compare_system_name = (
                    compare_system.replace("_", " ").title().replace("Heating System ", "")
                )
    
                for system in systems:
                    if compare_system == system:
                        continue  # Skip comparing the system to itself
    
                    results = []
    
                    filtered_df = attributes_expanded.loc[
                        (attributes_expanded["Owners Heating"] == compare_system)
                    ]
    
                    for param in settings.heating_systems["parameters"]:
                        df1 = attributes_expanded.loc[
                            (attributes_expanded["System"] == compare_system)
                            & (attributes_expanded["Category"] == param),
                        ]
    
                        df2 = attributes_expanded.loc[
                            (attributes_expanded["System"] == system)
                            & (attributes_expanded["Category"] == param),
                        ]
    
                        # Remove a houseowner if they have a 0 rating in any of
                        # the evaluated or compared systems
                        mask = (df1["Value"] != 0) & (df2["Value"] != 0)
    
                        results.append(df1[mask]["Value"] - df2[mask]["Value"])
    
                    # Create a new figure for each comparison
                    plt.figure(figsize=(7, 12))  # Increase figure size for better spacing
                    bp = plt.boxplot(results, labels=labels, vert=True, patch_artist=True)
                    
                    system_name = (
                        system.replace("_", " ").title().replace("Heating System ", "")
                    )
                    
                    # Plotting
                    plt.title(_("{comparesysname} vs {system_name}").format(
                        comparesysname=compare_system_name,
                        system_name=system_name
                    ))
                    plt.xlabel(_("Category"))
                    plt.ylabel(_("Difference"))
                    plt.axhline(0, color="black")
                    plt.ylim(-1.5, 1.5)
                    
                    # Rotate labels and adjust spacing
                    plt.xticks(rotation=45, ha="right")
                    plt.subplots_adjust(bottom=0.25)  # Adjust bottom margin to fit labels
                    
                    for box, color in zip(bp["boxes"], bar_colors):
                        box.set_facecolor(color)
                    
                    # Save the figure with bbox_inches='tight' to prevent clipping
                    plt.savefig(
                        os.path.join(
                            save_dir,
                            f"{get_images_name(self.milieu)}{compare_system_name}_vs_{system_name}.png",
                        ),
                        bbox_inches="tight",  # Ensures all elements fit within the image
                        dpi=300  # Optional: increases image quality
                    )
                    
                    plt.close()

    def compare_attributes_median(self):
        """
        Creates bar plots of median attribute rating differences.

        Similar to `compare_attributes`, this method compares system ratings
        but visualises the results as a bar chart of the *median* difference
        in ratings. The error bars on the chart represent the interquartile
        range (IQR), providing a robust view of the central tendency of
        perceptual differences.
        """
    
        if hasattr(self, "agent_df"):
            # Filter DataFrame for the last step and Houseowner class
            filtered_df = self.agent_df[
                (self.agent_df["Class"] == "Houseowner")
                & (self.agent_df["Attribute ratings"].notnull())
            ]
    
            rows = []
            # Expand the attribute ratings to have a row for each system, heating, and category
            for agent_id, row in filtered_df.iterrows():
                owners_heating = row["Heating"]
                attribute_ratings = row["Attribute ratings"]
                owner_id = agent_id
    
                for system, rating in attribute_ratings.items():
                    for category, value in rating.items():
                        rows.append(
                            {
                                "Owner ID": owner_id,
                                "Owners Heating": owners_heating,
                                "System": system,
                                "Category": category,
                                "Value": value,
                            }
                        )
    
            attributes_expanded = pd.DataFrame(rows).set_index("Owner ID")
    
            if attributes_expanded.empty:
                print("Not enough data to compare attitudes")
                return
    
            compare_systems = settings.heating_systems.compare_scenario[
                settings.main.current_scenario
            ]
            labels = [_(label) for label in settings.heating_systems["parameters"]]
    
            save_dir = f"{self.outpath}/Attribute ratings"
            os.makedirs(save_dir, exist_ok=True)
            systems = settings.heating_systems.list
    
            for compare_system in compare_systems:
                compare_system_name = (
                    compare_system.replace("_", " ").title().replace("Heating System ", "")
                )
    
                for system in systems:
                    if compare_system == system:
                        continue  # Skip comparing the system to itself
    
                    medians = []
                    iqr_errors = []  # IQR as error bars
    
                    for param in settings.heating_systems["parameters"]:
                        df1 = attributes_expanded.loc[
                            (attributes_expanded["System"] == compare_system)
                            & (attributes_expanded["Category"] == param),
                        ]
    
                        df2 = attributes_expanded.loc[
                            (attributes_expanded["System"] == system)
                            & (attributes_expanded["Category"] == param),
                        ]
    
                        # Remove houseowners with 0 rating in either system
                        mask = (df1["Value"] != 0) & (df2["Value"] != 0)
                        data = (df1[mask]["Value"] - df2[mask]["Value"]).dropna()
    
                        if data.empty:
                            medians.append(np.nan)
                            iqr_errors.append((0, 0))
                        else:
                            median_value = np.median(data)
                            q1, q3 = np.percentile(data, [25, 75])  # First and third quartiles
                            iqr = q3 - q1
    
                            medians.append(median_value)
                            iqr_errors.append((median_value - q1, q3 - median_value))
    
                    # Convert IQR errors into numpy arrays for proper plotting
                    iqr_errors = np.array(iqr_errors).T  # Transpose to get lower & upper errors
    
                    # Create a bar plot
                    plt.figure(figsize=(7, 12))
                    plt.bar(labels, medians, yerr=iqr_errors, capsize=5, color="steelblue", alpha=0.7)
    
                    system_name = (
                        system.replace("_", " ").title().replace("Heating System ", "")
                    )
    
                    # Plot styling
                    plt.title(_("{comparesysname} vs {system_name}").format(
                        comparesysname=compare_system_name,
                        system_name=system_name
                    ))
                    plt.xlabel(_("Category"))
                    plt.ylabel(_("Median Difference"))
                    plt.axhline(0, color="black")
                    plt.ylim(-1.5, 1.5)
    
                    # Rotate labels and adjust spacing
                    plt.xticks(rotation=45, ha="right")
                    plt.subplots_adjust(bottom=0.25)
    
                    # Save the figure with bbox_inches='tight' to prevent clipping
                    plt.savefig(
                        os.path.join(
                            save_dir,
                            f"{get_images_name(self.milieu)}{compare_system_name}_vs_{system_name}_median.png",
                        ),
                        bbox_inches="tight",  # Ensures all elements fit within the image
                        dpi=300  # Optional: increases image quality
                    )
    
                    plt.close()
        
    
    def compare_metrics(self):
        """
        Creates detailed comparative plots for comprehensive decision metrics.

        This method generates a set of boxplots that compare agents' ratings
        of different heating systems based on the comprehensive metrics of
        the Theory of Planned Behaviour (Attitude, Social Norm, Perceived
        Behavioural Control).
        """
        if hasattr(self,"agent_df"):
            # Filter DataFrame for the last step and Houseowner class
            filtered_df = self.agent_df[
                (self.agent_df["Class"] == "Houseowner")
                & (self.agent_df["Comprehensive metrics"].notnull())
            ]
    
            rows = []
            # Expand the attribute ratings to have a row for each system, heating and category
            for owner_id, row in filtered_df.iterrows():
                owners_heating = row["Heating"]
                comprehensive_metrics = row["Comprehensive metrics"]
    
                for system, rating in comprehensive_metrics.items():
                    for category, value in rating.items():
                        rows.append(
                            {
                                "Owner ID": owner_id,
                                "Owners Heating": owners_heating,
                                "System": system,
                                "Category": category,
                                "Value": value,
                            }
                        )
    
            attributes_expanded = pd.DataFrame(rows).set_index("Owner ID")
    
            if attributes_expanded.empty:
                print("Not enough data to compare attitudes")
                return
    
            compare_systems = settings.heating_systems.compare_scenario[
                settings.main.current_scenario
            ]
            metrics = settings.heating_systems["comprehensive_metrics"]
    
            # Generate random colors for each category
            bar_colors = {"#{:06x}".format(random.randint(0, 0xFFFFFF)) for _ in metrics}
    
            save_dir = f"{self.outpath}/Comprehensive metrics"
            os.makedirs(save_dir, exist_ok=True)
            systems = settings.heating_systems.list
    
            group_size = 3
    
            # Iterate through metrics by group size - 3
            for i in range(0, len(metrics), group_size):
                for compare_system in compare_systems:
                    # Creating sublot for each compare_system, according to the group size
                    fig, ax = plt.subplots(
                        len(metrics[i : i + group_size]), 1, figsize=(15, 20)
                    )
                    compare_system_name = (
                        compare_system.replace("_", " ")
                        .title()
                        .replace("Heating System ", "")
                    )
    
                    # Iterate through each metric in the group
                    for param_index in range(len(metrics[i : i + group_size])):
                        results = []
    
                        for system in systems:
                            # Skip the compare_system if it is the same as the syste
                            if compare_system == system:
                                continue
    
                            df1 = attributes_expanded.loc[
                                (attributes_expanded["System"] == compare_system)
                                & (
                                    attributes_expanded["Category"]
                                    == metrics[i : i + group_size][param_index]
                                ),
                            ]
    
                            df2 = attributes_expanded.loc[
                                (attributes_expanded["System"] == system)
                                & (
                                    attributes_expanded["Category"]
                                    == metrics[i : i + group_size][param_index]
                                ),
                            ]
    
                            # Remove a houseowner if they have a 0 rating in any of
                            # the evaluated or compared systems
                            mask = (df1["Value"] != 0) & (df2["Value"] != 0)
    
                            results.append(df1[mask]["Value"] - df2[mask]["Value"])
    
                        systems_cut = [_(x) for x in systems if x != compare_system]
    
                        metrics_name = (
                            metrics[i : i + group_size][param_index]
                            .replace("_", " ")
                            .title()
                        )
                        systems_name = [
                            x.replace("_", " ").title().replace("Heating System", "")
                            for x in systems_cut
                        ]
    
                        bp = ax[param_index].boxplot(
                            results, labels=systems_name, vert=True, patch_artist=True
                        )
    
                        # Plotting
                        ax[param_index].set_title(_("{compare_system_name} - {metrics_name}").format(
                            compare_system_name=compare_system_name,
                            metrics_name = metrics_name)
                        )
                        ax[param_index].set_xlabel(_("Category"))
                        ax[param_index].set_ylabel(_("Difference"))
                        ax[param_index].axhline(0, color="black")
                        ax[param_index].set_xticklabels(
                            systems_name, rotation=45, ha="right"
                        )
                        for box, color in zip(bp["boxes"], bar_colors):
                            box.set_facecolor(color)
    
                    
                    # Saving
                    plt.savefig(
                        os.path.join(
                            save_dir,
                            f"{get_images_name(self.milieu)}{compare_system_name} Comparsion for {', '.join(metrics[i:i + group_size])}.png",
                        )
                    )
                    plt.close()

    def stages_distribution(self):
        """
        Plot the distribution of agents across decision-making stages over time.

        This method generates a stacked area chart showing the percentage of
        the total agent population in each stage of the decision-making model
        (e.g., Predecisional, Actional) at each step of the simulation.
        """
        if hasattr(self,"agent_df"):
            # Filter for 'Houseowner' class and reset index for easy manipulation
            stages_filtered = self.agent_df[
                self.agent_df["Class"] == "Houseowner"
            ].reset_index()
    
            # Group by 'Step' and count the occurrences of each 'Stage'
            stage_counts = (
                stages_filtered.groupby(["Step", "Stage"]).size().unstack(fill_value=0)
            )
    
            # Normalize counts to get percentages
            stage_percentages = stage_counts.divide(stage_counts.sum(axis=1), axis=0) * 100
    
            # Plotting
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = stage_percentages.plot(
                kind="area",
                stacked=True,
                title=_("{imagename}Distribution of agents among stages").format(imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Percentage, %"),
                figsize=fig_size,
            )
    
            # Set legend
            legend_stages = settings.decision_making.stages
            h, l = ax.get_legend_handles_labels()
            ax.legend(h[: len(legend_stages)], legend_stages, loc=4)
            # Save plot
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Distribution of agents among stages.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def heating_distribution_advised(self):
        """
        Plots the heating systems chosen by agents who consulted an energy advisor.

        This method filters for houseowners who completed a job with an
        energy advisor and plots a bar chart of the final heating systems 
        they installed. The underlying data is also saved to a JSON file.
        """
        if hasattr(self,"intermediary_df") and hasattr(self,"last_agents"):
            plt.figure()
        
            # Merge data to find relevant agents
            houseowner_ids = self.intermediary_df["Houseowner"]
            merged = self.last_agents[self.last_agents["AgentID"].isin(houseowner_ids)]
        
            # Count and clean heating system names
            counts = merged["Heating"].str.replace("Heating_system_", "").value_counts()
        
            # Save to JSON
            image_name = get_images_name(self.milieu)
            counts.to_json(
                os.path.join(
                    self.outpath, f"{image_name}Heating_distribution_advised.json"
                )
            )
        
            # Plot the data
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = counts.plot(
                kind="bar",
                rot=360,
                figsize=fig_size,
                title=_("{image_name}Heating distribution of advised houseowners").format(image_name=image_name),
            )
        
            # Annotate each bar with the value
            for bar in ax.patches:
                yval = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    yval,
                    round(yval, 2),
                    va="bottom",
                    ha="center",
                )
        
            # Save the plot
            ax.figure.savefig(
                os.path.join(
                    self.outpath, f"{image_name}HS distribution of advised houseowners.png"
                ),
                dpi=dpi,
            )
            plt.close()

    def save_intermediary_progress(self):
        """
        Save the intermediary results DataFrame to a file.

        This utility method serialises the `intermediary_df` DataFrame, which
        contains the records of completed jobs by intermediaries, to either a
        CSV or Excel file, based on the global `serialization_function` setting.
        """
        # TODO: decide which one to use
        # filepath = os.path.join("data", "output", f"agent_results{self.file_ext}")
        # getattr(agent_df, self.serialization_function)(filepath, index = True)
        # filepath = os.path.join("data", "output", f"model_results{self.file_ext}")
        # getattr(model_df, self.serialization_function)(filepath, index = True)
        
        if hasattr(self,"intermediary_df"):
            filepath = os.path.join(
                self.outpath,
                f"{get_images_name()} intermediary_results{self.file_ext}",
            )
            getattr(self.intermediary_df, self.serialization_function)(filepath, index=True)

    def intermediary_queue_length_by_ids(self, ids: list[int], intermediary_type: str):
        """
        Plots the service queue length for specific intermediary agents.

        This method generates a line chart showing the number of jobs in the
        service queue over time, but only for the individual intermediary
        agents specified in the `ids` list. It is used for detailed analysis
        of specific agents' workloads.

        Parameters
        ----------
        ids : list[int]
            A list of intermediary agent IDs to plot.
        intermediary_type : str
            The class name of the intermediary type (e.g., "Plumber").
        """
        if self.intermediary_queue_df:
            grouped_df = (
                self.intermediary_queue_df.groupby(
                    ["Intermediary", "Step", "Intermediary ID"]
                )["Queue Length"]
                .sum()
                .reset_index()
            )
    
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            plt.figure(figsize=fig_size)
    
            for agent_id in ids:
                agent_label = f"{intermediary_type} {agent_id}"
    
                agent_df_grouped = grouped_df[grouped_df["Intermediary ID"] == agent_label]
    
                # Extract the series for each agent
                plt.plot(
                    agent_df_grouped["Step"],
                    agent_df_grouped["Queue Length"],
                    label=agent_label,
                )
    
            plt.xlabel(_("Step"))
            plt.ylabel(_("Aggregated Queue Length"))
            plt.title(_("{imagename} Aggregated Queue Length by {intermediary_type} and Step").format(
                imagename=get_images_name(self.milieu)))
            plt.legend()
            plt.savefig(
                f"{self.outpath}/{get_images_name()} Aggregated Queue Length by {intermediary_type} and Step.png",
                dpi=dpi,
            )
            plt.close()

    def intermediary_queue_length(self, window_size=52):
        """
        Plots the average length of intermediary service queues over time.

        This method calculates the aggregated queue length for each type of
        intermediary at each step and plots a smoothed line (using a moving
        average) to visualise workload.

        Parameters
        ----------
        window_size : int, optional
            The window size in weeks for the moving average calculation, by
            default 52.
        """
        if hasattr(self, "intermediary_queue_df"):
            # Group and sum the queue lengths by intermediary and step
            grouped_df = (
                self.intermediary_queue_df.groupby(["Intermediary", "Step"])["Queue Length"]
                .sum()
                .reset_index()
            )
        
            # Prepare figure
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            plt.figure(figsize=fig_size)
        
            # Calculate moving averages and plot
            for intermediary in grouped_df["Intermediary"].unique():
                subset = grouped_df[grouped_df["Intermediary"] == intermediary].copy()
                
                # Compute moving average of the queue length
                subset["Queue Length MA"] = subset["Queue Length"].rolling(window=window_size, min_periods=1, center = True).mean()
                
                # Track the rate of change using the moving average
                self.rate_of_change[f"Queue Length MA - {intermediary}"] = subset["Queue Length MA"].diff()
                
                # Plot the moving average
                plt.plot(
                    subset["Step"],
                    subset["Queue Length MA"],
                    marker="o",
                    label=_("{intermediary}".format(intermediary=intermediary))
                )
        
            # Add labels and title
            plt.xlabel(_("Step"))
            plt.ylabel(_("Aggregated Queue Length (Moving Average)"))
            plt.title(_("{imagename} Aggregated Queue Length (Moving Average) by Intermediary and Step").format(
                imagename=get_images_name(self.milieu)))
            plt.legend(title=_("Intermediary"))
            
            # Save the plot
            plt.savefig(
                f"{self.outpath}/{get_images_name()} Aggregated Queue Length (Moving Average) by Intermediary and Step.png",
                dpi=dpi,
            )
            plt.close()

    def intermediary_job_progression(self):
        """
        Plots the cumulative number of completed intermediary jobs over time.

        This method creates a step plot showing the total number of
        consultations or installations completed by all intermediary agents
        as the simulation progresses.
        """
        # Prepare the DataFrame with unique steps as index and cumulative job counts
        if hasattr(self,"intermediary_df"):
            df = pd.DataFrame(
                {
                    _("Amount"): self.intermediary_df.index + 1,
                }
            )
            df.index = self.intermediary_df["Step"].astype(int)
            df = df[~df.index.duplicated(keep="last")]
    
            # Ensure that the first and last steps are included in the DataFrame
            if 0 not in df.index:
                df.loc[0] = 0
            if settings.main.steps not in df.index:
                df.loc[settings.main.steps] = len(self.intermediary_df)
            df = df.sort_index()
    
            # Save DataFrame to JSON
            json_path = os.path.join(
                self.outpath,
                f"{get_images_name()} num_completed_jobs.json",
            )
            df.to_json(json_path)
    
            self.rate_of_change["Intermediary job progression"] = (
                df[_("Amount")].fillna(0).diff()
            )
    
            # Plotting configuration
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            plt.figure(figsize=fig_size)
            ax = df.plot(
                drawstyle="steps-post", title=_("{imagename} Number of completed jobs").format(
                    imagename=get_images_name())
            )
            plt.xlabel(_("Step"))
            
            # Save the plot with specified dpi
            image_path = os.path.join(
                self.outpath,
                f"{get_images_name()} Intermediary number of completed jobs.png",
            )
            ax.figure.savefig(image_path, dpi=dpi)
            plt.close()

    def stages_history(self):
        """
        Creates an interactive plot of agent distribution across historical stages.

        Using Plotly, this method generates an interactive stacked area chart
        that shows the percentage of agents who have reached a certain stage
        in their decision-making history. This includes the specific transitions between stages.
        """
        if hasattr(self,"agent_df"):
            # Filter for 'Houseowner' class and reset index for easy manipulation
            stages_filtered = self.agent_df[
                self.agent_df["Class"] == "Houseowner"
            ].reset_index()
    
            # Group by 'Step' and count the occurrences of each 'Stage'
            stage_counts = (
                stages_filtered.groupby(["Step", "History"]).size().unstack(fill_value=0)
            )
    
            # Normalize counts to get percentages
            stage_percentages = stage_counts.divide(stage_counts.sum(axis=1), axis=0) * 100
            stage_renamed = stage_percentages.rename(
                columns=settings.decision_making.stages_numerical
            )
    
            # Convert the DataFrame to a long format
            stage_percentages_long = stage_renamed.reset_index().melt(
                id_vars="Step", var_name="Stage", value_name="Percentage"
            )
    
            # Plotting
            fig = px.area(
                stage_percentages_long,
                x="Step",
                y="Percentage",
                color="Stage",
                labels={"Percentage": _("Percentage, %"), "Step": _("Week")},
                title=_("{imagename}Distribution of agents among stages").format(
                    imagename=get_images_name(self.milieu)),
            )
    
            # Hide the 'No stage' stage
            fig.data[0].visible = "legendonly"
    
            # Save plot
            fig.write_html(
                f"{self.outpath}/{get_images_name(self.milieu)}Distribution of agents among stages.html"
            )
            # fig.show()
            plt.close()

    def deciding_agents_by_ids(
        self,
        column: str,
        ids: list[int],
        tickvals: list[int] = [],
        ticktext: list[str] = [],
    ):
        """
        Creates an interactive plot for a specific metric for individual agents.

        This utility method generates an interactive line chart (using Plotly)
        that tracks a specific column from the agent data (e.g., 'Stage',
        'Budget') over time for a small, specified list of agent IDs. It is
        primarily used for debugging and detailed inspection of individual
        agent behavior.

        Parameters
        ----------
        column : str
            The name of the column in the agent DataFrame to plot.
        ids : list[int]
            A list of agent IDs to include in the plot.
        tickvals : list[int], optional
            Positions for custom ticks on the y-axis.
        ticktext : list[str], optional
            Labels for the custom ticks on the y-axis.
        """
        if hasattr(self,"agent_df"):
            # Reset index to work with 'Step' and 'Houseowner' as columns
            stages_filtered = self.agent_df.reset_index()
    
            # Filter by agent IDs
            stages_filtered = stages_filtered[
                stages_filtered["AgentID"].isin([f"Houseowner {id}" for id in ids])
            ]
    
            # Plot using Plotly Express
            fig = px.line(
                stages_filtered,
                x="Step",
                y=f"{column}",
                color="AgentID",
                markers=True,
                labels={
                    "Step": _("Step (Week)"),
                    f"{column}": _(f"{column}"),
                    "AgentID": _("Houseowners"),
                },
                title=_(f"{column}") + _(" progression over Steps for multiple Houseowners"),
            )
    
            # Customize the y-axis to show the stages:
            fig.update_yaxes(
                tickvals=tickvals,
                ticktext=ticktext,
            )
    
            # Save the figure as an HTML file
            output_file = f"{self.outpath}/{get_images_name(self.milieu)} Generalized Distribution of Houseowners' {column}.html"
            fig.write_html(output_file)
            plt.close()

    def deciding_agents_aggregated(self, step_interval=52):
        """Plots the stage distribution of only the actively deciding agents.

        Unlike `stages_distribution`, this method filters out agents in the
        passive 'Stage 0' and creates a stacked area chart showing the
        proportional distribution of the remaining agents across the active
        decision-making stages.

        Parameters
        ----------
        step_interval : int, optional
            The interval in steps (weeks) at which to group the data, by default 52.
        """
        if hasattr(self,"agent_df"):
            # Reset index to work with 'Step' and 'Houseowner' as columns
            stages_filtered = self.agent_df.reset_index()
    
            # Filter for 'Houseowner' class, assuming 'Class' is a column after resetting the index
            stages_filtered = stages_filtered[stages_filtered["Class"] == "Houseowner"]
            # Exclude agents in the 'No stage' stage
            stages_filtered = stages_filtered[stages_filtered["Stage"] != 0]
    
            # Group by 'Step' and 'Stage', count the occurrences, and normalize
            stage_counts = (
                stages_filtered.groupby(["Step", "Stage"]).size().unstack(fill_value=0)
            )
            total_agents_per_step = stages_filtered.groupby("Step").size()
            stage_percentages = stage_counts.divide(total_agents_per_step, axis=0) * 100
    
            # Aggregate stages by summing up for each 'step_interval'
            # Create a new column for step groups
            stages_filtered["StepGroup"] = (
                stages_filtered["Step"] // step_interval
            ) * step_interval
            grouped = stages_filtered.groupby(["StepGroup", "Stage"])
            stage_counts_grouped = grouped.size().unstack(fill_value=0)
            total_agents_per_step_grouped = stages_filtered.groupby("StepGroup").size()
            stage_percentages_grouped = (
                stage_counts_grouped.divide(total_agents_per_step_grouped, axis=0) * 100
            )
    
            # Moving average for the grouped percentages
            stage_percentages_ma = stage_percentages_grouped.rolling(
                window=3, min_periods=1
            ).mean()
    
            # Plotting
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = stage_percentages_ma.plot(
                kind="area",
                stacked=True,
                title=_("{imagename}Generalized Distribution of Agents in Decision-Making Process").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Weeks"),
                ylabel=_("Percentage of the deciding population, %"),
                figsize=fig_size,
            )
            # Set legend
            legend_stages = [_("Predecisional"), _("Preactional"), _("Actional"), _("Postactional")]
            h, l = ax.get_legend_handles_labels()
            ax.legend(h[: len(legend_stages)], legend_stages, loc="best")
    
            # Save plot
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Generalized Distribution of Agents every {step_interval} Steps.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def share_deciding_agents(self):
        """
        Plots the percentage of agents actively making a decision over time.

        This method generates a line chart showing what fraction of the total
        population is in an active decision-making stage (i.e., not in the
        passive "Stage 0") at each step.
        """
        if hasattr(self,"agent_df"):
            # Filter for 'Houseowner' class
            stages_filtered = self.agent_df[self.agent_df["Class"] == "Houseowner"]
            # Group by 'Step' and count the occurrences of each 'Stage'
            stage_counts = (
                stages_filtered.groupby(["Step", "Stage"]).size().unstack(fill_value=0)
            )
            # Calculate the total number of agents at each step
            total_agents_per_step = stages_filtered.groupby("Step").size()
            # Sum the counts for stages 1 to 4
            active_stages_count = stage_counts.loc[:, 1:4].sum(axis=1)
            # Calculate the percentage of agents in stages 1 to 4 relative to total agents
            active_stages_percentage = (active_stages_count / total_agents_per_step) * 100
    
            self.rate_of_change["Amount of deciding agents"] = active_stages_count.fillna(
                0
            ).diff()
            # Plotting
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = active_stages_percentage.plot(
                kind="line",
                title=_("{imagename}Percentage of deciding agents").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Percentage of deciding agents, %"),
                figsize=fig_size,
                ylim=(0, None),
            )
    
            # Save plot
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Percentage of deciding agents.png",
                dpi=dpi,
            )
            plt.close()

    def heating_distribution(self):
        """
        Plots the distribution of installed heating systems over time.

        This method generates a stacked area chart showing the total number
        of each type of heating system installed in the agent population at
        each step of the simulation.
        """
        if hasattr(self,"agent_df"):
            # Ensure 'Step' and 'AgentID' are columns, not part of a MultiIndex
            agent_df = self.agent_df.reset_index()
    
            # Filter for 'Houseowner' class and focus on 'Heating' data
            heating_filtered = agent_df[agent_df["Class"] == "Houseowner"][
                ["Step", "Heating"]
            ]
    
            # Group by 'Step' and count the occurrences of each 'Heating' type
            heating_counts = (
                heating_filtered.groupby(["Step", "Heating"]).size().unstack(fill_value=0)
            )
    
            # Define a consistent colormap with 8 colors
            color_map = {
                "Heating_system_oil": "#1f77b4",  # blue
                "Heating_system_gas": "#ff7f0e",  # orange
                "Heating_system_heat_pump": "#2ca02c",  # green
                "Heating_system_electricity": "#7f7f7f",  # red
                "Heating_system_pellet": "#9467bd",  # purple
                "Heating_system_network_district": "#8c564b",  # brown
                "Heating_system_network_local": "#e377c2",  # pink
                "Heating_system_heat_pump_brine": "#d62728",  # gray
            }
            
            desired_order = [
                "Heating_system_heat_pump",
                "Heating_system_heat_pump_brine",
                "Heating_system_oil",
                "Heating_system_gas",
                "Heating_system_electricity",
                "Heating_system_pellet",
                "Heating_system_network_district",
                "Heating_system_network_local",
            ]
            
            # Reorder columns, keeping only those present in the dataset
            heating_types = [ht for ht in desired_order if ht in heating_counts.columns]
            heating_counts = heating_counts[heating_types]
            
            # Define colors in the same order
            colors = [color_map[ht] for ht in heating_types]
            
            # Plot with reordered columns
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = heating_counts.plot(
                kind="area",
                stacked=True,
                title=_("{imagename}Distribution of heating systems among agents").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Systems, units"),
                figsize=fig_size,
                color=colors,  # Use the reordered colors
            )
            
            # Set legend
            legend_heating = heating_counts.columns.to_list()
            h, l = ax.get_legend_handles_labels()
            ax.legend(h[: len(legend_heating)], legend_heating, loc=4)
            
            # Save plot
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Distribution of heating systems among agents.png",
                dpi=dpi,
            )
            plt.close()

    def average_HS_age(self):
        """
        Plots the average age for each type of heating system over time.

        This method creates a line chart with a separate line for each heating
        system type, showing how the average age of that specific technology
        evolves throughout the simulation.
        """
        if hasattr(self,"agent_df"):
            ages_filtered = self.agent_df[self.agent_df["Class"] == "Houseowner"][
                ["System age"]
            ]  # Initial df
    
            ages_rate_of_change = ages_filtered.groupby("Step").mean().fillna(0).diff()
            self.rate_of_change["Average system age"] = ages_rate_of_change["System age"]
    
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = (
                ages_filtered.groupby("Step")
                .mean()
                .plot.line(
                    title=_("{imagename}Average system age").format(
                        imagename=get_images_name(self.milieu)),
                    xlabel=_("Week"),
                    ylabel=_("Years"),
                    ylim=(0, None),
                    figsize=fig_size,
                )
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average system age.png",
                dpi=dpi,
            )
            plt.close()

    def opex(self):
        """
        Plots the average total operating expenses per household over time.

        This method creates a line chart showing the average maintenance costs, 
        for a household across the simulation.
        """
        if hasattr(self,"agent_df"):
            df_filtered = self.agent_df[self.agent_df["Class"] == "Houseowner"][
                ["Opex"]
            ]  # Initial df
            self.rate_of_change["Opex"] = (
                self.agent_df["Opex"].groupby("Step").mean().fillna(0).diff()
            )
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = (
                df_filtered.groupby("Step")
                .mean()
                .plot.line(
                    title=_("{imagename}Average total operating expenses").format(
                        imagename=get_images_name(self.milieu)),
                    xlabel=_("Week"),
                    ylabel=_("EUR"),
                    ylim=(None, None),
                    figsize=fig_size,
                )
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average total operating expenses.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def average_HS_age_per_system(self):
        """
        Plots the average age for each type of heating system over time.

        This method creates a line chart with a separate line for each heating
        system type, showing how the average age of that specific technology
        evolves throughout the simulation.
        """
        if hasattr(self,"agent_df"):
            df_filtered = self.agent_df.loc[
                self.agent_df["Class"] == "Houseowner", ["Heating", "System age"]
            ]
            df_grouped = (
                df_filtered.groupby(["Step", "Heating"])["System age"].mean().unstack()
            )
    
            for column in df_grouped.columns:
                self.rate_of_change[f"Average system age - {column}"] = (
                    df_grouped[column].fillna(0).diff()
                )
    
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = df_grouped.plot.line(
                title=_("{imagename}Average System Age per Heating System").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Years"),
                ylim=(0, None),
                figsize=fig_size,
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average system age per system.png",
                dpi=dpi,
            )
            plt.close()

    def average_satisfaction(self):
        """
        Plots the average owner satisfaction for each heating system type over time.

        This method visualises the `Satisfied_ratio` for each heating system,
        which is influenced by the opinions of neighbouring agents. It shows how
        the perceived satisfaction with different technologies evolves.
        """
        if hasattr(self,"agent_df"):
            opinions_filtered = self.agent_df[self.agent_df["Class"] == "Houseowner"][
                ["Heating", "Satisfied_ratio"]
            ]
            opinions_rate_of_change = (
                opinions_filtered.groupby(["Step", "Heating"])
                .mean()
                .unstack()
                .fillna(0)
                .diff()
            )
    
            for column in opinions_rate_of_change.columns:
                self.rate_of_change[f"Average satisfaction - {column}"] = (
                    opinions_rate_of_change[column]
                )
    
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = (
                opinions_filtered.groupby(["Step", "Heating"])
                .mean()
                .unstack(level=-1)
                .plot.line(
                    title=_("{imagename}Average satisfaction by HS").format(
                        imagename=get_images_name(self.milieu)),
                    xlabel=_("Week"),
                    ylabel=_("Satisfied_ratio"),
                    ylim=(0, 1.1),
                    figsize=fig_size,
                )
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average opinion by HS.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def emissions(self):
        """
        Plots the average CO2 equivalent emissions per household over time.
        """
        # print(self.agent_df)
        if hasattr(self, "agent_df"):
            self.rate_of_change["Emissions"] = self.model_df[["Emissions"]].fillna(0).diff()
    
            emissions_filtered = self.agent_df[["Emissions"]].copy()
            emissions_filtered = emissions_filtered.groupby(["Step"]).mean(
                numeric_only=True
            )
    
            emissions_filtered["Emissions"] /= 1000000  # To get nicer numbers
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = emissions_filtered.plot.line(
                title=_("{imagename}Average emissions").format(imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Average Emissions, tons of CO2 equivalent per year"),
                ylim=(0, None),
                figsize=fig_size,
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average emissions.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def energy_demand(self):
        """
        Plots the average energy demand per household over time.
        """
        if hasattr(self,"agent_df"):
            self.rate_of_change["Energy demand"] = (
                self.model_df[["Energy demand"]].fillna(0).diff()
            )
            demand_filtered = self.agent_df[["Energy demand"]].copy()
            demand_filtered = demand_filtered.groupby(["Step"]).mean(numeric_only=True)
    
            demand_filtered["Energy demand"] /= 1000  # To get nicer numbers
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            ax = demand_filtered.plot.line(
                title=_("{imagename}Average energy demand").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Energy demand, MWh per year"),
                ylim=(0, None),
                figsize=fig_size,
            )
            ax.figure.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}Average energy demand.png",
                dpi=dpi,
            )
            # plt.show()
            plt.close()

    def scenario_fulfilment_comp(self):
        """
        Creates a comparative line plot of scenario fulfillment.

        This method is designed to plot the 'Scenario fulfilment' metric from
        multiple runs or scenarios overlaid on a single chart for direct
        comparison. It reads the 'scenario' column from the model's DataFrame
        to group the data.
        """
        df = self.model_df[["Scenario fulfilment","scenario"]].copy()
        
        df.reset_index(inplace=True)
        df['index'] = (df['index']/ 52) + settings.eval.start_year
        
        grouped = df.groupby(["index", "scenario"])
        data = grouped["Scenario fulfilment"].apply(np.mean)
        data_wide = data.unstack(level=-1)
        
        ax1 = data_wide.plot()

        if settings.eval.plot_title:
            ax1.set_title(_("Scenario fulfillment"))
        ax1.set_xlabel(_("Year"))
        ax1.set_ylabel(_("Percentage"))
        ax1.set_ylim(0, 100)

        # Bring the line plot to the front
        #ax1.set_zorder(2)
        #ax1.patch.set_visible(False)  # Hide the background of the primary axis
        ax1.legend(title=_('Scenario'))
        
        # Save the figure
        fig = ax1.get_figure()
        output_dir = get_output_path(runid=settings.main.run_id, subfolder='ScenarioFulfillment')
        output_path = os.path.join(output_dir, f"{get_images_name()}_ScenarioFulfillment.png")
        fig.set_size_inches(settings.eval.width, settings.eval.height)
        fig.savefig(output_path, dpi=settings.eval.dpi)
        plt.close()
           
    def scenario_fulfilment(self):
        """
        Plots the model's progress toward the defined scenario goal.

        This method visualises the "Scenario fulfilment" metric, showing the
        percentage of the target state (i.e. market share of a technology)
        that has been achieved over time. It also includes a secondary axis
        with a bar chart showing the rate of change.
        """
        fulfilment_filtered = self.model_df[["Scenario fulfilment"]].copy()

        # Calculate the rate of change
        fulfilment_filtered["Rate of Change"] = (
            fulfilment_filtered["Scenario fulfilment"].fillna(0).diff()
        )

        self.rate_of_change["Scenario fulfilment"] = fulfilment_filtered[
            "Rate of Change"
        ]

        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]

        # Create the figure and the primary axis
        fig, ax1 = plt.subplots(figsize=fig_size)

        # Plot the 'Rate of Change' as a bar chart on the secondary axis (background)
        ax2 = ax1.twinx()
        ax2.bar(
            fulfilment_filtered.index,
            fulfilment_filtered["Rate of Change"],
            color="red",
            alpha=0.5,
            label=_("Rate of Change"),
            width=0.8,
        )
        ax2.set_ylabel(_("Rate of Change"))
        ax2.grid(False)  # Disable grid on the secondary axis

        # Plot the 'Scenario fulfilment' as a line chart on the primary axis (foreground)
        ax1.plot(
            fulfilment_filtered.index,
            fulfilment_filtered["Scenario fulfilment"],
            color="blue",
            label=_("Scenario fulfillment"),
        )
        ax1.set_title(_("{imagename} Scenario fulfillment").format(
            imagename=get_images_name()))
        ax1.set_xlabel(_("Week"))
        ax1.set_ylabel(_("Percentage, %"))
        ax1.set_ylim(0, 100)

        # Bring the line plot to the front
        ax1.set_zorder(2)
        ax1.patch.set_visible(False)  # Hide the background of the primary axis

        # Save the figure
        fig.savefig(
            f"{self.outpath}/{get_images_name()} Scenario fulfilment.png",
            dpi=dpi,
        )
        plt.close()
        
    def indicator_plot_by_ids(
        self,
        column_name: str,
        ylim_min,
        ylim_max,
        ylabel: str,
        ids: list[int],
        divider: int = 1,
    ):
        """
        Plot a single indicator over time for specified agent IDs.

        This is a plotting utility that generates a simple line chart for a
        given metric (`column_name`) for a list of specified agent `ids`. It
        is called by `individual_plots_by_ids` to create detailed views of
        individual agent trajectories.

        Parameters
        ----------
        column_name : str
            The name of the column/metric to plot.
        ylim_min : float or None
            The minimum value for the y-axis.
        ylim_max : float or None
            The maximum value for the y-axis.
        ylabel : str
            The label for the y-axis.
        ids : list[int]
            A list of agent IDs to plot.
        divider : int, optional
            A factor to divide the metric by for scaling (e.g., 1000 to convert
            from kWh to MWh), by default 1.
        """
        if hasattr(self,"houseowner_df"):
            # Filter by agent IDs
            agent_labels = [f"Houseowner {agent_id}" for agent_id in ids]
            filtered_houseowners_df = self.houseowner_df[
                self.houseowner_df.index.isin(agent_labels, level=1)
            ].copy()
            # Save multiindex for later use
            multiindex = filtered_houseowners_df.index
            unique_agents = multiindex.get_level_values(1).unique()
    
            # Group by 'Step' and 'AgentID' and calculate the mean of the specified column
            df_grouped = filtered_houseowners_df.groupby(
                [multiindex.get_level_values(0), multiindex.get_level_values(1)]
            )
            df_grouped = (
                df_grouped[column_name].mean(numeric_only=True).div(divider)
            )  # Divide to get nicer numbers
    
            for agent_label in unique_agents:
                agent_df_grouped = df_grouped.xs(
                    agent_label, level=1
                )  # Extract the series for each agent
                plt.plot(agent_df_grouped, label=agent_label)
    
            plt.title(
                _("Avarage {imagename}{column_name} for individual agents").format(
                    imagename=get_images_name(self.milieu),
                    column_name=column_name)
            )
            plt.xlabel(_("Weeks"))
            plt.ylabel(_("{column_name}, {ylabel}").format(column_name=column_name, ylabel=ylabel))
            plt.ylim(ylim_min, ylim_max)
            plt.legend()
    
            plt.savefig(
                f"{self.outpath}/{get_images_name(self.milieu)}{column_name} for individual agents.png"
            )
            plt.close()

    def optimality(self):
        """
        Plots the average optimality of agents' choices over time.

        This method visualises the model's "Suboptimality" metric, which is a
        ratio indicating how close an agent's chosen heating system is to the
        best option available to them. A value of 1 represents a
        perfectly optimal choice.
        """
        if hasattr(self,"agent_df"):
            df_filtered = self.agent_df[self.agent_df["Class"] == "Houseowner"][
                ["Suboptimality"]
            ]
            df_grouped = df_filtered.groupby(["Step"])["Suboptimality"].mean()
            self.rate_of_change["Optimality"] = df_grouped.fillna(0).diff()
    
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
            ax.set_title(_("{imagename}Optimality").format(imagename=get_images_name(self.milieu)))
            ax.set_xlabel(_("Weeks"))
            ax.set_ylabel(_("Optimality, ratio"))
            ax.set_ylim(0, 1)
            ax.plot(df_grouped)
            fig.savefig(f"{self.outpath}/{get_images_name(self.milieu)}Optimality.png")
            plt.close()

    def preferences(self):
        """
        Plots the distribution of agent preferences at the end of the simulation.

        This method creates a boxplot showing the distribution of final
        preference weights (e.g., for cost, emissions, effort) across the
        entire houseowner population, providing a snapshot of the collective values.
        """
        if hasattr(self, "agent_df"):
            # Filter DataFrame for the last step and Houseowner class
            # Determine the last step from settings
            self.last_step = settings.main.steps
            filtered_df = self.agent_df.xs(self.last_step, level="Step")
            filtered_df = filtered_df[filtered_df["Class"] == "Houseowner"]
    
            # Prepare to collect preferences for distribution visualization
            preferences_collection = {
                key: []
                for key in [
                    "operation_effort",
                    "fuel_cost",
                    "emissions",
                    "price",
                    "installation_effort",
                    "opex",
                ]
            }
    
            # Iterate through each row to aggregate the preferences
            for preferences in filtered_df["Preferences"]:
                for key in preferences_collection:
                    preferences_collection[key].append(preferences[key])
    
            # Organize data for plotting
            data_to_plot = [preferences_collection[key] for key in preferences_collection]
            labels = list(preferences_collection.keys())
    
            # Plotting the results
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
            bp = ax.boxplot(data_to_plot, labels=labels, vert=True, patch_artist=True)
            ax.set_title(
                _("{imagename}Distribution of Preferences of Houseowners").format(
                    imagename=get_images_name(self.milieu))
            )
            ax.set_ylabel(_("Value"))
    
            # Customize colors of boxplots
            colors = ["red", "blue", "green", "yellow", "purple", "orange"]
            for box, color in zip(bp["boxes"], colors):
                box.set_facecolor(color)
    
            # Save the figure
            fig.savefig(f"{self.outpath}/{get_images_name(self.milieu)}Preferences.png")
            plt.close()

    def trigger_amount(self):
        """
        Plots the total number of triggers that have occurred over time.
        """
        column_name = "Trigger counter"
        self.rate_of_change["Trigger amount"] = (
            self.model_df[column_name].fillna(0).diff()
        )
        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
        ax.set_title(_("{imagename} Amount of triggers").format(
            imagename=get_images_name()))
        ax.set_xlabel(_("Weeks"))
        ax.set_ylabel(_("Number of triggers, units"))
        ax.plot(self.model_df.index, self.model_df[column_name])
        fig.savefig(f"{self.outpath}/{get_images_name()} Amount of triggers.png")
        plt.close()

    def trigger_types(self):
        """
        Plots the distribution of different trigger types over time.

        This method creates an interactive area chart (using Plotly) that shows
        the number of agents who have been activated by each type of trigger
        (e.g., "Breakdown", "Price shock") at each step.
        """
        if hasattr(self,"houseowner_df"):
            # Group by 'Step' and count the occurrences of each trigger type
            trigger_counts = (
                self.houseowner_df.groupby(["Step", "Trigger"]).size().unstack(fill_value=0)
            )
    
            # Plotting
            fig = px.area(
                trigger_counts,
                title=f"{get_images_name(self.milieu)}Distribution of different triggers among stages",
            )
    
            # Hide the 'Trigger none' trace and replace underscores with spaces in the legend
            for trace in fig.data:
                trace.name = _(trace.name).replace("_", " ")
                if trace.name == "Trigger none":
                    trace.visible = "legendonly"
    
            # Save plot
            fig.write_html(
                f"{self.outpath}/{get_images_name(self.milieu)}Distribution of different triggers among stages.html"
            )
            plt.close()
        
    def area_trigger_types(self):
        """
        Creates a stacked area plot of cumulative trigger counts over time.

        This method visualises the total number of times each trigger type has
        occurred up to each point in the simulation. The stacked area format
        shows both the individual contribution of each trigger and the overall
        growth in triggered events.
        """
        
        # Extract and transform "Trigger types" data into a DataFrame
        trigger_types_series = self.model_df["Trigger types"]
        trigger_types_df = pd.DataFrame(trigger_types_series.tolist()).fillna(0)  # Each column represents a trigger type
    
        # Exclude 'Trigger_none' column if it exists
        if 'Trigger_none' in trigger_types_df.columns:
            trigger_types_df = trigger_types_df.drop(columns=['Trigger_none'])
    
        # Calculate the cumulative sum for each trigger type over time
        cumulative_trigger_types = trigger_types_df
        cumulative_trigger_types.columns = cumulative_trigger_types.columns.map(_)
        
        # Set up the plot
        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
    
        # Create the area plot
        cumulative_trigger_types.plot.area(ax=ax, stacked=True)
    
        # Customize the plot
        ax.set_title(_("{imagename}Cumulative Trigger Types Over Time").format(
            imagename=get_images_name(self.milieu)))
        ax.set_xlabel(_("Weeks"))  # Assuming index represents steps/weeks
        ax.set_ylabel(_("Trigger Types"))
        ax.legend(title=_("Trigger Types"), bbox_to_anchor=(1.05, 1), loc='upper left')
        
        # Save the figure
        fig.savefig(f"{self.outpath}/{get_images_name(self.milieu)}Trigger types area.png", bbox_inches="tight")
    
        # Close the plot to free up memory
        plt.close()    
        
    def information_source_calls(self):
        """
        Plots the total number of times each information source was consulted.

        This method generates a bar chart showing the final count of how many
        times agents used each information source (e.g., "Internet", "Plumber")
        throughout the entire simulation.
        """

        # Get the dict from the last step, removing the 'Information_source_' prefix
        last_dict = {
            key.replace("Information_source_", ""): value
            for key, value in self.model_df["Information source calls"].iloc[-1].items()
        }

        # Generate categories and collect values in one loop
        categories = []
        values = []
        for source in settings.information_source.list:
            category = f"{source}_{self.milieu}" if self.milieu else source
            categories.append(_(source.capitalize()))
            values.append(last_dict.get(category, 0))

        # Plot
        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
        bars = ax.bar(categories, values)
        ax.set_title(
            _("{imagename}Frequency of information source calls").format(
                imagename=get_images_name(self.milieu))
        )
        ax.set_xlabel(_("Type of source"))
        ax.set_ylabel(_("Calls, units"))
        for bar in bars:
            yval = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                yval,
                round(yval, 2),
                va="bottom",
                ha="center",
            )
        fig.savefig(
            f"{self.outpath}/{get_images_name(self.milieu)}Information source calls.png",
            bbox_inches="tight",
        )
        plt.close()

    def changes_and_replacements(self):
        """
        Plots the cumulative number of system changes and replacements over time.
        """
        changes = self.model_df["Changes"]  # .diff().fillna(0)
        replacements = self.model_df["Replacements"]  # .diff().fillna(0)

        changes_df = pd.DataFrame(changes.tolist())
        replacements_df = pd.DataFrame(replacements.tolist())

        aggregated_changes = changes_df.sum(axis=1)
        aggregated_replacements = replacements_df.sum(axis=1)

        self.rate_of_change["Changes"] = aggregated_changes.fillna(0).diff()
        self.rate_of_change["Replacements"] = aggregated_replacements.fillna(0).diff()

        if self.milieu:
            aggregated_changes = changes_df[self.milieu]
            aggregated_replacements = replacements_df[self.milieu]

        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)

        ax.plot(aggregated_replacements, label=_("Replacements"))
        ax.plot(aggregated_changes, label=_("Changes"))

        ax.set_title(_("{imagename}Changes and replacements").format(
            imagename=get_images_name(self.milieu)))
        ax.set_xlabel(_("Weeks"))
        ax.set_ylabel(_("Number of events, units"))
        ax.legend()

        fig.savefig(
            f"{self.outpath}/{get_images_name(self.milieu)}Changes and replacements.png",
            bbox_inches="tight",
        )
        plt.close()
    
    def subsidised_hs(self):
        """
        Plots the number of households with a subsidised system installed.
        """
        hs_filtered = self.model_df["Subsidised houses"]  # Initial df

        fig_size = (10, 5.6)
        dpi = 1920 / fig_size[0]
        ax = (
            hs_filtered.plot.line(
                title=_("{imagename}Houses with a subsidised system installed").format(
                    imagename=get_images_name(self.milieu)),
                xlabel=_("Week"),
                ylabel=_("Houses"),
                ylim=(0, None),
                figsize=fig_size,
            )
        )
        ax.figure.savefig(
            f"{self.outpath}/{get_images_name(self.milieu)}Houses with a subsidised system installed.png",
            dpi=dpi,
        )
        plt.close()
  
    def dropouts_bars_in_periods(self, option, labels_sheet="dropouts"):
        """
        Analyses and plot dropout reasons within distinct time periods.

        This method provides a detailed temporal analysis of why agents fail
        to adopt a specific heating system. It divides the simulation into
        equal periods and creates a grouped bar chart showing the number of
        "dropouts" for each reason within each period.

        Parameters
        ----------
        option : str
            The name of the heating system to analyze dropouts for.
        labels_sheet : str, optional
            The name of the sheet in the labels Excel file to use for plotting,
            by default "dropouts".
        """
        # Extract and transform "Drop-Outs" data into a DataFrame
        dropouts_series = self.model_df["Drop-outs"]  # Each entry is a nested dictionary (converted DataFrame row)

        # Flatten nested dictionaries into a standard DataFrame
        all_dropouts_df = pd.json_normalize(dropouts_series).fillna(0)  # Flatten nested dictionaries
        all_dropouts_df = all_dropouts_df.filter(regex=f".*{option}\\.", axis=1)
                
        # Apply transformations to numeric data
        all_dropouts_df = all_dropouts_df.diff().fillna(0)  # Compute incremental changes
        
        # TODO SH
        index = all_dropouts_df.index.values.astype(int)
        all_dropouts_df.reset_index(inplace=True)
        period = settings.eval.years_in_period
        all_dropouts_df['index'] = np.char.add(np.char.add((np.floor((index/ 52) / period) * period + settings.eval.start_year).astype(int).astype(str)," - "),
                (np.ceil(((index  + 1)/ 52) / period) * period + settings.eval.start_year).astype(int).astype(str))
        all_dropouts_df = all_dropouts_df.groupby(["index"]).apply(np.sum, include_groups=False)
        
        labels = np.unique(all_dropouts_df.index)
        all_dropouts_df = all_dropouts_df.transpose()
        # rows: drops-outs; cols: periods
        
        labelsdf = getLabels(labels_sheet=labels_sheet, ascending=True)
        all_dropouts_df.index = all_dropouts_df.index.str.replace("Heating_system_"+ option + ".", "")
        all_dropouts_df["order"] = all_dropouts_df.index.map(
            dict(
                    zip(labelsdf["value"], range(len(labelsdf)))
                )
            ).astype("int")
        all_dropouts_df = all_dropouts_df.sort_values(["order"]).drop(columns="order")
            
        
        x = np.arange(len(labels))  # the label locations
        width = 1 / (len(all_dropouts_df) + 1)  # the width of the bars
        multiplier = 0
        
        fig, ax = plt.subplots() #layout='constrained')
        fig.set_size_inches(settings.eval.width, settings.eval.height)
        for dropout, row in all_dropouts_df.iterrows():
            offset = width * multiplier
            # plot dropout for all periods
            dropout = labelsdf[labelsdf["value"]==dropout]["label"].iloc[0]
            rects = ax.bar(x + offset, row, width, label=_(dropout),
                           color = labelsdf[labelsdf["label"]==dropout]["colour"])
            ax.bar_label(rects, padding=3)
            multiplier += 1
    
        # Add some text for labels, title and custom x-axis tick labels, etc.
        ax.set_ylabel(_('Decisions'))
        if settings.eval.plot_title:
            ax.set_title(_('Drop outs for ') + _(option))
        ax.set_xticks(x + width*(len(all_dropouts_df)-1)/2, labels)
        ax.legend(loc='upper left', ncols=3)
        ax.set_ylim(0, 120)
        
        # Save the figure
        output_dir = get_output_path(runid=settings.main.run_id, subfolder='Affordability_decisions')
        output_path = os.path.join(output_dir, f"{get_images_name(self.milieu)}{option}_Affordability_Decisions.png")
        fig.tight_layout()
        fig.savefig(output_path, bbox_inches="tight", dpi=settings.eval.dpi)
        
        # Close the plot to free up memory
        plt.close()

    def dropouts(self):
        """
        Plots the reasons why agents stop considering a certain heating option.

        This method creates line charts that track the number of agents who
        fail to adopt a specific heating system, broken down by the reason
        for their "dropout" (e.g., affordability, risk).
        """
        
        # Extract and transform "Drop-Outs" data into a DataFrame
        dropouts_series = self.model_df["Drop-outs"]  # Each entry is a nested dictionary (converted DataFrame row)
        
        # Flatten nested dictionaries into a standard DataFrame
        all_dropouts_df = pd.json_normalize(dropouts_series).fillna(0)  # Flatten nested dictionaries
        
        # Apply transformations to numeric data
        all_dropouts_df = all_dropouts_df.diff().fillna(0)  # Compute incremental changes
        smoothed_df = all_dropouts_df.rolling(window=52, center=True).mean()  # Smooth over a 52-week window
        
        # Extract the list of unique top-level options (columns grouped by option)
        options = {col.split('.')[0] for col in smoothed_df.columns}
        
        # Create the output directory
        output_dir = f"{self.outpath}/Affordability_decisions"
        os.makedirs(output_dir, exist_ok=True)
        
        # Create and save a plot for each option
        for option in options:
            # Filter data for the current option (exact match)
            option_data = smoothed_df.filter(regex=f"^{option}\\.", axis=1)
            
            option_data.index = (option_data.index.values / 52 + settings.eval.start_year).astype(int)
            
            # Prepare the figure
            fig_size = (10, 5.6)
            dpi = 1920 / fig_size[0]
            fig, ax = plt.subplots(figsize=fig_size, dpi=dpi)
            
            # Plot each reason as a separate line
            for reason in option_data.columns:
                ax.plot(option_data.index, option_data[reason], label=_(reason.split('.')[-1]))
            
            # Customize the plot
            if settings.eval.plot_title:
                ax.set_title(_("{imagename}Drop-Outs for {option}").format(
                    imagename=get_images_name(self.milieu), option=option))
            ax.set_xlabel(_("Years"))
            ax.set_ylabel(_("Decisions"))
            ax.set_ylim(0, 1)
            ax.legend(title=_("Decision Type"), loc="upper left", bbox_to_anchor=(1.05, 1))
            
            # Save the figure
            output_path = os.path.join(output_dir, f"{get_images_name(self.milieu)}{option}_Affordability_Decisions.png")
            fig.tight_layout()
            fig.savefig(output_path, bbox_inches="tight")
            
            # Close the plot to free up memory
            plt.close()

    def hs_budget_installation_ratios(self):
        """
        Plots the number of agents who can and cannot afford each heating system.

        This method generates area plots for each heating system type, showing
        the evolution of how many agents have a budget sufficient to cover the
        installation cost.
        """
        if hasattr(self,"agent_df"):
            # Reset the index to access Step or filter directly on the MultiIndex
            houseowner_df = self.agent_df.reset_index()
            houseowner_df = houseowner_df[houseowner_df["Class"] == "Houseowner"]
        
            # Ensure the 'Step' column is included (it comes from resetting the index)
            budgets = houseowner_df[["Step", "Budget", "House area"]]
        
            # Define heating systems
            heating_systems = [
                "Heating_system_oil",
                "Heating_system_gas",
                "Heating_system_heat_pump",
                "Heating_system_electricity",
                "Heating_system_pellet",
                "Heating_system_network_district",
                "Heating_system_network_local",
                "Heating_system_heat_pump_brine",
            ]
        
            # Precompute installation costs for all systems
            costs = {}
            for system in heating_systems:
                params = self.params_table.content.loc[system]
                price = params["price"]
                factor_area = params["factor_area"]
                factor_oppendorf = params["factor_oppendorf"]
                price_index = params["price_index"]
                sidecosts_index = params["sidecosts_index"]
        
                # Vectorized installation cost calculation
                costs[system] = (
                    price
                    * (budgets["House area"] ** factor_area)
                    * budgets["House area"]
                    * factor_oppendorf
                    * price_index
                    * sidecosts_index
                )
        
            # Compute ratios for all systems
            ratios = {system: budgets["Budget"] / costs[system] for system in heating_systems}
        
            # Combine all ratios into a single DataFrame
            ratios_df = pd.DataFrame(ratios)
            ratios_df["Step"] = budgets["Step"]
        
            # Create subplots for all heating systems
            num_systems = len(heating_systems)
            cols = 2
            rows = (num_systems + 1) // cols
        
            fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
            axes = axes.flatten()  # Flatten in case we have a grid larger than needed
        
            for idx, system in enumerate(heating_systems):
                # Calculate median, std deviation for each step
                df_stats = ratios_df.groupby("Step")[system].agg(
                    Ratio_mean="mean",
                    Ratio_std="std",
                ).reset_index()
        
                # Calculate upper and lower bounds as ±1 standard deviation
                df_stats["Ratio_upper"] = df_stats["Ratio_mean"] + df_stats["Ratio_std"]
                df_stats["Ratio_lower"] = df_stats["Ratio_mean"] - df_stats["Ratio_std"]
        
                ax = axes[idx]
                ax.plot(df_stats["Step"], df_stats["Ratio_mean"], label=_("Mean Ratio"), color="blue")
                ax.fill_between(
                    df_stats["Step"],
                    df_stats["Ratio_lower"],
                    df_stats["Ratio_upper"],
                    color="blue",
                    alpha=0.2,
                    label=_("±1 Std Dev")
                )
                ax.axhline(1, color="red", linestyle="--", label=_("Affordability Threshold (1.0)"))
                ax.set_title(_(system))
                ax.set_xlabel(_("Weeks"))
                ax.set_ylabel(_("Budget / Installation Cost Ratio"))
                ax.legend()
        
            # Hide unused subplots
            for idx in range(num_systems, len(axes)):
                fig.delaxes(axes[idx])
        
            # Adjust layout and save the combined plot
            
            plt.savefig(f"{self.outpath}/{get_images_name()}Budget to price ratios.png")
            plt.close()

    def hs_budget_affordability_counts(self):
        """
        Plots the count of agents with affordability 
        below 1 and those with 1 or above for each heating system.
        """
        if hasattr(self,"agent_df"):
            # Extract relevant data for Houseowners
            houseowner_df = self.agent_df.reset_index()
            houseowner_df = houseowner_df[houseowner_df["Class"] == "Houseowner"]
            budgets = houseowner_df[["Step", "Budget", "House area"]]
        
            # Define heating systems
            heating_systems = [
                "Heating_system_oil",
                "Heating_system_gas",
                "Heating_system_heat_pump",
                "Heating_system_electricity",
                "Heating_system_pellet",
                "Heating_system_network_district",
                "Heating_system_network_local",
                "Heating_system_heat_pump_brine",
            ]
        
            # Precompute installation costs for all systems
            costs = {}
            for system in heating_systems:
                params = self.params_table.content.loc[system]
                price = params["price"]
                factor_area = params["factor_area"]
                factor_oppendorf = params["factor_oppendorf"]
                price_index = params["price_index"]
                sidecosts_index = params["sidecosts_index"]
        
                # Vectorized installation cost calculation
                costs[system] = (
                    price
                    * (budgets["House area"] ** factor_area)
                    * budgets["House area"]
                    * factor_oppendorf
                    * price_index
                    * sidecosts_index
                )
        
            # Compute ratios for all systems
            ratios = {system: budgets["Budget"] / costs[system] for system in heating_systems}
        
            # Combine all ratios into a single DataFrame
            ratios_df = pd.DataFrame(ratios)
            ratios_df["Step"] = budgets["Step"]
        
            # Create subplots for all heating systems
            num_systems = len(heating_systems)
            cols = 2
            rows = (num_systems + 1) // cols
        
            fig, axes = plt.subplots(rows, cols, figsize=(15, 5 * rows))
            axes = axes.flatten()  # Flatten in case we have a grid larger than needed
        
            for idx, system in enumerate(heating_systems):
                # Categorize ratios into below and above/equals 1
                ratios_df[system + "_Below_1"] = ratios_df[system].apply(lambda x: 1 if x < 1 else 0)
                ratios_df[system + "_Above_1"] = ratios_df[system].apply(lambda x: 1 if x >= 1 else 0)
        
                # Group by step and count occurrences
                df_stats = ratios_df.groupby("Step").agg(
                    Below_1=(system + "_Below_1", "sum"),
                    Above_1=(system + "_Above_1", "sum"),
                ).reset_index()
        
                # Area plot
                ax = axes[idx]
                ax.fill_between(
                    df_stats["Step"],
                    0,
                    df_stats["Below_1"],
                    label=_("Not affordable"),
                    color="red",
                    alpha=0.6,
                )
                ax.fill_between(
                    df_stats["Step"],
                    df_stats["Below_1"],
                    df_stats["Below_1"] + df_stats["Above_1"],
                    label=_("Affordable"),
                    color="green",
                    alpha=0.6,
                )
                ax.set_title(_(system))
                ax.set_xlabel(_("Weeks"))
                ax.set_ylabel(_("Count of Agents"))
                ax.legend()
        
            # Hide unused subplots
            for idx in range(num_systems, len(axes)):
                fig.delaxes(axes[idx])
        
            # Adjust layout and save the combined plot
            
            plt.savefig(f"{self.outpath}/{get_images_name()}Budget_Affordability_Counts.png")
            plt.close()

    def to_excel(self):
        """
        Save the processed agent and model DataFrames to xlsx files.
        """
        if hasattr(self,"agent_df"):
            filepath = f"{self.outpath}/{get_file_name()}{'_' + self.milieu + ' ' if self.milieu else ' '}, agent_results.xlsx"
            self.agent_df.to_excel(filepath, index=True)
        filepath = f"{self.outpath}/{get_file_name()}{'_' + self.milieu + ' ' if self.milieu else ' '}, model_results.xlsx"
        self.model_df.to_excel(filepath, index=True)

    def to_csv(self):
        """
        Save the processed agent and model DataFrames to CSV files.
        """
        if hasattr(self,"agent_df"):
            agent_filepath = f"{self.outpath}/{get_file_name()}{'_' + self.milieu + ' ' if self.milieu else ' '}, agent_results.csv"
            self.agent_df.to_csv(agent_filepath, index=True)
        model_filepath = f"{self.outpath}/{get_file_name()}{'_' + self.milieu + ' ' if self.milieu else ' '}, model_results.csv"
        self.model_df.to_csv(model_filepath, index=True)

        self.rate_of_change.to_csv(
            f"{self.outpath}/{get_file_name()}{'_' + self.milieu + ' ' if self.milieu else ' '}, rate_of_change.csv",
            index=True,
        )
    
    def calculate_installation_costs(self, area, system_type):
        """
        Calculates the installation cost for a given system and house area.

        This is a helper method that uses the loaded heating system parameter
        table to calculate the cost of installing a specific `system_type` in
        a house of a given `area`.

        Parameters
        ----------
        area : float
            The living area of the house.
        system_type : str
            The class name of the heating system.

        Returns
        -------
        float
            The calculated installation cost.
        """
        # Access the content attribute of the Heating_params_table object
        params_table = self.params_table.content
    
        # Ensure the system_type exists in the table
        if system_type not in params_table.index:
            raise ValueError(f"System type '{system_type}' not found in params_table.")
    
        # Extract parameters for the given system type
        system_params = params_table.loc[system_type]
    
        # Perform the calculation using the extracted parameters
        price = system_params["price"]
        factor_area = system_params["factor_area"]
        factor_oppendorf = system_params["factor_oppendorf"]
        price_index = system_params["price_index"]
        sidecosts_index = system_params["sidecosts_index"]
    
        # Calculate the installation cost
        cost = (
            price
            * area**factor_area
            * area
            * factor_oppendorf
            * price_index
            * sidecosts_index
        )
    
        return round(cost)

if __name__ == "__main__":
    plotter = Plots()
    #plotter.dropouts()
    #plotter.dropouts_bars_in_periods(option="heat_pump")
    #plotter.analyze_obstacles_by_period()
    