# AHOIS-PRO: Agent Home Investment Decisions Stages Prototype

Welcome to AHOIS-PRO, a prototype tool designed to assist in making informed home investment decisions through simulation.

## Installation

To get started, install the required dependencies using the following command:

```bash
pip install -r requirements.txt
```

Copy `src/.env_template` to `src/.env` and possibly adapt `SN_SETTINGS_FILE_FOR_DYNACONF` to point to the
file `settings.toml` (network generation settings) in case you don't run the model from parent folder of
`src`.

### Testing and debugging
To run tests contained in the `test` directory, execute `python -m unittest` in the top-level directory.  
For debugging, add a `.pth` file to the python installation/virtual environment's site-packages, containing
the path to the top level directory (`"C:\\Users\\..."`). 

## Running the Simulation

### Linux

To run the simulation on a Linux system, execute the following commands in your terminal:


Run the simulation (main method):

```bash
python3 Run.py 
```


### Windows

To run the simulation on a Windows system, execute the following commands in your terminal:

Run the simulation:

```bash
python Run.py 
```

### Installing black and pre-commit
After installing all dependencies with

```bash
pip install -r requirements
```

You will need to activate pre-commit by

```bash
pre-commit install
```

# Profiling configuration
https://jiffyclub.github.io/snakeviz/

cd C:\Users\IvanDigel\git\ahois-pro
py -m cProfile -o program.prof Run.py
snakeviz program.prof

# Analyse

```python
python -m analysis.Analysis
```

# Server

```python
python -m server.Launch
```

# Plots building

```python
python -m plotting.Build_plots
```

# Cluster runs

## Prepare cluster

1. Login to the cluster entry node:

  ```
  ssh <username>@cs1.its.uni-kassel.de
  ```       

2. Configure SSH keys:

  ```
  ssh-keygen -t rsa -b 4096
  ```

3. [Add your public key to your git profile.](https://docs.github.com/de/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) 

4. Clone git repository

```
mkdir ~/ahoi/git
cd ~/ahoi/git
git clone git@github.com:UniK-INES/ahois-pro.git
```

5. Create pipenv and install requirements

```
module load gcc/14.2.0
module load python/3.13.0/gcc-14.2.0
export PYTHONUSERBASE=~/.local
pip install pipenv
cd ~/ahoi/git/ahois-pro/env/cluster
pipenv install
```

6. Copy src/.env_template to src/.env

```
cd ~/ahoi/git/ahois-pro/src 
cp .env_template .env
```

## Adapt settings_local.toml

These setting depend on the user and should be set in `settings_local.toml`:

```
[main]
task = "Validation"
excel_scenario_file = "settings/settings_sh.xlsx"
config_id_start = 0
config_id_end = 1
output_path = "./data/output"

[slurm]
target_cluster_mainpath = "~/ahoi/"
# path to agenthomid code at cluster (ending / required)
target_cluster_modelbase = "@format {this.slurm.target_cluster_mainpath}/git/ahois-pro/"
host = "its-cs1.its.uni-kassel.de"
username = "uk052959"
num_runs_per_batch = 1
transferSlurmFile = true
transferSettingsFile = true
transferScenarioExcelFile = true
executeSLURMscripts = true
fetch_pattern = "pickles/*.*"
```

## Create SLURM batch scripts

* Add configuration lines in `src/settings/settings.xlsx`
* Set `config_id_start` and `config_id_end` accordingly in `settings_local.toml`
* Execute script `experiments/slurm_management.py`

## Create settings_local.toml for cluster

```
[main]
current_scenario = "Scenario_heat_pumps"
project = "AHOI"
task = "Validation"
output_path = "../../../"
excel_scenario_file = "settings/settings_sh.xlsx"
```

Make sure that `settings.main.output_path`, when executed on the cluster,
points to the same location as `settings.slurm.target_cluster_mainpath`

Copy your `settings_local.toml` to the cluster (`settings` folder), e.g.
(performed automatically in case `settings.slurm.transferSettingsFile = true`):

```
cd <path to ahois-pro>/src/settings
scp ./settings_local_cluster.toml <cluster node>:~/ahoi/git/ahois-pro/settings/settings_local.toml
```

## Fetch back results

Use `experiments/slurm_fetchback.py` to copy result data back to your local hard drive.
Consider `settings.slurm.fetch_pattern`.

## Update l18n for figures

1. Extract messages from source code:

```
python setup.py extract_messages
```
        
2. Combine extracted messages and manually added messages (e.g. trigger classes):

```
xgettext(.exe) src/helpers/ahoi_parsed.pot src/helpers/ahoi_manual.pot -o src/helpers/ahoi.pot
```

3. Use [POEdit](https://poedit.net/) to create/edit PO files. 
