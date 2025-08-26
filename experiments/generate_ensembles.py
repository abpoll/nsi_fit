#!/usr/bin/env python
# generate_ensembles.py

import pandas as pd
import numpy as np
from pathlib import Path
import logging
import yaml
from yaml.loader import SafeLoader
import time
import pickle
from os.path import join
from scipy import stats
from sklearn.metrics import mean_squared_error

import unsafe.ensemble as unens

# We want to keep track of how the analysis goes
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s')
logger = logging.getLogger("generate_ensembles")

# Set up a few filename constants
ABS_DIR = Path().absolute().parents[0]
FI = join(ABS_DIR, "data", "interim")
FO = join(ABS_DIR, "data", "results")
EXP_DIR_I = join(FI, "exp")
HAZ_DIR_I = join(FI, "haz")
VULN_DIR_I = join(FI, "vuln")

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

def create_comparison_dataframe(results_dict,
                                phil_inventory,
                                nsi_inventory, 
                                dam_col,
                                ref_id,
                                result_keys=['phil']):
    """
    Create a dataframe that links building IDs to different reference IDs
    for both Philadelphia and NSI data and aggregates damage and value
    to the level of the reference ID.
    
    Parameters:
    -----------
    results_dict : dict
        Dictionary containing ensemble results
    phil_inventory : DataFrame
        Philadelphia inventory data
    nsi_inventory : DataFrame
        NSI inventory data
    dam_col : str
        Column name for damage values
    ref_id: str
        Name of the spatial reference (e.g., "tract_id"). Must be in
        the phil_refs and nsi_refs dataframes
    result_keys : list, default=['phil']
        Key to access specific results in results_dict
        
    Returns:
    --------
    DataFrame
        Comparison dataframe with damage and property values for both datasets aggregated to
        the level of ref_id
    """
    # Process each result key
    result_dfs = {}
    for key in result_keys:
        # Determine which reference dataframe to use based on key prefix
        if key.startswith('phil'):
            id_col = 'bfid'
            inventory = phil_inventory
        else:
            id_col = 'fd_id'
            inventory = nsi_inventory

        # Process ensemble results
        temp = results_dict[key]
        if ref_id not in temp.columns:
            # temp will have the id as a column, not index
            # but inventory has id as index
            # so reset index on inventory for merge
            temp = temp.merge(inventory.reset_index(), on=id_col)

        # Add dummy sow_ind for the no_unc dataframes
        if 'sow_ind' not in temp.columns:
            temp['sow_ind'] = 1

        temp_gb = temp.groupby(['sow_ind', ref_id]).agg({dam_col: 'sum'}).reset_index()
        loss_by_ref = temp_gb.groupby(ref_id)[dam_col].mean()
        
        ref_vals = inventory.groupby(ref_id).agg({'val_struct': ['median', 'sum', 'size']})
        ref_vals = ref_vals.reset_index()
        ref_vals.columns = [ref_id, 'median_val', 'total_val', 'n_prop']
        
        # Create result dataframe
        result_df = pd.DataFrame({
            dam_col: loss_by_ref,
            'median_val': ref_vals.set_index(ref_id)['median_val'],
            'total_val': ref_vals.set_index(ref_id)['total_val'],
            'n_prop': ref_vals.set_index(ref_id)['n_prop']
        })
        
        result_df = result_df[result_df[dam_col].notnull()]
        result_dfs[key] = result_df

    # Combine all dataframes
    all_dfs = []
    
    # Process result dataframes
    for key, df in result_dfs.items():
        df_reset = df.reset_index()
        df_reset.columns = [ref_id] + [f"{col}_{key.split(':')[0]}" for col in df.columns]
        all_dfs.append(df_reset)

    # Merge all dataframes
    if all_dfs:
        result = all_dfs[0]
        for df in all_dfs[1:]:
            result = result.merge(df, on=ref_id, how='outer')
        
        return result.fillna(0)
    else:
        return pd.DataFrame()

def calculate_metrics(comp_df, exps, dam_col, baseline='phil'):
    """Calculate various skill metrics for each experiment compared to baseline."""
    metrics = {}
    
    # Baseline values
    baseline_loss = comp_df[f"{dam_col}_{baseline}"]/1e6
    baseline_val = comp_df[f"median_val_{baseline}"]
    baseline_rank = baseline_loss.rank(ascending=False)
    baseline_total = baseline_loss.sum()
    
    # Top 10% tracts in baseline
    top10_threshold = int(len(comp_df) * 0.1)
    top10_tracts = baseline_loss.nlargest(top10_threshold).index
    
    for exp in exps:
        exp_metrics = {}
        
        # Calculate losses and ranks
        exp_loss = comp_df[f"{dam_col}_{exp}"]/1e6
        exp_val = comp_df[f"median_val_{exp}"]
        exp_rank = exp_loss.rank(ascending=False)
        exp_total = exp_loss.sum()
        
        # Total discrepancy metrics
        exp_metrics['total_discrepancy_dollar'] = exp_total - baseline_total
        exp_metrics['total_discrepancy_pct'] = 100 * (exp_total - baseline_total) / baseline_total
        
        # RMSE metrics
        exp_metrics['rmse_tract'] = np.sqrt(mean_squared_error(baseline_loss, exp_loss))
        
        # Correlation between structure value and damages

        exp_metrics['corr_val_dam'] = (stats.pearsonr(exp_loss, exp_val)[0] -
                                       stats.pearsonr(baseline_loss, baseline_val)[0])
        

        # Rank correlation metrics
        exp_metrics['rank_correlation'] = stats.spearmanr(exp_rank, baseline_rank)[0]
        
        # Top percentage rank correlation
        exp_metrics['rank_correlation_top20'] = stats.spearmanr( 
            exp_rank[baseline_rank <= len(top10_tracts)],
            baseline_rank[baseline_rank <= len(top10_tracts)]
        )[0]
        
        # Type 1 and Type 2 errors for top 10%
        # Type 1: Baseline says it's top 10%, experiment says it's not
        type1_error = len(set(top10_tracts) - set(exp_loss.nlargest(top10_threshold).index))
        exp_metrics['type1_error_count'] = type1_error 
        exp_metrics['type1_pct'] = 100*type1_error/top10_threshold
        
        # Type 2: Experiment says it's top 10%, baseline says it's not
        type2_error = len(set(exp_loss.nlargest(top10_threshold).index) - set(top10_tracts))
        exp_metrics['type2_error_count'] = type2_error 
        exp_metrics['type2_pct'] = 100*type2_error/top10_threshold
        
        # Mean absolute error in tract damage percent
        exp_metrics['matched_top_rank_pct'] = (
             exp_rank[exp_rank <= len(top10_tracts)] -
             baseline_rank[baseline_rank <= len(top10_tracts)] == 0
            ).sum()*100/len(top10_tracts)


        # std error of ranks
        exp_metrics['std_rank'] = np.std(
            baseline_rank - exp_rank
        )

        metrics[exp] = exp_metrics
    
    return metrics

def strct_summ_stats(primary_df, reference_df, strct_col, id_col='tract_id'):
    """
    Create statistical distributions of building characteristics for census tracts.
    
    Parameters:
    -----------
    primary_df : DataFrame
        The primary dataframe containing the characteristic to analyze
    reference_df : DataFrame
        The reference dataframe that may contain additional tracts not in primary_df
    strct_col : str
        The column name of the categorical characteristic to analyze (e.g., 'found_type', 'num_story')
    id_col : str, default='tract_id'
        The column name for the geographic identifier (e.g., census tract)
        
    Returns:
    --------
    DataFrame
        A dataframe with the distribution of the characteristic for all tracts in both dataframes,
        using tract-specific distributions where available and overall averages for tracts missing
        from the primary_df that we draw the tract-level distributions from.
    """

    # Find tracts in reference_df that are missing from primary_df
    missing_tracts = reference_df[~reference_df[id_col].isin(primary_df[id_col])][id_col].unique()
    
    # Calculate tract-level distributions for the characteristic in primary_df
    char_sum = primary_df.groupby([id_col, strct_col]).size()
    char_prop = char_sum / primary_df.groupby(id_col).size()
    
    # Convert to a pivot table with tracts as rows and characteristic values as columns
    char_stats = (
        char_prop.reset_index()
        .pivot(index=id_col, columns=strct_col, values=0)
        .fillna(0)
    )
    
    # Calculate the overall distribution across all records in primary_df
    overall_dist = primary_df.groupby(strct_col).size() / len(primary_df)
    
    # Get the unique values of the characteristic
    char_values = overall_dist.index.tolist()
    
    # Create a dataframe with the overall distribution for each missing tract
    n_missing = len(missing_tracts)
    
    if n_missing > 0:
        # Create a matrix of the overall distribution repeated for each missing tract
        fill_df = pd.DataFrame(
            np.repeat([overall_dist.values], n_missing, axis=0),
            index=missing_tracts,
            columns=overall_dist.index
        )
        
        # Combine with the tract-specific distributions
        char_stats = pd.concat([char_stats, fill_df], axis=0)
    
    # Ensure all columns exist (in case some characteristic values don't appear in some tracts)
    for val in char_values:
        if val not in char_stats.columns:
            char_stats[val] = 0
    
    return char_stats

def run_ensemble_analysis(base_configs, model_configs, dg_id, s_name, save_ens, output_dir):
    """
    Generate an UNSAFE ensemble for the depth grid id and compare
    the specified experiments to losses obtained with the Philly inventory. 

    Save only if save_ens == True, otherwise we only
    calculate performance metrics and save these.

    Parameters
    ----------
    base_configs : dict
        Dictionary of the base experimental configurations
        for generating ensembles.
    
    model_configs : dict
        Dictionary of the configurations for each experiment.

    dg_id: str
        The id for the depth grid.
    
    s_name: str
        Indicates which analysis the results are for (main, sens analysis 1, etc.,)
        
    save_ens : Boolean
        Whether to save the UNSAFE ensemble.

    output_dir : str
        Where to write performance metrics (and the ensemble, if specified) 
    
    Returns
    -------
    pandas.DataFrame
        DataFrame containing the experiment performance metrics for the flood scenario
    
    """

    start_time = time.time()

    # Run all simulations
    results = {}
    for model_name, model_config in model_configs.items():
        # Combine configurations
        run_config = {**base_configs}
        for key in ['struct_list', 'id_col', 'found_param', 'stories_param']:
            if key in model_config:
                run_config[key] = model_config[key]
        
        # Run the ensemble
        results[model_name] = unens.get_loss_ensemble(
            model_config['inventory'],
            model_config['depths'][[dg_id]],
            config=run_config,
            vuln_dir=VULN_DIR_I,
        )
        # Save all experiment ensembles if saving depth grid results
        if save_ens:
            exp_filep = join(output_dir, f'main_exp_{dg_id}_{model_name}_{s_name}.pqt')
            results[model_name].to_parquet(exp_filep)
        
    # We also run a no uncertainty variation for
    # the inventory approach skill analysis
    # We can use the inventory/depths from our main
    # comparison experiment
    no_unc = unens.benchmark_naccs_loss(
        model_configs['nsi_ddfs']['inventory'],
        model_configs['nsi_ddfs']['depths'][[dg_id]],
        VULN_DIR_I,
        base_adj=base_configs['base_adj'],
        depth_min=base_configs['depth_min'],
    )
    # Save no uncertainty results if saving depth grid results
    if save_ens:
        no_unc.to_parquet(join(output_dir, f"no_unc_{dg_id}_{s_name}.pqt"))

    ### Calculate summary stats for each experiment and return ### 
    # We need to aggregate all the damage estimates to the tract
    # level, combine the data, and then calculate the skill metrics

    # Add nsi_nounc key to results for combining estimates
    results['nsi_nounc'] = no_unc

    # Call the comparison dataframe function for census tract
    dam_col = 'naccs_loss_' + dg_id
    ref_col = 'tract_id'
    # We'll use all the generated results
    result_keys = [x for x in results.keys()]
    comp = create_comparison_dataframe(results,
                                       model_configs['phil']['inventory'],
                                       model_configs['nsi_ddfs']['inventory'],
                                       dam_col,
                                       ref_col,
                                       result_keys)

    # Calculate skill metrics from comparison dataframe
    exps = ['nsi_nounc', 'nsi_ddfs', 'nsi_unsafe', 'nsi_phil', 'nsi_allphil', 'nsiadj_unsafe']
    metrics = calculate_metrics(comp, exps, dam_col)

    elapsed_time = time.time() - start_time
    logger.info(f"Completed ensemble analysis in {elapsed_time:.2f} seconds")

    return metrics

def main():
    # Set up directory for our analyses
    output_dir = Path(join(FO, "ensembles"))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    ### Prepare experiment info from config ###
    # Number of flood scenarios
    n_ens = CONFIG['haz_nens']
    # Depth grids to save (list)
    main_scen = CONFIG['main_dg']
    # SOWs for main flood scenario ensemble
    # (rest are specified in experiment config)
    n_sow_main = CONFIG['sows']
    # Base & model-specific configurations
    base_configs = CONFIG['base_configs']
    model_configs = CONFIG['model_configs']
    # Sample configurations for main and sens analysis 
    sample_configs = CONFIG['sample_configs']
    # SOWs for non main scenarios
    n_sow_supp = base_configs['no_adj']['n_sow']

    ### Load in all input data for ensembles ### 
    # Load in NSI & Phil inventories
    nsi_inv_ens = pd.read_parquet(join(EXP_DIR_I, FIPS, 'nsi_inv_ens.pqt'))
    nsi_inv_ens_adj = pd.read_parquet(join(EXP_DIR_I, FIPS, 'nsi_inv_ens_adj.pqt'))
    phil_inv_ens = pd.read_parquet(join(EXP_DIR_I, FIPS, 'phil_inv_ens.pqt'))

    # Load in NSI & Phil depth dataframes
    nsi_depths_filep = join(EXP_DIR_I, FIPS, 'nsi_depths_updated.pqt')
    phil_depths_filep = join(EXP_DIR_I, FIPS, 'phil_depths.pqt')
    nsi_depths_df = pd.read_parquet(nsi_depths_filep)
    phil_depths_df = pd.read_parquet(phil_depths_filep).set_index('bfid')

    # Derive summary stats on structure distributions
    phil_found_stats = strct_summ_stats(phil_inv_ens, nsi_inv_ens, 'found_type')
    phil_stories_stats = strct_summ_stats(phil_inv_ens, nsi_inv_ens, 'num_story')
    nsi_found_stats = strct_summ_stats(nsi_inv_ens, phil_inv_ens, 'found_type')
    nsi_stories_stats = strct_summ_stats(nsi_inv_ens, phil_inv_ens, 'num_story')

    ### Update model configs ###
    # Loop through experiments and based on 
    # base_data & supp_data fields, update 
    # the dictionary key/values for passing on
    # to the analysis function

    # We want to run all experiments where we assume all
    # structures are res1 as well - this will be our
    # main analysis because of the missing res3 basement
    # ddfs (our ad hoc adjustments will be a sensitivity
    # analysis)

    for s_name, sample_filters in sample_configs.items():
        trunc_val = sample_configs[s_name]['trunc_val']
        depth_min = sample_configs[s_name]['depth_min']
        res1_bool = sample_configs[s_name]['res1_bool']

        for exp_name, fields in model_configs.items():
            # Set the inventory and depth data
            if model_configs[exp_name]['base_data'] == 'phil':
                model_configs[exp_name]['inventory'] = phil_inv_ens.copy()
                model_configs[exp_name]['depths'] = phil_depths_df.copy()
                model_configs[exp_name]['id_col'] = 'bfid'
            elif model_configs[exp_name]['base_data'] == 'nsi':
                model_configs[exp_name]['inventory'] = nsi_inv_ens.copy()
                model_configs[exp_name]['depths'] = nsi_depths_df.copy()

                # If value adjust flag is True, we need to update
                # the NSI inventory structure values
                # to better reflect the Philly structure values.
                # We will do this by calculating discrepancy of average
                # tract level value and applying this factor
                # to each property in the tract
                if model_configs[exp_name]['val_adj']:
                    phil_vals = phil_inv_ens.groupby('tract_id')['val_struct'].median()
                    temp_vals = nsi_inv_ens[['tract_id']].copy().reset_index()
                    temp_vals = temp_vals.merge(phil_vals, on='tract_id')
                    temp_vals['val_struct'] = temp_vals['val_struct'].fillna(0)
                    val_upd = dict(zip(temp_vals['fd_id'], temp_vals['val_struct']))
                    temp = model_configs[exp_name]['inventory'].copy()
                    temp['val_struct'] = temp.index.map(val_upd)

                    model_configs[exp_name]['inventory'] = temp.copy()
            else:
                model_configs[exp_name]['inventory'] = nsi_inv_ens_adj.copy()
                model_configs[exp_name]['depths'] = nsi_depths_df.copy()
            
            # Update occtype if sample rule calls for it
            if res1_bool:
               # Make all the properties RES1
               temp = model_configs[exp_name]['inventory'].copy()
               temp.loc[:,'occtype'] = 'RES1'
               model_configs[exp_name]['inventory'] = temp.copy()
            
            # Update base config
            base_configs['no_adj']['depth_min'] = depth_min

            # Truncate values if sample rule calls for it
            if trunc_val:
                temp = model_configs[exp_name]['inventory'].copy()
                # Update value structure based on the following rules
                # If stories_n in 3, we want to adjust value at risk
                # Assume uniform value throughout building
                # If no basement, multiply by 2/3
                # If basement, multiply by 3/4
                b_mask = (temp['stories_n'] == 3) & (temp['found_type'] == 'B')
                nb_mask = (temp['stories_n'] == 3) & (temp['found_type'] != 'B')
                temp.loc[b_mask, 'val_struct'] = temp.loc[b_mask, 'val_struct']*.75
                temp.loc[nb_mask, 'val_struct'] = temp.loc[nb_mask, 'val_struct']*.67

                model_configs[exp_name]['inventory'] = temp.copy()

            # Set the summary stats data
            if 'phil_stories_stats' in model_configs[exp_name]['supp_data']:
                model_configs[exp_name]['stories_param'] = phil_stories_stats
            if 'phil_stories_found' in model_configs[exp_name]['supp_data']:
                model_configs[exp_name]['stories_param'] = phil_found_stats
            if 'nsi_stories_stats' in model_configs[exp_name]['supp_data']:
                model_configs[exp_name]['stories_param'] = nsi_stories_stats
            if 'nsi_stories_found' in model_configs[exp_name]['supp_data']:
                model_configs[exp_name]['stories_param'] = nsi_found_stats

        ### Loop through scenarios and conduct analyses ###
        # Can easily adjust this to run batch processes
        # but looping through scenarios since relatively small problem
        # We'll concat all metrics together to write out a single file
        logger.info(f"Starting ensemble analysis across flood scenarios: {s_name}")
        all_metrics = []
        for ens in range(n_ens):
            # By default, we don't save the ensemble
            save_ens = False

            # Need to adjust the ensemble number to meet 
            # the format of our scenario ids
            dg_id = str(ens + 1).zfill(3)

            # Update sow for main scenario(s)
            # and save_ens option
            if dg_id in main_scen:
                base_configs['no_adj']['n_sow'] = n_sow_main
                save_ens = True
            else:
                base_configs['no_adj']['n_sow'] = n_sow_supp

            # Run ensemble analysis
            metrics = run_ensemble_analysis(base_configs['no_adj'], model_configs,
                                            dg_id, s_name, save_ens, output_dir)
            metrics_df = pd.DataFrame.from_dict(metrics).reset_index()
            metrics_df = metrics_df.rename(columns={'index': 'metric'})
            metrics_df = metrics_df.melt(id_vars='metric', var_name='experiment')
            metrics_df['dg_id'] = dg_id
            all_metrics.append(metrics_df)
            logger.info(f"Ran Ensemble Analysis for Flood Scenario: {dg_id}")

        all_metrics_df = pd.concat(all_metrics, axis=0)
        all_metrics_df.to_parquet(join(output_dir, f'all_metrics_{s_name}.pqt'))

        logger.info("Wrote all performance metrics to file")

if __name__ == "__main__":
    main()