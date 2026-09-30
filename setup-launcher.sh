#!/usr/bin/bash

srun --pty \
    --job-name=FunBLAST-Setup \
    --cpus-per-task=2 \
    --mem=4G \
    --time=00:15:00 \
    bash ./setup.sh

