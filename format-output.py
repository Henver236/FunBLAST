#!/usr/bin/env python3

import json
import csv
import re
import shutil
from html import escape
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# PARAMÈTRES
# ──────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "outdata"
OUTPUT_BASE = BASE_DIR / "output"

timestamp = datetime.now().strftime("%Y%m%d_%H%M")
today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

FINAL_OUTPUT_DIR = OUTPUT_BASE / f"MassBLASTer-ITS_{timestamp}"
FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CSV_OUT = FINAL_OUTPUT_DIR / f"Massblaster-ITS_{timestamp}.csv"

# ──────────────────────────────────────────────
# CSV
# ──────────────────────────────────────────────

csv_rows = []
csv_header = [
    "source_file","query_id","query_title","query_len",
    "sample_name","sci_name",
    "hit_num","accession","title","hit_len",
    "qcovs",
    "hsp_num","bit_score","evalue","identity",
    "align_len","identity_percent",
    "query_from","query_to","hit_from","hit_to","gaps",
    "qseq","hseq","midline"
]

# ──────────────────────────────────────────────
# FONCTIONS
# ──────────────────────────────────────────────

def parse_title(title):
    parts = title.split("|")
    genus_species = parts[0].replace("_"," ") if len(parts)>0 else "NA"
    sh = parts[2] if len(parts)>2 else "NA"
    seq_type = parts[3] if len(parts)>3 else "NA"
    return genus_species, sh, seq_type

# Parse a query title to extract the sample identifier and sample name.
# The title is split using underscores or whitespace as separators.
# If a field is missing, "NA" is returned as a fallback value.
def parse_sample(query_title):
    parts = re.split(r"[_\s]+", query_title)
    sample_id = parts[0] if parts else "NA"
    sample_name = parts[1] if len(parts)>1 else "NA"
    return sample_id, sample_name

# Extract a date from a text string.
# Support format such as: yymmdd
# Returns "unknown" if no date pattern is found.
#def extract_date(text):
#    m = re.search(r"(\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01]))", text)
#    return m.group(1) if m else "unknown"

# Robust date regex parsing
def extract_date(text):
    print(text)
    m = re.search(r"_(\d{6})_", text)
    if not m:
        return "unknown"
    try:
        # Parse YYMMDD
        dt = datetime.strptime(m.group(1), "%y%m%d")
        return dt.strftime("%d-%m-%Y")
    except ValueError:
        return "invalid_date"

# Extract the DB title ("TITLE" line) in .nal file at db_path, or return "unknown". 
def extract_db_name(data):
    try:
        # DB path --> in this case, DB alias path
        db_path = data["BlastOutput2"][0]["report"]["search_target"]["db"]        
        # Extract DB nme from path
        db_name = db_path.split("/")[-1]     
        # Supposing that alias .nal pat and db path are the same, but with file extension .nal
        nal_path = db_path + ".nal"   
        # Reading alias file .nal
        with open(nal_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()        
        # Looking for "TITLE" line
        title = None
        for line in lines:
            line = line.strip()
            if line.startswith("TITLE"):
                # Extract what's after "TITLE", after a space or tabulation
                parts = line.split(None, 1)  # Split on whitespace, max 2 parts
                if len(parts) > 1:
                    title = parts[1].strip()
                break      
        # Return fund title or "unknown"
        return title if title else "unknown"       
    except FileNotFoundError:
        return "unknown"
    except (KeyError, IndexError, TypeError):
        return "unknown"
    except Exception as e:
        return "unknown"

def compute_qcov(hit, qlen):
    intervals=[]
    for hsp in hit["hsps"]:
        s=min(hsp["query_from"],hsp["query_to"])
        e=max(hsp["query_from"],hsp["query_to"])
        intervals.append((s,e))
    intervals.sort()
    merged=[]
    for s,e in intervals:
        if not merged or s>merged[-1][1]:
            merged.append([s,e])
        else:
            merged[-1][1]=max(merged[-1][1],e)
    covered=sum(e-s+1 for s,e in merged)
    return covered/qlen*100 if qlen else 0

def colorize_nt(qc, mc, hc):
    if qc not in "ACTG" or hc not in "ACTG":
        return "red"
    if mc != "|":
        return "red"
    return "green"

def make_alignment(hsp):
    q=hsp["qseq"]; m=hsp["midline"]; h=hsp["hseq"]
    q_pos = hsp["query_from"]
    h_pos = hsp["hit_from"]

    html="<code>"
    for i in range(0,len(q),60):
        qb=q[i:i+60]; mb=m[i:i+60]; hb=h[i:i+60]

        qline=""; mline=""; hline=""

        for qc,mc,hc in zip(qb,mb,hb):
            color = colorize_nt(qc,mc,hc)
            qline += f'<span style="color:{color}">{qc}</span>'
            mline += f'<span style="color:{color}">{mc}</span>'
            hline += f'<span style="color:{color}">{hc}</span>'

        html += f"Query {str(q_pos).ljust(6)} {qline}<br>"
        html += f"{' '*13}{mline}<br>"
        html += f"Sbjct {str(h_pos).ljust(6)} {hline}<br><br>"

        q_pos += len(qb.replace("-",""))
        h_pos += len(hb.replace("-",""))

    html+="</code>"
    return html

def sh_link(sh):
    return f"https://unite.ut.ee/bl_forw_sh.php?sh_name={sh}#fndtn-panel1"

# ──────────────────────────────────────────────
# TRAITEMENT
# ──────────────────────────────────────────────

json_files = [f for f in INPUT_DIR.iterdir() if f.is_file()]

for json_file in json_files:

    with open(json_file) as f:
        data=json.load(f)

    # RAW avec timestamp
    raw_name = f"raw_results_{timestamp}.json"
    shutil.copy(json_file, FINAL_OUTPUT_DIR / raw_name)

    reports=data["BlastOutput2"]

    first_query_title = reports[0]["report"]["results"]["search"]["query_title"]
    seq_date = extract_date(first_query_title)

    fasta_name = json_file.name
    #seq_date = extract_date(fasta_name)
    db_name = extract_db_name(data)

    html_out = FINAL_OUTPUT_DIR / f"{json_file.stem}_{timestamp}.html"

    html=f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
body {{font-family:Arial;margin:20px;}}
table {{border-collapse:collapse;margin-bottom:30px;}}
th,td {{border:1px solid #aaa;padding:6px;}}
th {{background:#002060;color:white;}}
code {{background:#f5f5f5;display:block;font-family:monospace;white-space:pre;}}
.refs {{color:green;font-weight:bold;}}
.indexcol {{width: fit-content; line-height: 1.4em; height: 2.8em; overflow: hidden;}}
#backToTop {{
    position: fixed;
    bottom: 20px;
    right: 20px;
    background-color: #002060;
    color: white;
    padding: 12px 18px;
    border-radius: 8px;
    text-decoration: none;
    font-size: 14px;
    font-weight: bold;
    box-shadow: 0 2px 6px rgba(0,0,0,0.3);
    z-index: 9999;
}}
#backToTop:hover {{
    background-color: #0040a0;
}}
html {{
    scroll-behavior: auto;
}}
</style>
</head>
<body id="top">

<h1>MassBLASTer</h1>
<p><b>Sequenced on:</b> {seq_date}</p>
<p><b>BLASTed on:</b> {today_str}</p>
<p><b>From:</b> {escape(fasta_name)}</p>
<p><b>Database:</b> {escape(db_name)}</p>

<h2>Index</h2>

<table>
<tr>
<th>Query</th>
<th>Sample ID</th>
<th>Sample Name</th>
<th class="indexcol">Hit 1</th>
<th class="indexcol">Hit 2</th>
<th class="indexcol">Hit 3</th>
</tr>
"""

    # INDEX
    for rep in reports:
        s = rep["report"]["results"]["search"]
        qid = s["query_id"]

        sample_id, sample_name = parse_sample(s["query_title"])

        hits_html=""

        for hit in s["hits"][:3]:
            desc=hit["description"][0]
            hsp=hit["hsps"][0]

            genus, sh, seq_type = parse_title(desc["title"])
            identity = hsp["identity"]/hsp["align_len"]*100
            qcov = compute_qcov(hit, s["query_len"])

            seq_class = "refs" if seq_type=="refs" else ""

            hits_html += f"""
<td class="indexcol">
    <span><i>{escape(genus)}</i> <a href="{sh_link(sh)}" target="_blank">{sh}</a></span><br>
    <span><span class="{seq_class}">{seq_type}</span> <b>Ident:{identity:.1f}% Qcov:{qcov:.1f}%</b></span>
</td>
"""

        hits_html += "<td></td>"*(3-len(s["hits"][:3]))

        html += f"""
<tr>
<td><a href="#{qid}">{qid}</a></td>
<td>{sample_id}</td>
<td>{sample_name}</td>
{hits_html}
</tr>
"""

    html+="</table>"

    # DETAILS
    for rep in reports:
        s = rep["report"]["results"]["search"]
        qid = s["query_id"]

        html += f"<h2 id='{qid}'>{qid}</h2>"

        html += """
<table>
<tr>
<th></th>
<th>Hit #</th>
<th>Genus / Species</th>
<th>SH number</th>
<th>Query cover</th>
<th>Bit score</th>
<th>E-value</th>
<th>% identity</th>
<th>Seq type</th>
<th>Match length</th>
</tr>
"""

        for hit in s["hits"]:
            desc=hit["description"][0]
            hsp=hit["hsps"][0]

            genus, sh, seq_type = parse_title(desc["title"])
            identity = hsp["identity"]/hsp["align_len"]*100
            qcov = compute_qcov(hit, s["query_len"])

            rid=f"{qid}_{hit['num']}"
            seq_class = "refs" if seq_type=="refs" else ""

            # CSV remplissage
            for hsp_i in hit["hsps"]:
                pct = hsp_i["identity"]/hsp_i["align_len"]*100
                csv_rows.append([
                    json_file.name, qid, s["query_title"], s["query_len"],
                    sample_name, genus,
                    hit["num"], desc["accession"], desc["title"], hit["len"],
                    f"{qcov:.2f}",
                    hsp_i["num"], hsp_i["bit_score"], hsp_i["evalue"],
                    hsp_i["identity"], hsp_i["align_len"], f"{pct:.2f}",
                    hsp_i["query_from"], hsp_i["query_to"],
                    hsp_i["hit_from"], hsp_i["hit_to"], hsp_i["gaps"],
                    hsp_i["qseq"], hsp_i["hseq"], hsp_i["midline"]
                ])

            html += f"""
<tr>
<td><button onclick="toggle('{rid}')">+</button></td>
<td>{hit['num']}</td>
<td><i>{escape(genus)}</i></td>
<td><a href="{sh_link(sh)}" target="_blank">{sh}</a></td>
<td>{qcov:.1f}%</td>
<td>{hsp['bit_score']}</td>
<td>{hsp['evalue']}</td>
<td>{identity:.1f}%</td>
<td class="{seq_class}">{seq_type}</td>
<td>{hit['len']}</td>
</tr>

<tr id="{rid}" style="display:none;">
<td colspan="10">
<b>Full title:</b><br>{escape(desc["title"])}<br><br>
{make_alignment(hsp)}
</td>
</tr>
"""

        html+="</table>"

    html += """
<script>
function toggle(id){
 var r=document.getElementById(id);
 r.style.display=(r.style.display==="none")?"table-row":"none";
}
</script>

<a href="#top" id="backToTop">Back to the Top</a>

</body>
</html>
"""

    with open(html_out,"w") as f:
        f.write(html)

# CSV écriture
with open(CSV_OUT,"w",newline="") as f:
    writer=csv.writer(f)
    writer.writerow(csv_header)
    writer.writerows(csv_rows)

print("DONE", flush=True)