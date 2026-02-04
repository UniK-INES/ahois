"""
Fits statistical distributions to survey data on user preferences.

This script reads user preference data from an Excel file, preprocesses it,
and fits a beta distribution to several data columns for different user groups.
The primary goal is to find the parameters (alpha, beta) of a beta
distribution that best describes the empirical data for each preference.

For each user group and preference variable, the script performs the following:
1.  Loads and preprocesses the data by handling NaNs, truncating outliers,
    and normalising values to the (0, 1) interval.
2.  Fits a beta distribution using SciPy's `beta.fit` method.
3.  Generates and saves diagnostic plots (QQ plot and CDF comparison) to
    visually assess the goodness-of-fit.
4.  Performs a Kolmogorov-Smirnov (K-S) test to statistically quantify
    the goodness-of-fit.
5.  Exports the fitted distribution parameters and K-S test results to an
    Excel file for further use and analysis.

The script also contains a commented-out section for fitting a Weibull
distribution, which follows a similar process.

:Authors:
 - Ivan Digel <ivan.digel@uni-kassel.de>
"""
import pandas as pd
import numpy as np
from scipy.stats import beta, kstest, probplot
import matplotlib.pyplot as plt
import os

if __name__ == "__main__":
    #Reading the excel file
    file_dir = os.path.dirname(__file__)
    file_name = "data/input/preferences_exported.xlsx"
            
    df = pd.read_excel(os.path.join(file_dir, file_name))
    
    # Mapping of group numbers to labels
    group_labels = {
        1: "Leading",
        2: "Mainstream",
        3: "Traditionals",
        4: "Hedonists"
    }
    
    # Mapping of original column names to comprehensible names
    column_labels = {
        "PH_01_01_FW": "understanding",
        "PH_01_02_F": "installation_operation_costs",
        "PH_01_03_U": "environmental impact",
        "PH_01_04_A": "installation_operation_effort"
    }
    
    # Columns to fit the beta distribution to, excluding the grouping column
    columns = list(column_labels.keys())
    
    """Fit beta distribution"""
    # Initialize a list to store the results
    results_list = []
    
    for group, group_df in df.groupby('milieugroup'):
        for col in columns:
            # Extract the column data for the group, dropping NaN values for this column only
            data = group_df[col].dropna()
            
            # Truncate outliers based on percentiles
            lower_bound, upper_bound = data.quantile(0.01), data.quantile(0.99)
            data = data[(data >= lower_bound) & (data <= upper_bound)]
    
            #Min-max normalization, removing 0s and 1s
            data = (data - data.min()) / (data.max() - data.min())
            epsilon = 1e-5  # Small buffer value
            data = data.clip(lower=epsilon, upper=1-epsilon)
    
            # Fit the beta distribution
            a, b, loc, scale = beta.fit(data, floc=0, fscale=1)
            a = a*1.2
            
            # Generate QQ plot
            plt.figure(figsize=(8, 8))
            theoretical_quantiles = np.linspace(0, 1, len(data), endpoint=False)
            theoretical_values = beta.ppf(theoretical_quantiles, a, b)
            probplot(data, dist="uniform", sparams=(a, b), plot=plt)
            plt.title(f'QQ Plot for beta {group_labels[group]} - {column_labels[col]}')
            plt.xlabel('Theoretical Quantiles')
            plt.ylabel('Empirical Quantiles')
            plt.plot(theoretical_values, np.sort(data), 'o', color='red')  # Overlay the empirical data points
            # Save the plot to a file
            filename = f'data/input/fitting/QQPlot_{group_labels[group]}_{column_labels[col]}.png'.replace(" ", "_")
            plt.savefig(filename)
            plt.close()  # Close the plot to free memory
            
            #Generate theoretic vs. empirical cdf distribution
            # Set up the figure and axis
            plt.figure(figsize=(8, 6))
            ax = plt.subplot(111)
    
            # Calculate the empirical CDF
            data_sorted = np.sort(data)
            empirical_cdf = np.arange(1, len(data_sorted)+1) / len(data_sorted)
    
            # Calculate the theoretical CDF
            theoretical_cdf = beta.cdf(data_sorted, a, b, loc, scale)
    
            # Plot the empirical CDF
            ax.step(data_sorted, empirical_cdf, where="post", label="Empirical CDF")
    
            # Plot the theoretical CDF
            ax.plot(data_sorted, theoretical_cdf, label="Theoretical CDF", linestyle='--')
    
            # Add labels and title
            plt.title(f'CDF for {group_labels[group]} - {column_labels[col]}')
            plt.xlabel('Value')
            plt.ylabel('Cumulative Probability')
            plt.legend()
    
            # Save the plot to a file
            filename = f'data/input/fitting/CDF_{group_labels[group]}_{column_labels[col]}.png'.replace(" ", "_")
            plt.savefig(filename)
            plt.close()  # Close the plot to free memory
            
            
            # Perform the K-S test comparing the empirical data to the beta CDF
            # Note: The beta CDF needs to be scaled and located according to the fit
            ks_stat, ks_pvalue = kstest(data, 'beta', args=(a, b, loc, scale))
    
            # Store the results including K-S test statistics
            results_list.append({
                'Variable': column_labels.get(col, 'Unknown'),  # Map the column name
                'Group': group_labels.get(group, 'Unknown'),  # Get the label for the group
                'Alpha': round(a, 4),
                'Beta': round(b, 4),
                'KS Statistic': round(ks_stat, 6),
                'KS P-Value': round(ks_pvalue, 6)
            })
    
    # Convert the results list to a DataFrame
    results_df = pd.DataFrame(results_list)
    
    # Specify the filename for the Excel output
    output_filename = 'data/input/fitting/fitted_beta_parameters_with_ks_test.xlsx'
    # Export the DataFrame to an Excel file
    results_df.to_excel(output_filename, index=False)
    
    print(f"Results for beta have been exported to {output_filename}.")
    
    
    """Fit Weibull distribution
    results_list = []
    
    for group, group_df in df.groupby('milieugroup'):
        for col in columns:
            # Process the data
            data = group_df[col].dropna()
            data = (data - data.min()) / (data.max() - data.min())
            epsilon = 1e-5
            data = data.clip(lower=epsilon, upper=1-epsilon)
    
            # Fit the Weibull distribution
            c, loc, scale = weibull_min.fit(data, floc=0)
    
            # QQ plot for Weibull
            plt.figure(figsize=(8, 8))
            probplot(data, dist="weibull_min", sparams=(c, 0, 1), plot=plt)
            plt.title(f'QQ Plot for Weibull {group_labels[group]} - {column_labels[col]}')
            plt.xlabel('Theoretical Quantiles')
            plt.ylabel('Empirical Quantiles')
            plt.savefig(f'data/input/fitting/QQPlot_Weibull_{group_labels[group]}_{column_labels[col]}.png'.replace(" ", "_"))
            plt.close()
    
            # CDF for Weibull
            plt.figure(figsize=(8, 6))
            ax = plt.subplot(111)
            data_sorted = np.sort(data)
            empirical_cdf = np.arange(1, len(data_sorted)+1) / len(data_sorted)
            theoretical_cdf = weibull_min.cdf(data_sorted, c, loc, scale)
            ax.step(data_sorted, empirical_cdf, where="post", label="Empirical CDF")
            ax.plot(data_sorted, theoretical_cdf, label="Theoretical CDF", linestyle='--')
            plt.title(f'CDF for Weibull {group_labels[group]} - {column_labels[col]}')
            plt.xlabel('Value')
            plt.ylabel('Cumulative Probability')
            plt.legend()
            plt.savefig(f'data/input/fitting/CDF_Weibull_{group_labels[group]}_{column_labels[col]}.png'.replace(" ", "_"))
            plt.close()
    
            # K-S test for Weibull
            ks_stat, ks_pvalue = kstest(data, 'weibull_min', args=(c, loc, scale))
    
            # Store the results
            results_list.append({
                'Variable': column_labels.get(col, 'Unknown'),
                'Group': group_labels.get(group, 'Unknown'),
                'Shape': round(c, 4),
                'Scale': round(scale, 4),
                'KS Statistic': round(ks_stat, 6),
                'KS P-Value': round(ks_pvalue, 6)
            })
    
    # Convert the results list to a DataFrame and export to an Excel file
    results_df = pd.DataFrame(results_list)
    output_filename = 'data/input/fitting/fitted_weibull_parameters_with_ks_test.xlsx'
    results_df.to_excel(output_filename, index=False)
    
    print(f"Results for Weibull have been exported to {output_filename}.")
    """
    