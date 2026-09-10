#!/usr/bin/env bash

# A small script to convert fasta database to multi formats blastn db using blast+.
# Input --> .fasta
# Output --> .ndb .nhr .nin .njs .not .ntf .nto 


# Optional :
#module load python

# OPTIONAL: In Gamaello HPC environnment, the only way to install something is in conda :
goconda
# Environnment creation :
conda create -n blast-env
conda activate blast-env
# blastn install :
conda install -c bioconda blast
blastn -version

mkdir -p database
cd /database
# If needed, db decompression:
tar -xvzf /databases/sh_general_release_19.02.2025.tgz -C /databases/

# blastn db creation :
makeblastdb -in /databases/sh_general_release_dynamic_19.02.2025.fasta -dbtype nucl -out database/unite_fungi_its_250219

echo "Done !"