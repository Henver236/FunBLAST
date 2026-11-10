#!/usr/bin/bash

echo "--> [Info] Running on $(hostname)"
echo "--> [Info] Slurm job ID: $SLURM_JOB_ID"
echo "--> [Info] Allocated node(s): $SLURM_JOB_NODELIST"
echo "---------------------------- Sarting Setup -------------------------------

# Create input and output data directories for FunBLAST :
echo "--> [Info] Creating input and output directories for FunBLAST ..."
mkdir -p indata
mkdir -p userdir
mkdir -p outdata
mkdir -p output
mkdir -p slurm-logs

# Create FunBLAST container from funblast.def with security question :
if [ -f funblast.sif ]; then
    read -r -p "--> [Warning] Container already exists. Replace it? [y/N] " reply
    reply=${reply:-n}

    case "$reply" in
        y|Y|yes|YES|Yes)
            echo "--> [Info] Rebuilding container..."
            apptainer build funblast.sif funblast.def
            ;;
        *)
            echo "--> Skipping build."
            ;;
    esac
else
    echo "--> [Info] Start building container..."
    apptainer build funblast.sif funblast.def
fi

# Remove old blast database file :
#echo "[Info] Removing old blast database files ..."
#rm -fr databases/

# Download BLAST database files
DB_ARCHIVE="780b17f2-e53a-4631-9adf-9964963bf1ff.gz"
DB_DIR="databases"
DOWNLOAD_DB=1

if [ -d "$DB_DIR" ]; then
    read -r -p "--> [Warning] BLAST database already exists. Replace it? [y/N] " reply
    reply=${reply:-n}

    case "$reply" in
        y|Y|yes|YES|Yes)
            echo "--> Removing old database..."
            rm -rf "$DB_DIR"
            ;;
        *)
            echo "--> Keeping existing database."
            DOWNLOAD_DB=0
            ;;
    esac
fi

if [ "$DOWNLOAD_DB" -eq 1 ]; then
    echo "--> [Info] Downloading BLAST database..."
    wget -O "$DB_ARCHIVE" "https://s3.hpc.ut.ee/plutof-public/original/780b17f2-e53a-4631-9adf-9964963bf1ff.gz"

    echo "--> [Info] Extracting database..."
    tar -xzf "$DB_ARCHIVE"

    echo "--> [Info] Cleaning up..."
    rm -f "$DB_ARCHIVE"

    mv massblaster_plutof_rel databases

fi

export BLAST_DB="$PWD/databases"

# Control if the apptainer container have been created :
if [ -f funblast.sif ]; then
    echo "--> [Info] FunBLAST setup is successfully done !"
else
    echo "--> [Warning] FunBLAST container has not been created..."
fi

# Check for Conda install : Try goconda first, then check Conda version. If nothing detected, display error message.
if ! goconda; then
    echo "--> [Warning] goconda failed. Checking Conda installation..."

    if command -v conda >/dev/null 2>&1; then
        CONDA_VERSION=$(conda --version | awk '{print $2}')
        echo "--> Conda $CONDA_VERSION detected."
    else
        echo "--> [Error] Conda is not detected. Install conda 26.1.1 or newer version first."
        exit 1
    fi
fi


# Create ITSx environment
echo "--> [Info] Checking Conda environment for ITSx..."

if conda env list | grep -qE '^[[:space:]]*funblast-itsx[[:space:]]'; then
    read -r -p "--> [Warning] funblast-itsx conda environment already exists. Replace it? [y/N] " reply
    reply=${reply:-n}

    case "$reply" in
        y|Y|yes|YES|Yes)
            echo "--> Removing old conda environment..."
            conda env remove -n funblast-itsx -y || exit 1

            echo "--> Creating new conda environment..."
            conda create -n funblast-itsx \
                -c conda-forge \
                -c bioconda \
                itsx=1.1.3 \
                -y
            ;;
        *)
            echo "--> Keeping existing conda environment."
            ;;
    esac
else
    echo "--> Creating conda environment..."
    conda create -n funblast-itsx \
        -c conda-forge \
        -c bioconda \
        itsx=1.1.3 \
        -y
fi


# end here
echo "---------------------------- End of Setup -------------------------------"