from pathlib import Path
import re, sys, shutil
from datetime import datetime

ROOT=Path(__file__).resolve().parent
# O pacote pode ser extraído diretamente na raiz do sistema ou mantido em subpasta.
if not (ROOT/'app.py').exists(): ROOT=ROOT.parent
if not (ROOT/'app.py').exists() or not (ROOT/'static'/'app.js').exists():
    sys.exit('ERRO: Coloque instalar_cronograma.py na pasta que contém app.py e static/app.js.')

STAMP='ESTUDA_CRONOGRAMA_26_11_V1'
paths=[ROOT/'app.py',ROOT/'static'/'app.js',ROOT/'static'/'style.css',ROOT/'templates'/'index.html']
if all(STAMP in p.read_text(encoding='utf-8') for p in paths[:2]):
    print('Cronograma já instalado. Nenhuma alteração necessária.')
    sys.exit(0)

sources={p:p.read_text(encoding='utf-8') for p in paths}
py=sources[paths[0]]; js=sources[paths[1]];css=sources[paths[2]];html=sources[paths[3]]

def change_once(s,old,new,label):
    if old not in s: raise ValueError(f'Estrutura diferente na seção: {label}. Não alterei nenhum arquivo.')
    return s.replace(old,new,1)

# Banco: a migração acrescenta colunas, preservando as linhas existentes.
anchor="    weights={'Conhecimentos Específicos':40"
migration='''    # ESTUDA_CRONOGRAMA_26_11_V1 — migração sem perda de tarefas anteriores.
    for column,definition in [('day','TEXT'),('slot','TEXT'),('minutes','INTEGER')]:
        if column not in [r[1] for r in con.execute('PRAGMA table_info(planner)')]:
            con.execute(f'ALTER TABLE planner ADD COLUMN {column} {definition}')
    con.commit()
'''
py=change_once(py,anchor,migration+anchor,'migração do planner')
# Inserção da rotina no momento de montagem do bootstrap (sem modificar dados ao visitar tela).
py=change_once(py,"    planner=[rowdict(r) for r in con.execute('SELECT * FROM planner ORDER BY done,id')]", '''    planner=[rowdict(r) for r in con.execute("SELECT * FROM planner ORDER BY CASE WHEN day IS NULL OR day = '' THEN 1 ELSE 0 END, day, CASE slot WHEN 'meio-dia' THEN 0 WHEN 'noite' THEN 1 ELSE 2 END, id")]''','consulta do cronograma')
old="""    with db():db().execute('INSERT INTO planner(focus) VALUES (?)',(focus.strip(),))"""
new="""    day=obj.get('day') or None;slot=obj.get('slot') or None
    minutes=obj.get('minutes')
    if day is not None: day=iso_day(day)
    if slot not in (None,'meio-dia','noite'):abort(400,'Turno inválido')
    if minutes is not None and (type(minutes)!=int or not 1<=minutes<=600):abort(400,'Duração inválida')
    with db():db().execute('INSERT INTO planner(focus,day,slot,minutes) VALUES (?,?,?,?)',(focus.strip(),day,slot,minutes))"""
py=change_once(py,old,new,'criar tarefa')
old="""    with con:con.execute('UPDATE planner SET done=?,notes=?,focus=? WHERE id=?',(int(done) if done is not None else p['done'],notes if notes is not None else p['notes'],focus.strip() if focus is not None else p['focus'],pid))"""
new="""    day=d.get('day',p['day']);slot=d.get('slot',p['slot']);minutes=d.get('minutes',p['minutes'])
    if day == '':day=None
    if day is not None:day=iso_day(day)
    if slot == '':slot=None
    if slot not in (None,'meio-dia','noite'):abort(400,'Turno inválido')
    if minutes in ('',None): minutes=None
    if minutes is not None and (type(minutes)!=int or not 1<=minutes<=600):abort(400,'Duração inválida')
    with con:con.execute('UPDATE planner SET done=?,notes=?,focus=?,day=?,slot=?,minutes=? WHERE id=?',(int(done) if done is not None else p['done'],notes if notes is not None else p['notes'],focus.strip() if focus is not None else p['focus'],day,slot,minutes,pid))"""
py=change_once(py,old,new,'alterar tarefa')

# Preencher apenas itens pendentes SEM data, sem mudar itens concluídos, mantendo a ordem original.
marker="@app.patch('/api/planner/<int:pid>')"
endpoint='''# ESTUDA_CRONOGRAMA_26_11_V1: coloca datas apenas em objetivos pendentes sem agenda.
@app.post('/api/planner/schedule')
def planner_schedule():
    from datetime import date as _date
    con=db()
    rows=con.execute("SELECT id FROM planner WHERE done=0 AND (day IS NULL OR day='') ORDER BY id").fetchall()
    today_date=today()
    # Horários informados: segunda a quinta, 30 minutos ao meio-dia e 2 horas à noite.
    # Início informado apenas como "à noite": deliberadamente sem hora inventada.
    occupied={(r['day'],r['slot']) for r in con.execute("SELECT day,slot FROM planner WHERE day IS NOT NULL AND slot IS NOT NULL")}
    start=today_date
    date_cursor=start
    assigned=0
    with con:
        for row in rows:
            while True:
                if date_cursor >= _date.fromisoformat(EXAM):
                    break
                if date_cursor.weekday() < 4:
                    free_slots=[slot for slot in ('meio-dia','noite') if (date_cursor.isoformat(),slot) not in occupied]
                    if free_slots:break
                date_cursor+=timedelta(days=1)
            if date_cursor >= _date.fromisoformat(EXAM):break
            slot=free_slots[0];minutes=30 if slot=='meio-dia' else 120
            con.execute('UPDATE planner SET day=?,slot=?,minutes=? WHERE id=?',(date_cursor.isoformat(),slot,minutes,row['id']))
            occupied.add((date_cursor.isoformat(),slot));assigned+=1
    return jsonify(ok=True,assigned=assigned)

'''
py=change_once(py,marker,endpoint+marker,'rota agendar')
# Backup preserva as datas ao exportar/importar.
py=change_once(py,"SELECT id,focus,done,notes FROM planner ORDER BY id", "SELECT id,focus,done,notes,day,slot,minutes FROM planner ORDER BY id", 'backup')
old="""con.execute('INSERT INTO planner(focus,done,notes) VALUES (?,?,?)',(p['focus'].strip(),1 if p.get('done') else 0,str(p.get('notes',''))[:3000]))"""
new="""con.execute('INSERT INTO planner(focus,done,notes,day,slot,minutes) VALUES (?,?,?,?,?,?)',(p['focus'].strip(),1 if p.get('done') else 0,str(p.get('notes',''))[:3000],p.get('day') if isinstance(p.get('day'),str) and re.match(r'^\\d{4}-\\d{2}-\\d{2}$',p['day']) else None,p.get('slot') if p.get('slot') in ('meio-dia','noite') else None,p.get('minutes') if type(p.get('minutes')) is int and 1<=p['minutes']<=600 else None))"""
# re is imported separately at top, guarded by module alias to avoid namespace lookup problem.
new=new.replace("re.match(","__import__('re').match(")
py=change_once(py,old,new,'restaurar backup')

# Frontend: use campos nativos type=date (calendário) e preserve notas e tarefas.
start=js.index('function planner(){');end=js.index('function revisions(){',start)
replacement='''// ESTUDA_CRONOGRAMA_26_11_V1
function eoPlanLabel(p){
  if(!p.day)return 'Sem data definida';
  const [year,month,day]=p.day.split('-');
  return `${day}/${month}/${year}`;
}
function planner(){
  const plan=state.data.planner,completed=plan.filter(p=>p.done).length;
  const pending=plan.filter(p=>!p.done&&!p.day).length;
  return `${section('Meu plano de estudos','Segunda a quinta • 30 minutos ao meio-dia e 2 horas à noite. As datas podem ser alteradas.','<button class="btn primary" data-action="planner-add">＋ Adicionar assunto</button>')}
  <div class="card padded eo-plan-summary"><div class="flex-row"><div><strong>${completed} de ${plan.length} objetivos concluídos</strong><p class="muted small">Sua rotina: segunda, terça, quarta e quinta • 2h30 por dia (10h por semana).</p></div><span class="count-pill">${pct(completed,plan.length)}% concluído</span></div><div style="margin-top:12px">${bar(completed,plan.length,'teal')}</div>${pending?`<div class="eo-plan-generate"><span class="muted small">${pending} assunto(s) ainda sem data</span><button class="btn teal sm" data-action="planner-generate">▦ Distribuir datas</button></div>`:''}</div>
  <div class="planner-list">${plan.length?plan.map(p=>`<div class="card planner-item ${p.done?'completed':''}"><div class="planner-date" aria-hidden="true"><strong>${p.day?p.day.slice(8,10):(p.done?'✓':'▦')}</strong><small>${p.day?p.day.slice(5,7)+'/'+p.day.slice(2,4):'livre'}</small></div><div class="grow"><h3>${escapeHTML(p.focus)}</h3><p>${eoPlanLabel(p)}${p.slot?' • '+(p.slot==='meio-dia'?'Meio-dia':'Noite'):''}${p.minutes?' • '+(p.minutes===120?'2h':p.minutes+' min'):''}</p>${p.notes?`<p>✎ ${escapeHTML(p.notes)}</p>`:''}</div><button class="btn sm ${p.done?'soft':'primary'}" data-action="planner-toggle" data-id="${p.id}">${p.done?'↶ Reabrir':'✓ Concluir'}</button><button class="icon-btn" title="Editar data, turno e anotações" data-action="planner-notes" data-id="${p.id}">✎</button></div>`).join(''):'<div class="card empty">Sua lista está vazia. Adicione um assunto para começar.</div>'}</div>`;
}
'''
js=js[:start]+replacement+js[end:]
# Editar a forma existente diretamente.
start=js.index('function plannerModal(id){');end=js.index('function sessionModal(){',start)
replacement='''function eoPlannerFields(p){return `<div class="form-grid"><label class="form-field">Data<input type="date" name="day" value="${p.day||''}"></label><label class="form-field">Turno<select name="slot"><option value="">Sem turno</option><option value="meio-dia" ${p.slot==='meio-dia'?'selected':''}>Meio-dia</option><option value="noite" ${p.slot==='noite'?'selected':''}>Noite</option></select></label><label class="form-field">Duração (minutos)<input type="number" name="minutes" min="1" max="600" value="${p.minutes||''}" placeholder="30 ou 120"></label></div>`}
function plannerModal(id){let p=state.data.planner.find(x=>x.id===id);openModal('Editar objetivo de estudo',`<form id="plannerNoteForm" data-id="${id}">${formField('Assunto',`<input name="focus" maxlength="180" value="${escapeHTML(p.focus)}" required>`)}${eoPlannerFields(p)}${formField('Minhas anotações',`<textarea name="notes" rows="5" maxlength="3000" placeholder="Resumos, dúvidas ou questões para resolver...">${escapeHTML(p.notes)}</textarea>`)}<div class="form-actions"><button class="btn primary" type="submit">Salvar alterações</button></div></form>`)}
function plannerAddModal(){openModal('Adicionar assunto ao plano',`<form id="plannerAddForm">${formField('O que deseja estudar?',`<input name="focus" maxlength="180" placeholder="Ex.: Revisar questões de redes" required>`)}${eoPlannerFields({day:'',slot:'',minutes:''})}<div class="form-actions"><button class="btn primary" type="submit">Adicionar ao plano</button></div></form>`)}
'''
js=js[:start]+replacement+js[end:]
# Acrescente uma ação para preencher datas pela API; atualização do estado e exibição.
marker="if(action==='planner-add')plannerAddModal();"
js=change_once(js,marker,marker+"if(action==='planner-generate'){await api('/api/planner/schedule','POST',{});await refresh('planner');toast('Datas distribuídas no cronograma')} ",'botão gerar datas')
js=change_once(js,"body={focus:f.get('focus'),notes:f.get('notes')}","body={focus:f.get('focus'),notes:f.get('notes'),day:f.get('day')||null,slot:f.get('slot')||null,minutes:f.get('minutes')?Number(f.get('minutes')):null}",'enviar edição')
js=change_once(js,"body={focus:f.get('focus')}","body={focus:f.get('focus'),day:f.get('day')||null,slot:f.get('slot')||null,minutes:f.get('minutes')?Number(f.get('minutes')):null}",'enviar nova atividade')
# Torna os cartões legíveis em mobile sem aumentar muito sua altura.
css+='''\n/* ESTUDA_CRONOGRAMA_26_11_V1 */\n.eo-plan-summary{margin-bottom:18px}.eo-plan-generate{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-top:12px}.planner-item .planner-date{min-width:67px}.planner-item .planner-date strong{font-size:19px}.planner-item .planner-date small{font-size:11px}.planner-item .grow p{line-height:1.5}.form-grid input[type=date]{min-height:42px;width:100%}@media(max-width:650px){.eo-plan-generate .btn{width:100%}.planner-item{gap:9px}.planner-item .planner-date{min-width:52px;padding:7px 5px}.planner-item .planner-date strong{font-size:17px}.planner-item .grow{min-width:0}}\n'''
# Cache-busting apenas no script modificado, antigo SW continua adotando rota network-first.
html=html.replace('/static/app.js?v=2.5.0','/static/app.js?v=2.6.0-cronograma')

updates={paths[0]:py,paths[1]:js,paths[2]:css,paths[3]:html}
# Validar antes de gravar: tudo ou nada.
compile(py,str(paths[0]),'exec')
if 'function eoPlannerFields' not in js or 'planner-generate' not in js: raise ValueError('Falha ao montar JavaScript')
backup=ROOT/'backup_antes_cronograma';backup.mkdir(exist_ok=True)
for p in paths:
    shutil.copy2(p,backup/p.name)
for p,s in updates.items(): p.write_text(s,encoding='utf-8')
print('Atualização aplicada com sucesso! Arquivos:',', '.join(str(p.relative_to(ROOT)) for p in updates))
print('Cópias de segurança em:',backup)
print('Reinicie o Flask e clique em "Distribuir datas" na página Meu plano de estudos.')
