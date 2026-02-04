#!/bin/bash --login

# Execute the job from the current working directory
#$ -cwd

#SBATCH --job-name=AHOI_%PROJECT%_R%RUN_ID%_C%CONFIG_ID_START%
#SBATCH --partition=%PARTITION%
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=8G
#SBATCH --time=%DURATION%

#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=<EMAIL-ADDRESS>
#SBATCH -o /home/users/0003/%USERNAME%/ahoi/%TASK%/%RUN_ID%/logs/slurm_C%CONFIG_ID_START%.out
#SBATCH -e /home/users/0003/%USERNAME%/ahoi/%TASK%/%RUN_ID%/logs/slurm_C%CONFIG_ID_START%.err


echo "####################################################"
echo "Job started on " `hostname` `date`
echo "Current working directory:" `pwd`
echo "User account: $SBATCH_ACCOUNT"
echo "Job id: $SLURM_JOB_ID"
echo "Job name: $SLURM_JOB_NAME"
echo "####################################################"

module purge
module load gcc/14.2.0
module load python/3.13.0/gcc-14.2.0

#export PYTHONPATH=""

export PIPENV_PIPFILE=~/ahoi/git/ahois-pro/env/cluster/Pipfile

export AHOI_CONFIG_ID_START=%CONFIG_ID_START%
export AHOI_CONFIG_ID_END=%CONFIG_ID_END%
export AHOI_MAIN_RUNID=%RUN_ID%

cd /home/users/0003/%USERNAME%/ahoi/git/ahois-pro/src
srun pipenv run python ./Run.py

echo "finished"