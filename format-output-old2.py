#!/usr/bin/env python3
"""FunBLAST report generator: standalone, searchable and paginated HTML + CSV."""
import argparse, csv, json, re, shutil
from datetime import datetime
from pathlib import Path

CSV_HEADER = ["source_file","query_id","query_title","query_len","sample_name","sci_name","hit_num","accession","title","hit_len","qcovs","hsp_num","bit_score","evalue","identity","align_len","identity_percent","query_from","query_to","hit_from","hit_to","gaps","qseq","hseq","midline"]


def parse_title(title):
    p=(title or "").split("|")
    return (p[0].replace("_"," ") if p else "NA", p[2] if len(p)>2 else "NA", p[3] if len(p)>3 else "NA")


def parse_sample(title):
    p=re.split(r"[_\s]+", title or "")
    return (p[0] if p and p[0] else "NA", p[1] if len(p)>1 and p[1] else "NA")


def extract_date(text):
    m=re.search(r"_(\d{6})_", text or "")
    if not m: return "unknown"
    try: return datetime.strptime(m.group(1), "%y%m%d").strftime("%d-%m-%Y")
    except ValueError: return "invalid_date"


def extract_db_name(data):
    try:
        db=data["BlastOutput2"][0]["report"]["search_target"]["db"]
        nal=Path(db+".nal")
        if nal.is_file():
            for line in nal.read_text(encoding="utf-8",errors="replace").splitlines():
                if line.strip().startswith("TITLE"):
                    parts=line.strip().split(None,1)
                    if len(parts)>1: return parts[1]
        return Path(db).name or "unknown"
    except (KeyError,IndexError,TypeError,OSError): return "unknown"


def qcov(hit, qlen):
    spans=[]
    for h in hit.get("hsps",[]) or []:
        a,b=h.get("query_from",0),h.get("query_to",0)
        if a and b: spans.append((min(a,b),max(a,b)))
    spans.sort(); merged=[]
    for a,b in spans:
        if not merged or a>merged[-1][1]+1: merged.append([a,b])
        else: merged[-1][1]=max(merged[-1][1],b)
    return sum(b-a+1 for a,b in merged)/qlen*100 if qlen else 0.0


def number(x):
    try: return float(x)
    except (ValueError,TypeError): return 0.0


def make_query(rep, source, csv_rows):
    s=rep.get("report",{}).get("results",{}).get("search",{}) or {}
    qid=str(s.get("query_id") or "unknown_query"); title=str(s.get("query_title") or "")
    qlen=int(s.get("query_len") or 0); sample_id,sample_name=parse_sample(title)
    q={"id":qid,"title":title,"length":qlen,"sample_id":sample_id,"sample_name":sample_name,"hits":[]}
    for hit in s.get("hits",[]) or []:
        descs=hit.get("description",[]) or []; desc=descs[0] if descs else {}
        full_title=str(desc.get("title") or ""); organism,sh,seq_type=parse_title(full_title)
        hsps=hit.get("hsps",[]) or []; best=hsps[0] if hsps else {}
        alen=number(best.get("align_len")); ident=number(best.get("identity")); pct=ident/alen*100 if alen else 0
        coverage=qcov(hit,qlen)
        q["hits"].append({"num":hit.get("num",len(q["hits"])+1),"title":full_title,"descriptions":descs,"organism":organism,"sh":sh,"seq_type":seq_type,"accession":str(desc.get("accession") or ""),"length":hit.get("len",0),"qcov":coverage,"bit_score":best.get("bit_score",""),"evalue":best.get("evalue",""),"identity_pct":pct,"hsps":hsps})
        for h in hsps:
            n=number(h.get("align_len")); i=number(h.get("identity")); hpct=i/n*100 if n else 0
            csv_rows.append([source,qid,title,qlen,sample_name,organism,hit.get("num",""),desc.get("accession",""),full_title,hit.get("len",""),f"{coverage:.2f}",h.get("num",""),h.get("bit_score",""),h.get("evalue",""),h.get("identity",""),h.get("align_len",""),f"{hpct:.2f}",h.get("query_from",""),h.get("query_to",""),h.get("hit_from",""),h.get("hit_to",""),h.get("gaps",""),h.get("qseq",""),h.get("hseq",""),h.get("midline","" )])
    return q

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>FunBLAST</title>
<style>
:root{--navy:#092b58;--blue:#1769aa;--line:#d9e1eb;--muted:#5c6878;--bg:#f5f7fa}*{box-sizing:border-box}body{font:14px/1.45 Arial,sans-serif;margin:0;background:var(--bg);color:#172334}header{background:var(--navy);color:white;padding:22px 26px}header h1{margin:0 0 8px;font-size:25px}main{max-width:1500px;margin:22px auto;padding:0 18px}.meta,.stats,.toolbar,.panel{background:white;border:1px solid var(--line);border-radius:9px;padding:15px;margin-bottom:15px}.meta{display:flex;flex-wrap:wrap;gap:8px 24px}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}.stat strong{display:block;font-size:22px;color:var(--navy)}.stat span,.muted{color:var(--muted)}.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.toolbar input,.toolbar select{padding:9px;border:1px solid #bbc7d5;border-radius:6px;font:inherit}button{cursor:pointer;border:1px solid #9aabc0;background:white;border-radius:6px;padding:7px 10px;color:var(--navy)}button:disabled{opacity:.4;cursor:not-allowed}table{width:100%;border-collapse:collapse;background:white}th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#eaf0f7;color:#17375e;position:sticky;top:0}tr.query-row:hover{background:#f0f6fc}.pagination{display:flex;gap:10px;align-items:center;justify-content:flex-end;padding:12px 0}#details{display:none}.hit{border:1px solid var(--line);border-radius:8px;margin:12px 0;padding:12px;background:white}.hit h3{margin:0 0 8px;font-size:16px}.hit-meta{color:var(--muted);margin-bottom:8px}pre{overflow:auto;background:#f4f6f8;padding:12px;border-radius:6px;font:12px/1.5 monospace;white-space:pre}.empty{padding:25px;text-align:center;color:var(--muted)}@media(max-width:700px){main{padding:0 8px}th,td{padding:7px;font-size:12px}}
</style></head><body><header><h1>FunBLAST</h1><div id="subtitle"></div></header><main><section class="meta" id="meta"></section><section class="stats" id="stats"></section>
<section id="list" class="panel"><div class="toolbar"><input id="search" type="search" placeholder="Search query, sample, taxon, accession…" style="min-width:260px;flex:1"><select id="filter"><option value="all">All queries</option><option value="with">Queries with hits</option><option value="without">Queries without hits</option></select><select id="size"><option>25</option><option selected>50</option><option>100</option><option>200</option></select></div><div style="overflow:auto"><table><thead><tr><th>Query</th><th>Sample</th><th>Length</th><th>Hits</th><th>Top hit</th><th>Identity</th><th>Query cover</th></tr></thead><tbody id="rows"></tbody></table></div><div class="pagination"><span id="page-label" class="muted"></span><button id="prev">Previous</button><button id="next">Next</button></div></section>
<section id="details" class="panel"><button id="back">← Back to queries</button><h2 id="detail-title"></h2><div id="detail-meta" class="muted"></div><div id="hit-details"></div></section></main>
<script id="report-data" type="application/json">__DATA__</script><script>
"use strict";const D=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id);let page=0;
$('subtitle').textContent=D.filename+' · '+D.created;for(const [k,v] of [['Sequenced on',D.sequence_date],['Database',D.database],['BLAST',D.version]]){let s=document.createElement('span');s.textContent=k+': '+v;$('meta').append(s)}
const total=D.queries.reduce((n,q)=>n+q.hits.length,0);function stat(k,v){let d=document.createElement('div'),b=document.createElement('strong'),s=document.createElement('span');b.textContent=v;s.textContent=k;d.className='stat';d.append(b,s);$('stats').append(d)}stat('Queries',D.queries.length.toLocaleString());stat('Total hits',total.toLocaleString());stat('Queries with hits',D.queries.filter(q=>q.hits.length).length.toLocaleString());stat('Queries without hits',D.queries.filter(q=>!q.hits.length).length.toLocaleString());
function filtered(){let t=$('search').value.trim().toLowerCase(),f=$('filter').value;return D.queries.filter(q=>{if(f==='with'&&!q.hits.length)return false;if(f==='without'&&q.hits.length)return false;if(!t)return true;return [q.id,q.title,q.sample_id,q.sample_name,...q.hits.flatMap(h=>[h.organism,h.title,h.accession,h.sh])].join(' ').toLowerCase().includes(t)})}
function render(){let a=filtered(),n=Number($('size').value)||50,pages=Math.max(1,Math.ceil(a.length/n));page=Math.min(page,pages-1);let body=$('rows');body.replaceChildren();for(let q of a.slice(page*n,(page+1)*n)){let tr=document.createElement('tr');tr.className='query-row';let h=q.hits[0],vals=[q.id,q.sample_id+' / '+q.sample_name,q.length,q.hits.length,h?h.organism:'No hit',h?h.identity_pct.toFixed(1)+'%':'—',h?h.qcov.toFixed(1)+'%':'—'];for(let v of vals){let td=document.createElement('td');td.textContent=String(v??'');tr.append(td)}tr.tabIndex=0;tr.addEventListener('click',()=>show(q.id));tr.addEventListener('keydown',e=>{if(e.key==='Enter')show(q.id)});body.append(tr)}if(!a.length){let tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=7;td.className='empty';td.textContent='No matching query';tr.append(td);body.append(tr)}$('page-label').textContent=`${a.length} queries · Page ${page+1}/${pages}`;$('prev').disabled=page===0;$('next').disabled=page>=pages-1}
function show(id){let q=D.queries.find(x=>x.id===id);if(!q)return;$('list').style.display='none';$('details').style.display='block';$('detail-title').textContent=q.id+' — '+q.title;$('detail-meta').textContent=`Sample: ${q.sample_id} / ${q.sample_name} · ${q.length} nt · ${q.hits.length} hits`;let box=$('hit-details');box.replaceChildren();if(!q.hits.length){let p=document.createElement('p');p.className='empty';p.textContent='No BLAST hit for this query.';box.append(p)}for(let h of q.hits){let card=document.createElement('article');card.className='hit';let title=document.createElement('h3');title.textContent=`Hit ${h.num} — ${h.organism}`;card.append(title);let m=document.createElement('div');m.className='hit-meta';m.textContent=`Accession: ${h.accession||'NA'} · SH: ${h.sh} · ${h.seq_type} · Identity: ${h.identity_pct.toFixed(1)}% · Query cover: ${h.qcov.toFixed(1)}% · Bit score: ${h.bit_score} · E-value: ${h.evalue} · Length: ${h.length}`;card.append(m);let p=document.createElement('p');p.textContent='Full title: '+h.title;card.append(p);for(let [i,x] of h.hsps.entries()){let det=document.createElement('details'),sum=document.createElement('summary'),pre=document.createElement('pre');sum.textContent=`Alignment HSP ${x.num??i+1} — score ${x.bit_score??'NA'}, E-value ${x.evalue??'NA'}`;pre.textContent=`Query ${x.query_from??''}\n${x.qseq??''}\n${x.midline??''}\nSbjct ${x.hit_from??''}\n${x.hseq??''}`;det.append(sum,pre);card.append(det)}box.append(card)}window.scrollTo(0,0)}
$('search').addEventListener('input',()=>{page=0;render()});$('filter').addEventListener('change',()=>{page=0;render()});$('size').addEventListener('change',()=>{page=0;render()});$('prev').addEventListener('click',()=>{page--;render()});$('next').addEventListener('click',()=>{page++;render()});$('back').addEventListener('click',()=>{$('details').style.display='none';$('list').style.display='block';window.scrollTo(0,0)});render();
</script></body></html>'''


def process_file(path, outdir, stamp, created, csv_rows):
    with path.open(encoding="utf-8") as f: data=json.load(f)
    reports=data.get("BlastOutput2",[]) or []; queries=[make_query(r,path.name,csv_rows) for r in reports]
    version=reports[0].get("report",{}).get("version","unknown") if reports else "unknown"
    payload={"filename":path.name,"created":created,"sequence_date":extract_date(queries[0]["title"] if queries else ""),"database":extract_db_name(data),"version":version,"queries":queries}
    raw=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
    raw=raw.replace("&","\\u0026").replace("<","\\u003c").replace(">","\\u003e").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    html=HTML.replace("__DATA__",raw)
    dest=outdir/f"{path.stem}_{stamp}.html";dest.write_text(html,encoding="utf-8")
    return len(queries),sum(len(q["hits"]) for q in queries),dest


def main():
    base=Path(__file__).resolve().parent;p=argparse.ArgumentParser(description="Generate standalone FunBLAST HTML and CSV")
    p.add_argument("--input-dir",type=Path,default=base/"outdata");p.add_argument("--output-dir",type=Path,default=base/"output");a=p.parse_args()
    if not a.input_dir.is_dir():raise SystemExit(f"Input directory does not exist: {a.input_dir}")
    #files=sorted(x for x in a.input_dir.iterdir() if x.is_file() and x.suffix.lower()=='.json')
    files = sorted(x for x in a.input_dir.iterdir() if x.is_file() and x.suffix.lower() in {'.json', '.txt'})
    if not files:raise SystemExit(f"No JSON files found in {a.input_dir}")
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S');created=datetime.now().strftime('%Y-%m-%d %H:%M:%S');out=a.output_dir/f"FunBLAST-ITS_{stamp}";out.mkdir(parents=True,exist_ok=False)
    rows=[];nq=nh=0
    for f in files:
        shutil.copy2(f,out/f"raw_{f.name}");q,h,dest=process_file(f,out,stamp,created,rows);nq+=q;nh+=h
        print(f"[OK] {f.name}: {q} queries, {h} hits -> {dest.name}",flush=True)
    with (out/f"FunBLAST-ITS_{stamp}.csv").open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(CSV_HEADER);w.writerows(rows)
    print(f"[DONE] {nq} queries, {nh} hits, {len(rows)} HSP rows",flush=True);print(f"[OUTPUT] {out}",flush=True)

if __name__=='__main__':main()
