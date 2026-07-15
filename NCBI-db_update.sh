#!/usr/bin/env bash

# Download, timestamp and move database files from NCBI in /FunBLAST/databases/data.
# WARNING : First, run /MassBLASTer_ITS/massblaster_plutof_pub/run_setup.sh

set -euo pipefail

# Set variables :
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )" # Relatively to where the script is.
DBDIR="$SCRIPT_DIR/db"
ENV_NAME="blastdb_env"
DB_NAME="ITS_RefSeq_Fungi"
PIPELINE_DB_DIR="$SCRIPT_DIR/databases/data"

# Test if setup.sh has been run previously :
if [[ ! -d "$SCRIPT_DIR/databases" ]]; then
    echo "ERROR : First, launch setup.sh !"
    exit 1
fi
# ! -d path/to/folder = "the folder doesn't exist"
# "If the folder doesn't exist, then display error meassage."

# Check if conda is available :
if ! command -v conda &>/dev/null; then
    echo "Error : conda not found in the PATH."
    echo "Load the conda module ("go" or "goconda") or install Miniforge/Miniconda before launching this script."
    exit 1
fi

# Start conda in the current shell :
eval "$(conda shell.bash hook)"

# Create the environnment if needed :
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "conda env creation '$ENV_NAME'..."
    conda create -y -n "$ENV_NAME" -c bioconda -c conda-forge blast
fi

# env activation :
conda activate "$ENV_NAME"

# Timestamp variable (here because it needs a conda env):
TIMESTAMP=$(update_blastdb.pl --showall pretty | awk '$0 ~ /^ITS_RefSeq_Fungi/ { match($0, /[0-9]{4}-[0-9]{2}-[0-9]{2}$/, arr); print arr[0] }' | sed 's/-//g')
# TIMESTAMP = Official last update date from the NCBI repo. Manual check, in a conda shell, with : update_blastdb.pl --showall pretty

# Create a folder for DB files (if needed):
mkdir -p "$DBDIR" 

# Launching dowload in $DBDIR :
cd "$DBDIR"
update_blastdb.pl --decompress "$DB_NAME"

# Timestamp on downloaded files :
for file in *; do
    if [[ -f "$file" && "$file" != *_${TIMESTAMP}* ]]; then
        # Base name and extensions extraction :
        base="${file%.*}"
        ext="${file##*.}"
        
        # Rename, for exemple : ITS_RefSeq_Fungi.ndb → ITS_RefSeq_Fungi_20260119_142156.ndb
        mv "$file" "${base}_${TIMESTAMP}.${ext}"
    fi
done

echo "Files renamed with timestamp in : $DBDIR"

# Copie renamed files :
for file in *; do
    if [[ -f "$file" && "$file" == *_* ]]; then  # only timestamped files
        cp "$file" "$PIPELINE_DB_DIR/"
        echo "DB Files copied in : $file → $PIPELINE_DB_DIR/"
    fi
done

# Alias creation :
cd "$PIPELINE_DB_DIR"
LATEST_DB=$(ls -1 ITS_RefSeq_Fungi_*.ndb | tail -1 | sed 's/\..*//')
# List all files ITS_RefSeq_Fungi_*.ndb in reverse and take the latest created.
# Creation of alias file :
cat > plutof12.nal << EOF
#
# Alias file created $(date)
#
# Latest DB: $LATEST_DB
#
DBLIST $LATEST_DB
#
EOF

# Cleaning db folder :
rm -rf $DBDIR/*

echo "DB files updated with success !"

# Deactivate conda env :
conda deactivate


