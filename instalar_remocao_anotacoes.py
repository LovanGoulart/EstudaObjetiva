"""EstudaObjetiva: remove o formulário de anotações do cartão de respostas.
Não altera nem exclui dados do SQLite. Execute na raiz do projeto.
"""
from pathlib import Path
from datetime import datetime
import shutil

root = Path(__file__).resolve().parent
js = root / 'static' / 'real_exams.js'
css = root / 'static' / 'style.css'
if not js.exists() or not css.exists():
    raise SystemExit('Erro: coloque este arquivo na raiz do EstudaObjetiva, ao lado do app.py.')

original = js.read_text(encoding='utf-8')
if 'function qNotes(a,n)' not in original or 'function oldQuestion(a,n)' not in original:
    raise SystemExit('A versão do real_exams.js é diferente. Não alterei nenhum arquivo.')

# qNotes aparece somente nos dois pontos que incluem a caixa de anotações:
# (1) simulados interativos e (2) provas originais.
new = original.replace(',note=qNotes(a,n);return', ';return')
new = new.replace('${note}</div>`;', '</div>`;')
new = new.replace('${qNotes(a,n)}</div>`;', '</div>`;')
# Se já estava ajustado, não há erro e não duplicamos edições.
if new == original and '${qNotes(a,n)}' in original:
    raise SystemExit('Não encontrei o trecho esperado das anotações. Nada foi alterado.')
if new != original:
    backup = js.with_suffix('.js.bak-' + datetime.now().strftime('%Y%m%d%H%M%S'))
    shutil.copy2(js, backup)
    js.write_text(new, encoding='utf-8')
    print('Atualizado:', js.relative_to(root), '| backup:', backup.name)
else:
    print('Anotações já removidas da interface.')

marker = '/* EO: cartão de respostas compacto sem formulário de anotações */'
styles = '''\n''' + marker + '''
/* Mantém o cartão inteiro no fluxo da página, sem uma segunda rolagem. */
.q-layout .q-interactive{height:auto!important;max-height:none!important;overflow:visible!important}
.q-interactive #quizCurrent{height:auto!important;max-height:none!important;overflow:visible!important}
.q-interactive .q-number-grid{margin-bottom:12px;gap:4px}
.q-interactive .q-number{min-height:29px}
.q-interactive .q-question-toolbar{margin-bottom:7px}
.q-interactive .q-choice-field{margin-top:8px;margin-bottom:8px}
.q-interactive .q-body{margin-top:6px}
@media(max-width:650px){
  .q-interactive{padding:10px!important}
  .q-interactive .q-number-grid{gap:3px;margin-bottom:10px}
  .q-interactive .q-number{min-height:28px}
  .q-interactive .q-choices{gap:5px}
}
'''
current_css = css.read_text(encoding='utf-8')
if marker not in current_css:
    backup = css.with_suffix('.css.bak-' + datetime.now().strftime('%Y%m%d%H%M%S'))
    shutil.copy2(css, backup)
    css.write_text(current_css + styles, encoding='utf-8')
    print('Atualizado:', css.relative_to(root), '| backup:', backup.name)
else:
    print('Estilos compactos já instalados.')
print('Concluído. O banco instance/estudos.db não foi alterado.')
