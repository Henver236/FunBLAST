#!/usr/bin/env bash
set -euo pipefail

START=$(date +%s)

FILE="$1"
BASE_DIR="$PWD"

if [ -z "$FILE" ]; then
    echo "[Error] No input file provided !"
    exit 1
fi

THREADS=${SLURM_CPUS_PER_TASK:-1}

# Extract run_id
FILENAME=$(basename "$FILE")
RUN_ID=${FILENAME#source_}

echo "[INFO] Processing: $RUN_ID with $THREADS threads"

WORK_DIR="$BASE_DIR"
USER_DIR="$WORK_DIR/userdir/$RUN_ID"
OUTDATA_DIR="$WORK_DIR/outdata"

mkdir -p "$USER_DIR"
rm -rf "$USER_DIR"/*

cp "$FILE" "$USER_DIR/"

cd "$WORK_DIR"

# Apptainer should be available on computing nodes, but, if needed :
# module load apptainer

# Apptainer + blast in one shot
apptainer exec funblast.sif blastn \
    -task megablast \
    -num_threads "$THREADS" \
    -dust no \
    -db "$WORK_DIR/databases/data/NCBI" \
    -outfmt 15 \
    -reward 1 \
    -gapextend 2 \
    -max_target_seqs 10 \
    -penalty -2 \
    -word_size 28 \
    -gapopen 0 \
    -query "$USER_DIR/source_$RUN_ID" \
    -out "$USER_DIR/result.txt"

# Move result
mv "$USER_DIR/result.txt" "$OUTDATA_DIR/"

# Post-processing
python3 "$BASE_DIR/format-output.py"

# Cleanup
rm -rf "$WORK_DIR/outdata/"*
rm -rf "$WORK_DIR/userdir/"*

END=$(date +%s)
ELAPSED=$((END - START))

printf "[OK] FunBLAST run time --> %02d:%02d:%02d\n" \
$((ELAPSED/3600)) $((ELAPSED%3600/60)) $((ELAPSED%60))
