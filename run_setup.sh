#!/usr/bin/env bash

# Create input and output data directories for MassBLASTer :
echo "[Info] Creating input and output directories for MassBLASTer ..."
mkdir -p indata
mkdir -p userdir
mkdir -p outdata
mkdir -p output
mkdir -p slurm-logs

# Create massblaster container from massblaster.def with security question :
if [ -f massblaster.sif ]; then
    read -r -p "[Warning] Container already exists. Replace it? [y/N] " reply
    reply=${reply:-n}

    case "$reply" in
        y|Y|yes|YES|Yes)
            echo "[Info] Rebuilding container..."
            apptainer build massblaster.sif massblaster.def
            ;;
        *)
            echo "Skipping build."
            ;;
    esac
else
    echo "[Info] Start building container..."
    apptainer build massblaster.sif massblaster.def
fi

# Remove old blast database file :
#echo "[Info] Removing old blast database files ..."
#rm -fr massblaster_plutof_rel/

# Download BLAST database files
DB_ARCHIVE="780b17f2-e53a-4631-9adf-9964963bf1ff.gz"
DB_DIR="massblaster_plutof_rel"

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

export BLAST_DB="$PWD/massblaster_plutof_rel"


# end here
echo "[Info] Setup is done !"
