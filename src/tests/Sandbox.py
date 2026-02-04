"""
A sandbox script for various experiments, statistical tests, and debugging.

This file serves as a collection of independent code snippets used for
development, analysis, and exploratory work. It is not part of the main
application logic or the formal test suite.

The contents include:

- Statistical analysis scripts to compare beta distributions that model agent
  preferences, using methods like the KS-test and permutation tests on the
  Jensen-Shannon distance.

- A utility for checking system environment variables for debugging purposes.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import numpy as np

if __name__ == "__main__":
    # The parameter dictionary from before
    params = {
        'Leading': {
            'effort':      (1.5999, 0.1777),
            'fuel_cost':   (1.9027, 0.2114),
            'emissions':   (1.5896, 0.3255),
            'price':       (1.9027, 0.2114),
        },
        'Mainstream': {
            'effort':      (1.4431, 0.1967),
            'fuel_cost':   (2.5135, 0.3106),
            'emissions':   (1.8604, 0.5875),
            'price':       (2.5135, 0.3106),
        },
        'Traditionals': {
            'effort':      (1.1314, 0.4399),
            'fuel_cost':   (1.9854, 0.5599),
            'emissions':   (0.4518, 0.3012),
            'price':       (1.9854, 0.5599),
        },
        'Hedonists': {
            'effort':      (0.8126, 0.0427),
            'fuel_cost':   (0.8126, 0.0427),
            'emissions':   (0.2822, 0.0842),
            'price':       (0.8126, 0.0427),
        }
    }
    
    N = 5000  # sample size for each Beta distribution
    
    # Dictionary to store the means
    means = {}
    
    # For each group and dimension, generate a sample and compute mean
    for group, dist_dict in params.items():
        means[group] = {}
        for dimension, (alpha, beta) in dist_dict.items():
            sample = np.random.beta(alpha, beta, size=N)
            means[group][dimension] = np.mean(sample)
    
    # Print out the results
    for group in means:
        print(f"{group} means:")
        for dimension, mean_val in means[group].items():
            print(f"  {dimension}: {mean_val:.4f}")
        print()
    
    
    import numpy as np
    from scipy.stats import ks_2samp
    from itertools import combinations
    
    # 1) Define the alpha/beta parameters for each distribution in each group
    params = {
        'Leading': {
            'effort':      (1.5999, 0.1777),
            'fuel_cost':   (1.9027, 0.2114),
            'emissions':   (1.5896, 0.3255),
            'price':       (1.9027, 0.2114),
        },
        'Mainstream': {
            'effort':      (1.4431, 0.1967),
            'fuel_cost':   (2.5135, 0.3106),
            'emissions':   (1.8604, 0.5875),
            'price':       (2.5135, 0.3106),
        },
        'Traditionals': {
            'effort':      (1.1314, 0.4399),
            'fuel_cost':   (1.9854, 0.5599),
            'emissions':   (0.4518, 0.3012),
            'price':       (1.9854, 0.5599),
        },
        'Hedonists': {
            'effort':      (0.8126, 0.0427),
            'fuel_cost':   (0.8126, 0.0427),
            'emissions':   (0.2822, 0.0842),
            'price':       (0.8126, 0.0427),
        }
    }
    
    # 2) Set up which dimensions (i.e., which Beta distributions) you want to compare
    dimensions = ['effort', 'fuel_cost', 'emissions', 'price']
    
    # 3) Specify the group names and a sample size for random draws
    groups = list(params.keys())
    N = 10_000  # e.g., 10,000 random draws from each Beta distribution
    
    # 4) For each dimension, perform pairwise comparisons
    for dim in dimensions:
        results = []
        # Generate all pairwise combinations of groups (Leading vs Mainstream, etc.)
        for g1, g2 in combinations(groups, 2):
            alpha1, beta1 = params[g1][dim]
            alpha2, beta2 = params[g2][dim]
    
            # Generate samples from each Beta distribution
            sample1 = np.random.beta(alpha1, beta1, size=N)
            sample2 = np.random.beta(alpha2, beta2, size=N)
    
            # KS test (non-parametric) for distribution difference
            stat, pval = ks_2samp(sample1, sample2)
            results.append((g1, g2, pval))
    
        # 5) Apply a multiple-comparison correction (Bonferroni)
        #    There are 6 pairwise comparisons if you have 4 groups.
        alpha_corrected = 0.05 / len(results)
    
        # Identify which pairs differ significantly
        sig_pairs = [(g1, g2) for (g1, g2, pval) in results if pval < alpha_corrected]
    
        # 6) Format the output
        if len(sig_pairs) == 0:
            print(f"{dim.capitalize()} beta distributions: NO significant differences.")
        elif len(sig_pairs) == len(results):
            print(f"{dim.capitalize()} beta distributions: ALL pairs differ significantly.")
        else:
            print(
                f"{dim.capitalize()} beta distributions: "
                f"Significant differences only for these pairs: {sig_pairs}"
            )
    """+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++ """
    import numpy as np
    from scipy.stats import entropy
    from itertools import combinations
    
    # ----------------------------
    # 1) Beta distribution parameters
    # ----------------------------
    params = {
        'Leading': {
            'effort':      (1.5999, 0.1777),
            'fuel_cost':   (1.9027, 0.2114),
            'emissions':   (1.5896, 0.3255),
            'price':       (1.9027, 0.2114),
        },
        'Mainstream': {
            'effort':      (1.4431, 0.1967),
            'fuel_cost':   (2.5135, 0.3106),
            'emissions':   (1.8604, 0.5875),
            'price':       (2.5135, 0.3106),
        },
        'Traditionals': {
            'effort':      (1.1314, 0.4399),
            'fuel_cost':   (1.9854, 0.5599),
            'emissions':   (0.4518, 0.3012),
            'price':       (1.9854, 0.5599),
        },
        'Hedonists': {
            'effort':      (0.8126, 0.0427),
            'fuel_cost':   (0.8126, 0.0427),
            'emissions':   (0.2822, 0.0842),
            'price':       (0.8126, 0.0427),
        }
    }
    
    dimensions = ['effort', 'fuel_cost', 'emissions', 'price']
    groups = list(params.keys())
    
    # Sample size for drawing from Beta
    N = 10000  
    
    # ----------------------------
    # 2) Define a Jensen-Shannon distance function for discrete distributions
    # ----------------------------
    def jensen_shannon_distance(p, q, base=2):
        """
        Calculates the Jensen-Shannon distance between 
        two discrete probability distributions.

        Parameters
        ----------
        p : numpy.ndarray
            The first discrete probability distribution. Must be a 1D array
            of probabilities that sum to 1.
        q : numpy.ndarray
            The second discrete probability distribution. Must be a 1D array
            of probabilities that sum to 1.
        base : int, optional
            The logarithmic base to use in the calculation. Defaults to 2, which
            results in a distance measured in bits.
    
        Returns
        -------
        float
            The Jensen-Shannon distance between distributions p and q.
        """
        # We assume p and q are already normalized (sum to 1).
        m = 0.5 * (p + q)
        return 0.5 * entropy(p, m, base=base) + 0.5 * entropy(q, m, base=base)
    
    def js_distance_from_samples(x, y, bins=50):
        """Approximates the JS distance by converting continuous samples 
        into discrete distributions.

        This function takes two arrays of continuous samples (e.g., from a beta
        distribution) and creates histograms with a shared set of bins to
        represent them as discrete probability distributions. It then calculates
        the JS distance between these binned distributions.
    
        Parameters
        ----------
        x : numpy.ndarray
            An array of continuous samples from the first distribution.
        y : numpy.ndarray
            An array of continuous samples from the second distribution.
        bins : int, optional
            The number of bins to use for creating the histograms. Defaults to 50.
    
        Returns
        -------
        float
            The approximate Jensen-Shannon distance between the distributions
            represented by the samples x and y.
        """
        # We create the same bin edges for x, y
        p_hist, bin_edges = np.histogram(x, bins=bins, range=(0,1), density=True)
        q_hist, _         = np.histogram(y, bins=bin_edges, density=True)
    
        # Convert histogram counts to probability densities
        p_hist = p_hist / np.sum(p_hist)
        q_hist = q_hist / np.sum(q_hist)
    
        return jensen_shannon_distance(p_hist, q_hist, base=2)
    
    # ----------------------------
    # 3) Permutation test on the JS distance
    # ----------------------------
    def permutation_test_js(x, y, n_permutations=1000, bins=50, random_state=None):
        """Performs a permutation test to determine the significance 
        of the JS distance.

        This non-parametric test evaluates if two sets of samples likely come from
        different distributions. It first calculates the observed JS distance
        between the samples `x` and `y`. It then pools the data, repeatedly
        shuffles it, splits it back into two groups, and recalculates the JS
        distance. The p-value is the proportion of times a permuted distance was
        greater than or equal to the observed distance.
    
        Parameters
        ----------
        x : numpy.ndarray
            An array of samples from the first distribution.
        y : numpy.ndarray
            An array of samples from the second distribution.
        n_permutations : int, optional
            The number of permutation iterations to run. Defaults to 1000.
        bins : int, optional
            The number of bins to use for the histogram approximation of JS
            distance. Defaults to 50.
        random_state : int, optional
            A seed for the random number generator to ensure reproducibility.
            Defaults to None.
    
        Returns
        -------
        tuple
            A tuple containing:
            - observed_js (float): The actual JS distance between samples x and y.
            - p_value (float): The calculated p-value from the permutation test.
        """
        rng = np.random.default_rng(random_state)
    
        # Observed distance
        observed_js = js_distance_from_samples(x, y, bins=bins)
    
        # Pool the data
        combined = np.concatenate([x, y])
        len_x = len(x)
    
        # Count how many permuted distances exceed or equal the observed distance
        count = 0
        for _ in range(n_permutations):
            rng.shuffle(combined)
            x_perm = combined[:len_x]
            y_perm = combined[len_x:]
            dist_perm = js_distance_from_samples(x_perm, y_perm, bins=bins)
            if dist_perm >= observed_js:
                count += 1
    
        # +1 numerator and +1 denominator => "augmented" for stability
        p_value = (count + 1) / (n_permutations + 1)
    
        return observed_js, p_value
    
    # ----------------------------
    # 4) Run pairwise tests for each dimension
    # ----------------------------
    alpha_global = 0.05  # family-wise significance level
    for dim in dimensions:
        # We'll store (group1, group2, distance, pval) for each pair
        pairwise_results = []
        
        # Generate all pairwise combos: (Leading vs Mainstream, etc.)
        for g1, g2 in combinations(groups, 2):
            alpha1, beta1 = params[g1][dim]
            alpha2, beta2 = params[g2][dim]
    
            # Draw samples from each Beta distribution
            x = np.random.beta(alpha1, beta1, size=N)
            y = np.random.beta(alpha2, beta2, size=N)
    
            # Permutation test on the Jensen-Shannon distance
            observed_js, pval = permutation_test_js(x, y, n_permutations=1000, bins=50)
            pairwise_results.append((g1, g2, observed_js, pval))
    
        # Bonferroni correction for 6 comparisons (4 groups => 6 pairs)
        alpha_corrected = alpha_global / len(pairwise_results)
    
        # Determine which pairs are significant
        significant_pairs = [(g1, g2) for (g1, g2, dist, pval) in pairwise_results
                             if pval < alpha_corrected]
    
        # Print results
        if len(significant_pairs) == 0:
            print(f"{dim.capitalize()} distributions: NO significant differences.")
        elif len(significant_pairs) == len(pairwise_results):
            print(f"{dim.capitalize()} distributions: ALL pairs differ significantly.")
        else:
            print(f"{dim.capitalize()} distributions: Significant differences for pairs: {significant_pairs}")


if __name__ == "__main__":
    import os
    
    print("--- Checking  Environment Variable Path ---")
    
    path_variable = os.environ.get('Path')
    
    if path_variable:
        print("Path variable found!")
        # Print each path on a new line for readability
        for p in path_variable.split(';'):
            print(p)
    else:
        print("ERROR: Path variable not found in the environment!")
    
    print("--- End of Check ---")