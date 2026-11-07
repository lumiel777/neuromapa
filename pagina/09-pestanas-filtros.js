
  function iniciarPestanasFiltros() {
    const caja = document.getElementById('pestanas-filtros');
    const lateral = document.getElementById('lateral');
    if (!caja || !lateral) return;
    const pastilla = caja.querySelector('.pestanas-pastilla');
    const botones = Array.from(caja.querySelectorAll('button[data-pestana]'));
    const secciones = Array.from(lateral.querySelectorAll('section[data-pestana]'));
    let activa = 'grupos';
    try { activa = localStorage.getItem('cerebro-pestana') || 'grupos'; } catch (e) {}

    const disponible = n => secciones.some(s => s.dataset.pestana === n && !s.hidden);
    function moverPastilla() {
      const b = botones.find(x => x.dataset.pestana === activa);
      if (!b || !b.offsetWidth) return;
      caja.style.setProperty('--px', b.offsetLeft + 'px');
      caja.style.setProperty('--pw', b.offsetWidth + 'px');
    }
    function aplicar() {
      if (!disponible(activa)) activa = 'grupos';
      for (const b of botones) {
        const n = b.dataset.pestana;
        b.hidden = !disponible(n);
        b.setAttribute('aria-selected', String(n === activa));
        b.tabIndex = n === activa ? 0 : -1;
      }
      for (const s of secciones) s.classList.toggle('fuera-de-pestana', s.dataset.pestana !== activa);
      moverPastilla();
    }
    function elegir(n, foco) {
      activa = n;
      try { localStorage.setItem('cerebro-pestana', n); } catch (e) {}
      aplicar();
      if (foco) botones.find(x => x.dataset.pestana === n).focus();
    }

    for (const b of botones) b.addEventListener('click', () => elegir(b.dataset.pestana, false));
    caja.addEventListener('keydown', e => {
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
      const vis = botones.filter(b => !b.hidden);
      const i = vis.findIndex(b => b.dataset.pestana === activa);
      const j = (i + (e.key === 'ArrowRight' ? 1 : vis.length - 1)) % vis.length;
      e.preventDefault();
      elegir(vis[j].dataset.pestana, true);
    });
    const vigia = new MutationObserver(aplicar);
    for (const s of secciones) vigia.observe(s, { attributes: true, attributeFilter: ['hidden'] });
    if (typeof ResizeObserver === 'function') new ResizeObserver(moverPastilla).observe(caja);
    aplicar();
    requestAnimationFrame(() => pastilla.classList.add('pastilla-movil'));
  }

  iniciarPestanasFiltros();
