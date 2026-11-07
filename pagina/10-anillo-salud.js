
  function iniciarAnilloSalud() {
    const boton = document.getElementById('salud-resumen');
    const bloque = document.getElementById('bloque-salud');
    if (!boton || !bloque) return;
    const total = nodos.length;
    const sanas = nodos.filter(n => !n.problemas.some(p => p.tono === 'peligro' || p.tono === 'aviso')).length;
    const nota = total ? Math.round(100 * sanas / total) : 100;
    const color = nota < 70 ? 'var(--peligro)' : nota < 90 || cuentaTonos.peligro ? 'var(--aviso)' : '#22c55e';
    const largo = 2 * Math.PI * 24;
    const cifra = (n, uno, varios, tono) => '<span class="tono-' + tono + '">' + n + ' ' + (n === 1 ? uno : varios) + '</span>';
    const partes = [];
    if (cuentaTonos.peligro) partes.push(cifra(cuentaTonos.peligro, 'grave', 'graves', 'peligro'));
    if (cuentaTonos.aviso) partes.push(cifra(cuentaTonos.aviso, 'aviso', 'avisos', 'aviso'));
    if (cuentaTonos.revisar) partes.push(cuentaTonos.revisar + ' para revisar');
    const titulo = nota === 100 ? 'Todas las notas sanas' : sanas + ' de ' + total + ' notas sanas';
    boton.innerHTML =
      '<svg class="anillo" viewBox="0 0 58 58" aria-hidden="true">' +
      '<circle class="pista" cx="29" cy="29" r="24"/>' +
      '<circle class="avance" cx="29" cy="29" r="24" style="--c:' + color + '" stroke-dasharray="' + largo.toFixed(2) + '" stroke-dashoffset="' + (largo * (1 - nota / 100)).toFixed(2) + '" transform="rotate(-90 29 29)"/>' +
      '<text x="29" y="34.5" text-anchor="middle">' + nota + '</text></svg>' +
      '<span class="salud-resumen-texto"><b>' + titulo + '</b><span>' + (partes.length ? partes.join(' · ') : 'Sin problemas') + '</span></span>' +
      '<svg class="flecha" width="16" height="16" viewBox="0 0 24 24" aria-hidden="true" style="fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round"><path d="M6 9l6 6 6-6"/></svg>';
    boton.title = 'El número es el porcentaje de notas sin problemas graves ni avisos. Tocá para ver el detalle.';
    boton.setAttribute('aria-label', 'Salud: ' + nota + ' de 100. ' + titulo + '. ' + boton.querySelector('.salud-resumen-texto span').textContent);

    function ponerAbierto(abierto, guardar) {
      bloque.classList.toggle('salud-plegada', !abierto);
      boton.setAttribute('aria-expanded', String(abierto));
      if (guardar) try { localStorage.setItem('cerebro-salud', abierto ? 'abierta' : 'plegada'); } catch (e) {}
    }
    let guardado = null;
    try { guardado = localStorage.getItem('cerebro-salud'); } catch (e) {}
    ponerAbierto(guardado === 'abierta', false);
    boton.addEventListener('click', () => ponerAbierto(bloque.classList.contains('salud-plegada'), true));
    document.getElementById('totales').addEventListener('click', ev => {
      if (ev.target.closest('#ir-salud')) ponerAbierto(true, false);
    }, true);
  }

  iniciarAnilloSalud();

  function iniciarDetalleAhorro() {
    const bloque = document.getElementById('bloque-ahorro');
    const boton = document.getElementById('ahorro-ver');
    if (!bloque || !boton) return;
    function poner(abierto) {
      bloque.classList.toggle('ahorro-plegado', !abierto);
      boton.setAttribute('aria-expanded', String(abierto));
      boton.textContent = abierto ? 'Ocultar el detalle' : 'Ver el detalle';
    }
    poner(false);
    boton.addEventListener('click', () => poner(bloque.classList.contains('ahorro-plegado')));
  }

  iniciarDetalleAhorro();
