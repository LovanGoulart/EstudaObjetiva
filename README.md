# EstudaObjetiva — app de estudos para o concurso de Novo Cabrais/RS

Aplicação web **Python + Flask + SQLite + HTML + CSS + JavaScript** para organizar os estudos de Técnico em Informática. O projeto é independente, com interface original. O layout e fluxo foram inspirados no uso de painéis de planejamento e acompanhamento por aplicativos de produtividade, como Todoist e StudySmarter, sem copiar seu código.

## Funcionalidades

- **181 tópicos** com prioridades P1, P2 e P3, organizados pelas cinco disciplinas e grupos do checklist.
- Estados **Pendente / Estudando / Concluído**, com progresso de cada disciplina.
- **Anotações individuais por tópico** e anotações nos objetivos de estudo sem datas fixas.
- **Revisões automáticas** agendadas para 1, 7 e 30 dias após marcar um tópico como concluído.
- **Plano flexível**, com sugestões de assuntos sem datas obrigatórias. É possível adicionar, editar, concluir, reabrir e excluir objetivos a qualquer momento.
- Registro de minutos de estudo, tipo e disciplina, com histórico e gráficos simples.
- Registro de simulados com 40 questões e pesos do edital: Português 10×2, Matemática 8×2, Gerais 6×2, Legislação 6×2, Específicos 10×4.
- Backup e restauração em JSON, tema claro/escuro, interface responsiva e PWA instalável.

## Instalação no Windows

Requer Python 3.10+.

```powershell
cd EstudaObjetiva
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra **http://127.0.0.1:5000**.

## Instalação no Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Onde ficam os dados?

Em `instance/estudos.db`, criado automaticamente. Não apague esse arquivo para não perder progresso. Use também **Backup e ajustes → Exportar backup JSON** regularmente.

## Uso em celular e publicação

- O servidor padrão escuta apenas `127.0.0.1` para uso pessoal no computador.
- Para usar em outros aparelhos, implante em um servidor com HTTPS (por exemplo, PythonAnywhere com aplicação WSGI). O arquivo `wsgi.py` já exporta `application`.
- **Antes de publicar**, defina `SECRET_KEY` com 32+ caracteres aleatórios persistentes e `APP_PASSWORD_HASH` com um hash criado por `werkzeug.security.generate_password_hash('sua_senha_forte')`. Exemplo para gerar hash: `python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('SUA_SENHA'))"`. Configure o valor impresso no ambiente, sem inserir a senha em código-fonte.
- Não publique o app sem senha de acesso. Não use o servidor de desenvolvimento Flask em produção: utilize o servidor WSGI da plataforma, HTTPS e backups.
- O PWA facilita instalação e mantém a interface no cache, mas **não promete edição de dados offline nem notificações push**. O servidor precisa estar acessível para salvar informações.
- Não há contas multiusuário, envio de e-mails nem sincronização automática entre instâncias independentes.

## Observações sobre conteúdo e fonte

Os 181 tópicos foram extraídos do PDF `Checklist_Estudos_Tecnico_Informatica_Novo_Cabrais_2027.pdf` discutido nesta conversa. As prioridades são indicativas e não representam probabilidades oficiais. As normas devem ser estudadas pela legislação vigente no escopo temporal do edital.

## Testes

```bash
python -m unittest discover -s tests -v
```

## Atualização: provas reais e datas brasileiras

Na atualização, substitua **somente os arquivos do ZIP**, preservando a pasta
`instance/` e seu banco de dados SQLite. A nova tabela de tentativas é criada
automaticamente na primeira inicialização. Use `pip install -r requirements.txt`
no ambiente virtual existente para instalar também `tzdata` no Windows.

Acesse **Provas reais** no menu. Há nove cadernos PDF originais: Guaraniaçu,
Santa Leopoldina, FEAS, Dezesseis de Novembro, Tapes, Mato Rico, Candiota,
Portão e Sentinela do Sul. Selecione **Nova tentativa**, leia as questões no PDF,
preencha o cartão de respostas e clique em **Finalizar e corrigir**. Você pode
interromper e retomar provas sem perder as respostas e refazê-las quantas vezes
quiser; o histórico fica em SQLite e está incluído no backup.

São oito gabaritos no material. Candiota não tinha gabarito correspondente e,
portanto, permite salvar respostas, mas **não oferece correção automática**.
Os gabaritos marcados como preliminares podem ser alterados pelo organizador.
Nas provas com questões anuladas, a questão recebe crédito.

Datas exibidas e digitadas pelo usuário seguem o formato **dd/mm/aaaa**.
Internamente, banco de dados e APIs utilizam `aaaa-mm-dd` (ISO 8601), sem alterar
cálculos ou ordenações. Os formulários validam a data antes de salvar.

Para verificar a instalação: `python -m unittest discover -s tests -v`.

## Atualização do plano flexível

Ao iniciar a versão atualizada, o aplicativo transforma automaticamente o antigo cronograma com datas em uma lista de objetivos sem prazo definido. Marcações de concluído e anotações já existentes são preservadas. Faça um backup JSON antes da atualização e mantenha a pasta `instance` intacta. A data oficial da prova, as datas do histórico e as sugestões de revisão continuam funcionando normalmente.
