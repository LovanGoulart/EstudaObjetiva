"""Desfaz somente o instalador de layout anterior, se aplicado, e esconde a
barra vertical EXTERNA da página sem impedir a rolagem.
Execute na raiz do EstudaObjetiva: python corrigir_barra_vertical_desfazer_layout.py
"""
from pathlib import Path
from datetime import datetime
import shutil
import re
import sys

ROOT = Path(__file__).resolve().parent
PATHS = [Path('static/real_exams.js'), Path('static/style.css'), Path('static/sw.js'), Path('templates/index.html')]
OLD_MARKER = '/* EO-BANCO-SEM-SCROLL-LATERAL-20261126 */'
NEW_MARKER = '/* EO-OCULTAR-BARRA-VERTICAL-20261126 */'

for relative in PATHS:
    if not (ROOT / relative).is_file():
        sys.exit(f'Arquivo ausente: {relative}. Coloque o instalador na pasta ao lado do app.py.')

css_file = ROOT / 'static/style.css'
css = css_file.read_text(encoding='utf-8')
if NEW_MARKER in css:
    print('Correção já aplicada. Nada foi modificado.')
    sys.exit(0)

rollback_needed = OLD_MARKER in css
backup_source = None
if rollback_needed:
    candidates = sorted(ROOT.glob('backup_layout_provas_*'), reverse=True)
    for candidate in candidates:
        if all((candidate / relative).is_file() for relative in PATHS):
            backup_source = candidate
            break
    if backup_source is None:
        sys.exit('A última atualização está instalada, mas sua pasta backup_layout_provas_* não foi encontrada. '
                 'Nenhum arquivo foi alterado. Recupere essa pasta antes de desfazer.')

# Recuperação completa da versão atual, antes de qualquer alteração.
snapshot = ROOT / ('backup_antes_barra_vertical_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
snapshot.mkdir(exist_ok=False)
for relative in PATHS:
    destination = snapshot / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / relative, destination)

if rollback_needed:
    # Restaurar a versão exata que existia imediatamente antes do instalador anterior.
    for relative in PATHS:
        shutil.copy2(backup_source / relative, ROOT / relative)
    print('Última atualização de layout DESFEITA usando:', backup_source.name)
else:
    print('Última atualização de layout não está instalada; mantido o leitor atual.')

css_file = ROOT / 'static/style.css'
css = css_file.read_text(encoding='utf-8')
css += '''\n''' + NEW_MARKER + '''
/* Oculta SOMENTE a barra vertical externa do navegador.
   A rolagem continua funcionando no mouse, touchpad e toque. */
html, body { scrollbar-width: none !important; -ms-overflow-style: none !important; }
html::-webkit-scrollbar, body::-webkit-scrollbar {
    width: 0 !important; height: 0 !important; display: none !important;
}
'''
css_file.write_text(css, encoding='utf-8')

# Troca de versão para o Chrome/PWA reconhecerem a folha de estilos restaurada.
html_file = ROOT / 'templates/index.html'
html = html_file.read_text(encoding='utf-8')
html, count = re.subn(r'(/static/style\.css\?v=)[^"\']+', r'\g<1>2.6.2-scroll-vertical', html, count=1)
if not count:
    html = html.replace('/static/style.css"', '/static/style.css?v=2.6.2-scroll-vertical"', 1)
html_file.write_text(html, encoding='utf-8')

sw_file = ROOT / 'static/sw.js'
sw = sw_file.read_text(encoding='utf-8')
sw = re.sub(r"(const CACHE=')[^']+", r'\g<1>estudaobjetiva-v262-scroll-vertical', sw, count=1)
sw_file.write_text(sw, encoding='utf-8')

print('Barra de rolagem vertical externa OCULTA; rolagem preservada.')
print('Cópia de segurança dos arquivos anteriores:', snapshot.name)
print('Banco SQLite, login e cronograma não foram modificados.')
