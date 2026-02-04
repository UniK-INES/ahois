.. _recipes_slurmClusterRuns:

SLURM-managed Cluster Runs
==========================

.. contents::
   :local:
   :backlinks: top


.. _cluster_config:

Preface
-------

 * Per project, a particular Scenario-Excel-File should be maintained
   (see :ref:`Preparation <recipes_slurmClusterRuns_preparation>`).

 * SLURM Batch files und their execution script are locally created and copied to the cluster via SCP

 * Local folder structure for generated SLRUM files:

 	Generated execution scripts (`executeScript_<AHOI_MAIN__PROJECT>_<AHOI_MAIN__SCENARIO_ID>.sh`) are stored in

 		``<AHOI_MAIN__OUTPUT_PATH>/<AHOI_MAIN__PROJECT>/<initial runnumber>/<AHOI_SLURM__TARGET_EXECFILES>``

 	Batch files (`sbatchScript_<AHOI_MAIN__PROJECT>_R<RUNID>.sh`) will be stored in

 		``<AHOI_MAIN__OUTPUT_PATH>/<AHOI_MAIN__PROJECT>/<initial runnumber>/<AHOI_SLURM__TARGET_BATCHFILES>``

 * The cluster folder structure for generated execution scripts is (see also :ref:`concepts_output_structure`):

 	Generated SLURM execution scripts are stored in

 		``<AHOI_SLURM__TARGET_CLUSTER_MAINPATH>/<AHOI_MAIN__PROJECT>/<initial runnumber>/<AHOI_SLURM_TARGET_EXECFILES>``

 	Batch files will be stored in

 		``<AHOI_SLURM__TARGET_CLUSTER_MAINPATH>/<AHOI_MAIN__PROJECT>/<initial runnumber>/<AHOI_SLURM__TARGET_BATCHFILES>``


.. _`cluster_config_setup`:


Obtain Cluster Login
--------------------

1.  Register at the cluster (e.g. using `IDM of Uni Kassel <https://www.uni-kassel.de/its/it-dienste-software/hochleistungsrechnen-hpc/zugang.html>`_).


Setup Cluster
-------------

1.  Login from local machine to cluster server:

    ::

        ssh <USERNAME>@its-cs1.its.uni-kassel.de


2.  Create folder for git-Repository, e.g.:

    ::

        mkdir -p ahois/git


3.  Create SSH key pair

    ::

        ssh-keygen -t rsa -b 4096

    - just confirm suggested target dir
    - just confirm empty passphrase

3. [Add your public key to your git profile.]() 


4.  Copy public key to gitlab (
    `Gitlab instructions <https://docs.github.com/de/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account>`_)

    1. Open /home/<USERNAME>/.ssh/id_rsa.pub at the cluster server and copy content
    2. Login to gitlab
    3. Your avatar > Edit profile > SSH keys
    4. Add new key
    5. Paste the file content into 'Key'
    6. Remove the 'Expiration date' avoiding expiring
    7. Add Key

5.  Clone repository

    ::

        cd  ahois/git
        git clone git@github.com:UniK-INES/ahois-pro.git


6.  Checkout devel

    ::

        cd ahois-pro/
        git checkout main


7. Create pipenv and install requirements

	::
	
		module load gcc/14.2.0
		module load python/3.13.0/gcc-14.2.0
		export PYTHONUSERBASE=~/.local
		pip install pipenv
		cd ~/ahoi/git/ahois-pro/env/cluster
		pipenv install


8. Copy src/.env_template to src/.env

	::

		cd ~/ahoi/git/ahois-pro/src 
		cp .env_template .env


Optional: Configure SSH keys to avoid password typing when accessing from local machine
---------------------------------------------------------------------------------------

Linux
~~~~~

::

       ssh-copy-id <USERNAME>@its-cs1.its.uni-kassel.de
       ssh its-cs1.its.uni-kassel.de "chmod 0600 ~/.ssh/authorized_keys"

Windows
~~~~~~~

1. Generate SSH key if not existing. Follow prompts, agree to the default suggested file location.
   This will create 2 files: id_rsa and id_rsa.pub

	::

		cd $env:USERPROFILE\.ssh; ssh-keygen.exe

.. hint::

	If you want to use the ssh key with PuTTY and/or WinSCP, you need to generate a key with puttygen. puttygen is automatically included in a PuTTY installation, as a separate program. It is also possible to have both keys.

2. Transfer public key to server:

	::

		type $env:USERPROFILE\.ssh\id_rsa.pub |
		mkdir -p -m 700 .ssh;
		ssh its-cs1.its.uni-kassel.de "cat >> .ssh/authorized_keys"

3. Adjust file permissions settings:

	::

	   ssh its-cs1.its.uni-kassel.de "chmod 0600 ~/.ssh/authorized_keys"


.. hint::

	In case you want to shortcut the ssh command you may add an entry to `~\\.ssh\\config`:

	::

		Host clus
		  HostName its-cs1.its.uni-kassel.de
		  User <YOUR CLUSTER SERVER USERNAME>
		    IdentityFile C:\Users\<YOUR WINDWOS USERNAME>\.ssh\id_rsa
		    IdentitiesOnly yes
			ForwardAgent yes


Requirements
------------
 * There are unique Scenario-IDs per project.

 * SLURM related settings need to be adapted, preferrably in your `settings.toml`:

 	::

 		[slurm]
		host = "its-cs1.its.uni-kassel.de"
		username = "<CLUSTER USERNAME>"


.. _recipes_slurmClusterRuns_preparation:



Preparation (per Project)
-------------------------

#. Copy ``src/settings/settings.xlsx`` to ``settings/<PROJECT>/settings_<PROJECT>.xlsx``

#. Assign filename of ``cluster/<PROJECT>/settings_<PROJECT>.xlsx`` to ``MAIN__EXCEL_SCENARIO_FILE``.

#. Define scenarios in ``cluster/<PROJECT>/settings_<PROJECT>.xlsx``.

#. Copy and adapt ``experiments/slurm_script_template.sh``.

   - <EMAIL-ADDRESS> (1x)
   - <USERNAME> (5x)

#. Set filename of the new SLURM template to ``SLURM__TEMPLATE_FILE``

#. To execute SLURM on the cluster by the script make sure your SSH configuration is working.
   To this end, an entry in ``<USER-DIRECTORY>/.ssh/config`` such as the following may help:

::

	Host clus
	  HostName its-cs1.its.uni-kassel.de
	  User <YOUR CLUSTER SERVER USERNAME>
	    IdentityFile C:\Users\<YOUR WINDWOS USERNAME>\.ssh\id_rsa
	    IdentitiesOnly yes
		ForwardAgent yes

Optional: Copy files to the cluster
-----------------------------------

::

   cd <local dir of file to copy>
   scp <file> <USERNAME>@its-cs1.its.uni-kassel.de:/home/<USERNAME>/ahois/slurm

Creation of Cluster scripts
---------------------------
* Add configuration lines in `src/settings/settings.xlsx`
* Set `config_id_start` and `config_id_end` accordingly in `settings_local.toml`
* 

1. Define scenario to simulate

	..	code-block:: toml
	
		[main]
		current_scenario = "Scenario_heat_pumps"
		project = "AHOI"
		task = "Validation"
		output_path = "../../../"
		excel_scenario_file = "settings/settings_sh.xlsx"
	
	
	Make sure that `settings.main.output_path`, when executed on the cluster,
	points to the same location as `settings.slurm.target_cluster_mainpath`
	
	Copy your `settings_local.toml` to the cluster (`settings` folder), e.g.
	(performed automatically in case `settings.slurm.transferSettingsFile = true`):
	
		::
	
			cd <path to ahois-pro>/src/settings
			scp ./settings_local_cluster.toml <cluster node>:~/ahoi/git/ahois-pro/settings/settings_local.toml


2. Make sure cluster code is up-to-date

::

	ssh <username>@its-cs1.its.uni-kassel.de
	cd <Path to local git repository>
	git pull


3. Run python script (``slurm_management.py``) to

	::
	
		execute script `experiments/slurm_management.py`


Cluster commands
----------------

- State of cluster nodes

  ::

      sinfo -l -e

- Inspect own queue

  ::

      squeue -u <USERNAME> -o "%.7i %.9P %.18j %.8u %.2t %.10M %.6D %R" |more

- Detailed information about a job

  ::

      scontrol show jobid -dd <Job-ID>

- Cancel job

  ::

      scancel <jobid>

- Inspect finished job

  ::

      sacct -j <jobid>


Fetch back results
------------------

Use `experiments/slurm_fetchback.py` to copy result data back to your local hard drive.
Consider `settings.slurm.fetch_pattern`.
