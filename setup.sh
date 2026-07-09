#!/usr/bin/env bash

# Create input and output data directories for FunBLAST :
echo "[Info] Creating input and output directories for FunBLAST ..."
mkdir -p indata
mkdir -p userdir
mkdir -p outdata
mkdir -p output
mkdir -p slurm-logs

# Create FunBLAST container from funblast.def with security question :
if [ -f funblast.sif ]; then
    read -r -p "[Warning] Container already exists. Replace it? [y/N] " reply
    reply=${reply:-n}

    case "$reply" in
        y|Y|yes|YES|Yes)
            echo "[Info] Rebuilding container..."
            apptainer build funblast.sif funblast.def
            ;;
        *)
            echo "Skipping build."
            ;;
    esac
else
    echo "[Info] Start building container..."
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
    read -r -p "[Warning] BLAST database already exists. Replace it? [y/N] " reply
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
    echo "[Info] Downloading BLAST database..."
    wget -O "$DB_ARCHIVE" "https://s3.hpc.ut.ee/plutof-public/original/780b17f2-e53a-4631-9adf-9964963bf1ff.gz"

    echo "[Info] Extracting database..."
    tar -xzf "$DB_ARCHIVE"

    echo "[Info] Cleaning up..."
    rm -f "$DB_ARCHIVE"
fi

export BLAST_DB="$PWD/databases"

# end here
echo "[Info] Setup is done !"
