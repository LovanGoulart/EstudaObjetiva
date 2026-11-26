"""Cria ou altera usuário/senha sem armazenar senha em texto puro.
Execute: python setup_login.py
"""
from pathlib import Path
from getpass import getpass
from werkzeug.security import generate_password_hash
import json, os, tempfile

instance = Path(__file__).resolve().parent / 'instance'
instance.mkdir(parents=True,exist_ok=True)
path = instance / '.login_credentials.json'

print('CONFIGURAR LOGIN DO ESTUDAOBJETIVA')
if path.exists():print('Aviso: o usuário anterior será substituído; as sessões já abertas devem ser encerradas.')
username = input('Nome de usuário: ').strip()
if not (3 <= len(username) <= 64) or any(ch.isspace() for ch in username):
    raise SystemExit('Usuário inválido: use de 3 a 64 caracteres sem espaços.')
password = getpass('Senha (mínimo 12 caracteres): ')
confirmation = getpass('Confirme a senha: ')
if len(password) < 12 or password != confirmation:
    raise SystemExit('Senha muito curta ou confirmação diferente. Nenhum arquivo alterado.')
data = json.dumps({'username':username,'password_hash':generate_password_hash(password)},ensure_ascii=False,indent=2)
fd,tmp=tempfile.mkstemp(prefix='.login_',dir=instance)
try:
    with os.fdopen(fd,'w',encoding='utf-8') as f:
        f.write(data+'\n')
    os.chmod(tmp,0o600)
    os.replace(tmp,path)
finally:
    if os.path.exists(tmp):os.unlink(tmp)
print('OK: usuário e senha configurados. Senha não foi armazenada em texto puro.')
print('IMPORTANTE: execute Web > Reload no PythonAnywhere e abra o site em janela anônima.')
