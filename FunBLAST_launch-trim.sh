#!/usr/bin/bash

FUNBLAST_DIR="$HOME/FunBLAST"
INPUT_DIR="$FUNBLAST_DIR/input"
OUTPUT_DIR="$FUNBLAST_DIR/input-trimmed"


cd $FUNBLAST_DIR

mkdir -p $OUTPUT_DIR

# Initialize Conda in the current shell
eval "$(conda shell.bash hook)"

# Activate environment
conda activate funblast-itsx

if [[ "$CONDA_DEFAULT_ENV" != "funblast-itsx" ]]; then
    echo "--> [Error] Failed to activate funblast-itsx environment."
    exit 1
fi

echo "--> Conda environment activated: $CONDA_DEFAULT_ENV"

# Launch trimming script
python3 FunBLAST-trim-ITSx.py \
    --input-dir $INPUT_DIR \
    --output-dir $OUTPUT_DIR \
    --keep-work

