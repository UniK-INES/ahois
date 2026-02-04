"""
Defines classes for agent socio-cognitive properties and preferences.

This module contains the building blocks for an agent's intrinsic profile,
often referred to as their "milieu." These classes encapsulate an agent's
preferences for heating systems and information sources, their personal
standards for evaluating options, and the cognitive weights used in their
decision-making processes. These properties are typically initialized from
external data tables and randomized to create heterogeneity among agents.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
 - Sascha Holzhauer <sascha.holzhauer@uni-kassel.de>
"""
import uuid
from modules.Rng import rng_milieu_init
from helpers.config import settings


class Milieu:
    """
    A container for an agent's socio-cognitive profile.
    This class represents an agent's "milieu," which groups together all their
    intrinsic preferences, standards, and cognitive weights. It is initialised
    for a specific milieu type (e.g., "Mainstream," "Leading") and serves as a
    central object for an agent's characteristics.

    Parameters
    ----------
    table : Milieu_table
        A data object containing the parameters for all milieu types.
    milieu_type : str, optional
        The specific type of milieu to initialize, by default "Generalized".

    Attributes
    ----------
    unique_id : uuid.UUID
        A unique identifier for the milieu instance.
    milieu_type : str
        The name of the milieu.
    heating_preferences : Heating_preferences
        An object holding the agent's preferences for heating system attributes.
    source_preferences : Information_source_preferences
        An object holding the agent's preferences for information sources.
    standard : Personal_standard
        An object defining the agent's thresholds for decision-making.
    tpb_weights : tuple[float, float, float]
        A tuple containing the weights for attitude, social norm, and
        perceived behavioural control in the Theory of Planned Behaviour.
    ra_exposure : dict
        A dictionary of exposure values for the relative agreement model.
    uncertainty_factor: float
            USed during risk calculation to define the attitude towards unknown information
    """

    def __init__(self, table, milieu_type="Generalized"):
        """
        Initializes a milieu defining all agent preferences and standards.

        Parameters
        ----------
        table : Milieu_table
            A data object containing the parameters for all milieu types.
        milieu_type : str, optional
            The specific type of milieu to initialize, by default "Generalized".
        """
        self.unique_id = uuid.uuid4()
        
        self.milieu_type = milieu_type
        params = table.content.loc[milieu_type]

        # Preferences over HS parameters
        self.heating_preferences = Heating_preferences(
            table=table, milieu_type=milieu_type
        )
        # Preferences over types of information sources
        self.source_preferences = Information_source_preferences(
            table=table, milieu_type=milieu_type
        )
        # Threshold to define standard that HS must meet
        self.standard = Personal_standard(table=table, milieu_type=milieu_type)
        # Placeholder for weights for attitude, social norm and PBC
        self.tpb_weights = self.generate_TPB_weights(params = params)
        # Exposure to other's opinions, used for relative agreement
        self.ra_exposure = {
            "Leading": params["ra_exposure_leading"],
            "Mainstream": params["ra_exposure_mainstream"],
            "Traditionals": params["ra_exposure_traditionals"],
            "Hedonists": params["ra_exposure_hedonists"],
        }
        
        uncertainty_dict = {"Leading": settings.houseowner.leading.uncertainty_factor,
                        "Mainstream": settings.houseowner.mainstream.uncertainty_factor,
                        "Traditionals": settings.houseowner.traditionals.uncertainty_factor,
                        "Hedonists": settings.houseowner.hedonists.uncertainty_factor}
        
        self.uncertainty_factor = uncertainty_dict[milieu_type]
        
    def generate_TPB_weights(self, params):
        """
        Generate randomised weights for Theory of Planned Behaviour factors.

        This method creates a set of weights for the three components of the
        Theory of Planned Behaviour (TPB): attitude, social norm, and
        perceived behavioural control. The weights are drawn from a uniform
        distribution, where the bounds are determined by a mean value specific
        to the milieu and a standard deviation from the global settings.

        Parameters
        ----------
        params : pandas.Series
            A series containing the mean TPB weights for the milieu.

        Returns
        -------
        dict
            A dict containing the generated weights for attitude, social
            norm, and control, respectively.
        """
        means = [
            params["tpb_attitude"],
            params["tpb_social"],
            params["tpb_control"]
        ]
        
        means[0] = means[0] * settings.houseowner.attitude_multiplier
        means[1] = means[1] * settings.houseowner.social_norm_multiplier
        means[2] = means[2] * settings.houseowner.pbc_multiplier
        
        # First Normalisation
        total_mean = sum(means)
        if total_mean > 0:
            means = [m / total_mean for m in means]

        if settings.experiments.sa_active:
            std_val = settings.experiments.sa_tpb_weights_std
            stds = [std_val, std_val, std_val]
        else:
            stds = settings.houseowner.tpb_weights_std

        # Generate Random Weights
        raw_weights = []
        for mean, std in zip(means, stds):
            # Calculate bounds
            w_min = max(mean - std, 0.0)
            w_max = min(mean + std, 1.0)
            
            # Draw random value
            if w_max > w_min:
                val = rng_milieu_init().uniform(w_min, w_max)
            else:
                val = mean
            raw_weights.append(val)
        
        # Second Normalisation
        total_weight = sum(raw_weights)
        if total_weight > 0:
            final_weights = [w / total_weight for w in raw_weights]
        else:
            final_weights = raw_weights

        w_att = final_weights[0]
        w_soc = final_weights[1]
        w_pbc = 1.0 - w_att - w_soc
        
        # Keys must match the attributes used in calculate_integral_rating
        return {
            "attitude": w_att,
            "social_norm": w_soc,
            "behavioural_control": w_pbc
        }

class Heating_preferences:
    """
    This class represents an agent's set of preferences (weights) concerning
    the different characteristics of a heating system. 
    Each preference is generated as a random value drawn from a Beta distribution 
    to create individual variations based on the agent's milieu.

    Parameters
    ----------
    table : Milieu_table
        The data object containing parameters for all milieus.
    milieu_type : str, optional
        The specific milieu to generate preferences for, by default "Generalized".
    """

    def __init__(self, table, milieu_type="Generalized"):
        """
        Initializes preferences for heating system parameters.

        Parameters
        ----------
        table : Milieu_table
            The data object containing parameters for all milieus.
        milieu_type : str, optional
            The specific milieu to generate preferences for, 
            by default "Generalized".
        """
        params = table.content.loc[milieu_type]

        self.operation_effort = self.generate_preferences(
            params["effort_a"], params["effort_b"]
        )
        self.fuel_cost = self.generate_preferences(
            params["fuel_cost_a"], params["fuel_cost_b"]
        )
        self.emissions = self.generate_preferences(
            params["emissions_a"], params["emissions_b"]
        )
        self.price = self.generate_preferences(params["price_a"], params["price_b"])
        self.installation_effort = self.generate_preferences(
            params["effort_a"], params["effort_b"]
        )
        self.opex = self.generate_preferences(params["price_a"], params["price_b"])

        # TODO: Knowledge, understanding as an attribute

    def generate_preferences(self, alpha, beta):
        """
        Generates a single preference value from a Beta distribution.

        Parameters
        ----------
        alpha : float
            The alpha shape parameter for the Beta distribution.
        beta : float
            The beta shape parameter for the Beta distribution.

        Returns
        -------
        float
            A random value between 0 and 1 representing a preference weight.
        """
        alpha_param = alpha
        beta_param = beta
        value = rng_milieu_init().beta(alpha_param, beta_param)
        return value


class Information_source_preferences:
    """
    This class represents an agent's preferences for various information
    sources (e.g., internet, plumber, neighbors). The preferences are
    generated as a set of probabilities that sum to 1, drawn from a
    Dirichlet distribution. This determines the likelihood that an agent
    will choose one source over another.

    Parameters
    ----------
    table : Milieu_table
        The data object containing parameters for all milieus.
    milieu_type : str, optional
        The specific milieu to generate preferences for, by default "Generalized".
    """

    def __init__(self, table, milieu_type="Generalized"):
        """
        Initializes preferences for different information sources.

        Parameters
        ----------
        table : Milieu_table
            The data object containing parameters for all milieus.
        milieu_type : str, optional
            The specific milieu to generate preferences for, by default "Generalized".
        """
        params = table.content.loc[milieu_type]
        ratios = (
            params["internet"],
            params["magazine"],
            params["plumber"],
            params["neighbour"],
            params["energy_advisor"],
        )

        randomizer = rng_milieu_init().dirichlet(ratios, size=1)
        self.internet = randomizer[0][0]
        self.magazine = randomizer[0][1]
        self.plumber = randomizer[0][2]
        self.neighbour = randomizer[0][3]
        self.energy_advisor = randomizer[0][4]


class Personal_standard:
    """
    This class holds the set of thresholds that an agent uses to evaluate
    whether a heating system is still acceptable. These standards apply to specific
    attributes. It also includes a lifetime threshold, 
    which determines how close to the end of its lifespan a system
    must be before the agent considers replacing it.

    Parameters
    ----------
    table : Milieu_table
        The data object containing parameters for all milieus.
    milieu_type : str, optional
        The specific milieu to define standards for, by default "Generalized".
    """

    def __init__(self, table, milieu_type="Generalized"):
        """
        Initializes the personal standards and decision thresholds.

        Parameters
        ----------
        table : Milieu_table
            The data object containing parameters for all milieus.
        milieu_type : str, optional
            The specific milieu to define standards for, 
            by default "Generalized".
        """
        params = table.content.loc[milieu_type]
        self.operation_effort = params["s_operation_effort"]
        self.fuel_cost = params["s_fuel_cost"]
        self.emissions = params["s_emissions"]
        self.lifetime = params["s_lifetime"]
