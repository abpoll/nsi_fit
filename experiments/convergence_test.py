#!/usr/bin/env python
# convergence_test.py

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import yaml
from yaml.loader import SafeLoader
import time
from os.path import join
import glob
import seaborn as sns
import matplotlib.pyplot as plt

import unsafe.ensemble as unens
import unsafe.files as unfile

# We want to keep track of how the analysis goes
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s')
logger = logging.getLogger("convergence_test")

# Set up a few filename constants
ABS_DIR = Path().absolute().parents[0]
FI = join(ABS_DIR, "data", "interim")
FO = join(ABS_DIR, "data", "results")
EXP_DIR_I = join(FI, "exp")
HAZ_DIR_I = join(FI, "haz")
VULN_DIR_I = join(FI, "vuln")
FIG_DIR = join(ABS_DIR, "fig")

# Load in the config file for some other
# constants
CONFIG_FILEP = join(ABS_DIR, 'config', 'config.yaml')
# Open the config file and load
with open(CONFIG_FILEP) as f:
    CONFIG = yaml.load(f, Loader=SafeLoader)

# Not best practice, but this is 
# specific to this case study
# and is pretty easily adaptable for the future
FIPS = '42101'

def parse_arguments():
    """
    The only thing you need to specify to run the convergence test
    is the flood depth grid id you want to use
    """
    parser = argparse.ArgumentParser(description='Run convergence tests for flood damage ensembles')
    parser.add_argument('--scenario', type=str, required=True,
                        help='Flood depth grid id to test convergence for')
    return parser.parse_args()

def run_seed_analysis(config, dg_id, seed, output_dir):
    """
    Generate an UNSAFE ensemble of size N (specified in config file)
    Estimate each property's mean damage in progressively
    increasing sample sizes n_1 to n_m, where n_m=N
    Write out these statistics to a temp file
    """

    start_time = time.time()

    # Max sample size is the last element of the list
    # in our config file
    sows = config['sow_test']
    sow_max = sows[-1]

    # In our main analysis, we vary all input values 
    # for some experiments, so that's what we want to
    # test convergence for. We specify the NSI here
    # because that's one of the experiments where
    # we vary all inputs. 

    nsi_ens_filep = join(EXP_DIR_I, FIPS, 'nsi_inv_ens.pqt')
    nsi_inv_ens = pd.read_parquet(nsi_ens_filep)
    nsi_depths_filep = join(EXP_DIR_I, FIPS, 'nsi_depths.pqt')
    nsi_depths_df = pd.read_parquet(nsi_depths_filep).set_index('fd_id')

    d_min = 0.01
    model_config = {
        'struct_list': ['val_struct', 'ffe', 'num_story', 'found_type'],
        'id_col': 'fd_id',
        'inventory': nsi_inv_ens,
        'depths': nsi_depths_df[[dg_id]],
        'coef_var': config['coef_var'],
        'n_sow': sow_max,
        'id_col': 'fd_id',
        'base_adj': False,
        'depth_min': d_min
    }

    results = unens.get_loss_ensemble(
                    model_config['inventory'],
                    model_config['depths'],
                    config=model_config,
                    vuln_dir=VULN_DIR_I,
                    random_seed=seed
              )

    # Synthesize results for subsets
    dam_col = 'naccs_loss_' + dg_id
    id_col = model_config['id_col']

    sub_dfs = []
    for sow in sows:
        if sow < sow_max:
            temp = results.groupby([id_col]).sample(sow).groupby([id_col])[dam_col].mean()
        else:
            temp = results.groupby([id_col])[dam_col].mean()
        sub_dfs.append(pd.Series(temp, name='n{}'.format(sow)))
    dfs = pd.concat(sub_dfs, axis=1)

    # Write out temp file
    temp_filep = join(output_dir, "seed_{}.pqt".format(seed))
    unfile.prepare_saving(temp_filep)
    dfs.to_parquet(temp_filep)

    elapsed_time = time.time() - start_time
    logger.info(f"Completed seed {seed} in {elapsed_time:.2f} seconds")


def assess_convergence(config, output_dir, fig_dir):
    """
    Load in all the means across seeds
    Estimate the "grand" mean, the mean estimate
    across seeds for the n_m sized samples
    Specify a +/-10% threshold around that value
    Calculate how many properties' mean estimates across all
    seeds fall into the threshold across n_1 through n_m
    Write out the distribution of properties meeting the threshold 
    across the seeds for n_1 through n_m (i.e., how many properties 
    meet it in 0 seeds, 1 seed, ... K seeds for all n_1 through n_m)
    Plot barplots of the proportion of properties that meet the threshold
    across all seeds for n_1 through n_m
    """
    start_time = time.time()

    # Max sample size is the last element of the list
    # in our config file
    sows = config['sow_test']
    sow_max = sows[-1]

    # Directory with our output analyses
    result_files = glob.glob(join(output_dir, "seed_*.pqt"))
    all_seed_results = []
    
    for result in result_files:
        df = pd.read_parquet(result)
        df.loc[:, 'seed'] = int(result.strip('.pqt').split('_')[-1])
        all_seed_results.append(df)

    all_results = pd.concat(all_seed_results, axis=0)    
        
    # Across all seeds, get the mean damage for the property
    # based on the largest sample
    max_col = 'n{}'.format(sow_max)
    all_results.loc[:, 'grand_mean'] = all_results.groupby(['fd_id']).apply(lambda x: x[max_col].mean())

    # Calculate the threshold values
    all_results['low'] = all_results['grand_mean']*.9
    all_results['high'] = all_results['grand_mean']*1.1

    # Check that each damage column meets the threshold
    samp_check = []
    for sow in sows:
        sow_col = f"n{sow}"
        conv_col = f"n{sow}_converged"
        thresh_check = ((all_results[sow_col] >= all_results['low']) &
                        (all_results[sow_col] <= all_results['high']))
        all_results.loc[:, conv_col] = np.where(thresh_check,
                                                1,
                                                0)
        
        # Calculate proportion of properties converged in each seed
        prop_conv = (all_results.groupby(['seed'])[conv_col].sum()/
                    all_results.groupby(['seed'])[conv_col].size())
        samp_check.append(prop_conv)

    # Dataframe with the convergence statistics for each sample size
    # across each seed
    sample_conv_stats = pd.concat(samp_check, axis=1)

    # Write out summary table
    conv_summ_filep = join(FO, "conv_summ.csv")
    sample_conv_stats.to_csv(conv_summ_filep, index=False)

    # Create and write out a diagnostic figure
    sample_conv_stats.columns = sows
    temp = sample_conv_stats.reset_index().melt(id_vars='seed')
    fig, ax = plt.subplots(dpi=300)
    sns.pointplot(data=temp,
                x='variable',
                y='value',
                errorbar='sd',
                ax=ax)
    ax.set_xlabel('Sample Size', size=12)
    ax.set_ylabel('Proportion of Properties\nWith Converged Damage Estiamtes', size=12)
    ax.tick_params(labelsize=12)
    ax.set_ylim([0, 1.02])
    fig.savefig(join(FIG_DIR, 'conv_check.png'), dpi=300, bbox_inches='tight')

    elapsed_time = time.time() - start_time
    logger.info(f"Completed convergence analysis in {elapsed_time:.2f} seconds")


def main():
    args = parse_arguments()
    
    # Set up directory for our analyses
    output_dir = join(FO, "convergence")
    
    # Can easily adjust this to run batch processes
    # but looping through seeds since relatively small problem
    seeds = [x + 1 for x in range(CONFIG['seeds'])]
    logger.info("Starting analysis across {} seeds".format(seeds))
    for seed in seeds:
        run_seed_analysis(CONFIG, args.scenario, seed, output_dir)
        logger.info("Ran Seed: " + str(seed))
    
    logger.info("Assessing convergence")
    # Analyze results
    assess_convergence(CONFIG, output_dir, FIG_DIR)
    
    logger.info("Analysis completed")

if __name__ == "__main__":
    main()