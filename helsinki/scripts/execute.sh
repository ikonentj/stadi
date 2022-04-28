#!/bin/bash
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=<<<N_CPU>>>
#SBATCH --array=0-<<<N_BATCHES>>>
#SBATCH --mem=22000

module purge
module load anaconda
source activate hullbikes_env

srun python execute.py <<<CASE>>> <<<RUN>>> <<<MODEL>>> -l $SLURM_ARRAY_TASK_ID
