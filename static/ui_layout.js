"use strict";
/* Tela cheia nativa com fallback para navegadores/PWAs que não a suportam. */
(() => {
  let fallback = null;
  const changed = () => {
    const el = document.fullscreenElement || fallback;
    document.body.classList.toggle('eo-viewer-lock', !!el);
    document.querySelectorAll('#pdfFullscreen,#libraryFullscreen').forEach(button => {
      const on = !!el && el.contains(button);
      button.textContent = on ? '✕ Sair da tela cheia' : '⛶ Tela cheia';
      button.setAttribute('aria-pressed', String(on));
    });
  };
  const close = async () => {
    if (document.fullscreenElement) {
      try { await document.exitFullscreen(); } catch (error) { /* já encerrado */ }
    }
    if (fallback) { fallback.classList.remove('eo-fullscreen'); fallback = null; }
    changed();
  };
  const toggle = async (element, button) => {
    if (!element) return;
    if (document.fullscreenElement === element || fallback === element) { await close(); return; }
    await close();
    try {
      if (!element.requestFullscreen) throw new Error('Sem API de tela cheia');
      await element.requestFullscreen();
    } catch (error) {
      fallback = element;
      fallback.classList.add('eo-fullscreen');
    }
    changed();
    if(button) button.focus({preventScroll:true});
  };
  document.addEventListener('fullscreenchange', changed);
  document.addEventListener('keydown', event => {
    if(event.key === 'Escape' && fallback) { event.stopPropagation(); close(); }
  });
  window.EOViewer = {toggle, close};
})();
