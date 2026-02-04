"""
Performs analysis and visualisation of model outputs using methods 
of AgentHomeID (ahid) by Fraunhofer IEE.

This script acts as a bridge to reuse visualisation capabilities. 
It loads and transforms the output data from the
current model into a format compatible with the 'ahid' plotting functions.
Using Python's 'mock' library, it intercepts data loading calls within the
'ahid' functions, injects the transformed data, and generates the desired plots.

:Authors:
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>

"""

import pandas as pd
import os
from  helpers.config import settings, get_output_path, config_logging
from helpers.utils import files_name, get_file_name
from unittest import TestCase, mock, main
import analysis.dynaconf_filter

settings.execute_loaders(loaders=[analysis.dynaconf_filter])
from building_stock_model.config.config import set_settings
set_settings(settings)
    
import logging
from building_stock_model.locale_figures.i18n import _
from building_stock_model.evaluation.constants import GT_RB, GT_NRB, BAC_RB, BAC_NRB
from building_stock_model.evaluation.figure_utils import getLabels
from building_stock_model.evaluation.heatingsystems import (
    plot_total_num_heatingsystems,
    plot_share_heatingsystems__sns
)
from cachetools.func import lru_cache

def read_output_data(run_id = None):
    """
    Reads the agent output DataFrame from a pickle file.

    Parameters
    ----------
    run_id : int, optional
        The ID of the simulation run from which to load the data. 
        If None, it uses the default path settings.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the agent data for the specified run.
    """
    agent_df = pd.read_pickle(f"{get_output_path(runid=run_id, subfolder='pickles')}/agent_df_{get_file_name()}.pkl")
    return agent_df

@lru_cache(maxsize=None)
def convert_output_data():
    """
    Converts and reformats the model's output data for 'ahid' compatibility.

    This function fetches the raw agent data and applies several transformations
    to make it suitable for the 'building_stock_model' evaluation functions.
    Transformations include adding a scale factor, renaming columns to match
    the expected schema, adding a placeholder ID, and converting simulation
    steps into calendar years. The result is cached to avoid redundant processing.

    Returns
    -------
    pandas.DataFrame
        The transformed and analysis-ready DataFrame.
    """
    data_df = read_output_data()
    data_df[settings.eval.colname_scalefactor] = 1
    data_df.reset_index(drop=False, inplace=True)
    data_df.rename(columns={'Step': settings.eval.colname_step,
                            'Heating': settings.eval.colname_heating,
                            "Emissions": settings.eval.colname_ghgemissions_demand,
                            }, inplace = True)
    data_df[settings.eval.colname_id] = 1
    data_df[settings.eval.colname_step] = data_df[settings.eval.colname_step]/52 + 2025
    return data_df
    
@mock.patch("building_stock_model.evaluation.heatingsystems.get_data")
@mock.patch("building_stock_model.evaluation.figure_utils.get_output_path")
def ahoi_plot_total_num_heatingsystems(mocked_path, mocked_data):
    """
    Generates a plot of the total number of heating systems using an 'ahid' function.

    This wrapper uses mocking to inject the model's converted data into the
    `plot_total_num_heatingsystems` function from the 'building_stock_model'.
    It bypasses that function's data loading and path discovery mechanisms,
    allowing it to work directly with the local model's output.

    Parameters
    ----------
    mocked_path : unittest.mock.MagicMock
        A mock object that replaces `get_output_path` in the target module.
    mocked_data : unittest.mock.MagicMock
        A mock object that replaces `get_data` in the target module.
    """
    mocked_data.return_value =  convert_output_data()
    mocked_path.return_value = get_output_path()
    plot_total_num_heatingsystems(multiplyflats=False)

@mock.patch("building_stock_model.evaluation.heatingsystems.get_data")
@mock.patch("building_stock_model.evaluation.figure_utils.get_output_path")
def ahoi_plot_share_heatingsystems__sns(mocked_path, mocked_data):
    """
    Generates a plot of the market share of heating systems using an 'ahid' function.

    Similar to `ahoi_plot_total_num_heatingsystems`, this wrapper uses
    mocking to inject this model's data into the `plot_share_heatingsystems__sns`
    visualisation function from the 'building_stock_model'.

    Parameters
    ----------
    mocked_path : unittest.mock.MagicMock
        A mock object that replaces `get_output_path` in the target module.
    mocked_data : unittest.mock.MagicMock
        A mock object that replaces `get_data` in the target module.
    """
    mocked_data.return_value = convert_output_data()
    mocked_path.return_value = get_output_path()
    plot_share_heatingsystems__sns(multiplyflats=False)
        
if __name__ == '__main__':
    config_logging()
    

    ahoi_plot_total_num_heatingsystems()
    ahoi_plot_share_heatingsystems__sns()
    