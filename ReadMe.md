# MassBLATer ITS pipeline #

## Disclaimer 
This software is a custom adaptation of the TU‑NHM/massblaster_plutof_pub pipeline. By using it, you agree to comply with the original project's licensing terms as set forth by its creator, Kessy Abarenkov for the Biodiversity Informatics research group of Tartu Univeristy. I dont't own any of code or ressources provided in the massblaster_plutof_pub submodule:  
https://github.com/Henver236/MassBLASTer_ITS/tree/main/massblaster_plutof_pub  
Here is the adresse of the original project:  
https://github.com/TU-NHM/massblaster_plutof_pub   
The author of this customized version provides the code “as‑is” and makes no warranties regarding its performance, accuracy, or suitability for any particular purpose. Consequently, the author cannot be held responsible for the quality, correctness, or any consequences arising from the results generated with this pipeline. Users assume all risk associated with its deployment and should verify outputs independently before relying on them.

## Introduction

This pipeline is designed to run BLASTn on a large number of sequences gathered in a FASTA file (.fas), using ITS databases such as UNITE or INSD.

The output consists of a dynamic HTML page that allows you to view the results, as well as a CSV file (.csv).

The pipeline keeps the three best hits.

---

## Expected Inputs & parsing

Ideally, the pipeline expects a FASTA file (.fas) with a header line that starts with `>`, containing the sequence name and some additional information, followed by a line with the trimmed sequence (without primers).

The expected sequence‑name format is:
```text
<SAMPLE_ID>_<YYMMDD>-<SAMPLE_CODE>[_<OPTIONAL_INFO>...]
````

În other words :
Sequence ID; `_`; sequencing date; `-`; sample code; `_`; the primer used (optionnal).

Exemple :
```fasta
>NTW-6_251027-L7_ITS1F
```
This is the naming convention used by the Fasteris laboratory. However, it's possible to name samples freely as long as the `_` character is avoided.

---

## Usage

1. Upload the data into a `data` folder.
2. Transfer the file to be processed to 
   `~/MassBLASTer_ITS/massblaster_plutof_pub/indata`
3. Prefix the file name with `source_` 
   (e.g.: `source_My_Fasta_File.fas`)
4. Launch the pipeline with the command:
```bash
bash ~/unite-massblaster/load-scale-launcher.sh
```

---

## SLURM

By default, the pipeline runs under SLURM.
SLURM is used to optimise and schedule ressources usage on HPC cluster.

It is possible to modify the SLURM behavior or run the command locally by editing or removing the SLURM snippet at the beginning of the wrapper:
```bash
~/unite-massblaster/launch-massblaster-v3.slurm.sh
```
SLURM snippet looks like this :  
```bash
#SBATCH --job-name=MassBLASTer         # Slurm job name.
#SBATCH --output=slurm-logs/%x_%j.out  # A log output file is created with job name and date/time, and placed in /logs.
#SBATCH --error=slurm-logs/%x_%j.err   # A log errors file is created with job name and date/time, and placed in /logs.
#SBATCH --cpus-per-task=8              # Number of CPU cores used. 8 is enough for 20-30 query Megablast. 
#SBATCH --mem=16G                      # Number of RAM GB used. 16 GB is enough for 20-30 query Megablast.
#SBATCH --time=01:00:00                # Time allocated to the job. 1 hours is enough for a 20-30 query Megablast.
```
Adjuste computational parameters `-num_threads 4` accordingly (see below).

---
## BLAST

BLAST (Basic Local Alignment Search Tool) performs heuristic local sequence alignment: it first detects exact k-mer seeds ("words") and then extends them to produce High Scoring Pairs (HSPs). These alignments are scored according to matches, mismatches, and gap penalties.

Authoritative documentation for these parameters is provided in the NCBI BLAST+ Command Line Applications User Manual :
https://www.ncbi.nlm.nih.gov/books/NBK279690/  
There are other very usefull ressources to understand BLAST tools :  
https://conmeehan.github.io/blast+tutorial.html  
https://www.i.animalgenome.org/bioinfo/resources/manuals/blast2.2.24/user_manual.pdf  
https://www.biob.in/2020/12/creating-custom-database-using.html  

### Line by line description of MassBLASTer launch command

```bash
./massblaster.sif /run_massblaster.sh "$CLEAN_NAME" \
    -num_threads 4 \
    -dust no \
    -db "/massblaster_plutof_rel/data/plutof_fungi_its" \
    -outfmt 15 \
    -reward 1 \
    -gapextend 2 \
    -max_target_seqs 1 \
    -penalty -2 \
    -word_size 28 \
    -gapopen 0
```
---

###  Main command line
`./massblaster.sif /run_massblaster.sh "$CLEAN_NAME"`  
This command runs the Massblaster pipeline inside an Apptainer (Singularity) container (massblaster.sif).
The script internally launches a BLAST+ nucleotide alignment (likely blastn or megablast) to compare query sequences ($CLEAN_NAME) against a local reference database (check -db section below).

---
### Computational parameters  
`-num_threads 4`  

Number of CPU threads (logical cores) used to parallelize the BLAST search. (in this exemple: 4 threads).

Possible values : Integer  
Tipically between 2 to 64, depends of hardware limitations.

---
### Sequence filtering  
`-dust no`  
Controls (enable or disable) the DUST low-complexity filter.  
  
DUST detects low-complexity nucleotide regions such as:  
• homopolymer runs (e.g., AAAAAA)  
• microsatellite-like repeats  
• low-information sequence composition  
  
In this exemple, it's turn off because ITS regions can contain repetitive motifs that may still be taxonomically informative.  

This is also preferred when analyzing:  
• short barcode markers  
• other type of ITS regions (plants, eukaryote)  
• metabarcoding amplicons  
  
Possible values: Boolean ("yes" / "no")

---
### Reference database  
`-db "/massblaster_plutof_rel/data/plutof_fungi_its"`  

Database against which the sequences are compare. 
In this example it's  `plutof_fungi_its`

Other database options are available :
```bash
Option               "Description"

plutof_fungi_its:    "UNITE (only fungi); rDNA ITS"
plutof_nf_its:       "UNITE (non-fungi) / Other_euk_1; rDNA ITS"
insd_its:            "INSD (only fungi); rDNA ITS"
insd_nf_its:         "INSD (non-fungi); rDNA ITS / Other_euk_2"
envir_plutof_its:    "UNITE environmental (all eukaryotes) / Envir; rDNA ITS"
plutof_tri12:        "ToxGen; Tri12"
plutof1:             "UNITE+INSD"
plutof2:             "UNITE+Envir"
plutof3:             "UNITE+Other_euk"
plutof4:             "INSD+Envir"
plutof5:             "INSD+Other_euk"
plutof6:             "Envir+Other_euk"
plutof7:             "UNITE+INSD+Envir"
plutof8:             "UNITE+INSD+Other_euk"
plutof9:             "INSD+Envir+Other_euk"
plutof10:            "UNITE+Envir+Other_euk"
plutof11:            "UNITE+INSD+Envir+Other_euk"
```
Replace the last part of the path with the desired option.
It's alo possible to create a new database from FASTA file. For exemple, UNITE provide FASTA file database that can be convert to multiple files formats needed by BLAST, using the "makeblastdb" command from BLAST+ tool :  
`makeblastdb -in /path/to/fasta/database.fasta -dbtype nucl -out path/to/output/files`  
To download the latest version of UNITE database, go to the adresse belowe and check under "General FASTA release :  
https://unite.ut.ee/repository.php  

Plutof1, plutof2, etc... are alias files. You can create your own.  
Or, instead, you can refer to a groupe of BLAST database files, simply by avoiding using the file format in the path :
`-db "/massblaster_plutof_rel/data/custom_version_of_database"`  
In this exemple, the command refere to all database files who start with a name like "custom_version_of_database", that's to say :  
```text
custom_version_of_database.ndb  
custom_version_of_database.nhr  
custom_version_of_database.nin  
custom_version_of_database.njs  
custom_version_of_database.not  
custom_version_of_database.nsq  
custom_version_of_database.ntf  
custom_version_of_database.nto  
```
Possible values : String  

---
### Output format  
`-outfmt 15`  
Specifies the format of the BLAST output.
Format 15 corresponds to single-file BLAST JSON output.  
JSON file as output is not easy to read but it have advantages :  
•	structured hierarchical format  
•	easy parsing in pipelines  
•	compatible with Python / R / workflow managers  
So it's easier to use it for results visualisation and downstream analysis. 

Default :
Output format is JSON (standard BLAST format 15). 
However, for an unknown reason, output JSON file has a .txt extension. 
Possible values : Integer  

---
### Alignment scoring parameters  
BLAST computes alignment scores using:  
•	match rewards        = `-reward 1`  
•	mismatch penalties   = `-penalty -2`  
•	gap penalties        = `-gapextend 2`  
These parameters directly affect alignment sensitivity and specificity.  

#### Match rewards  
`-reward 1`  
Reward score for a matching nucleotide pair.
Default :  
+1 per correct match.  
Possible values : Integer  

#### Mismatch penalties  
`-penalty -2`  
Penalty assigned to a mismatch.  
Default :  
One different base = –2 points.  
Thus, the alignment score is calculated as +1 for a match, –2 for a mismatch. 
This ratio favors precise alignments, which is suited with ITS data.  

---

### Gap penalties  

#### Opening gap penalties  
`-gapopen 0`  
Cost for opening a gap in the alignment.

Default :  
Gap opening cost = 0.  
This means there is no penalty for initiating a gap, which can increase alignment flexibility.  
Apparently it's atypical, but this makes sense in megablast-like configuration, especially for ITS sequences where insertions/deletions are very frequent.  
Possible values : Integer  

#### Extending gap penalties  
`-gapextend 2`  
Cost for extending an existing gap.  
Higher values discourage long gaps.  
Default :  
Cost to extend a gap = 2.  
A long gap therefore costs more, but the opening penalty is zero (useful for ITS, which often has structural indels).
Possible values : Integer  

---
### Hits limit number  
`-max_target_seqs 1`  
Maximum number of target sequences (hits) reported for each query.  
Default:  
Keep only the best hit. 
MassBLASTER returns only the best single assignment.  
It's possible (recommanded) to customise this option to retrieve 3, 10, or more hits by query.
Possible values : Integer  

---
### Seed size  
`-word_size 28`  
Size of the initial exact match seed used by BLAST.  
Default:  
Seed word length = 28 bases.  
This is unusually long for classic BLASTN but it's align with MassBLASTER’s strategy: stricter matches, less noise, and only serious hits retained.  
If I understand correctly, BLAST's algorithm starts by searching for a perfect match of 28 consecutive nucleotides between the query and sequences in the database. And only then does the algorithm begin to process the similarity of the entire sequence, or sorting best hits.  


Possible values : Integer  
Smaller = higher sensitivity  
Larger = faster but less sensitive  

---
## Files description

#### ► update-NCBI-ITS-db.sh  
Usefull to update manually with the last UNITE database version and convert in extensions needed by BLAST. 

#### ► db-update+convert.sh  
A script to update UNITE db with the last General FASTA release (manually downloaded). 

#### ► its-trim.py  
Used to trim sequences before blast. 
This script will cut every nuclotides before the fisrt "CAT" pattern.
It use a "sliding window" algorithm to choose where to cut the end of each sequence.
By default, the algorithm is set with a 50 nucleotide windows and a 5% treshold. 
It means that if there is more than 5% of ambiguous nucleotide in the 50 nucleotide window, it will cut here and discard the end of the sequence. 

#### ► load-scale-launcher.sh  
This is the main wrapper.  
It will enumerate the numbre of nucleotide in the whole FASTA input file and automatically set ressources needs for BLAST, via SLURM.

#### ► run-massblaster.sh  
This script is launched by load-scale-launcher.sh.  
It will launch BLAST and give the output (a JSON file with a .txt extension) to format-output.py.

#### ► run-massblaster.slurm.sh  
A wrapper to launch the pipeline with custom on a computing node when working on a HPC cluster. 

#### ► format-output.py  
A script that create a CSV file woth all the results and use it to create a HTML page.
Then, this HTML page can be used to display and explore results, a little bit like a NCBI blastn results page.  

---

## Considerations about UNITE database  

### Reps and Refs sequences  
In the UNITE database, the core difference between RefS (Reference Sequences) and RepS (Representative Sequences) lies in curation. 
RepS are automatically chosen from the most common sequence in a Species Hypothesis (SH), while RefS are explicitly selected or confirmed by experts for high quality. 
All species hypotheses (SH) in the UNITE database have a representative sequence (RepS), but only a subset have a manually designated reference sequence (RefS).  
If both exist, the RefS is considered higher quality and takes precedence over the RepS.  
  
More informations available here :  
https://unite.ut.ee/repository.php#:~:text=Following%20K%C3%B5ljalg%20et%20al.,of%20the%20taxon%20at%20hand  


---
## References  
1.	NCBI BLAST+ Command Line Applications User Manual  
https://www.ncbi.nlm.nih.gov/books/NBK279690/ (i.animalgenome.org)  
2.	BLAST output formats and JSON format (outfmt)  
https://www.biob.in/2020/12/creating-custom-database-using.html (biob.in)  
3.	BLAST report formatting and use of max_target_seqs  
https://www.ncbi.nlm.nih.gov/sites/books/NBK279684/ (ncbi.nlm.nih.gov)  
4. UNITE community  
https://unite.ut.ee/  
5. Massblaster PLUTOF GitHub repository  
https://github.com/TU-NHM/massblaster_plutof_pub.git  
6.	Altschul et al. 1990 – Basic Local Alignment Search Tool  
https://doi.org/10.1016/S0022-2836(05)80360-2  



