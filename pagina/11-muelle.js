
  function iniciarMuelle() {
    const muelle = document.getElementById('controles-grafo');
    const boton = document.getElementById('muelle-compartir');
    if (!muelle || !boton) return;
    function ponerAbierto(abierto) {
      muelle.classList.toggle('compartir-abierto', abierto);
      boton.setAttribute('aria-expanded', String(abierto));
    }
    boton.addEventListener('click', () => ponerAbierto(!muelle.classList.contains('compartir-abierto')));
    muelle.addEventListener('keydown', e => {
      if (e.key === 'Escape' && muelle.classList.contains('compartir-abierto')) {
        e.stopPropagation();
        ponerAbierto(false);
        boton.focus();
      }
    });
  }

  iniciarMuelle();
