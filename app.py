"""EstudaObjetiva - painel de preparação individual para o concurso de Novo Cabrais."""
import json, os, secrets, sqlite3, threading
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from flask import Flask, render_template, request, jsonify, g, session, abort, send_file
from werkzeug.security import check_password_hash

ROOT=Path(__file__).resolve().parent
DB_PATH=Path(os.getenv('DATABASE_PATH', str(ROOT/'instance'/'estudos.db')))
DB_PATH.parent.mkdir(parents=True,exist_ok=True)
app=Flask(__name__)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY',secrets.token_hex(32)),JSON_AS_ASCII=False,MAX_CONTENT_LENGTH=1024*1024)
TZ=ZoneInfo('America/Sao_Paulo')
EXAM='2027-01-10'
EXAM_ASSETS=ROOT/'exam_assets'
REAL_EXAMS={e['id']:e for e in json.loads((EXAM_ASSETS/'catalog.json').read_text(encoding='utf-8'))}
WRITE_LOCK=threading.Lock()

def today():return datetime.now(TZ).date()
def db():
    if 'db' not in g:
        g.db=sqlite3.connect(DB_PATH,timeout=15)
        g.db.row_factory=sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

@app.teardown_appcontext
def close_db(_):
    con=g.pop('db',None)
    if con:con.close()

def init_db():
    con=sqlite3.connect(DB_PATH)
    first_planner = not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='planner'").fetchone()
    con.executescript('''PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,points INTEGER NOT NULL,sort INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS topics(id INTEGER PRIMARY KEY,subject_id INTEGER NOT NULL REFERENCES subjects(id),section TEXT NOT NULL,title TEXT NOT NULL,priority TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',notes TEXT NOT NULL DEFAULT '',completed_at TEXT,updated_at TEXT,UNIQUE(subject_id,section,title));
    CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY,day TEXT NOT NULL,minutes INTEGER NOT NULL CHECK(minutes>0 AND minutes<=600),subject_id INTEGER REFERENCES subjects(id),kind TEXT NOT NULL,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY,day TEXT NOT NULL,name TEXT NOT NULL,port INTEGER NOT NULL,mat INTEGER NOT NULL,ger INTEGER NOT NULL,leg INTEGER NOT NULL,esp INTEGER NOT NULL,notes TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY,topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,due_date TEXT NOT NULL,kind TEXT NOT NULL,completed_at TEXT, UNIQUE(topic_id,due_date,kind));
    CREATE TABLE IF NOT EXISTS planner(id INTEGER PRIMARY KEY,focus TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '');
    CREATE TABLE IF NOT EXISTS real_exam_attempts(id INTEGER PRIMARY KEY, exam_id TEXT NOT NULL, answers TEXT NOT NULL DEFAULT '{}', started_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT, CHECK(length(answers)<15000));
    ''')
    # Migrar a lista antiga com datas para objetivos livres sem perder marcações e notas.
    if 'day' in [r[1] for r in con.execute('PRAGMA table_info(planner)')]:
        with con:
            con.execute('ALTER TABLE planner RENAME TO planner_old')
            con.execute("CREATE TABLE planner(id INTEGER PRIMARY KEY,focus TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '')")
            con.execute('INSERT INTO planner(id,focus,done,notes) SELECT id,focus,done,notes FROM planner_old ORDER BY day')
            con.execute('DROP TABLE planner_old')
    weights={'Conhecimentos Específicos':40,'Língua Portuguesa':20,'Matemática':16,'Conhecimentos Gerais':12,'Legislação':12}
    data=json.loads((ROOT/'seed.json').read_text(encoding='utf-8'))
    with con:
        for i,subject in enumerate(data):
            con.execute('INSERT OR IGNORE INTO subjects(name,points,sort) VALUES (?,?,?)',(subject['name'],weights[subject['name']],i))
            sid=con.execute('SELECT id FROM subjects WHERE name=?',(subject['name'],)).fetchone()[0]
            for group in subject['groups']:
                for topic in group['topics']:
                    con.execute('INSERT OR IGNORE INTO topics(subject_id,section,title,priority) VALUES (?,?,?,?)',(sid,group['name'],topic['title'],topic['priority']))
        if first_planner:
            suggestions=['Redes TCP/IP, DNS e DHCP','Matemática: regra de três e porcentagem',
                'Segurança da Informação','Português: gramática e interpretação',
                'Normas legais de Informática','Windows, Linux e hardware',
                'Prova real: Guaraniaçu','Regime jurídico e Lei Orgânica',
                'Matemática financeira e geometria','Prova real: Santa Leopoldina',
                'Prova real: Dezesseis de Novembro','Revisão dos erros e legislação']
            for focus in suggestions:
                con.execute('INSERT INTO planner(focus) VALUES (?)',(focus,))
    con.close()

init_db()

@app.before_request
def security():
    # Optional protection for Internet deployments: set APP_PASSWORD_HASH with Werkzeug hash.
    password_hash=os.getenv('APP_PASSWORD_HASH','')
    if password_hash and request.endpoint not in ('login','static','manifest','service_worker') and not session.get('authenticated'):
        if request.path.startswith('/api/'):return jsonify(error='Autenticação necessária'),401
        return render_template('login.html')
    if request.method in ('POST','PATCH','PUT','DELETE') and request.endpoint!='login':
        token=request.headers.get('X-CSRF-Token','')
        if not token or token!=session.get('csrf'):return jsonify(error='CSRF inválido, atualize a página'),403

@app.after_request
def headers(resp):
    resp.headers['X-Content-Type-Options']='nosniff';resp.headers['X-Frame-Options']='SAMEORIGIN' if request.path.startswith('/exam-files/') else 'DENY'
    resp.headers['Referrer-Policy']='same-origin'
    if request.path.startswith('/api/'):resp.headers['Cache-Control']='no-store'
    return resp

@app.route('/login',methods=['GET','POST'])
def login():
    password_hash=os.getenv('APP_PASSWORD_HASH','')
    if not password_hash:return render_template('index.html',csrf=get_csrf())
    if request.method=='POST':
        if check_password_hash(password_hash,request.form.get('password','')):
            session.clear();session['authenticated']=True
            from flask import redirect
            return redirect('/')
        return render_template('login.html',error='Senha incorreta'),401
    return render_template('login.html')

@app.route('/logout',methods=['POST'])
def logout():
    session.clear();return jsonify(ok=True)

def get_csrf():
    if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
    return session['csrf']

@app.route('/')
def index():return render_template('index.html',csrf=get_csrf(),auth=bool(os.getenv('APP_PASSWORD_HASH')))

@app.route('/manifest.webmanifest')
def manifest():return app.send_static_file('manifest.webmanifest')
@app.route('/sw.js')
def service_worker():
    resp=app.send_static_file('sw.js');resp.headers['Service-Worker-Allowed']='/';resp.headers['Cache-Control']='no-cache';return resp

def rowdict(row):return dict(row)

def required_data():
    obj=request.get_json(silent=True)
    if not isinstance(obj,dict):abort(400,'JSON inválido')
    return obj

def iso_day(value):
    if not isinstance(value,str):abort(400,'Data inválida')
    try:return date.fromisoformat(value).isoformat()
    except ValueError:abort(400,'Data inválida')

@app.errorhandler(400)
@app.errorhandler(404)
def err(e):return jsonify(error=getattr(e,'description',str(e))),e.code

@app.get('/api/bootstrap')
def bootstrap():
    con=db();subjects=[rowdict(r) for r in con.execute('SELECT * FROM subjects ORDER BY sort')]
    topics=[rowdict(r) for r in con.execute('SELECT * FROM topics ORDER BY subject_id,id')]
    planner=[rowdict(r) for r in con.execute('SELECT * FROM planner ORDER BY done,id')]
    sessions=[rowdict(r) for r in con.execute('SELECT * FROM sessions ORDER BY day DESC,id DESC LIMIT 200')]
    exams=[rowdict(r) for r in con.execute('SELECT *,port*2+mat*2+ger*2+leg*2+esp*4 AS score FROM exams ORDER BY day DESC,id DESC')]
    revisions=[rowdict(r) for r in con.execute('SELECT r.*,t.title,t.subject_id FROM revisions r JOIN topics t ON t.id=r.topic_id WHERE r.completed_at IS NULL ORDER BY due_date,id LIMIT 300')]
    return jsonify(subjects=subjects,topics=topics,planner=planner,sessions=sessions,exams=exams,revisions=revisions,today=today().isoformat(),exam=EXAM)

@app.patch('/api/topics/<int:tid>')
def topic_update(tid):
    obj=required_data();allowed=['pending','studying','done'];con=db()
    t=con.execute('SELECT * FROM topics WHERE id=?',(tid,)).fetchone()
    if not t:abort(404,'Tópico não encontrado')
    status=obj.get('status',t['status']);notes=obj.get('notes',t['notes'])
    if status not in allowed or not isinstance(notes,str) or len(notes)>10000:abort(400,'Dados inválidos')
    completed_at=t['completed_at']
    if status=='done' and t['status']!='done':completed_at=today().isoformat()
    if status!='done':completed_at=None
    with con:
        con.execute('UPDATE topics SET status=?,notes=?,completed_at=?,updated_at=? WHERE id=?',(status,notes,completed_at,datetime.now(TZ).isoformat(),tid))
        if status=='done' and t['status']!='done':
            for days,kind in ((1,'24h'),(7,'7 dias'),(30,'30 dias')):
                con.execute('INSERT OR IGNORE INTO revisions(topic_id,due_date,kind) VALUES (?,?,?)',(tid,(today()+timedelta(days=days)).isoformat(),kind))
        elif status!='done' and t['status']=='done':
            con.execute('DELETE FROM revisions WHERE topic_id=?',(tid,))
    return jsonify(ok=True)

@app.post('/api/sessions')
def add_session():
    d=required_data();day=iso_day(d.get('day'));minutes=d.get('minutes');sid=d.get('subject_id')
    if type(minutes)!=int or not 1<=minutes<=600:abort(400,'Minutos devem estar entre 1 e 600')
    if sid is not None and not db().execute('SELECT 1 FROM subjects WHERE id=?',(sid,)).fetchone():abort(400,'Disciplina inválida')
    kind=d.get('kind','Teoria');notes=d.get('notes','')
    if kind not in ['Teoria','Questões','Revisão','Simulado'] or not isinstance(notes,str) or len(notes)>2000:abort(400,'Dados inválidos')
    with db():db().execute('INSERT INTO sessions(day,minutes,subject_id,kind,notes,created_at) VALUES (?,?,?,?,?,?)',(day,minutes,sid,kind,notes,datetime.now(TZ).isoformat()))
    return jsonify(ok=True),201

@app.delete('/api/sessions/<int:sid>')
def delete_session(sid):
    with db():db().execute('DELETE FROM sessions WHERE id=?',(sid,))
    return jsonify(ok=True)

@app.post('/api/exams')
def add_exam():
    d=required_data();day=iso_day(d.get('day'));name=d.get('name','');notes=d.get('notes','')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100 or not isinstance(notes,str) or len(notes)>2000:abort(400,'Dados inválidos')
    nums=[]
    for key,limit in [('port',10),('mat',8),('ger',6),('leg',6),('esp',10)]:
        v=d.get(key)
        if type(v)!=int or not 0<=v<=limit:abort(400,f'{key}: intervalo 0 a {limit}')
        nums.append(v)
    with db():db().execute('INSERT INTO exams(day,name,port,mat,ger,leg,esp,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(day,name.strip(),*nums,notes,datetime.now(TZ).isoformat()))
    return jsonify(ok=True),201

@app.delete('/api/exams/<int:eid>')
def delete_exam(eid):
    with db():db().execute('DELETE FROM exams WHERE id=?',(eid,))
    return jsonify(ok=True)

@app.patch('/api/revisions/<int:rid>')
def revision_update(rid):
    con=db();r=con.execute('SELECT * FROM revisions WHERE id=?',(rid,)).fetchone()
    if not r:abort(404,'Revisão não encontrada')
    with con:con.execute('UPDATE revisions SET completed_at=? WHERE id=?',(datetime.now(TZ).isoformat(),rid))
    return jsonify(ok=True)

@app.post('/api/planner')
def planner_create():
    obj=required_data();focus=obj.get('focus','')
    if not isinstance(focus,str) or not 1<=len(focus.strip())<=180:abort(400,'Informe um assunto com até 180 caracteres')
    with db():db().execute('INSERT INTO planner(focus) VALUES (?)',(focus.strip(),))
    return jsonify(ok=True),201

@app.patch('/api/planner/<int:pid>')
def planner_update(pid):
    d=required_data();done=d.get('done');notes=d.get('notes');focus=d.get('focus');con=db()
    p=con.execute('SELECT * FROM planner WHERE id=?',(pid,)).fetchone()
    if not p:abort(404,'Sessão do cronograma não encontrada')
    if done is not None and type(done)!=bool:abort(400,'Concluído inválido')
    if notes is not None and (not isinstance(notes,str) or len(notes)>3000):abort(400,'Nota inválida')
    if focus is not None and (not isinstance(focus,str) or not 1<=len(focus.strip())<=180):abort(400,'Assunto inválido')
    with con:con.execute('UPDATE planner SET done=?,notes=?,focus=? WHERE id=?',(int(done) if done is not None else p['done'],notes if notes is not None else p['notes'],focus.strip() if focus is not None else p['focus'],pid))
    return jsonify(ok=True)

@app.get('/api/backup')
def backup():
    con=db()
    data={'version':1,'exported_at':datetime.now(TZ).isoformat(), 'topics':[rowdict(r) for r in con.execute('SELECT subject_id,section,title,status,notes,completed_at,updated_at FROM topics')], 'sessions':[rowdict(r) for r in con.execute('SELECT day,minutes,subject_id,kind,notes,created_at FROM sessions')], 'exams':[rowdict(r) for r in con.execute('SELECT day,name,port,mat,ger,leg,esp,notes,created_at FROM exams')], 'revisions':[rowdict(r) for r in con.execute('SELECT topic_id,due_date,kind,completed_at FROM revisions')], 'planner':[rowdict(r) for r in con.execute('SELECT id,focus,done,notes FROM planner ORDER BY id')], 'real_exam_attempts':[rowdict(r) for r in con.execute('SELECT exam_id,answers,started_at,updated_at,completed_at FROM real_exam_attempts')]}
    resp=app.response_class(json.dumps(data,ensure_ascii=False,indent=2),mimetype='application/json')
    resp.headers['Content-Disposition']=f'attachment; filename="backup-estudaobjetiva-{today().strftime("%d-%m-%Y")}.json"'
    return resp

@app.post('/api/restore')
def restore():
    data=required_data()
    if data.get('version')!=1:abort(400,'Versão de backup incompatível')
    con=db()
    with con:
        # Restore progress safely using stable topic identifiers from source file.
        index={(r['subject_id'],r['section'],r['title']):r['id'] for r in con.execute('SELECT id,subject_id,section,title FROM topics')}
        for item in data.get('topics',[]):
            if not isinstance(item,dict):continue
            tid=index.get((item.get('subject_id'),item.get('section'),item.get('title')))
            status=item.get('status')
            if tid and status in ('pending','studying','done') and isinstance(item.get('notes',''),str):
                con.execute('UPDATE topics SET status=?,notes=?,completed_at=?,updated_at=? WHERE id=?',(status,item['notes'][:10000],item.get('completed_at'),item.get('updated_at'),tid))
        for table in ('sessions','exams','revisions'):
            con.execute(f'DELETE FROM {table}')
        for s in data.get('sessions',[]):
            try:
                day=iso_day(s['day']);minutes=int(s['minutes']);kind=s['kind'];sid=s.get('subject_id')
                if 1<=minutes<=600 and kind in ('Teoria','Questões','Revisão','Simulado'):
                    con.execute('INSERT INTO sessions(day,minutes,subject_id,kind,notes,created_at) VALUES (?,?,?,?,?,?)',(day,minutes,sid,kind,str(s.get('notes',''))[:2000],s.get('created_at',datetime.now(TZ).isoformat())))
            except (KeyError,TypeError,ValueError,sqlite3.IntegrityError):pass
        for e in data.get('exams',[]):
            try:
                day=iso_day(e['day']);nums=[int(e[k]) for k in ('port','mat','ger','leg','esp')]
                if all(0<=v<=cap for v,cap in zip(nums,(10,8,6,6,10))):
                    con.execute('INSERT INTO exams(day,name,port,mat,ger,leg,esp,notes,created_at) VALUES (?,?,?,?,?,?,?,?,?)',(day,str(e['name'])[:100],*nums,str(e.get('notes',''))[:2000],e.get('created_at',datetime.now(TZ).isoformat())))
            except (KeyError,ValueError,TypeError,sqlite3.IntegrityError):pass
        for r in data.get('revisions',[]):
            try:
                if con.execute('SELECT 1 FROM topics WHERE id=?',(r['topic_id'],)).fetchone():
                    con.execute('INSERT OR IGNORE INTO revisions(topic_id,due_date,kind,completed_at) VALUES (?,?,?,?)',(r['topic_id'],iso_day(r['due_date']),str(r['kind'])[:30],r.get('completed_at')))
            except (KeyError,ValueError,TypeError):pass
        con.execute('DELETE FROM real_exam_attempts')
        for attempt in data.get('real_exam_attempts',[]):
            try:
                if attempt.get('exam_id') not in REAL_EXAMS:continue
                raw=json.loads(attempt.get('answers','{}'))
                exam=REAL_EXAMS[attempt['exam_id']]
                if not isinstance(raw,dict) or any(not str(k).isdigit() or not 1<=int(k)<=exam['count'] or v not in list('ABCDE'[:exam['options']]) for k,v in raw.items()):continue
                con.execute('INSERT INTO real_exam_attempts(exam_id,answers,started_at,updated_at,completed_at) VALUES (?,?,?,?,?)',
                    (attempt['exam_id'],json.dumps(raw),attempt['started_at'],attempt['updated_at'],attempt.get('completed_at')))
            except (KeyError,ValueError,TypeError,sqlite3.Error):pass
        if isinstance(data.get('planner'),list):
            con.execute('DELETE FROM planner')
            for p in data['planner'][:1000]:
                if isinstance(p,dict) and isinstance(p.get('focus'),str) and 1<=len(p['focus'].strip())<=180:
                    con.execute('INSERT INTO planner(focus,done,notes) VALUES (?,?,?)',(p['focus'].strip(),1 if p.get('done') else 0,str(p.get('notes',''))[:3000]))
    return jsonify(ok=True)



# Provas reais fornecidas pelo usuário — o PDF é exibido ao lado do cartão de respostas.
def real_exam_info(item):
    return {k:item[k] for k in ('id','name','year','count','options','gabarito','version')}

def attempt_data(row):
    exam=REAL_EXAMS[row['exam_id']]
    response={'id':row['id'],'exam':real_exam_info(exam),'answers':json.loads(row['answers']),
              'started_at':row['started_at'],'updated_at':row['updated_at'],
              'completed_at':row['completed_at'],'finished':bool(row['completed_at'])}
    if row['completed_at']:
        official=exam['answers']
        if official:
            detail=[]
            for i,key in enumerate(official,1):
                given=response['answers'].get(str(i),'')
                annulled=key in ('NULA','ANULADA')
                detail.append({'number':i,'given':given,'correct':key,'annulled':annulled,
                               'result':'anulada' if annulled else 'acerto' if given==key else 'branco' if not given else 'erro'})
            response['correction']=detail
            response['totals']={name:sum(d['result']==name for d in detail) for name in ('acerto','erro','branco','anulada')}
            response['totals']['points_earned']=response['totals']['acerto']+response['totals']['anulada']
        else:
            response['correction']=None
            response['totals']=None
    return response

def get_real_attempt(attempt_id):
    row=db().execute('SELECT * FROM real_exam_attempts WHERE id=?',(attempt_id,)).fetchone()
    if row is None:abort(404,'Tentativa não encontrada')
    return row

@app.get('/api/real-exams')
def real_exam_list():
    con=db()
    attempts=[dict(r) for r in con.execute('SELECT id,exam_id,started_at,updated_at,completed_at,answers FROM real_exam_attempts ORDER BY id DESC')]
    data=[]
    for exam in REAL_EXAMS.values():
        related=[a for a in attempts if a['exam_id']==exam['id']]
        info=real_exam_info(exam)
        info['attempts']=len(related)
        info['latest_attempt_id']=related[0]['id'] if related else None
        info['draft_attempt_id']=next((a['id'] for a in related if not a['completed_at']),None)
        info['finished_count']=sum(bool(a['completed_at']) for a in related)
        data.append(info)
    return jsonify(exams=data)

@app.get('/api/real-exams/history')
def real_exam_history():
    records=db().execute('SELECT * FROM real_exam_attempts ORDER BY id DESC LIMIT 200').fetchall()
    return jsonify(attempts=[attempt_data(row) for row in records])

@app.get('/exam-files/<exam_id>')
def real_exam_pdf(exam_id):
    if exam_id not in REAL_EXAMS:abort(404,'Prova inexistente')
    response=send_file(EXAM_ASSETS/f'{exam_id}.pdf',mimetype='application/pdf',as_attachment=False,
                       download_name=f'{exam_id}.pdf',conditional=True)
    response.headers['Cache-Control']='private, max-age=3600'
    return response

@app.post('/api/real-exams/<exam_id>/attempts')
def start_real_exam(exam_id):
    if exam_id not in REAL_EXAMS:abort(404,'Prova inexistente')
    now=datetime.now(TZ).isoformat()
    con=db()
    with con:
        cursor=con.execute('INSERT INTO real_exam_attempts(exam_id,answers,started_at,updated_at) VALUES (?,?,?,?)',(exam_id,'{}',now,now))
    return jsonify(attempt=attempt_data(get_real_attempt(cursor.lastrowid))),201

@app.get('/api/real-exams/attempts/<int:attempt_id>')
def read_real_attempt(attempt_id):
    return jsonify(attempt=attempt_data(get_real_attempt(attempt_id)))

@app.patch('/api/real-exams/attempts/<int:attempt_id>')
def save_real_attempt(attempt_id):
    row=get_real_attempt(attempt_id)
    if row['completed_at']:abort(400,'A prova já foi finalizada. Inicie outra tentativa para refazê-la.')
    payload=required_data()
    answers=payload.get('answers')
    if not isinstance(answers,dict):abort(400,'Respostas inválidas')
    exam=REAL_EXAMS[row['exam_id']]
    for number,letter in answers.items():
        if not isinstance(number,str) or not number.isdigit() or not 1<=int(number)<=exam['count']:
            abort(400,'Número da questão inválido')
        if letter not in ['']+list('ABCDE'[:exam['options']]):abort(400,'Alternativa inválida')
    with db():db().execute('UPDATE real_exam_attempts SET answers=?,updated_at=? WHERE id=?',
                           (json.dumps({k:v for k,v in answers.items() if v},sort_keys=True),datetime.now(TZ).isoformat(),attempt_id))
    return jsonify(attempt=attempt_data(get_real_attempt(attempt_id)))

@app.post('/api/real-exams/attempts/<int:attempt_id>/finish')
def finish_real_attempt(attempt_id):
    row=get_real_attempt(attempt_id)
    if not row['completed_at']:
        now=datetime.now(TZ).isoformat()
        with db():db().execute('UPDATE real_exam_attempts SET completed_at=?,updated_at=? WHERE id=?',(now,now,attempt_id))
    return jsonify(attempt=attempt_data(get_real_attempt(attempt_id)))

@app.delete('/api/real-exams/attempts/<int:attempt_id>')
def delete_real_attempt(attempt_id):
    get_real_attempt(attempt_id)
    with db():db().execute('DELETE FROM real_exam_attempts WHERE id=?',(attempt_id,))
    return jsonify(ok=True)

if __name__=='__main__':
    app.run(host='127.0.0.1',port=int(os.getenv('PORT','5000')),debug=os.getenv('FLASK_DEBUG')=='1')
