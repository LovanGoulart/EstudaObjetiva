from pathlib import Path
import re
import shutil
from datetime import datetime

root = Path(__file__).resolve().parent
js = root / 'static' / 'real_exams.js'
if not js.is_file():
    raise SystemExit('ERRO: static/real_exams.js nao encontrado. Coloque este instalador na pasta que contem app.py.')
original = js.read_text(encoding='utf-8')
updated = original

notes_fn = '''function qNotes(a,n){return `<div class="q-notes"><label for="questionNote">Minhas anotações e comentários sobre a questão ${n}</label><textarea id="questionNote" rows="3" maxlength="5000" placeholder="Comentários, dúvidas, conceitos e observações...">${escapeHTML(noteMap[n]||'')}</textarea><div class="flex-row"><small class="muted">Anotações preservadas ao refazer a prova.</small><button type="button" class="btn soft sm" id="saveQuestionNote">Salvar anotação</button></div></div>`;}\n'''
if not re.search(r'function\s+qNotes\s*\(',updated):
    target=re.search(r'function\s+(?:authoredQuestion|oldQuestion)\s*\(',updated)
    if not target:raise SystemExit('ERRO: funcoes de questoes nao encontradas. Nenhum arquivo foi alterado.')
    updated=updated[:target.start()]+notes_fn+updated[target.start():]

def restore_section(src,name,next_name):
    start=re.search(r'function\s+'+name+r'\s*\(',src)
    end=re.search(r'function\s+'+next_name+r'\s*\(',src[start.end():]) if start else None
    if not start or not end:raise SystemExit(f'ERRO: trecho {name} nao localizado. Nenhum arquivo foi alterado.')
    finish=start.end()+end.start()
    section=src[start.start():finish]
    if name=='oldQuestion':
        if '${qNotes(a,n)}' not in section and '${note}' not in section:
            if '</div>`;}' not in section:raise SystemExit('ERRO: modelo de questao original desconhecido. Sem alteracoes.')
            section=section.replace('</div>`;}', '${qNotes(a,n)}</div>`;}',1)
    else:
        if '${qNotes(a,n)}' not in section and '${note}' not in section:
            # Incluir nota ao final da resposta, antes do fechamento do corpo da questão.
            if '</div>`;}' not in section:raise SystemExit('ERRO: modelo de simulado desconhecido. Sem alteracoes.')
            insertion = '${note}' if re.search(r'\b(?:let|const|var)\s+note\s*=\s*qNotes\(',section) else '${qNotes(a,n)}'
            section=section.replace('</div>`;}', insertion+'</div>`;}',1)
    return src[:start.start()]+section+src[finish:]

updated=restore_section(updated,'authoredQuestion','oldQuestion')
updated=restore_section(updated,'oldQuestion','realAttemptView')

# O campo precisa ter eventos de salvar e persistencia quando o usuario muda de questao.
if "function bindQuestionCurrent" not in updated or "function saveQuestionNote" not in updated:
    raise SystemExit('ERRO: suporte a notas nao encontrado neste JS. Sem alteracoes.')
if "#saveQuestionNote" not in updated or "#questionNote" not in updated:
    raise SystemExit('ERRO: eventos de anotacao nao encontrados. Sem alteracoes.')

if updated == original:
    print('Os campos de anotacoes ja estao presentes neste arquivo. Se ainda nao aparecem, verifique o cache do navegador ou outra versao do arquivo.')
else:
    backup=js.with_name('real_exams.js.backup_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(js,backup)
    js.write_text(updated,encoding='utf-8')
    print('Anotacoes e comentarios restaurados em static/real_exams.js')
    print('Backup:',backup.name)
print('Banco SQLite e respostas nao foram alterados.')
