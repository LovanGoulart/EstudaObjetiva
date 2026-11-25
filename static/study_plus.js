'use strict';
/* Planos de aula, biblioteca de documentos e evolução dos resultados. */
const plus={lessons:[],docs:[],links:[],tests:[],average:null,best:null,loaded:false,loading:false,openLesson:null,openDoc:null,lessonFilter:'Todos'};
async function loadStudyPlus(page){
  if(plus.loaded||plus.loading)return;
  plus.loading=true;
  try{
    const [a,b,c]=await Promise.all([api('/api/lesson-plans'),api('/api/library'),api('/api/evolution')]);
    Object.assign(plus,{lessons:a.lessons,docs:b.documents,links:b.links,tests:c.tests,average:c.average,best:c.best,loaded:true});
    if(state.page===page){$('#page').innerHTML=({dashboard:()=>dashboard()+dashboardExtra(),lessons:lessonPage,library:libraryPage}[page])();bindPage()}
  }catch(e){toast('Não foi possível carregar os materiais: '+e.message,true)}finally{plus.loading=false}
}
function dashboardExtra(){
  const tested=plus.tests.filter(x=>x.percentage!==null);
  return `<div class="card padded plus-summary"><div class="section-title"><h2>Evolução nas provas</h2><button class="link" data-page="real-exams">Praticar agora →</button></div>${!plus.loaded?'<p class="muted">Carregando seus resultados...</p>':`<div class="plus-summary-stats"><div><small>Provas corrigidas</small><strong>${tested.length}</strong></div><div><small>Média de aproveitamento</small><strong>${plus.average===null?'—':String(plus.average).replace('.',',')+'%'}</strong></div><div><small>Melhor resultado</small><strong>${plus.best===null?'—':String(plus.best).replace('.',',')+'%'}</strong></div></div>${tested.length?`<div class="plus-mini-bars">${tested.slice(0,8).reverse().map(a=>`<div class="plus-mini-bar" title="${escapeHTML(a.name)} — ${a.percentage}%"><div style="height:${a.percentage}%"></div><small>${fmtDate(a.date)}</small></div>`).join('')}</div>`:'<p class="muted small">Seu gráfico de evolução aparecerá após finalizar uma prova com gabarito.</p>'}`}</div>`;
}
function lessonPage(){
  let list=plus.lessons.filter(l=>plus.lessonFilter==='Todos'||l.discipline===plus.lessonFilter);
  const completed=plus.lessons.filter(l=>l.done).length;
  const active=plus.lessons.find(l=>l.id===plus.openLesson);
  return `${section('Planos de aula','Aulas curtas e orientadas por assunto. Estude em qualquer dia, no seu ritmo.')}<div class="card padded" style="margin-bottom:16px"><div class="flex-row"><div><strong>${completed} de ${plus.lessons.length} aulas concluídas</strong><p class="muted small">Escolha uma aula, siga o roteiro e marque quando concluir.</p></div><span class="count-pill">${plus.lessons.length?pct(completed,plus.lessons.length):0}%</span></div>${bar(completed,plus.lessons.length,'teal')}</div>
  <div class="lesson-filter"><label class="muted small">Disciplina: </label><select id="lessonFilter">${['Todos','Informática','Português','Matemática','Legislação','Conhecimentos Gerais'].map(s=>`<option value="${s}" ${s===plus.lessonFilter?'selected':''}>${s}</option>`).join('')}</select></div>
  ${active?`<div class="card padded lesson-detail"><div class="flex-row"><div><span class="q-label">${escapeHTML(active.discipline)}</span><h2>${escapeHTML(active.title)}</h2></div><button class="btn soft" id="lessonClose">← Voltar</button></div><p class="muted">Objetivo: ${escapeHTML(active.goal)}</p><h3>Conteúdos da aula</h3><ul>${active.topics.map(t=>`<li>${escapeHTML(t)}</li>`).join('')}</ul><h3>Atividade prática</h3><p>${escapeHTML(active.practice)}</p><div class="field" style="margin-top:15px"><label for="lessonNotes">Minhas anotações</label><textarea id="lessonNotes" rows="5" maxlength="6000" placeholder="Resuma os conceitos principais e dúvidas...">${escapeHTML(active.notes)}</textarea></div><div class="flex-row" style="margin-top:12px"><label class="lesson-checkbox"><input type="checkbox" id="lessonDone" ${active.done?'checked':''}> Aula concluída</label><button class="btn primary" id="lessonSave" data-id="${active.id}">Salvar aula</button></div></div>`:
  `<div class="lesson-grid">${list.map(l=>`<button type="button" class="card lesson-card" data-lesson="${l.id}"><div class="flex-row"><span class="q-label">${escapeHTML(l.discipline)}</span><span class="badge ${l.done?'done':'pending'}">${l.done?'✓ Concluída':'Pendente'}</span></div><h3>${escapeHTML(l.title)}</h3><p>${escapeHTML(l.goal)}</p><div class="flex-row"><span class="muted tiny">${l.minutes} min sugeridos • Sem dia fixo</span><b>Ver aula →</b></div></button>`).join('')}</div>`}`;
}
function libraryPage(){
  return `${section('Legislação e arquivos','Consulte o edital, o resumo e as normas oficiais em um só lugar.')}<div class="card padded" style="margin-bottom:17px"><h2>Biblioteca em PDF</h2><p class="muted small">Documentos disponíveis para leitura dentro do aplicativo. Você também pode acrescentar seus PDFs de estudo.</p><div class="library-grid">${plus.docs.map(d=>`<button type="button" class="library-card" data-doc="${d.id}"><span class="library-icon">▤</span><strong>${escapeHTML(d.name)}</strong><small>${escapeHTML(d.detail)}</small><span class="muted tiny">Abrir no aplicativo →</span></button>`).join('')}</div><div class="library-upload"><input type="file" id="pdfUpload" accept=".pdf,application/pdf" aria-label="Selecionar PDF"><button class="btn primary" id="uploadStudyPdf">Adicionar PDF</button><small class="muted">Até 10 MB por arquivo. A biblioteca não oferece exclusão de documentos.</small></div></div>
  ${plus.openDoc?`<div class="card padded pdf-doc-shell" id="libraryPdfShell" style="margin-bottom:17px"><div class="flex-row"><h2>Leitura do documento</h2><div class="pdf-doc-actions"><button class="btn soft" type="button" id="libraryFullscreen" title="Expandir PDF para tela cheia">⛶ Tela cheia</button><button class="btn soft" type="button" id="closeStudyPdf">Fechar leitura</button></div></div><iframe class="study-doc-viewer" title="Documento para estudo" src="/library/${encodeURIComponent(plus.openDoc)}#toolbar=1"></iframe></div>`:''}
  <div class="card padded"><h2>Fontes oficiais de legislação</h2><p class="muted small">Consulte o texto atualizado; o resumo é apenas material de revisão.</p><div class="leg-links">${plus.links.map(x=>`<a href="${escapeHTML(x.url)}" target="_blank" rel="noopener noreferrer"><strong>${escapeHTML(x.name)}</strong><small>${escapeHTML(x.detail)}</small><span>↗</span></a>`).join('')}</div></div>`;
}
function bindStudyPlus(){
  const root=$('#page');
  if(state.page==='lessons'){
    root.querySelector('#lessonFilter')?.addEventListener('change',e=>{plus.lessonFilter=e.target.value;root.innerHTML=lessonPage();bindPage()});
    root.querySelectorAll('[data-lesson]').forEach(b=>b.addEventListener('click',()=>{plus.openLesson=b.dataset.lesson;root.innerHTML=lessonPage();bindPage();window.scrollTo(0,0)}));
    root.querySelector('#lessonClose')?.addEventListener('click',()=>{plus.openLesson=null;root.innerHTML=lessonPage();bindPage()});
    root.querySelector('#lessonSave')?.addEventListener('click',async e=>{const id=e.target.dataset.id;try{await api('/api/lesson-plans/'+id,'PATCH',{done:!!$('#lessonDone')?.checked,notes:$('#lessonNotes')?.value||''});plus.loaded=false;plus.openLesson=id;await loadStudyPlus('lessons');toast('Plano de aula salvo')}catch(err){toast(err.message,true)}});
  }
  if(state.page==='library'){
    root.querySelectorAll('[data-doc]').forEach(b=>b.addEventListener('click',()=>{plus.openDoc=b.dataset.doc;root.innerHTML=libraryPage();bindPage();root.querySelector('.study-doc-viewer')?.scrollIntoView({behavior:'smooth',block:'start'})}));
    root.querySelector('#closeStudyPdf')?.addEventListener('click',()=>{plus.openDoc=null;root.innerHTML=libraryPage();bindPage()});
    root.querySelector('#libraryFullscreen')?.addEventListener('click',e=>window.EOViewer?.toggle(root.querySelector('#libraryPdfShell'),e.currentTarget));
    root.querySelector('#uploadStudyPdf')?.addEventListener('click',async()=>{const file=$('#pdfUpload')?.files?.[0];if(!file)return toast('Escolha um PDF para enviar.',true);const form=new FormData();form.append('file',file);try{const res=await fetch('/api/library/upload',{method:'POST',headers:{'X-CSRF-Token':window.APP_CSRF},body:form});const data=await res.json();if(!res.ok)throw Error(data.error||'Falha ao enviar PDF');plus.loaded=false;await loadStudyPlus('library');toast('PDF adicionado à biblioteca')}catch(e){toast(e.message,true)}});
  }
}
