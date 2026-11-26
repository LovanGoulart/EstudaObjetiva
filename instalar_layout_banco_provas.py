"""Ajuste localizado do Banco de Provas, sem modificar banco ou outros módulos.
Execute na pasta principal do EstudaObjetiva: python instalar_layout_banco_provas.py
"""
from pathlib import Path
from datetime import datetime
import shutil
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
JS = ROOT / 'static' / 'real_exams.js'
CSS = ROOT / 'static' / 'style.css'
SW = ROOT / 'static' / 'sw.js'
HTML = ROOT / 'templates' / 'index.html'
MARKER = '/* EO-BANCO-SEM-SCROLL-LATERAL-20261126 */'
files = [JS, CSS, SW, HTML]
for f in files:
    if not f.is_file():
        sys.exit(f'Arquivo ausente: {f}. Execute na pasta principal do EstudaObjetiva.')

js = JS.read_text(encoding='utf-8')
css = CSS.read_text(encoding='utf-8')
sw = SW.read_text(encoding='utf-8')
html = HTML.read_text(encoding='utf-8')

if MARKER in css:
    print('Atualização já instalada. Nenhum arquivo modificado.')
    sys.exit(0)

# Retira o título superior da tentativa, mas preserva o título de resultado após finalização.
old = "return `${section(a.finished?'Resultado e revisão':'Responder prova',`${escapeHTML(e.name)} • ${e.count} questões • ${e.year}`)}"
new = "return `${a.finished?section('Resultado e revisão',`${escapeHTML(e.name)} • ${e.count} questões • ${e.year}`):''}"
if old in js:
    js = js.replace(old, new, 1)
elif "Responder prova" in js:
    sys.exit('Não foi possível localizar com segurança o título. Nenhum arquivo modificado.')

# Substitui o visualizador PDF de terceiros pelo visualizador interno que se ajusta à tela.
# Evita a barra horizontal que pertence ao navegador embutido (não pode ser ocultada via CSS externo).
image = '<img id="qExamPage" class="eo-mobile-page" src="/static/exam_pages/${encodeURIComponent(e.id)}/${String(pageNav).padStart(2,\'0\')}.webp" alt="Página ${pageNav} da prova ${escapeHTML(e.name)}" loading="eager" decoding="async">'
pattern_conditional = re.compile(r"\$\{window\.matchMedia\('\(max-width: 700px\)'\)\.matches\?`<img id=\"qExamPage\".*?</iframe>`\}", re.S)
js, n = pattern_conditional.subn(lambda _: image, js, count=1)
if n == 0:
    pattern_iframe = re.compile(r'<iframe id="qExamPage"[^>]*></iframe>', re.S)
    js, n = pattern_iframe.subn(lambda _: image, js, count=1)
if n != 1:
    sys.exit('Não foi encontrado o leitor de prova esperado. Nenhum arquivo modificado.')

# O leitor por imagem tem zoom com gesto de arrastar, sem barras horizontais.
start = js.find('function syncOriginalPdf(){')
end = js.find('\nasync function loadRealExams()', start)
if start < 0 or end < 0:
    sys.exit('Funções de navegação do PDF não encontradas. Nenhum arquivo modificado.')
replacement = r'''function syncOriginalPdf(){
  const e=state.realAttempt?.exam;
  if(!e || e.kind==='native')return;
  const img=$('#qExamPage');
  if(img){
    img.src=`/static/exam_pages/${encodeURIComponent(e.id)}/${String(pageNav).padStart(2,'0')}.webp`;
    img.style.setProperty('--eo-zoom', String((pdfZoom??100)/100));
    img.style.setProperty('--eo-pan-x','0px');
    img.style.setProperty('--eo-pan-y','0px');
  }
  const label=$('#currentPdfPage');if(label)label.textContent=pageNav;
}
function adjustPdfZoom(delta){
  pdfZoom=Math.max(75,Math.min(250,(pdfZoom??100)+delta));
  const img=$('#qExamPage');
  if(img){img.style.setProperty('--eo-zoom',String(pdfZoom/100));img.style.setProperty('--eo-pan-x','0px');img.style.setProperty('--eo-pan-y','0px');}
}
function enableExamImagePan(){
  const img=$('#qExamPage');if(!img)return;
  let x=0,y=0,startX=0,startY=0,originX=0,originY=0,dragging=false;
  img.addEventListener('pointerdown',ev=>{
    if((pdfZoom??100)<=100)return;
    dragging=true;startX=ev.clientX;startY=ev.clientY;originX=x;originY=y;
    img.setPointerCapture?.(ev.pointerId);
    ev.preventDefault();
  });
  img.addEventListener('pointermove',ev=>{
    if(!dragging)return;
    const stage=img.parentElement, zoom=(pdfZoom??100)/100;
    const maxX=(stage.clientWidth*(zoom-1))/2;
    const maxY=(stage.clientHeight*(zoom-1))/2;
    x=Math.max(-maxX,Math.min(maxX,originX+ev.clientX-startX));
    y=Math.max(-maxY,Math.min(maxY,originY+ev.clientY-startY));
    img.style.setProperty('--eo-pan-x',`${x}px`);
    img.style.setProperty('--eo-pan-y',`${y}px`);
  });
  img.addEventListener('pointerup',()=>{dragging=false});
  img.addEventListener('pointercancel',()=>{dragging=false});
}
'''
js = js[:start] + replacement + js[end:]

# Chamar a ligação de arrastar após a renderização (a função bindRealExams é chamada após render).
needle = "function bindRealExams(){const root=$('#page');if(!state.realAttempt)return;"
if needle not in js:
    sys.exit('bindRealExams não encontrado. Nenhum arquivo modificado.')
js=js.replace(needle,needle+'enableExamImagePan();',1)

css += '\n' + MARKER + r'''
/* Cabeçalho superior mais baixo e menor espaçamento horizontal. */
body.bank-page .topbar {height:55px!important;min-height:55px!important;padding-left:16px!important;padding-right:16px!important;}
body.bank-page .main-content {padding-top:12px!important;}
body.bank-page .real-toolbar {margin-bottom:10px!important;}

/* Não permitir que conteúdos excedam a largura do documento. */
html,body{max-width:100%;overflow-x:hidden!important;}
.app-layout,.main-area,.main-content,#page,.q-layout,.q-book,.q-interactive{min-width:0;max-width:100%;}
body.bank-page .q-layout.with-pages{grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:14px;}
body.bank-page .q-book{top:66px;}

/* Exibe uma página inteira da prova, ajustada à caixa, sem rolagem horizontal.
   O zoom funciona por ampliação e arraste da imagem, sem barra de rolagem. */
body.bank-page .q-book .eo-pdf-stage{
  display:flex!important;align-items:center!important;justify-content:center!important;
  width:100%!important;height:min(74dvh,780px)!important;min-height:320px;
  max-width:100%!important;overflow:hidden!important;padding:8px!important;
  background:#edf1f7;
}
body.bank-page .q-book .eo-pdf-stage img#qExamPage{
  display:block!important;width:100%!important;height:100%!important;
  min-width:0!important;max-width:100%!important;max-height:100%!important;
  object-fit:contain!important;object-position:center!important;
  margin:0!important;touch-action:none!important;user-select:none!important;
  transform:translate(var(--eo-pan-x,0px),var(--eo-pan-y,0px)) scale(var(--eo-zoom,1));
  transform-origin:center center;
}
body.bank-page .q-book-help{font-size:11px!important;padding:7px 10px!important;}
body.bank-page .q-book:fullscreen .eo-pdf-stage,
body.bank-page .q-book.eo-fullscreen .eo-pdf-stage{height:auto!important;min-height:0!important;flex:1 1 auto!important;}
@media(max-width:1150px){
  body.bank-page .q-layout.with-pages{grid-template-columns:minmax(0,1fr);}
  body.bank-page .q-book{top:55px;}
  body.bank-page .q-book .eo-pdf-stage{height:min(58dvh,620px)!important;min-height:280px;}
}
@media(max-width:700px){
  body.bank-page .topbar{height:52px!important;min-height:52px!important;padding:0 10px!important;}
  body.bank-page .q-book{position:relative!important;top:0!important;}
  body.bank-page .q-book .eo-pdf-stage{height:52dvh!important;min-height:250px;overflow:hidden!important;}
  body.bank-page .q-page-toolbar{gap:5px!important;padding:7px!important;}
  body.bank-page .q-page-toolbar>div{gap:3px!important;}
  body.bank-page .q-page-toolbar .btn{font-size:11px!important;padding:5px 7px!important;min-height:29px!important;}
}
'''

# Bump cache do PWA e URLs de assets sem tocar nas demais integrações.
sw = re.sub(r"(const CACHE=')[^']+", r'\1estudaobjetiva-v26-banco-ajuste', sw, count=1)
html = re.sub(r'(/static/(?:style\.css|real_exams\.js)\?v=)[^"\']+',r'\g<1>2.6.1',html)

# Sintaxe Python não é tocada; validar JS antes de instalar.
backup = ROOT / ('backup_layout_provas_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
backup.mkdir(exist_ok=True)
for f in files:
    relative=f.relative_to(ROOT)
    dest=backup/relative
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(f,dest)

try:
    probe = subprocess.run(['node','--check','-'],input=js,text=True,capture_output=True)
    if probe.returncode:
        print('Validação JS falhou: '+probe.stderr)
        sys.exit('Nenhum arquivo modificado. Backup salvo em: '+str(backup))
except FileNotFoundError:
    print('Node.js não encontrado; pulando validação JS local.')

for f,content in [(JS,js),(CSS,css),(SW,sw),(HTML,html)]:
    f.write_text(content,encoding='utf-8')

print('Atualização instalada com sucesso!')
print('Arquivos: static/real_exams.js, static/style.css, static/sw.js, templates/index.html')
print('Backup: '+str(backup))
print('Banco de dados e cronograma não modificados.')
