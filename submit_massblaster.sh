#!/usr/bin/env bash

# Enforce strict error handling and more reliable pipelines.
set -euo pipefail

# Define base and input directories relative to where the script is executed.
BASE_DIR="$PWD"
INPUT_DIR="$BASE_DIR/indata"

# Check if INPUT_DIR exist. If it return nothing, a warning is display. 
ls -l "$INPUT_DIR" || echo "⚠ INPUT_DIR not reachable or not existing ! --> Please run "run_setup.sh" before the fisrt Blast. "

# Create directory for SLURM logs if it does not exist.
mkdir -p slurm-logs

# Enable nullglob to avoid unmatched patterns and list input FASTA files.
shopt -s nullglob
FILES=("$INPUT_DIR"/source_*.fas)

# Check for input files and exit if none found.
if [ ${#FILES[@]} -eq 0 ]; then
    echo "⚠ No file source_*.fas found ⚠"
    exit 1
fi

###############################
### Scaling SLURM Resources ###
###############################

# Iterate over each source FASTA file.
for FILE in "${FILES[@]}"; do

    # Compute total nucleotides (excluding headers) using awk.
    TOTAL_BP=$(awk '!/^>/ {sum += length($0)} END {print sum+0}' "$FILE")

    # Skip files that contain no sequence data.
    if [ "$TOTAL_BP" -eq 0 ]; then
        echo "⚠ Skipping empty file: $FILE"
        continue
    fi

    # Dynamically scale CPU, memory, and time requests based on sequence size.
    if [ "$TOTAL_BP" -lt 50000 ]; then          # Less than 50'000 bp --> 4 cores / 8 GB RAM / 15 min
        CORE=4; MEM=8; TIME=00:15:00
    elif [ "$TOTAL_BP" -lt 500000 ]; then       # Less than 500'000 bp --> 8 cores / 16 GB RAM / 30 min
        CORE=8; MEM=16; TIME=00:30:00
    elif [ "$TOTAL_BP" -lt 1000000 ]; then      # Less than 1'000'000 bp --> 8 cores / 16 GB RAM / 1 h
        CORE=8; MEM=16; TIME=01:00:00
    elif [ "$TOTAL_BP" -lt 10000000 ]; then     # Less than 10'000'000 bp --> 16 cores / 32 GB RAM / 2 h
        CORE=16; MEM=32; TIME=02:00:00
    elif [ "$TOTAL_BP" -lt 500000000 ]; then    # Less than 500'000'000 bp --> 32 cores / 64 GB RAM / 3 h
        CORE=32; MEM=64; TIME=03:00:00
    else
        CORE=64; MEM=128; TIME=05:00:00    # More than 500'000'000 bp --> 64 cores / 128 GB RAM / 5 h
    fi

    # Prevent requesting too many cores for small datasets.
    MIN_BP_PER_CORE=200
    MAX_CORES_BY_SIZE=$(( TOTAL_BP / MIN_BP_PER_CORE ))
    (( MAX_CORES_BY_SIZE < 1 )) && MAX_CORES_BY_SIZE=1
    (( CORE > MAX_CORES_BY_SIZE )) && CORE=$MAX_CORES_BY_SIZE

    # Apply upper limits for CPU and memory resources, according to HPC documentation.
    (( CORE > 64 )) && CORE=120
    (( MEM > 128 )) && MEM=800

    # Print diagnostic information before job submission.
    echo "[INFO] File(s) founded : $FILE"
    echo "[INFO] Total BP: $TOTAL_BP → CPU = $CORE MEM = ${MEM}GB TIME = $TIME"

    # Submit job to SLURM scheduler with specified resources and log locations.
    sbatch \
        --job-name=MassBLASTer \
        --nodes 1 \
        --cpus-per-task="$CORE" \
        --mem="${MEM}G" \
        --time="$TIME" \
        --output=slurm-logs/%x_%j.out \
        --error=slurm-logs/%x_%j.err \
        run_massblaster_pipeline.sh "$FILE"

    echo "[INFO] $FILE is now processed with MassBLASTer..."

done
# End of main loop.

######################
### Job monitoring ###
######################

# Give SLURM time to register the job
sleep 1

# Get the most recent job with this name for this user
JOB_ID=$(squeue -u "$USER" -n MassBLASTer -h -o "%A %V" \
    | sort -k2 -r \
    | head -n1 \
    | awk '{print $1}')

echo "[INFO] Job ID : $JOB_ID"

# Get the Slurm log file using job id
LOG_FILE="slurm-logs/MassBLASTer_${JOB_ID}.out"

echo "[INFO] Monitoring job $JOB_ID..."

while true; do
    STATUS=$(squeue -j "$JOB_ID" -h -o "%T")

    # Job ended or disappeared 
    if [ -z "$STATUS" ]; then
        echo -e "\n[INFO] Job $JOB_ID finished."
        break
    fi

    # Dynamic job status display
    printf "\r[INFO] Job %s status: %s   " "$JOB_ID" "$STATUS"

    # As soon as "RUNNING" status is confirmed → "tail" start to display the log file
    if [ "$STATUS" = "RUNNING" ]; then
        echo -e "\n[INFO] Job is running. Attaching to log..."

        while [ ! -f "$LOG_FILE" ]; do
            sleep 1
        done

        tail -n 50 -f "$LOG_FILE"
        break
    fi

    sleep 1
done
