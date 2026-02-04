"""
Provides classes for loading and accessing model input data from CSV files.

This module contains container classes responsible for reading specific
input data files. Although the module name suggests Excel, it is designed to
read data from Comma-Separated Values (CSV) files using the pandas library.
Each class corresponds to a key data table required by the model, such as
milieu parameters or heating system specifications.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
import os
import logging
import pandas as pd
from helpers.config import settings

logger = logging.getLogger("ahoi.input")

class Milieu_table:
    """
    A container for milieu parameters loaded from a CSV file.

    Attributes
    ----------
    content : pandas.DataFrame
        A DataFrame holding the milieu parameter data, indexed by milieu type.
    """

    def __init__(self):
        """
        Initialises the Milieu_table by loading the data.
        """
        outpath = os.path.join(
            settings.main.input_path,
            str(settings.data.milieu_params)
            )
        
        self.content = pd.read_csv(os.path.join(outpath), index_col="type")


class Heating_params_table:
    """A container for heating system parameters loaded from a CSV file.
    This class reads the primary CSV file containing the technical and economic
    parameters for all available heating systems. It performs minor cleaning,
    by stripping whitespace from column headers and setting the system
    name as the index. The data is accessible through the `content` attribute.

    Attributes
    ----------
    content : pandas.DataFrame
        A DataFrame holding the heating system parameter data, indexed by
        the system's name.
    """

    def __init__(self):
        """
        Initialises the Heating_params_table by loading and preparing the data.
        """
        outpath = os.path.join(
            settings.main.input_path,
            str(settings.data.heat_sys_params)
            )
        #logger.info(f"Apply Heating param table {outpath}...")
        self.content = pd.read_csv(outpath)
        self.content.columns = self.content.columns.str.strip()
        self.content.set_index("name", inplace=True)
        
class Heating_params_dynamics_table:
    """
    A container for the dynamic parameters of heating systems.

    This class reads the CSV file that contains time-series or dynamic data
    related to heating system parameters, such as evolving fuel prices or
    emissions factors. The data is loaded into a pandas DataFrame and is
    accessible through the `content` attribute.

    Attributes
    ----------
    content : pandas.DataFrame
        A DataFrame holding the dynamic parameter data for heating systems.
    """
    
    def __init__(self):
        """
        Initializes the Heating_params_dynamics_table by loading the data.
        """
        outpath = os.path.join(
            settings.main.input_path,
            str(settings.data.heat_sys_params_dynamics)
            )
        #logger.info(f"Apply Heating param table {outpath}...")
        self.content = pd.read_csv(outpath)