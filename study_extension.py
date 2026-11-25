"""Extensões da versão 2: aulas, biblioteca, notas por questão e evolução.
Não altera as tabelas existentes e nunca apaga registros do usuário.
"""
import json
import secrets
from datetime import datetime
from pathlib import Path

from flask import jsonify, request, abort, send_file, send_from_directory
from werkzeug.utils import secure_filename

OFFICIAL_LAWS = [
    {'name': 'Constituição Federal (Planalto)', 'kind':'link', 'url':'https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm', 'detail':'Art. 1º a 69; 76 a 92; 101 e 102; 127 a 129'},
    {'name': 'Lei Orgânica de Novo Cabrais', 'kind':'link', 'url':'https://www.novocabrais.cespro.com.br/visualizarDiploma.php?cdMunicipio=7706&cdDiploma=99993&cdTipoDiploma=2310', 'detail':'Texto oficial municipal; confirmar atualizações'},
    {'name': 'Lei Municipal nº 335/2001 — Regime Jurídico', 'kind':'link', 'url':'https://www.novocabrais.cespro.com.br/visualizarDiploma.php?cdMunicipio=7706&cdDiploma=200103351&NroLei=335', 'detail':'Texto municipal; consultar prazos no documento oficial'},
    {'name': 'Lei nº 9.609/1998 — Software', 'kind':'link', 'url':'https://www.planalto.gov.br/ccivil_03/leis/l9609.htm', 'detail':'Normas Legais específicas'},
    {'name': 'Lei nº 12.965/2014 — Marco Civil da Internet', 'kind':'link', 'url':'https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2014/lei/l12965.htm', 'detail':'Normas Legais específicas'},
    {'name': 'Lei nº 13.709/2018 — LGPD', 'kind':'link', 'url':'https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm', 'detail':'Normas Legais específicas'},
    {'name': 'Código Penal — artigos do edital', 'kind':'link', 'url':'https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm', 'detail':'Art. 154-A, 154-B, 155 e 171'},
]
BUNDLED = [
    {'id':'resumo-legislacao','name':'Resumo estratégico de legislação','filename':'Resumo_Legislacao_Concurso.pdf','detail':'Material de revisão; algumas regras municipais dependem de conferência no texto integral'},
    {'id':'edital-2026','name':'Edital oficial — Novo Cabrais 2026','filename':'Edital_Novo_Cabrais_2026.pdf','detail':'O edital utilizado para organizar conteúdos e pesos'},
]


def register_study_routes(app, db, root, db_path, exams, attempt_data, today, tz):
    root=Path(root)
    library=root/'study_library'
    uploads=root/'instance'/'arquivos'
    uploads.mkdir(parents=True,exist_ok=True)
    lessons=json.loads((library/'lesson_plans.json').read_text(encoding='utf8'))
    lesson_index={x['id']:x for x in lessons}

    @app.get('/exam-pages/<exam_id>/<int:page>')
    def exam_page(exam_id,page):
        ex=exams.get(exam_id)
        if not ex or ex.get('kind')=='native' or not 1<=page<=ex.get('pages',0):
            abort(404,'Página indisponível')
        response=send_from_directory(root/'exam_assets'/'pages'/exam_id,f'{page:02d}.webp',mimetype='image/webp')
        response.headers['Cache-Control']='private, max-age=86400'
        return response

    @app.get('/api/question-notes/<exam_id>')
    def question_notes(exam_id):
        if exam_id not in exams: abort(404,'Prova desconhecida')
        notes=[dict(r) for r in db().execute('SELECT question_num,note,updated_at FROM question_notes WHERE exam_id=? ORDER BY question_num',(exam_id,))]
        return jsonify(notes=notes)

    @app.patch('/api/question-notes/<exam_id>/<int:number>')
    def set_question_note(exam_id,number):
        ex=exams.get(exam_id)
        if not ex or not 1<=number<=ex['count']: abort(404,'Questão inexistente')
        payload=request.get_json(silent=True)
        if not isinstance(payload,dict) or not isinstance(payload.get('note'),str) or len(payload['note'])>5000:
            abort(400,'Anotação inválida (máximo de 5.000 caracteres)')
        with db():db().execute('INSERT INTO question_notes(exam_id,question_num,note,updated_at) VALUES (?,?,?,?) ON CONFLICT(exam_id,question_num) DO UPDATE SET note=excluded.note,updated_at=excluded.updated_at',(exam_id,number,payload['note'],datetime.now(tz).isoformat()))
        return jsonify(ok=True)

    @app.get('/api/lesson-plans')
    def lesson_plans():
        current={r['lesson_id']:dict(r) for r in db().execute('SELECT * FROM lesson_progress')}
        result=[dict(x,done=bool(current.get(x['id'],{}).get('done')),notes=current.get(x['id'],{}).get('notes','')) for x in lessons]
        return jsonify(lessons=result)

    @app.patch('/api/lesson-plans/<lesson_id>')
    def update_lesson(lesson_id):
        if lesson_id not in lesson_index: abort(404,'Aula não encontrada')
        d=request.get_json(silent=True)
        if not isinstance(d,dict):abort(400,'Dados inválidos')
        row=db().execute('SELECT * FROM lesson_progress WHERE lesson_id=?',(lesson_id,)).fetchone()
        done=d.get('done',bool(row['done']) if row else False)
        notes=d.get('notes',row['notes'] if row else '')
        if type(done)!=bool or not isinstance(notes,str) or len(notes)>6000: abort(400,'Dados da aula inválidos')
        with db():db().execute('INSERT INTO lesson_progress(lesson_id,done,notes,updated_at) VALUES (?,?,?,?) ON CONFLICT(lesson_id) DO UPDATE SET done=excluded.done, notes=excluded.notes,updated_at=excluded.updated_at',(lesson_id,int(done),notes,datetime.now(tz).isoformat()))
        return jsonify(ok=True)

    @app.get('/api/library')
    def list_library():
        docs=[dict(d,kind='built-in') for d in BUNDLED]
        docs += [dict(id=f"upload-{row['id']}",name=row['name'],kind='upload',detail='Arquivo PDF enviado ao aplicativo') for row in db().execute('SELECT id,name FROM library_files ORDER BY id DESC')]
        return jsonify(documents=docs,links=OFFICIAL_LAWS)

    @app.get('/library/<doc_id>')
    def open_document(doc_id):
        bundle=next((d for d in BUNDLED if d['id']==doc_id),None)
        if bundle:
            path=(library/bundle['filename']).resolve()
        elif doc_id.startswith('upload-') and doc_id[7:].isdigit():
            doc=db().execute('SELECT filename FROM library_files WHERE id=?',(int(doc_id[7:]),)).fetchone()
            if not doc:abort(404,'Arquivo não encontrado')
            path=(uploads/doc['filename']).resolve()
        else:abort(404,'Arquivo não encontrado')
        if not path.is_file():abort(404,'Arquivo não disponível no servidor')
        return send_file(path,mimetype='application/pdf',as_attachment=False)

    @app.post('/api/library/upload')
    def upload_document():
        file=request.files.get('file')
        if not file or not file.filename or not file.filename.lower().endswith('.pdf'):
            abort(400,'Selecione um PDF de até 10 MB')
        contents=file.read(10*1024*1024+1)
        if len(contents)>10*1024*1024 or not contents.startswith(b'%PDF-'):
            abort(400,'Arquivo inválido ou maior que 10 MB')
        original=secure_filename(file.filename)[:100] or 'documento.pdf'
        actual=secrets.token_hex(12)+'.pdf'
        (uploads/actual).write_bytes(contents)
        try:
            with db():db().execute('INSERT INTO library_files(name,filename,added_at) VALUES (?,?,?)',(original,actual,datetime.now(tz).isoformat()))
        except Exception:
            (uploads/actual).unlink(missing_ok=True)
            raise
        return jsonify(ok=True),201

    @app.get('/api/evolution')
    def evolution():
        rows=db().execute("SELECT * FROM real_exam_attempts WHERE completed_at IS NOT NULL ORDER BY completed_at DESC LIMIT 150").fetchall()
        history=[]
        for row in rows:
            if row['exam_id'] not in exams:continue
            attempt=attempt_data(row)
            t=attempt.get('totals')
            history.append({'id':row['id'],'name':exams[row['exam_id']]['name'],'date':row['completed_at'],
                            'percentage':t['percentual'] if t else None,
                            'earned':t['pontos'] if t else None,'maximum':t['maximo'] if t else None,
                            'correct':t['acerto'] if t else None,'count':exams[row['exam_id']]['count']})
        counts=[x['percentage'] for x in history if x['percentage'] is not None]
        return jsonify(tests=history,average=round(sum(counts)/len(counts),1) if counts else None,best=max(counts) if counts else None)
