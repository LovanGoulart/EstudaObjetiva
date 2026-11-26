"""Aplica a autenticação por usuário + senha ao app.py existente, sem tocar no SQLite.
Execute na raiz do projeto: python install_login.py
"""
from pathlib import Path
import re
import shutil
import datetime
import sys

ROOT=Path(__file__).resolve().parent
APP=ROOT/'app.py'
if not APP.is_file():
    raise SystemExit('ERRO: coloque este arquivo na mesma pasta do app.py.')
source=APP.read_text(encoding='utf-8')
if '# LOGIN_USUARIO_SENHA_V1' in source:
    print('Autenticação por usuário e senha já instalada. Nada a alterar.');sys.exit(0)

helpers='''# LOGIN_USUARIO_SENHA_V1: arquivo privado, fora da pasta static e fora do Git.
import hmac
from flask import redirect, url_for

LOGIN_FILE = INSTANCE_DIR / '.login_credentials.json'

def login_credentials():
    """Lê somente credenciais com senha criptograficamente hasheada."""
    try:
        value = json.loads(LOGIN_FILE.read_text(encoding='utf-8'))
        if isinstance(value.get('username'), str) and isinstance(value.get('password_hash'), str):
            return value
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None

'''
anchor='@app.before_request\ndef security():'
if source.count(anchor)!=1:
    raise SystemExit('ERRO: não encontrei o bloco de segurança esperado. O app.py não foi alterado.')
source=source.replace(anchor,helpers+anchor,1)
security='''@app.before_request
def security():
    # Todas as rotas privadas exigem sessão autenticada; falha fechado sem configuração.
    public_endpoints = ('login', 'static', 'manifest', 'service_worker')
    if request.endpoint not in public_endpoints and not session.get('authenticated'):
        if request.path.startswith('/api/'):
            return jsonify(error='Autenticação necessária'), 401
        return redirect(url_for('login'))
    if request.method in ('POST', 'PATCH', 'PUT', 'DELETE') and request.endpoint != 'login':
        token = request.headers.get('X-CSRF-Token', '')
        if not token or not hmac.compare_digest(token, session.get('csrf', '')):
            return jsonify(error='CSRF inválido, atualize a página'), 403

'''
source,n=re.subn(r'@app\.before_request\ndef security\(\):\n.*?(?=@app\.after_request)',security,source,count=1,flags=re.S)
if n!=1:raise SystemExit('ERRO: não consegui atualizar segurança. Sem alterações salvas.')
login='''@app.route('/login', methods=['GET', 'POST'])
def login():
    credentials = login_credentials()
    if request.method == 'POST':
        if not credentials:
            return render_template('login.html', error='Acesso não configurado. Execute python setup_login.py no servidor.'), 503
        supplied_username = request.form.get('username', '').strip()
        supplied_password = request.form.get('password', '')
        # Verifique ambos os campos; evite diferenças de tempo na comparação do usuário.
        name_ok = hmac.compare_digest(
            supplied_username.encode('utf-8'), credentials['username'].encode('utf-8')
        )
        password_ok = check_password_hash(credentials['password_hash'], supplied_password)
        if name_ok and password_ok:
            session.clear()
            session['authenticated'] = True
            session['login_user'] = credentials['username']
            return redirect(url_for('index'))
        return render_template('login.html', error='Usuário ou senha incorretos.'), 401
    if session.get('authenticated') and credentials:
        return redirect(url_for('index'))
    return render_template('login.html', setup_needed=not bool(credentials))

'''
source,n=re.subn(r"@app\.route\('/login',methods=\['GET','POST'\]\)\ndef login\(\):\n.*?(?=@app\.route\('/logout')",login,source,count=1,flags=re.S)
if n!=1:raise SystemExit('ERRO: rota de login não encontrada; arquivo original preservado.')
# Atualiza a bandeira de autenticação exibida na página: JS de logout precisa dela.
old="auth=bool(os.getenv('APP_PASSWORD_HASH'))"
if old not in source: raise SystemExit('ERRO: marcação de autenticação inesperada, arquivo original preservado.')
source=source.replace(old,'auth=True',1)
# O navegador não pode reutilizar páginas HTML protegidas depois do logout.
source=source.replace("if request.path.startswith('/api/'):resp.headers['Cache-Control']='no-store'", "if request.path.startswith('/api/') or request.path in ('/', '/login'):resp.headers['Cache-Control']='no-store'",1)
compile(source,str(APP),'exec')
backup=ROOT/f"app.py.pre_login_{datetime.datetime.now():%Y%m%d_%H%M%S}.bak"
shutil.copy2(APP,backup)
APP.write_text(source,encoding='utf-8')
print('OK: login por usuário e senha instalado em app.py')
print('Backup do app.py:',backup.name)
print('PRÓXIMO: python setup_login.py')
