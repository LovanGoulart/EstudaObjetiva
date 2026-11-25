# EstudaObjetiva 2.0 — Novo Cabrais/RS

Aplicativo pessoal de preparação para o cargo de **Técnico em Informática** (Instituto Objetiva, prova prevista em **10/01/2027**). Projeto em **Python, Flask, SQLite, HTML, CSS, JavaScript e PWA**, com interface responsiva em português do Brasil.

## Funcionalidades

- **Painel:** conteúdos concluídos, tempo estudado, revisões, contagem regressiva, média e evolução nas provas.
- **Conteúdo programático:** 181 tópicos divididos nas cinco matérias do edital; status Pendente, Estudando ou Concluído; anotações por assunto; busca, filtros e revisões espaçadas (1, 7 e 30 dias).
- **Plano livre:** objetivos sem datas obrigatórias. Permite adicionar, editar, concluir e reabrir objetivos; não oferece exclusão de conteúdos.
- **Banco de provas — 11 cadernos:** nove provas anteriores fornecidas pelo usuário e dois simulados autorais; responder dentro do aplicativo, salvar e continuar depois, refazer quantas vezes quiser, conferir gabarito e registrar anotações por questão.
- **Simulados autorais:** 40 questões de múltipla escolha, textos e alternativas nativos no app, explicação individual e pontuação de acordo com o edital: 2 pontos nas quatro primeiras disciplinas, 4 em Conhecimentos Específicos, total 100.
- **Provas antigas:** páginas originais convertidas em imagens para leitura dentro do aplicativo, com navegação sincronizada ao número da questão, cartão de respostas, correção por gabarito fornecido e aproveitamento percentual. O sistema não atribui pesos do edital novo a provas antigas com estrutura diferente. As explicações individuais das provas antigas não acompanham o gabarito enviado; o aplicativo indica isso claramente, e permite registrar o raciocínio no campo de notas.
- **Sem gabarito:** Candiota/RS 2023 permite responder, salvar e revisar as marcações, mas não recebe nota inventada.
- **Planos de aula:** 19 roteiros práticos por disciplina, com objetivos, conteúdos, exercícios sugeridos, anotações e opção de marcar concluído. Sem dias ou horários obrigatórios.
- **Legislação e arquivos:** resumo de legislação, edital, links para textos oficiais e inclusão de PDFs próprios (até 10 MB) com leitura dentro da tela.
- **Registros:** horas dedicadas, simulados avulsos e resultados de provas realizadas dentro do aplicativo.
- **Backup em JSON:** inclui tópicos, notas, revisões, aulas, tentativas e anotações por questão. Documentos PDF que você enviar devem ser guardados separadamente em `instance/arquivos`.
- **PWA:** instalável em Android e desktop; iOS pelo menu Compartilhar > Adicionar à Tela de Início. Dados são armazenados no servidor (não há gravação offline nem push neste pacote).

## Instalação no Windows

Requer Python 3.10 ou superior. Extraia o ZIP e, na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Acesse **http://127.0.0.1:5000**. No Windows, se o PowerShell bloquear a ativação, execute o arquivo `iniciar_windows.bat` que já acompanha o projeto.

## Atualização no PythonAnywhere SEM APAGAR DADOS

1. Em **Files**, faça backup de `/home/SEU_USUARIO/EstudaObjetiva/instance/estudos.db` e da pasta `instance/arquivos`, se houver.
2. Envie os arquivos e pastas do ZIP **para a raiz existente** `~/EstudaObjetiva`, preservando **a pasta `instance` existente**. Não crie uma segunda subpasta `EstudaObjetiva`.
3. Os nomes `exam_assets/catalog.json`, `exam_assets/native_quizzes.json`, `exam_assets/pages`, `static/study_plus.js` e `study_extension.py` são necessários. A pasta `exam_assets` deve conter as nove provas PDF originais.
4. No Bash, use o **Python da virtualenv configurada em Web**:

```bash
cd ~/EstudaObjetiva
python -m pip install -r requirements.txt
python -c "import app; print('Banco:', app.DB_PATH); print('Provas:', len(app.REAL_EXAMS))"
```

**Resultado esperado:** `Provas: 11`. O banco permanece em `~/EstudaObjetiva/instance/estudos.db`, a menos que você configure `DATABASE_PATH`.

5. Em **Web → WSGI configuration file**, mantenha a importação com o caminho correto:

```python
import sys
PROJECT = '/home/SEU_USUARIO/EstudaObjetiva'
if PROJECT not in sys.path:
    sys.path.insert(0, PROJECT)
from app import app as application
```

6. Clique em **Web → Reload**. Para atualizar o PWA, abra o site, force a atualização (`Ctrl + F5`) e, se necessário, desregistre o service worker antigo em DevTools → Application → Service Workers.

### Atenção: deploy público e senha

Este aplicativo é de **uso individual**. Se o site for acessível pela internet, **ative autenticação** com a variável de ambiente `APP_PASSWORD_HASH`. Gere um hash com:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash(input('Digite sua senha: ')))"
```

Configure a variável `APP_PASSWORD_HASH` com o hash obtido **no ambiente do servidor**, nunca em arquivos versionados no GitHub. Também é recomendado definir `SECRET_KEY` com valor aleatório e `APP_COOKIE_SECURE=1` ao usar HTTPS. Configure a virtualenv do site na aba **Web** do PythonAnywhere.

### Banco e compatibilidade

- As tabelas novas (`question_notes`, `lesson_progress`, `library_files`) são criadas automaticamente em `init_db()`.
- Os tópicos antigos são preservados via `INSERT OR IGNORE`; notas, progresso, simulados e tentativas continuam no banco preexistente.
- **Nunca** envie um `estudos.db` vazio sobre o banco de produção e não remova a pasta `instance`.
- Uma instalação limpa cria automaticamente as tabelas e cadastra os 181 tópicos do edital.

## Estrutura principal

```text
EstudaObjetiva/
  app.py                 # Backend e rotas anteriores
  study_extension.py     # Notas de questões, aulas, biblioteca e métricas
  seed.json              # 181 assuntos
  requirements.txt
  templates/
  static/
    app.js               # Painel, tópicos, revisões, agenda livre
    real_exams.js        # Resolução e correção das provas
    study_plus.js        # Planos de aula e legislação
    style.css, sw.js, manifest.webmanifest, icons/
  exam_assets/
    catalog.json         # 9 provas com gabaritos quando fornecidos
    native_quizzes.json  # 2 simulados inéditos com comentários
    *.pdf                # cadernos originais e gabaritos
    pages/<prova>/*.webp # páginas ilustradas para consulta no próprio app
  study_library/
    lesson_plans.json
    Edital_Novo_Cabrais_2026.pdf
    Resumo_Legislacao_Concurso.pdf
  instance/              # criado no primeiro uso, NÃO ENVIAR AO GITHUB
  tests/
```

## Testes

Após instalar as dependências:

```bash
python -m unittest discover -s tests -v
```

A correção automática das provas antigas depende dos gabaritos fornecidos no arquivo original do usuário, incluindo versões preliminares. É possível haver anulações ou alterações posteriores; revise as informações antes de usar como decisão oficial.

## Limitações intencionais

- **Não** fornece a prova sigilosa de 10/01/2027: os simulados do aplicativo são autorais.
- **Não** inventa comentário detalhado de questões antigas sem fonte de explicação verificada.
- Bibliotecas e sites externos podem mudar; consultar legislação atualizada nas fontes oficiais é responsabilidade do estudante.
- Não inclui trabalho em tempo real, sincronização entre bancos independentes, push ou exercícios gerados automaticamente por IA.
