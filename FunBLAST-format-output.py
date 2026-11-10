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
:root{--navy:#092b58;--blue:#1769aa;--line:#d9e1eb;--muted:#5c6878;--bg:#f5f7fa}*{box-sizing:border-box}body{font:14px/1.45 Arial,sans-serif;margin:0;background:var(--bg);color:#172334}header{background:var(--navy);color:white;padding:22px 26px}header h1{margin:0 0 8px;font-size:25px}main{max-width:1600px;margin:22px auto;padding:0 18px}.meta,.stats,.toolbar,.panel{background:white;border:1px solid var(--line);border-radius:9px;padding:15px;margin-bottom:15px}.meta{display:flex;flex-wrap:wrap;gap:8px 24px}.meta span{white-space:nowrap}.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}.stat strong{display:block;font-size:22px;color:var(--navy)}.stat span,.muted{color:var(--muted)}.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.toolbar input,.toolbar select{padding:9px;border:1px solid #bbc7d5;border-radius:6px;font:inherit}button{cursor:pointer;border:1px solid #9aabc0;background:white;border-radius:6px;padding:7px 10px;color:var(--navy)}button:disabled{opacity:.4;cursor:not-allowed}table{width:100%;border-collapse:collapse;background:white}th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{background:#eaf0f7;color:#17375e;position:sticky;top:0;white-space:nowrap}tr.query-row{cursor:pointer}tr.query-row:hover{background:#f0f6fc}.pagination{display:flex;gap:10px;align-items:center;justify-content:flex-end;padding:12px 0}.muted{color:var(--muted)}.table-wrap{overflow:auto}.results-title{font-size:19px;color:var(--navy);margin:3px 0 12px}.hit-table{table-layout:fixed;min-width:1120px}.hit-table th{position:relative;overflow:hidden}.hit-table th .col-resizer{position:absolute;right:0;top:0;width:7px;height:100%;cursor:col-resize;user-select:none}.hit-table th .col-resizer:hover{background:#9bb6d3}.hit-table td{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.hit-table .full-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hit-table a{color:#075da8;text-decoration:none}.hit-table a:hover{text-decoration:underline}.type-reps{color:#c62828;font-weight:700}.type-refs{color:#218739;font-weight:700}.type-other{color:var(--muted)}.mismatch{color:#d00000;font-weight:700}.hit-table th:nth-child(1){width:360px}.hit-table th:nth-child(2){width:105px}.hit-table th:nth-child(3){width:130px}.hit-table th:nth-child(4){width:70px}.hit-table th:nth-child(n+5){width:100px}#details,#alignment-page{display:none}.page-heading{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px}.page-heading h2{margin:0;color:var(--navy);font-size:20px}.hit-summary{background:#f6f8fb;border:1px solid var(--line);padding:12px;border-radius:6px;margin:12px 0}.alignment-block{margin:16px 0;padding:12px;border:1px solid var(--line);border-radius:7px;background:white}.alignment-block h3{margin:0 0 8px;color:var(--navy);font-size:16px}.graphic-summary{margin:14px 0 22px;padding:14px;border:2px solid var(--line);border-radius:8px;background:#fff}.graphic-summary h3{margin:0 0 5px;color:var(--navy);font-size:18px}.graphic-summary .summary-help{color:var(--muted);margin:0 0 10px}.graphic-scroll{max-height:680px;overflow:auto;border:1px solid #e2e7ed;border-radius:6px;background:#fff}.graphic-svg{display:block;width:100%;min-width:760px;height:auto}.graphic-hit{cursor:pointer;outline:none}.graphic-hit rect{stroke:rgba(0,0,0,.18);stroke-width:.5}.graphic-hit:hover rect,.graphic-hit:focus rect{stroke:#111;stroke-width:2}.graphic-hit:focus text{font-weight:bold}.graphic-legend{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin:10px 0 0;font-size:12px;color:var(--muted)}.graphic-legend span{display:inline-flex;align-items:center;gap:5px}.legend-swatch{display:inline-block;width:17px;height:9px;border-radius:2px}.graphic-empty{padding:18px;color:var(--muted);background:#f8fafc;border-radius:5px}.alignment-stats{color:var(--muted);margin-bottom:10px}.alignment-pre{overflow-x:auto;background:#f4f6f8;border:1px solid #e2e7ed;border-radius:5px;padding:12px;font:12px/1.55 Consolas,Monaco,monospace;white-space:pre;margin:0}.empty{padding:25px;text-align:center;color:var(--muted)}.back-row{display:flex;gap:8px;margin-bottom:14px}@media(max-width:700px){main{padding:0 8px}th,td{padding:7px;font-size:12px}.meta{gap:6px 12px}}
</style></head><body><header><h1>FunBLAST</h1><div id="subtitle"></div></header><main><section class="meta" id="meta"></section><section class="stats" id="stats"></section>
<section id="list" class="panel"><div class="toolbar"><input id="search" type="search" placeholder="Search query, sample, taxon, accession…" style="min-width:260px;flex:1"><select id="filter"><option value="all">All queries</option><option value="with">Queries with hits</option><option value="without">Queries without hits</option></select><select id="size"><option>25</option><option selected>50</option><option>100</option><option>200</option></select></div><div class="pagination"><span id="page-label-top" class="muted"></span><button id="prev-top">Previous</button><button id="next-top">Next</button></div><div class="table-wrap"><table><thead><tr><th>Query</th><th>Sample</th><th>Length</th><th>Hits</th><th>Top hit</th><th>Type</th><th>Identity</th><th>Query cover</th></tr></thead><tbody id="rows"></tbody></table></div><div class="pagination"><span id="page-label" class="muted"></span><button id="prev">Previous</button><button id="next">Next</button></div></section>
<section id="details" class="panel"><div class="back-row"><button id="back-queries">← Back to queries</button></div><div class="page-heading"><h2 id="detail-title"></h2></div><div id="detail-meta" class="muted"></div><section class="graphic-summary"><h3>Graphic Summary</h3><p class="summary-help">Distribution of BLAST hits across the query sequence. Hover over a bar for details; click a bar to open its alignment.</p><div id="graphic-summary-content"></div><div class="graphic-legend"><strong>Alignment score (bits):</strong><span><i class="legend-swatch" style="background:#222"></i>&lt; 40</span><span><i class="legend-swatch" style="background:#2878b8"></i>40–50</span><span><i class="legend-swatch" style="background:#2b9b55"></i>50–80</span><span><i class="legend-swatch" style="background:#c13bbd"></i>80–200</span><span><i class="legend-swatch" style="background:#e32636"></i>≥ 200</span></div></section><h3 class="results-title">Sequences producing significant alignments</h3><div class="table-wrap"><table class="hit-table"><thead><tr><th>Full title</th><th>Accession</th><th>SH</th><th>Type</th><th>Identity</th><th>Query cover</th><th>Bit score</th><th>E-value</th><th>Length</th></tr></thead><tbody id="hit-rows"></tbody></table></div><div id="no-hits"></div></section>
<section id="alignment-page" class="panel"><div class="back-row"><button id="back-hits">← Back to alignments</button><button id="back-queries-2">Back to queries</button></div><div class="page-heading"><h2>Pairwise sequence alignment</h2></div><div id="alignment-title"></div><div id="alignment-content"></div></section></main>
<script id="report-data" type="application/json">__DATA__</script><script>
"use strict";const D=JSON.parse(document.getElementById('report-data').textContent),$=id=>document.getElementById(id);let page=0,currentQuery=null,currentHit=null;
$('subtitle').textContent=D.source_filename+' · '+D.created;
for(const [k,v] of [['Sequenced on',D.sequence_date],['Database',D.database],['Software version',D.version]]){let s=document.createElement('span'),b=document.createElement('strong');b.textContent=k+': ';s.append(b,document.createTextNode(v));$('meta').append(s)}
const total=D.queries.reduce((n,q)=>n+q.hits.length,0);function stat(k,v){let d=document.createElement('div'),b=document.createElement('strong'),s=document.createElement('span');b.textContent=v;s.textContent=k;d.className='stat';d.append(b,s);$('stats').append(d)}stat('Queries',D.queries.length.toLocaleString());stat('Total hits',total.toLocaleString());stat('Queries with hits',D.queries.filter(q=>q.hits.length).length.toLocaleString());stat('Queries without hits',D.queries.filter(q=>!q.hits.length).length.toLocaleString());
function typeLabel(value){let v=String(value||'').toLowerCase();if(v.startsWith('reps'))return 'RepS';if(v.startsWith('refs'))return 'RefS';return value||'—'}
function typeClass(value){let v=typeLabel(value);return v==='RepS'?'type-reps':v==='RefS'?'type-refs':'type-other'}
function filtered(){let t=$('search').value.trim().toLowerCase(),f=$('filter').value;return D.queries.filter(q=>{if(f==='with'&&!q.hits.length)return false;if(f==='without'&&q.hits.length)return false;if(!t)return true;return [q.id,q.title,q.sample_id,q.sample_name,...q.hits.flatMap(h=>[h.organism,h.title,h.accession,h.sh])].join(' ').toLowerCase().includes(t)})}
function render(){let a=filtered(),n=Number($('size').value)||50,pages=Math.max(1,Math.ceil(a.length/n));page=Math.max(0,Math.min(page,pages-1));let body=$('rows');body.replaceChildren();for(let q of a.slice(page*n,(page+1)*n)){let tr=document.createElement('tr');tr.className='query-row';let h=q.hits[0],vals=[q.id,q.sample_id+' / '+q.sample_name,q.length,q.hits.length,h?h.organism:'No hit',h?typeLabel(h.seq_type):'—',h?h.identity_pct.toFixed(1)+'%':'—',h?h.qcov.toFixed(1)+'%':'—'];for(let [i,v] of vals.entries()){let td=document.createElement('td');td.textContent=String(v??'');if(i===5&&h)td.className=typeClass(h.seq_type);tr.append(td)}tr.tabIndex=0;tr.addEventListener('click',()=>showQuery(q.id));tr.addEventListener('keydown',e=>{if(e.key==='Enter')showQuery(q.id)});body.append(tr)}if(!a.length){let tr=document.createElement('tr'),td=document.createElement('td');td.colSpan=8;td.className='empty';td.textContent='No matching query';tr.append(td);body.append(tr)}let label=`${a.length} queries · Page ${page+1}/${pages}`;for(let id of ['page-label','page-label-top'])$(id).textContent=label;for(let [prev,next] of [['prev','next'],['prev-top','next-top']]){$(prev).disabled=page===0;$(next).disabled=page>=pages-1}}
function showOnly(id){for(let x of ['list','details','alignment-page'])$(x).style.display='none';$(id).style.display='block';window.scrollTo(0,0)}
function scoreColor(score){let v=Number(score)||0;if(v>=200)return '#e32636';if(v>=80)return '#c13bbd';if(v>=50)return '#2b9b55';if(v>=40)return '#2878b8';return '#222222'}
function svgEl(name,attrs={},textValue=null){let el=document.createElementNS('http://www.w3.org/2000/svg',name);for(let [k,v] of Object.entries(attrs))el.setAttribute(k,String(v));if(textValue!==null)el.textContent=String(textValue);return el}
function renderGraphicSummary(q){let host=$('graphic-summary-content');host.replaceChildren();if(!q.hits.length||!q.length){let empty=document.createElement('div');empty.className='graphic-empty';empty.textContent=q.hits.length?'Query length unavailable; cannot scale alignments.':'No BLAST hits to display.';host.append(empty);return}
 const W=1200,left=270,right=22,plotW=W-left-right,axisY=48,rowTop=100,rowH=21,barH=10,H=rowTop+q.hits.length*rowH+18,svg=svgEl('svg',{class:'graphic-svg',viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':`Graphic summary showing ${q.hits.length} BLAST hits across a query of ${q.length} base pairs`});
 const x=pos=>left+((Math.max(1,Math.min(q.length,Number(pos)||1))-1)/Math.max(1,q.length-1))*plotW;
 // Query backbone and coordinate scale.
 svg.append(svgEl('text',{x:8,y:20,fill:'#17375e','font-size':13,'font-weight':'bold'},'Query sequence'));
 svg.append(svgEl('text',{x:left,y:20,fill:'#5c6878','font-size':12},`${q.length.toLocaleString()} bp`));
 svg.append(svgEl('line',{x1:left,y1:axisY,x2:left+plotW,y2:axisY,stroke:'#bd2634','stroke-width':5,'stroke-linecap':'round'}));
 svg.append(svgEl('line',{x1:left,y1:axisY+9,x2:left+plotW,y2:axisY+9,stroke:'#9aa8b8','stroke-width':1}));
 for(let i=0;i<=4;i++){let pos=1+(q.length-1)*i/4,xx=left+plotW*i/4;svg.append(svgEl('line',{x1:xx,y1:axisY+7,x2:xx,y2:axisY+14,stroke:'#66788a','stroke-width':1}));svg.append(svgEl('text',{x:xx,y:axisY+29,fill:'#536273','font-size':11,'text-anchor':i===0?'start':i===4?'end':'middle'},Math.round(pos).toLocaleString()));}
 q.hits.forEach((hit,index)=>{let cy=rowTop+index*rowH,hsps=(hit.hsps||[]).filter(h=>Number(h.query_from)>0&&Number(h.query_to)>0);let label=String(hit.num??index+1);let name=hit.organism||hit.accession||hit.title||'Hit';let short=name.length>31?name.slice(0,28)+'…':name;
 svg.append(svgEl('text',{x:8,y:cy+4,fill:'#334155','font-size':11},`${label}. ${short}`));
 let segments=hsps.map(h=>{let a=Math.min(Number(h.query_from),Number(h.query_to)),b=Math.max(Number(h.query_from),Number(h.query_to));return {h,a,b,mid:(a+b)/2}}).sort((a,b)=>a.a-b.a);
 // NCBI-style connector between multiple HSPs belonging to the same subject.
 for(let j=1;j<segments.length;j++){let prev=segments[j-1],next=segments[j];svg.append(svgEl('line',{x1:x(prev.mid),y1:cy,x2:x(next.mid),y2:cy,stroke:'#8b96a5','stroke-width':1,'stroke-dasharray':'3 3'}));}
 if(!segments.length){svg.append(svgEl('text',{x:left+4,y:cy+4,fill:'#9aa4b2','font-size':10},'No coordinates'));}
 for(let seg of segments){let h=seg.h,score=Number(h.bit_score)||Number(h.score)||0,ident=Number(h.align_len)?(Number(h.identity||0)/Number(h.align_len)*100):0;let rect=svgEl('rect',{x:x(seg.a),y:cy-barH/2,width:Math.max(2,x(seg.b)-x(seg.a)),height:barH,rx:2,fill:scoreColor(score)});let g=svgEl('g',{class:'graphic-hit',tabindex:0,role:'button','aria-label':`${name}; query ${seg.a} to ${seg.b}; identity ${ident.toFixed(1)} percent; bit score ${score.toFixed(1)}`});let tip=svgEl('title',{},`${hit.title||name}\nQuery: ${seg.a}–${seg.b}\nIdentity: ${ident.toFixed(1)}%\nBit score: ${score.toFixed(1)}\nE-value: ${h.evalue??'NA'}\nClick to view alignment`);g.append(tip,rect);g.addEventListener('click',()=>showAlignment(hit));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();showAlignment(hit)}});svg.append(g);}
 });
 host.append(svg);
}
function showQuery(id,navigateHistory=true){let q=D.queries.find(x=>x.id===id);if(!q)return;currentQuery=q;currentHit=null;$('detail-title').textContent=q.id+' — '+q.title;$('detail-meta').textContent=`Sample: ${q.sample_id} / ${q.sample_name} · ${q.length} nt · ${q.hits.length} hits`;
renderGraphicSummary(q);let body=$('hit-rows');body.replaceChildren();$('no-hits').textContent='';if(!q.hits.length){$('no-hits').className='empty';$('no-hits').textContent='No BLAST hit for this query.'}else for(let h of q.hits){let tr=document.createElement('tr');let td=document.createElement('td'),a=document.createElement('a');a.href='#alignment';a.className='full-title';a.textContent=h.title||'(untitled hit)';a.title=h.title||'';a.addEventListener('click',e=>{e.preventDefault();showAlignment(h)});td.append(a);tr.append(td);let vals=[h.accession||'—',h.sh||'—',h.seq_type||'—',h.identity_pct.toFixed(1)+'%',h.qcov.toFixed(1)+'%',h.bit_score,h.evalue,h.length];for(let [i,v] of vals.entries()){let cell=document.createElement('td');if(i===1&&h.sh){let link=document.createElement('a');link.href='https://unite.ut.ee/bl_forw_sh.php?sh_name='+encodeURIComponent(h.sh)+'#fndtn-panel1';link.target='_blank';link.rel='noopener noreferrer';link.textContent=h.sh;cell.append(link)}else if(i===2){cell.textContent=typeLabel(h.seq_type);cell.className=typeClass(h.seq_type)}else cell.textContent=String(v??'—');tr.append(cell)}body.append(tr)}
showOnly('details');enableColumnResize();if(navigateHistory)navigate(routeState('query',{queryId:id}))}
function fmtCoord(v){return v===undefined||v===null?'':String(v)}
function alignmentText(hsp){let q=String(hsp.qseq||''),s=String(hsp.hseq||''),m=String(hsp.midline||''),chunks=[],width=60;let qbase=Number(hsp.query_from||1),sbase=Number(hsp.hit_from||1),qsign=hsp.query_strand==='Minus'?-1:1,ssign=hsp.hit_strand==='Minus'?-1:1;const esc=x=>x.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));for(let i=0;i<Math.max(q.length,s.length,m.length);i+=width){let qpart=q.slice(i,i+width),spart=s.slice(i,i+width),mpart=m.slice(i,i+width);let qstart=qbase+qsign*q.slice(0,i).replace(/-/g,'').length,qcount=qpart.replace(/-/g,'').length,qend=qcount?qstart+qsign*(qcount-1):qstart;let sstart=sbase+ssign*s.slice(0,i).replace(/-/g,'').length,scount=spart.replace(/-/g,'').length,send=scount?sstart+ssign*(scount-1):sstart;let sbj='';for(let j=0;j<spart.length;j++){let qc=qpart[j]||'',sc=spart[j]||'';sbj+=(qc&&sc&&qc.toUpperCase()!==sc.toUpperCase()&&qc!=='-'&&sc!=='-'?'<span class="mismatch">'+esc(sc)+'</span>':esc(sc));}chunks.push('<div>Query  '+String(qstart).padStart(6)+'  '+esc(qpart)+'  '+String(qend).padStart(6)+'</div><div>               '+esc(mpart)+'</div><div>Sbjct  '+String(sstart).padStart(6)+'  '+sbj+'  '+String(send).padStart(6)+'</div>');}return chunks.join('<div style="height:12px"></div>')}
function showAlignment(h,navigateHistory=true){currentHit=h;$('alignment-title').replaceChildren();let title=document.createElement('p');title.textContent=h.title;$('alignment-title').append(title);let meta=document.createElement('div');meta.className='hit-summary';meta.textContent=`Accession: ${h.accession||'NA'} · SH: ${h.sh||'NA'} · ${h.seq_type||'NA'} · Identity: ${h.identity_pct.toFixed(1)}% · Query cover: ${h.qcov.toFixed(1)}% · Length: ${h.length}`;$('alignment-title').append(meta);let box=$('alignment-content');box.replaceChildren();if(!h.hsps.length){let p=document.createElement('p');p.className='empty';p.textContent='No alignment data available.';box.append(p)}for(let [i,x] of h.hsps.entries()){let card=document.createElement('article');card.className='alignment-block';let heading=document.createElement('h3');heading.textContent=`Alignment ${x.num??i+1}`;card.append(heading);let stats=document.createElement('div');stats.className='alignment-stats';let pct=Number(x.align_len)?(Number(x.identity)/Number(x.align_len)*100).toFixed(1):'0.0';stats.textContent=`Score = ${x.bit_score??'NA'} bits (${x.score??'NA'}), Expect = ${x.evalue??'NA'}, Identities = ${x.identity??0}/${x.align_len??0} (${pct}%), Gaps = ${x.gaps??0}/${x.align_len??0}`;card.append(stats);let pre=document.createElement('pre');pre.className='alignment-pre';pre.innerHTML=alignmentText(x);card.append(pre);box.append(card)}showOnly('alignment-page');if(navigateHistory)navigate(routeState('alignment',{queryId:currentQuery?.id,hitIndex:currentQuery?.hits.indexOf(h)}))}
function enableColumnResize(){let table=document.querySelector('.hit-table');if(!table)return;for(let th of table.querySelectorAll('th')){if(th.querySelector('.col-resizer'))continue;let grip=document.createElement('span');grip.className='col-resizer';grip.setAttribute('aria-hidden','true');grip.addEventListener('mousedown',e=>{e.preventDefault();let start=e.clientX,startWidth=th.getBoundingClientRect().width;function move(ev){let w=Math.max(55,startWidth+ev.clientX-start);th.style.width=w+'px'}function up(){document.removeEventListener('mousemove',move);document.removeEventListener('mouseup',up)}document.addEventListener('mousemove',move);document.addEventListener('mouseup',up)});th.append(grip)}}
function routeState(view='list',extra={}){return {view,page,search:$('search').value,filter:$('filter').value,size:$('size').value,...extra}}
function navigate(state){let hash='#'+state.view+(state.queryId?'='+encodeURIComponent(state.queryId):'')+(state.hitIndex!==undefined?'&hit='+state.hitIndex:'')+'&page='+(state.page||0);try{history.pushState(state,'',hash)}catch(err){location.hash=hash}}
function restoreRoute(st){st=st||{};$('search').value=st.search??$('search').value;$('filter').value=st.filter??$('filter').value;$('size').value=st.size??$('size').value;page=st.page??0;render();if(st.view==='query'&&st.queryId){showQuery(st.queryId,false)}else if(st.view==='alignment'&&st.queryId){let q=D.queries.find(x=>x.id===st.queryId);if(q){showQuery(st.queryId,false);let h=q.hits[st.hitIndex];if(h)showAlignment(h,false)}}else showOnly('list')}
function routeFromHash(){let raw=location.hash.slice(1),[route,queryPart]=raw.split('='),[queryId,hitPart]=[(queryPart||'').split('&')[0],(queryPart||'').split('&')[1]],st={view:route||'list',queryId:queryId?decodeURIComponent(queryId):undefined,hitIndex:hitPart&&hitPart.startsWith('hit=')?Number(hitPart.slice(4)):undefined,page:Number(new URLSearchParams(location.hash.split('&').slice(1).join('&')).get('page')||0)};restoreRoute(st)}
function changePage(delta){let old=page;page=Math.max(0,page+delta);render();if(page!==old)navigate(routeState('list'))}
$('search').addEventListener('input',()=>{page=0;render();history.replaceState(routeState('list'),'','#list')});$('filter').addEventListener('change',()=>{page=0;render();history.replaceState(routeState('list'),'','#list')});$('size').addEventListener('change',()=>{page=0;render();history.replaceState(routeState('list'),'','#list')});
for(let id of ['prev','prev-top'])$(id).addEventListener('click',()=>changePage(-1));for(let id of ['next','next-top'])$(id).addEventListener('click',()=>changePage(1));
$('back-queries').addEventListener('click',()=>{showOnly('list');navigate(routeState('list'))});$('back-hits').addEventListener('click',()=>{showOnly('details');navigate(routeState('query',{queryId:currentQuery?.id}))});$('back-queries-2').addEventListener('click',()=>{showOnly('list');navigate(routeState('list'))});
window.addEventListener('popstate',e=>restoreRoute(e.state||null));window.addEventListener('hashchange',routeFromHash);
render();history.replaceState(routeState('list'),'','#list');
</script></body></html>'''


def process_file(path, outdir, stamp, created, csv_rows, source_filename):
    with path.open(encoding="utf-8") as f: data=json.load(f)
    reports=data.get("BlastOutput2",[]) or []; queries=[make_query(r,path.name,csv_rows) for r in reports]
    version=reports[0].get("report",{}).get("version","unknown") if reports else "unknown"
    payload={"filename":path.name,"source_filename":source_filename,"created":created,"sequence_date":extract_date(queries[0]["title"] if queries else ""),"database":extract_db_name(data),"version":version,"queries":queries}
    raw=json.dumps(payload,ensure_ascii=False,separators=(",",":"))
    raw=raw.replace("&","\\u0026").replace("<","\\u003c").replace(">","\\u003e").replace("\u2028","\\u2028").replace("\u2029","\\u2029")
    html=HTML.replace("__DATA__",raw)
    dest=outdir/f"{path.stem}_{stamp}.html";dest.write_text(html,encoding="utf-8")
    return len(queries),sum(len(q["hits"]) for q in queries),dest


def main():
    base=Path(__file__).resolve().parent;p=argparse.ArgumentParser(description="Generate standalone FunBLAST HTML and CSV")
    p.add_argument("--input-dir",type=Path,default=base/"outdata");p.add_argument("--output-dir",type=Path,default=base/"output");p.add_argument("--source-dir",type=Path,default=base/"indata",help="Directory containing the source_* input file");a=p.parse_args()
    if not a.input_dir.is_dir():raise SystemExit(f"Input directory does not exist: {a.input_dir}")
    files=sorted(x for x in a.input_dir.iterdir() if x.is_file() and x.suffix.lower() in {'.json','.txt'})
    if not files:raise SystemExit(f"No JSON files found in {a.input_dir}")
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S');created=datetime.now().strftime('%Y-%m-%d %H:%M:%S');out=a.output_dir/f"FunBLAST-ITS_{stamp}";out.mkdir(parents=True,exist_ok=False)
    source_files=sorted((x for x in a.source_dir.iterdir() if x.is_file() and x.name.startswith("source_")),key=lambda x:x.stat().st_mtime,reverse=True) if a.source_dir.is_dir() else []
    source_filename=source_files[0].name.removeprefix("source_") if source_files else "Source file not found (source_* in indata)"
    if source_files: print(f"[INFO] Source file: {source_filename}",flush=True)
    else: print(f"[WARNING] No source_* file found in {a.source_dir}; report will indicate this",flush=True)
    rows=[];nq=nh=0
    for f in files:
        shutil.copy2(f,out/f"raw_{f.name}");q,h,dest=process_file(f,out,stamp,created,rows,source_filename);nq+=q;nh+=h
        print(f"[OK] {f.name}: {q} queries, {h} hits -> {dest.name}",flush=True)
    with (out/f"FunBLAST-ITS_{stamp}.csv").open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f);w.writerow(CSV_HEADER);w.writerows(rows)
    print(f"[DONE] {nq} queries, {nh} hits, {len(rows)} HSP rows",flush=True);print(f"[OUTPUT] {out}",flush=True)

if __name__=='__main__':main()
