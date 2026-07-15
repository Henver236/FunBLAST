#!/usr/bin/env python3

from Bio import SeqIO
from Bio.Seq import Seq
import re
import sys
import os
from datetime import datetime

# =========================
# Parameters
# =========================
START_PATTERN = "CAT"
WINDOW_SIZE = 80
THRESHOLD = 0.05

AMBIGUOUS_RE = re.compile(r"[NRYWSKMBDHV]", re.IGNORECASE)

# =========================
# Input / Output
# =========================
# Input file provided in the command (e.g.: python its-trim-3.py my_fasta-file.fas)
input_file = sys.argv[1]

# Extract base name (remove path)
base_name = os.path.basename(input_file)

# Split name and extension
name, ext = os.path.splitext(base_name)

# Format timestamp (DDMMYY_HHMMSS)
timestamp = datetime.now().strftime("%d%m%y_%H%M%S")

# Build output filename
output_file = f"{name}_trimmed_{timestamp}{ext}"

# =========================
# Trimming function
# =========================
def trim_sequence(seq, start_pattern=START_PATTERN,
                  window_size=WINDOW_SIZE,
                  threshold=THRESHOLD):

    seq = str(seq)

    # 1) Trim from start pattern
    start = seq.find(start_pattern)
    if start == -1:
        return None

    seq = seq[start:]

    # 2) Trim from end (robust approach)
    for i in range(len(seq) - window_size, 0, -1):
        window = seq[i:i + window_size]
        amb = len(AMBIGUOUS_RE.findall(window))

        if amb / window_size <= threshold:
            return seq[:i + window_size]

    # 3) Fallback: aggressive trim in mid sequence if no clean region found
    return seq[:len(seq) // 2]


# =========================
# Processing
# =========================
total = 0
kept = 0
discarded = 0

with open(output_file, "w") as out:
    for record in SeqIO.parse(input_file, "fasta"):
        total += 1

        trimmed = trim_sequence(record.seq)

        if trimmed and len(trimmed) > 0:
            kept += 1
            record.seq = Seq(trimmed)
            SeqIO.write(record, out, "fasta")
        else:
            discarded += 1

# =========================
# Summary
# =========================
print("\n=== Trimming summary ===")
print(f"Input file      : {input_file}")
print(f"Output file     : {output_file}")
print(f"Total sequences : {total}")
print(f"Kept            : {kept}")
print(f"Discarded       : {discarded}")
print("========================\n")