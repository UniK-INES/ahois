"""
Visualises the mean preference values of different agent milieus.

This script reads the `milieu_parameters.csv` input file, which contains the
alpha and beta shape parameters that define agent preferences for various
heating system attributes (e.g., cost, emissions). It calculates the mean
preference value for each attribute and milieu from these parameters.

The script then generates and saves two distinct bar plots to visualize these
preferences, allowing for easy comparison:
1.  A plot grouped by milieu, showing the different attribute preferences for each.
2.  A plot grouped by attribute, showing how different milieus value each one.

:Authors: 
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import yaml
import logging
from helpers.i18n import _
from helpers.config import settings, get_output_path

preffile = "/home/sascha/git/ahois-pro/src/data/input/milieu_parameters.csv"

logger = logging.getLogger("ahoi.plot")

if __name__ == '__main__':
    
    with open(settings.data.plt_settings, "r") as configfile:
            config = yaml.safe_load(configfile)
    if "Layout" in config:
        plt.rcParams.update(config["Layout"])
    else:
        raise ValueError("Invalid plotting configuration file: 'Layout' section missing.")
        
    prefnames = ["effort", "fuel_cost", "emissions", "price"]

    prefs = pd.read_csv(preffile)
    
    for p in prefnames:
        prefs[_(p)] = prefs[p + "_a"] / (prefs[p + "_a"] + prefs[p + "_b"])
    
    prefs.set_index("type", inplace=True)
    prefs.drop("Generalized", inplace=True)
    prefs = prefs[[_(p) for p in prefnames]]
    prefs.rename(index={"Leading": _("LEA"),
                        "Mainstream":_("MAI"),
                        "Hedonists":_("HED"),
                        "Traditionals":_("TRA")}, inplace=True)
    prefs.plot(kind="bar")
    plt.legend(loc="lower right")
    plt.tight_layout()
    targetfile = f'/home/sascha/git/ahois-pro/src/data/input/milieu_preferences_by_milieu.png'
    plt.savefig(targetfile)
    logger.info(f"Store figure to {targetfile}")
    plt.close(plt.gcf())
    
    # prefs > bar groups | milieus > colours
    prefs = prefs.transpose()
    prefs = prefs / prefs.max()
    prefs = pd.melt(prefs,
                    value_vars=(_("LEA"), _("TRA"), _("MAI"), _("HED")),
                    var_name="Milieu",
                    value_name="Preference",
                    ignore_index=False)
    
    palette = ["#006666", "#7e0024", "#83ccff", "#fecc00"]
    ax = sns.barplot(x="index", y='Preference', data=prefs.reset_index(), hue="Milieu", palette=palette,)
    plt.xticks(rotation=25, ha="right")
    plt.legend(loc="lower right")
    ax.set_xlabel(None)
    ax.set_ylabel(_("Preference value"))
    plt.tight_layout()
    targetfile = f'/home/sascha/git/ahois-pro/src/data/input/milieu_preferences_by_prefs.png'
    plt.savefig(targetfile)
    logger.info(f"Store figure to {targetfile}")
    