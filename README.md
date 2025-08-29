# Pollack-etal-2025-inprep

**Refining structure inventories for improved flood-risk assessment**

## Abstract
Flood-risk assessments inform consequential public decisions. These assessments increasingly use large-scale structure inventories that offer granular resolution but provide little quality assurance. The U.S. Army Corps’ National Structure Inventory (NSI) is a prominent example. The Corps explicitly recommends that users evaluate data quality and adjust attributes as necessary. However, many studies skip this step. How accurate is the NSI and how do any errors influence risk assessments and decisions? Here we use a case study for the city of Philadelphia, comparing NSI-based damage estimates against estimates with high-quality local inventory data under 50 realistic Hurricane Irene flood scenarios. The common practice of naively adopting the NSI can systematically distort flood damage estimates with potentially drastic implications for resource allocation decisions. Using the NSI to rank census tracts by damage – a common metric for prioritizing federal disaster funding – generally misclassifies one-fifth of tracts regarding their priority status. Simple refinements, including structure location corrections, dramatically improve reliability, leading to correct identification of all tracts with respect to priority status in all but one flood scenario. Our findings demonstrate how overconfident use of granular structure inventories can compromise risk assessments and we provide actionable guidance for enhancing inventory reliability. 

## Journal reference
Will update upon acceptance to a peer-reviewed journal. 

## Overview
This repository stores the entire workflow for the article "Refining structure inventories for improved flood-risk assessment." This study evaluates whether the National Structure Inventory is fit-for-purpose for common risk assessment goals through a Philadelphia, PA case study. 

## Data and Code Reference
This analysis makes use of raw data from a variety of sources and model output data from Deb et al., (2024), [Estuarine hurricane wind can intensify surge-dominated extreme water level in shallow and converging coastal systems, Nat. Hazards Earth Syst. Sci.](https://doi.org/10.5194/nhess-24-2461-2024).

Below, we include links to all of the input data used in this analysis. Some of these data are not available in unique and persistent repositories, which could complicate a user's attempt to reproduce our analysis from scratch in the future. We make all input, processed, and output data from the day of our final analysis available at several Zenodo repositories. 

### Input data

Several datasets were downloaded from minted repositories:

| Dataset | DOI |
|---------|-----|
| Flood depth grids for case study | TO DO - could also just include in our input data release |
| NACCS depth-damage functions | https://zenodo.org/doi/10.5281/zenodo.10027235 |

Several datasets were downloaded from URLs:

| Dataset | URL | Download Data |
|---------|-----|---------------|
| National Structure Inventory (Philadelphia) | https://nsi.sec.usace.army.mil/nsiapi/structures?fips=42101 | May 2, 2025 |
| Philadelphia Assessment Records | https://phl.carto.com/api/v2/sql?filename=opa_properties_public&format=geojson&skipfields=cartodb_id&q=SELECT+*+FROM+opa_properties_public | May 2, 2025 |
| Philadelphia Building Footprints | https://opendata.arcgis.com/api/v3/datasets/ab9e89e1273f445bb265846c90b38a96_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1 | May 2, 2025 |
| Philadelphia Tax Parcel Boundaries | https://opendata.arcgis.com/api/v3/datasets/84baed491de44f539889f2af178ad85c_0/downloads/data?format=geojson&spatialRefId=4326&where=1%3D1 | May 2, 2025 |

The analysis code can automatically downloads datasets from these URLs, but that option is commented out for sharing purposes so that users can readily work with the same data as the published analysis. The download code all downloads US Census shape files (e.g., tracts) and other datasets, all of which are included at this Zenodo repo: .

If you want to download the latest version of the data above, you can uncomment the download code and double-check the specified URLs in the `config/config.yaml` file under the `download` key. 

### Contributing model software

| Model | Repository Link | Version
| ----- | --------------- | ------|
| Uncertain Structure and Fragility Ensemble (UNSAFE) framework for property-level flood risk estimation | https://github.com/abpoll/unsafe | 0.2|

### Output data

All processed and output data are avaialble at the Zenodo repo: . 

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
2) If you used `conda` or `mamba` to create your environment, run `pip install git+https://github.com/abpoll/unsafe@v0.2` to use the modules in UNSAFE. 
3) Set up the [Input data](#input-data).

    a) Run `mkdir data/raw/external/haz/` then download the flood depth grids and catchment area shapefile from the Zenodo repository, which are available in a .zip directory, and unzip the directory. Move the contents (other .zip directories) into `data/raw/external/haz/`.
4) Run the analysis in the following order:

| Script Name | Description | Additional Details|
| ----------- | ----------- | ------------------ |
| `notebooks/prepare_data.ipynb` | Download and unzip data, create structure inventories from raw data, prepare and generate base ensemble data for damage estimates. | You can just run all the cells, but we made this a notebook in the interest of transparency for processing decisions and include detailed descriptions of various processing steps for community scrutiny. |
| `experiments/convergence_test.py` | Identify the sample sizes required for the UNSAFE ensembles. | This script outputs a figure for revieiwng convergence at different sample sizes. |
| `experiments/generate_ensemble.py` | Generate ensembles for all 50 flood scenarios and calcluate performance metrics for different inventory design approaches. | The `config.yaml` file specifies the experimental design choices. |
| `notebooks/results.ipynb` | Generate figures and summary statistics. | -- |

## Contact (corresponding author)
So far, these instructions have resulted in successful reproduction of the figures and statistics reported in the manuscript, but you may run into issues and need assistance debugging. Please contact Adam Pollack at adam.b.pollack@dartmouth.edu if you have any issues following these steps. 
