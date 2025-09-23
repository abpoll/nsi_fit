# Pollack-etal-2025-inprep

**Overconfident use of national structure inventories can misguide risk assessments and resource allocation**

## Abstract
Flood-risk assessments guide billions in investments. These assessments increasingly use nationwide structure inventories that offer granular resolution but come with little quality assurance. What are the inaccuracies surrounding these datasets and how do they influence risk assessments and decisions? Here we show that typical application of the U.S. National Structure Inventory (NSI) can systematically distort flood damage estimates compared to a more accurate local inventory, with critical implications for resource allocation. The NSI introduces damage discrepancies even when structure characteristics match between inventories. Crucially, discrepancies do not cancel out in aggregate. Using the NSI to rank census tracts by damage—a common approach for prioritizing federal funding—misranks all but one of the top 10% most damaged tracts. Recognizing the important role of national structure inventories in research and practice, we identify practical recommendations to help remedy their overconfident use. 

## Journal reference
Will update upon acceptance to a peer-reviewed journal. 

## Overview
This repository stores the entire workflow for the article "Overconfident use of national structure inventories can misguide risk assessments and resource allocation." This study evaluates whether the National Structure Inventory is fit-for-purpose for common risk assessment goals through a Philadelphia, PA case study. 

## Data and Code Reference
This analysis makes use of raw data from a variety of sources and model output data from Deb et al., (2024), [Estuarine hurricane wind can intensify surge-dominated extreme water level in shallow and converging coastal systems, Nat. Hazards Earth Syst. Sci.](https://doi.org/10.5194/nhess-24-2461-2024).

Below, we include links to all of the input data used in this analysis. Some of these data are not available in unique and persistent repositories, which could complicate a user's attempt to reproduce our analysis from scratch in the future. We make all input, processed, and output data from the day of our final analysis available at the MSD-Live Data Repository: [TO DO]

### Input data

Several datasets were downloaded from minted repositories:

| Dataset | DOI |
|---------|-----|
| Flood depth grids for case study | TO DO |
| NACCS depth-damage functions | https://zenodo.org/doi/10.5281/zenodo.10027235 |

Note that the damage functions are included when you clone this repository. 

Several datasets were downloaded from URLs:

| Dataset | URL | Download Data |
|---------|-----|---------------|
| National Structure Inventory (Philadelphia) | https://nsi.sec.usace.army.mil/nsiapi/structures?fips=42101 | May 2, 2025 |
| Philadelphia Assessment Records | https://phl.carto.com/api/v2/sql?filename=opa_properties_public&format=geojson&skipfields=cartodb_id&q=SELECT+*+FROM+opa_properties_public | May 2, 2025 |
| Philadelphia Building Footprints | https://opendata.arcgis.com/api/v3/datasets/ab9e89e1273f445bb265846c90b38a96_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1 | May 2, 2025 |
| Philadelphia Tax Parcel Boundaries | https://opendata.arcgis.com/api/v3/datasets/84baed491de44f539889f2af178ad85c_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1 | May 2, 2025 |

The analysis code automatically downloads datasets from these URLs, but that option is commented out for sharing purposes so that users can readily work with the same downloads as us. The download code all downloads US Census shape files (e.g., tracts) and other datasets, all of which are included at the MSD-LIVE repo and specified in the `config/config.yaml` file under the `download` key. 

### Contributing model software

| Model | Repository Link | Version
| ----- | --------------- | ------|
| Uncertain Structure and Fragility Ensemble (UNSAFE) framework for property-level flood risk estimation | https://github.com/abpoll/unsafe | 0.2|

### Output data

All processed and output data are avaialble at the MSD-LIVE repo. 

## Reproduce our analysis
Reproducibility for this project does not guarantee bit-wise reproduction for all results because there are stochastic processes. However, you should obtain very similar results because we tested our sample sizes for convergence (with specified seeds, so you can reproduce those results) to ensure we sample sufficiently for all reported results. 

These instructions assume that you have [conda](https://docs.conda.io/en/latest/) or [mamba](https://mamba.readthedocs.io/en/latest/) installed. These instructions were successfully followed on the following systems:
1. A macOS Sequoia (version 15.5) machine with conda version 23.11.0 and mamba version 1.5.5. Mamba solves the environment much faster than conda and is recommended if you have it set up.

### Environment set up
Clone the repository into a local project directory.

This project was developed with Python version 3.12.10

#### With Conda
From the terminal in your local project directory, run `cd env` and then `conda env create -f env/environment.yml` or replace `conda` with `mamba`.

This is the approach the developers used, and our colleagues who tested the repository for reproducibility.

#### With Pip
From the terminal in your local project directory, `pip install -r requirements.txt` The developers have less experience with `pip`, but it seems like if you use this approach you may want to create a virtual environment with Python verison 3.12.10 before installing the packages into the environment. 

#### Create ipykernel to run Jupyter Notebooks
Create an ipykernel for the environment. For the remainder of the instructions, we refer to this as the 'project environment.' If you are new to Jupyter Notebooks and/or conda, please see: https://ipython.readthedocs.io/en/stable/install/kernel_install.html#kernels-for-different-environments. 

### Rerunning the analysis

1) Activate the environment you set up
2) Run `pip install git+https://github.com/abpoll/unsafe@v0.2` to use the modules in UNSAFE. 
3) Set up the [Input data](#input-data).

    a) Run `mkdir data/raw/external/haz/` then download the flood depth grids and catchment area shapefile, which are available in a .zip directory, and unzip the directory. Move the contents (other .zip directories) into `data/raw/external/haz/`.
4) Run the analysis in the following order:

| Script Name | Description | Additional Details|
| ----------- | ----------- | ------------------ |
| `notebooks/prepare_data.ipynb` | Download and unzip data, create structure inventories from raw data, prepare and generate base ensemble data for damage estimates | You can just run all the cells, but we made this a notebook in the interest of transparency for processing decisions and include detailed descriptions of various processing steps for community scrutiny. |
| `experiments/generate_ensemble.py` | Generate ensembles for all 50 flood scenarios and calcluate performance metrics for different inventory design approaches | The `config.yaml` file specifies the experimental design choices. |
| `experiments/convergence_test.py` | Identify the sample sizes required for the UNSAFE ensembles | This script outputs a figure for revieiwng convergence at different sample sizes. Run `python convergence_test.py --scenario 009` from the `experiments/` directory to reproduce our results. |
| `notebooks/results.ipynb` | Generate figures and summary statistics | -- |

For the `notebooks/prepare_data.ipynb`, some cells are initially commented out (e.g., downloading data and unzipping compressed data) because we make all the inputs available. You are free to uncomment and test that functionality, but note that the code downloads data from servers and this may be different than the inputs we used in our analysis. 

## Contact (corresponding author)
So far, these instructions have resulted in successful reproduction of the figures and statistics reported in the manuscript, but you may run into issues and need assistance debugging. Please contact Adam Pollack at adam.b.pollack@dartmouth.edu if you have any issues following these steps. 
