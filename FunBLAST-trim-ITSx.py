#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FunBLAST: extraction ITS1+5.8S+ITS2 par ITSx, secours conservateur par motifs.

Cette version traite les entrées FASTA. Les FASTQ seront intégrés dans l'étape
qualité prévue ensuite (fastp/ITSxpress).
"""
from __future__ import annotations
import argparse, csv, datetime as dt, logging, re, shutil, subprocess, sys
from pathlib import Path

DEFAULT_OUTPUT = Path("/home/f80878358/FunBLAST/input-trimmed")
EXTENSIONS = {".fa", ".fasta", ".fna", ".fas"}
START_MOTIFS = ("CATTA", "CATTC", "CATTG", "CACTA", "CAGTA", "CATT", "CAT")
ANCHOR_58S = "GAAGAAC"
COMP = str.maketrans("ACGTRYMKBDHVNacgtrymkbdhvn",
                     "TGCAYRKMVHDBNtgcayrkmvhdbn")

def revcomp(s):
    return s.translate(COMP)[::-1]

def read_fasta(path):
    header, chunks = None, []
    with path.open(encoding="utf-8", errors="replace") as f:
        for n, raw in enumerate(f, 1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks).upper()
                header, chunks = line[1:].strip() or f"unnamed_{n}", []
            else:
                if header is None:
                    raise ValueError(f"{path}: séquence avant le premier en-tête FASTA (ligne {n})")
                chunks.append(re.sub(r"\s+", "", line))
    if header is not None:
        yield header, "".join(chunks).upper()

def write_fasta(records, path):
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for header, seq in records:
            count += 1
            f.write(f">{header}\n")
            for i in range(0, len(seq), 80):
                f.write(seq[i:i+80] + "\n")
    return count

def fallback(seq):
    """Coupe le 5' après CATTA/variante; confirme GAAGAAC en aval.
    Ne coupe PAS le 3': ces motifs ne définissent pas la frontière ITS2/28S.
    """
    possibilities = []
    for oriented, strand in ((seq, "forward"), (revcomp(seq), "reverse_complement")):
        window = oriented[:40]
        found = None
        for pos in range(len(window)):
            for motif in START_MOTIFS:
                if window.startswith(motif, pos):
                    found = (pos, pos + len(motif), motif, strand, oriented)
                    break
            if found:
                break
        if found:
            possibilities.append(found)
    if not possibilities:
        return None, "NO_START_MOTIF", "Aucun motif CATTA/variante dans les 40 premières bases"
    pos, end, motif, strand, oriented = sorted(
        possibilities, key=lambda x: (x[0], -len(x[2]))
    )[0]
    anchor_pos = oriented.find(ANCHOR_58S, end)
    if anchor_pos < 0:
        return None, "NO_5_8S_ANCHOR", f"{motif} trouvé, mais {ANCHOR_58S} absent en aval"
    candidate = oriented[end:]
    note = (f"Début coupé après {motif}; {ANCHOR_58S} trouvé à la position "
            f"{anchor_pos+1}; fin 3' conservée sans coupe (frontière ITS2/28S inconnue); "
            f"orientation={strand}")
    return candidate, "FALLBACK_3PRIME_UNTRIMMED", note

def main():
    ap = argparse.ArgumentParser(description="Extraction du segment fongique ITS1+5.8S+ITS2.")
    ap.add_argument("-i", "--input-dir", type=Path, default=Path("indata"),
                    help="Dossier des fichiers FASTA (défaut: ./indata).")
    ap.add_argument("-o", "--output-dir", type=Path, default=DEFAULT_OUTPUT,
                    help=f"Dossier de sortie (défaut: {DEFAULT_OUTPUT}).")
    ap.add_argument("--itsx", default="ITSx", help="Exécutable ITSx (défaut: ITSx).")
    ap.add_argument("--keep-work", action="store_true", help="Conserver les fichiers intermédiaires ITSx.")
    a = ap.parse_args()

    outdir = a.output_dir.expanduser().resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("FunBLAST_ITSx")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (logging.FileHandler(outdir/"trimming_ITSx.log", encoding="utf-8"),
                    logging.StreamHandler(sys.stdout)):
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    start_time = dt.datetime.now()
    indir = a.input_dir.expanduser().resolve()
    logger.info("Début du trimming ITS FunBLAST")
    logger.info("Entrée: %s", indir)
    logger.info("Sortie: %s", outdir)
    if not indir.is_dir():
        logger.error("Dossier d'entrée introuvable: %s", indir)
        return 2
    files = sorted(x for x in indir.iterdir() if x.is_file() and x.suffix.lower() in EXTENSIONS)
    fastqs = sorted(x for x in indir.iterdir() if x.is_file() and
                    x.name.lower().endswith((".fastq", ".fq", ".fastq.gz", ".fq.gz")))
    if fastqs:
        logger.warning("%d FASTQ ignoré(s) dans cette première étape; ils seront traités dans l'étape fastp/ITSxpress.", len(fastqs))
    if not files:
        logger.error("Aucun FASTA trouvé (extensions: %s)", ", ".join(sorted(EXTENSIONS)))
        return 2
    itsx = shutil.which(a.itsx)
    if not itsx:
        logger.error("ITSx introuvable dans le PATH: %s", a.itsx)
        return 2

    records, serial = [], 0
    combined = outdir/"input_combined_internal_ids.fasta"
    with combined.open("w", encoding="utf-8") as dest:
        for file in files:
            nfile = 0
            try:
                for header, seq in read_fasta(file):
                    if not seq:
                        logger.warning("Séquence vide ignorée: %s | %s", file.name, header)
                        continue
                    serial += 1
                    iid = f"FBITS{serial:08d}"
                    records.append((iid, header, seq, file.name))
                    dest.write(f">{iid}\n")
                    for i in range(0, len(seq), 80):
                        dest.write(seq[i:i+80] + "\n")
                    nfile += 1
            except Exception as e:
                logger.exception("Erreur de lecture %s: %s", file, e)
                return 2
            logger.info("%s: %d séquence(s)", file.name, nfile)
    if not records:
        logger.error("Aucune séquence exploitable.")
        return 2
    logger.info("Total: %d séquence(s)", len(records))

    work = outdir/"ITSx_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir()
    prefix = work/"fungal_ITS"
    cmd = [itsx, "-i", str(combined), "-o", str(prefix), "-t", "F",
           "--save_regions", "all", "--preserve", "T", "--fasta", "T",
           "--positions", "T", "--summary", "T", "--not_found", "T",
           "--detailed_results", "T", "--graphical", "F", "--truncate", "T",
           "--partial", "1", "--temp", str(work)]
    logger.info("Lancement ITSx, profil Fungi.")
    logger.info("Commande: %s", " ".join(cmd))
    with (work/"ITSx_stdout.log").open("w") as stdout, (work/"ITSx_stderr.log").open("w") as stderr:
        run = subprocess.run(cmd, stdout=stdout, stderr=stderr, text=True)
    if run.returncode:
        logger.error("ITSx a échoué (code %d). Voir %s et %s", run.returncode,
                     work/"ITSx_stdout.log", work/"ITSx_stderr.log")
        return run.returncode or 1

    full = Path(str(prefix)+".full.fasta")
    if not full.exists():
        logger.error("Fichier ITSx attendu absent: %s. Voir %s", full, work)
        return 1
    accepted = {}
    for header, seq in read_fasta(full):
        iid = header.split()[0]
        accepted[iid] = seq
    logger.info("Extraits ITS complets ITSx: %d", len(accepted))

    final, fallback_records, not_done, rows = [], [], [], []
    for iid, header, seq, source in records:
        if iid in accepted:
            trimmed = accepted[iid]
            final.append((f"{header} | FunBLAST_trim=ITSx | source={source}", trimmed))
            method, status, note = "ITSx", "ACCEPTED_ITSx_FULL", "ITSx a extrait le segment ITS complet."
            after = len(trimmed)
        else:
            candidate, status, note = fallback(seq)
            if candidate:
                fallback_records.append((f"{header} | FunBLAST_trim=FALLBACK_REVIEW | source={source}", candidate))
                method, after = "MOTIF_FALLBACK_REVIEW", len(candidate)
            else:
                not_done.append((f"{header} | FunBLAST_trim=NOT_EXTRACTED | source={source}", seq))
                method, after = "NONE", len(seq)
            rows.append([iid, header, source, method, status, len(seq), after, note])
            continue
        rows.append([iid, header, source, method, status, len(seq), after, note])

    final_path = outdir/"FunBLAST_ITS_full_ITSx.fasta"
    fallback_path = outdir/"FunBLAST_ITS_fallback_candidates_REVIEW.fasta"
    failed_path = outdir/"FunBLAST_ITS_not_extracted.fasta"
    manifest = outdir/"trimming_manifest.csv"
    n1, n2, n3 = write_fasta(final, final_path), write_fasta(fallback_records, fallback_path), write_fasta(not_done, failed_path)
    with manifest.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["sequence_id", "original_header", "source_file", "method", "status",
                    "length_before", "length_after", "notes"])
        w.writerows(rows)

    logger.info("BILAN: total=%d | ITSx complet=%d | secours à vérifier=%d | non extraites=%d",
                len(records), n1, n2, n3)
    logger.info("ITSx complet: %s", final_path)
    logger.info("Secours à vérifier (3' non coupé): %s", fallback_path)
    logger.info("Non extraites: %s", failed_path)
    logger.info("Manifest CSV: %s", manifest)
    logger.info("Log: %s", outdir/"trimming_ITSx.log")
    logger.info("Durée: %.1f secondes", (dt.datetime.now()-start_time).total_seconds())
    if a.keep_work:
        logger.info("Fichiers intermédiaires conservés: %s", work)
    else:
        shutil.rmtree(work, ignore_errors=True)
        logger.info("Fichiers intermédiaires ITSx supprimés (utiliser --keep-work pour les conserver).")
    logger.info("Fin du trimming ITS FunBLAST.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
