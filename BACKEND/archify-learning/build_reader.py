"""Render the deliberately small Markdown subset in README to a portable reader."""
from html import escape
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def inline(text):
    value = escape(text)
    value = re.sub(r'`([^`]+)`', r'<code>\1</code>', value)
    value = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', value)
    def link(match):
        label, href = match.groups()
        if href.startswith('../'):
            return f'<code class="source" title="Open this path in your editor">{label} <small>({href})</small></code>'
        return f'<a href="{href}">{label}</a>'
    return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link, value)


lines = (HERE/'README.md').read_text(encoding='utf-8').splitlines()
out, toc, i = [], [], 0
while i < len(lines):
    line = lines[i]
    if not line.strip():
        i += 1
        continue
    if line.startswith('```'):
        language = line[3:].strip()
        code=[]
        i+=1
        while i < len(lines) and not lines[i].startswith('```'):
            code.append(lines[i]); i+=1
        out.append(f'<div class="code-label">{escape(language or "text")}</div><pre><code>{escape(chr(10).join(code))}</code></pre>')
        i+=1
        continue
    if line.startswith('# '):
        i+=1
        continue
    if line.startswith('## '):
        title=line[3:]
        slug='section-'+str(len(toc)+1)
        toc.append((slug,title))
        out.append(f'<h2 id="{slug}">{inline(title)}</h2>')
        i+=1
        continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            parts=[p.strip() for p in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',p) for p in parts): rows.append(parts)
            i+=1
        out.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(p)+'</th>' for p in rows[0])+'</tr></thead><tbody>')
        for row in rows[1:]: out.append('<tr>'+''.join('<td>'+inline(p)+'</td>' for p in row)+'</tr>')
        out.append('</tbody></table></div>')
        continue
    if re.match(r'^(\d+\. |\- )',line):
        ordered=bool(re.match(r'^\d+\.',line))
        tag='ol' if ordered else 'ul'
        out.append('<'+tag+'>')
        while i<len(lines) and re.match(r'^(\d+\. |\- )',lines[i]):
            out.append('<li>'+inline(re.sub(r'^(\d+\. |\- )','',lines[i]))+'</li>'); i+=1
        out.append('</'+tag+'>')
        continue
    paragraph=[line]
    i+=1
    while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|\- |\d+\. )',lines[i]):
        paragraph.append(lines[i]); i+=1
    out.append('<p>'+inline(' '.join(paragraph))+'</p>')

cards = [
    ('01','taskflow-map','The big picture','Follow your request from React to stored task data.'),
    ('02','task-edit','One task edit','Trace authorization, version checks, and commit.'),
    ('03','reminders','Background work','Separate beat, broker, worker, and database roles.'),
    ('04','how-archify-works','The diagram pipeline','Explore how editable JSON becomes checked HTML.'),
]
links=''.join(f'<a class="map-card" href="diagrams/{num}-{slug}.html"><span class="number">{num}</span><h3>{title}</h3><p>{desc}</p><span class="open">Explore map →</span></a>' for num,slug,title,desc in cards)
nav=''.join(f'<a href="#{slug}">{escape(title)}</a>' for slug,title in toc)
html='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TaskFlow Learning Atlas — Archify</title><style>
:root{--ink:#172b43;--muted:#52677d;--blue:#245bc5;--line:#dce4ec;--paper:#fff;--bg:#f4f7fb}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:24px}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 system-ui,-apple-system,Segoe UI,sans-serif}
a{color:var(--blue);text-underline-offset:3px}a:focus-visible{outline:3px solid #e5a72e;outline-offset:4px}
.hero{background:#142e4f;color:#fff;padding:56px max(24px,calc((100vw - 1200px)/2)) 48px}.eyebrow{text-transform:uppercase;letter-spacing:.18em;color:#b9d3f6;font-size:12px;font-weight:700}.hero h1{font-size:clamp(32px,5vw,54px);line-height:1.12;max-width:850px;letter-spacing:-.035em;margin:14px 0 20px}.hero p{max-width:760px;color:#d3e1f2;font-size:18px}.hero .tag{display:inline-block;border:1px solid #59708b;padding:5px 12px;border-radius:20px;font-size:12px;margin:8px 7px 0 0}
main{max-width:1248px;margin:auto;padding:32px 24px 72px}.maps{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}.map-card{display:flex;flex-direction:column;background:white;border:1px solid var(--line);padding:24px;border-radius:12px;text-decoration:none;color:var(--ink);transition:transform .15s,box-shadow .15s}.map-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px #15325212}.number{font-size:13px;font-weight:800;color:var(--blue);letter-spacing:.1em}.map-card h3{font-size:20px;line-height:1.3;margin:14px 0 4px}.map-card p{font-size:14px;color:var(--muted);margin:8px 0 24px}.open{margin-top:auto;font-size:13px;font-weight:700;color:var(--blue)}
.reading{display:grid;grid-template-columns:242px minmax(0,1fr);gap:32px;margin-top:40px}aside{align-self:start;position:sticky;top:24px}aside h2{font-size:12px;text-transform:uppercase;letter-spacing:.12em;margin:0 0 12px}nav{display:flex;flex-direction:column;gap:10px}nav a{font-size:13px;line-height:1.45;text-decoration:none;color:var(--muted)}nav a:hover{color:var(--blue)}article{min-width:0;background:var(--paper);border:1px solid var(--line);padding:32px 40px;border-radius:12px}article>p:first-child{font-size:19px;color:var(--muted);margin-top:0}h2{font-size:26px;letter-spacing:-.02em;line-height:1.3;margin:48px 0 18px}p{margin:0 0 18px}li{padding-left:3px;margin:8px 0}ul,ol{padding-left:25px}strong{font-weight:700}code{font:13px/1.6 Consolas,monospace;background:#eef2f7;border-radius:4px;padding:2px 5px;overflow-wrap:anywhere}.source{display:inline;font-size:12px}.source small{font:inherit;color:var(--muted)}.code-label{background:#243c56;color:#bcd5ee;border-radius:8px 8px 0 0;padding:6px 16px;font:11px/1.6 Consolas,monospace;text-transform:uppercase}pre{margin:0 0 24px;padding:18px;background:#152a42;color:#e1ecf8;border-radius:0 0 8px 8px;overflow:auto}pre code{background:transparent;color:inherit;padding:0;overflow-wrap:normal;font-size:12px}.table-wrap{overflow:auto;margin:20px 0 26px}table{width:100%;border-collapse:collapse;font-size:13px;line-height:1.55}th{text-align:left;background:#eaf0f8;color:#173c70;font-weight:700}th,td{border:1px solid var(--line);padding:11px 13px;vertical-align:top}tr:nth-child(even) td{background:#f8fafc}.note{padding:16px 20px;border-left:3px solid #2b67c5;background:#eaf1fb;font-size:14px;margin:24px 0 0}.footer{font-size:12px;color:var(--muted);margin-top:30px}
@media(max-width:1000px){.maps{grid-template-columns:repeat(2,minmax(0,1fr))}.reading{grid-template-columns:1fr}aside{position:static}nav{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:600px){.maps{grid-template-columns:1fr}.hero{padding:36px 22px}main{padding:24px 14px}article{padding:22px 18px}nav{grid-template-columns:1fr}h2{font-size:23px}th,td{min-width:135px}}@media print{.hero{background:white;color:black;padding:0}.hero p,.eyebrow{color:black}.maps,aside{display:none}.reading{display:block}article{border:0;padding:0}body{background:white;font-size:11pt}pre{white-space:pre-wrap}h2{break-after:avoid}}
</style></head><body><header class="hero"><div class="eyebrow">TaskFlow × Archify · Beginner learning atlas</div><h1>Understand the project.<br>Follow every important arrow.</h1><p>Start with four interactive maps, connect them to real source files, then practice the complete path from a browser action to a verified release.</p><span class="tag">4 interactive diagrams</span><span class="tag">13 guided chapters</span><span class="tag">Editable JSON sources</span></header>
<main><section class="maps" aria-label="Interactive learning maps">'''+links+'''</section>
<p class="note">Read in order: big picture → task edit → reminders → Archify. These are learning maps of the local project. Public deployment still needs its own release and verification. Source paths shown below are for opening in your code editor.</p>
<div class="reading"><aside><h2>Your learning route</h2><nav aria-label="Guide chapters">'''+nav+'''</nav></aside><article>'''+''.join(out)+'''<p class="footer">Created from the local TaskFlow source and the downloaded Archify repository. The Markdown guide and diagram JSON remain editable beside this reader.</p></article></div></main></body></html>'''
(HERE/'index.html').write_text(html,encoding='utf-8')
print(f'Built reader with {len(toc)} chapters and {len(cards)} diagram links.')
