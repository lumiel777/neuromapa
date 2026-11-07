  const actividad = { focos: [], onda: null };
  const bufOnda = new Float32Array(4);
  const bufOndaCol = new Float32Array(4);
  const bufHuella = new Float32Array(HUELLAS * 4);
  const bufHuellaCol = new Float32Array(HUELLAS * 4);
  const VIDA_BRASA = 240000;
  const VENTANA_TOQUES = 1800000;
  const PESO_TOQUE = { leer: 1, editar: 3, crear: 3, buscar: 0.5 };
  const sangre = s => Math.pow(s / 5, 5) * Math.exp(5 - s);
  function curvaBrasa(ms) {
    if (ms <= 0) return 0;
    const h = sangre(ms / 1000);
    return ms < 5000 ? h : Math.max(h, 0.55 * Math.pow(2, (5000 - ms) / VIDA_BRASA));
  }
  function calorBrasa(b, ahora) {
    const nuevos = b.nuevos;
    let quedan = 0;
    for (let i = 0; i < nuevos.length; i += 2) {
      const edad = ahora - nuevos[i];
      if (edad > 15000) {
        b.acum = b.acum * Math.pow(2, Math.min(0, b.tAcum - ahora) / VIDA_BRASA) + nuevos[i + 1] * 0.55 * Math.pow(2, (5000 - edad) / VIDA_BRASA);
        b.tAcum = Math.max(b.tAcum, ahora);
      } else {
        nuevos[quedan++] = nuevos[i];
        nuevos[quedan++] = nuevos[i + 1];
      }
    }
    nuevos.length = quedan;
    let h = b.acum * Math.pow(2, Math.min(0, b.tAcum - ahora) / VIDA_BRASA);
    for (let i = 0; i < nuevos.length; i += 2) h += nuevos[i + 1] * curvaBrasa(ahora - nuevos[i]);
    return h;
  }
  function tocarBrasa(n, color, peso, t, sinContar) {
    if (!n || !peso) return;
    const ahora = performance.now();
    let b = n._brasa;
    if (!b) {
      b = { acum: 0, tAcum: ahora, nuevos: [], c: hexARgb(color), calor: 0 };
      n._brasa = b;
      brasas.notas.set(n, b);
    }
    const c = hexARgb(color);
    const k = peso / (peso + calorBrasa(b, ahora));
    for (let i = 0; i < 3; i++) b.c[i] += (c[i] - b.c[i]) * k;
    b.nuevos.push(t, peso);
    if (!sinContar) brasas.golpes.push(t, n);
    brasas.tElegir = 0;
    if (ahora - t < 6000) anim.escenaHasta = Math.max(anim.escenaHasta, t + 6000);
    programarCuadro();
  }
  function elegirBrasas(ahora) {
    if (ahora - brasas.tElegir < 500) return;
    brasas.tElegir = ahora;
    const lista = brasas.lista;
    lista.length = 0;
    for (const [n, b] of brasas.notas) {
      b.calor = calorBrasa(b, ahora);
      if (b.calor < 0.03 && !b.nuevos.length) {
        brasas.notas.delete(n);
        n._brasa = null;
        continue;
      }
      if (n._visible) lista.push(n);
    }
    lista.sort((a, b) => b._brasa.calor - a._brasa.calor);
    if (lista.length > HUELLAS) lista.length = HUELLAS;
    const g = brasas.golpes;
    let i = 0;
    while (i < g.length && ahora - g[i] > VENTANA_TOQUES) i += 2;
    if (i) g.splice(0, i);
    const rot = cerebro && cerebro.rotulos;
    if (!rot) return;
    if (!brasas.porLobulo || brasas.porLobulo.length !== rot.length * 2) brasas.porLobulo = new Float64Array(rot.length * 2);
    const suma = brasas.porLobulo;
    suma.fill(0);
    for (let j = 0; j < g.length; j += 2) {
      const l = lobuloDe(g[j + 1]);
      if (l >= 0 && l < rot.length) suma[l]++;
    }
    for (const [n, b] of brasas.notas) {
      const l = lobuloDe(n);
      if (l >= 0 && l < rot.length) suma[rot.length + l] += b.calor;
    }
    let cambio = false;
    rot.forEach((r, j) => {
      const c = suma[rot.length + j];
      if (r.toques !== suma[j] || Math.abs(r.calor - c) > 0.08) {
        r.toques = suma[j];
        r.calor = c;
        cambio = true;
      }
    });
    if (cambio) pedirDibujo();
  }
  function activar(x, y, z, radio, color, fuerza, dur, viaje) {
    const ahora = performance.now();
    const lista = actividad.focos;
    if (!viaje) {
      for (let i = lista.length - 1; i >= 0; i--) {
        const f = lista[i];
        if (f.ruta || f.x !== x || f.y !== y || f.z !== z) continue;
        const edad = ahora - f.t0;
        const sigue = edad < f.dur;
        f.t0 = sigue ? ahora - Math.min(180, edad) : ahora;
        f.fuerza = sigue ? Math.max(f.fuerza, fuerza) : fuerza;
        f.c = hexARgb(color);
        f.radio = Math.max(f.radio, radio);
        f.dur = dur || 2600;
        lista.splice(i, 1);
        lista.push(f);
        programarCuadro();
        return;
      }
    }
    lista.push({ x, y, z, radio, c: hexARgb(color), fuerza, t0: ahora, dur: dur || 2600 });
    if (lista.length > 12) lista.shift();
    programarCuadro();
  }
  function activarNota(n, color, fuerza, dur) {
    if (!n || !cerebro) return;
    activar(n.x, n.y, n.z || 0, 120 * cerebro.S, color, fuerza, dur);
  }
  function activarLobulo(id, color, fuerza) {
    if (!cerebro) return;
    const l = cerebro.lobulos.find(x => x.id === id);
    if (l) activar(l.wx, l.wy, 0, l.wr * 0.9, color, fuerza, 3200);
  }
  const puntoVia = [0, 0, 0];
  function viajar(a, b, color, dur) {
    if (!cerebro || !a || !b) return;
    const k = ranuraVia(a, b);
    const mx = (a.x + b.x) / 2;
    const my = (a.y + b.y) / 2;
    const mz = ((a.z || 0) + (b.z || 0)) / 2;
    if (k >= 0) {
      viaMundo(k, puntoVia);
      puntoVia[0] = 2 * puntoVia[0] - mx;
      puntoVia[1] = 2 * puntoVia[1] - my;
      puntoVia[2] = 2 * puntoVia[2] - mz;
    } else {
      puntoVia[0] = mx + (giro.cx - mx) * 0.3;
      puntoVia[1] = my + (giro.cy - my) * 0.3;
      puntoVia[2] = mz * 0.7;
    }
    activar(b.x, b.y, b.z || 0, 80 * cerebro.S, color, 0.85, 1600, true);
    const f = actividad.focos[actividad.focos.length - 1];
    f.ruta = [a.x, a.y, a.z || 0, puntoVia[0], puntoVia[1], puntoVia[2], b.x, b.y, b.z || 0];
    f.viaje = dur;
  }
  function ondaGlobal(color, fuerza, origen, dur, deFondo) {
    const ahora = performance.now();
    const o = actividad.onda;
    if (!origen && o && o.origen && !o.deFondo && ahora - o.t0 < 700) return;
    const onda = { c: hexARgb(color), fuerza, t0: ahora, x: giro.cx, y: giro.cy, z: 0, alcance: giro.R * 1.35, dur: dur || 1800, origen: null, deFondo: !!deFondo };
    if (origen && cerebro) {
      const l = typeof origen === 'string' ? cerebro.lobulos.find(v => v.id === origen) : null;
      const p = l ? [l.wx, l.wy, 0] : Array.isArray(origen) ? origen : null;
      if (p) {
        onda.x = p[0];
        onda.y = p[1];
        onda.z = p[2] || 0;
        onda.alcance = giro.R * 1.55;
        onda.dur = dur || 2300;
        onda.origen = origen;
      }
    }
    actividad.onda = onda;
    programarCuadro();
  }

  const ANTICIPA = 160;
  const DUR_CHOQUE = 1300;
  const ANCHO_CHOQUE = 30;
  const ANCHO_CORTINA = 70;
  const EMPUJE = 14;
  const DIR_BARRIDO = [0.96, 0.28, 0];
  const bufChoque = new Float32Array(CHOQUES * 4);
  const bufChoqueF = new Float32Array(CHOQUES * 4);
  const EMP = [0, 0, 0];
  const gestoPosible = () => !!cerebro && completo() && graficoListo && estado.vista === 'grafo';
  const elastico = t => t >= 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * TAU / 3) + 1;

  function choque(n, color, fuerza) {
    if (!n || !n._visible) return;
    choqueEn(n.x, n.y, n.z || 0, color, fuerza, n);
  }

  function choqueLobulo(id, color, fuerza) {
    const l = cerebro ? cerebro.lobulos.find(x => x.id === id) : null;
    if (l) choqueEn(l.wx, l.wy, 0, color, fuerza, null);
  }

  function choqueEn(x, y, z, color, fuerza, n) {
    if (!gestoPosible()) return;
    const ahora = performance.now();
    const L = gestos.choques;
    const alcance = giro.R * (0.4 + 0.5 * Math.min(1.2, fuerza));
    const igual = L.find(c => ahora - c.t0 < 250 && (n ? c.n === n : Math.abs(c.x - x) + Math.abs(c.y - y) + Math.abs(c.z - z) < 1));
    if (igual) {
      igual.c = hexARgb(color);
      if (fuerza > igual.fuerza) {
        igual.fuerza = fuerza;
        igual.alcance = alcance;
        if (n) n._choqueF = fuerza;
      }
      return;
    }
    if (L.length >= CHOQUES) {
      if (ahora - L[0].t0 < 250) return;
      L.shift();
    }
    L.push({ n: n || null, x, y, z, c: hexARgb(color), fuerza, alcance, r0: 34 * cerebro.S, t0: ahora, r: 0, f: 0 });
    if (n) {
      n._choque = ahora;
      n._choqueF = fuerza;
    }
    gestos.t = -1;
    anim.escenaHasta = Math.max(anim.escenaHasta, ahora + ANTICIPA + DUR_CHOQUE + 80);
    programarCuadro();
  }

  function escalaChoque(n, ahora) {
    const e = ahora - n._choque;
    const f = Math.min(1.2, n._choqueF || 1);
    if (e < 0) return 1;
    if (e < ANTICIPA) return 1 - 0.15 * f * seno(e / ANTICIPA);
    const s = e - ANTICIPA;
    if (s < 200) return 1 - 0.15 * f + 0.45 * f * sale3(s / 200);
    const u = (s - 200) / 700;
    if (u >= 1) {
      n._choque = 0;
      return 1;
    }
    return 1 + 0.3 * f * (1 - u) * Math.exp(-2.5 * u) * Math.cos(2.2 * Math.PI * u);
  }

  function apretar(tipo, fuerza) {
    if (!gestoPosible()) return;
    const ahora = performance.now();
    gestos.apreton = { tipo, fuerza: fuerza || 1, t0: ahora, dur: tipo === 'suspiro' ? 2000 : 1850 };
    gestos.t = -1;
    anim.escenaHasta = Math.max(anim.escenaHasta, ahora + gestos.apreton.dur + 60);
    programarCuadro();
  }

  function curvaApreton(a, e) {
    if (a.tipo === 'suspiro') {
      const u = e / a.dur;
      return u < 0.12 ? seno(u / 0.12) : 1 - seno((u - 0.12) / 0.88);
    }
    if (e < 150) return -0.3 * seno(e / 150);
    if (e < 750) return -0.3 + 1.3 * sale3((e - 150) / 600);
    return 1 - elastico((e - 750) / 1100);
  }

  function barrido(color, desde) {
    if (!gestoPosible()) return;
    const ahora = performance.now();
    const [nx, ny, nz] = DIR_BARRIDO;
    const c0 = giro.cx * nx + giro.cy * ny;
    gestos.barrido = { c: hexARgb(color), hex: color, t0: ahora, dur: 1700, nx, ny, nz, desde: c0 - giro.R * 1.12, hasta: c0 + giro.R * 1.12, pos: c0 - giro.R * 1.12, a: 0 };
    gestos.t = -1;
    anim.escenaHasta = Math.max(anim.escenaHasta, ahora + 1760);
    if (desde && desde._visible) chispasDesde(desde, color, 30);
    programarCuadro();
  }

  function chispasDesde(n, color, cuantas) {
    const px = cerebro.px;
    const ady = cerebro.ady;
    if (!px || !ady) return;
    const x = n.x;
    const y = n.y;
    const z = n.z || 0;
    const tope = (260 * cerebro.S) ** 2;
    const cerca = [];
    for (let i = 0; i < px.length; i++) {
      if (!ady[i].length) continue;
      const p = px[i];
      const d = (p.x - x) ** 2 + (p.y - y) ** 2 + (p.z - z) ** 2;
      if (d < tope) cerca.push([d, i]);
    }
    cerca.sort((a, b) => a[0] - b[0]);
    const lista = cerca.slice(0, cuantas * 2);
    const ahora = performance.now();
    for (let k = 0; k < cuantas && lista.length && vida.chispas.length < 200; k++) {
      const i = lista.splice(Math.floor(Math.random() * lista.length), 1)[0][1];
      let b = ady[i][0];
      let lejos = -1;
      for (const j of ady[i]) {
        const q = px[j];
        const d = (q.x - x) ** 2 + (q.y - y) ** 2 + (q.z - z) ** 2;
        if (d > lejos) {
          lejos = d;
          b = j;
        }
      }
      vida.chispas.push({ a: i, b, t0: ahora + Math.random() * 90, color, saltos: 0, max: 3 + Math.floor(Math.random() * 4) });
    }
    asegurarVida();
  }

  function actualizarGestos(ahora) {
    if (gestos.t === ahora) return gestos;
    gestos.t = ahora;
    const L = gestos.choques;
    for (let i = L.length - 1; i >= 0; i--) if (ahora - L[i].t0 >= ANTICIPA + DUR_CHOQUE) L.splice(i, 1);
    for (const c of L) {
      const e = Math.max(0, ahora - c.t0);
      if (e < ANTICIPA) {
        c.r = c.r0;
        c.f = -0.3 * c.fuerza * Math.sin(Math.PI * e / ANTICIPA);
      } else {
        const s = e - ANTICIPA;
        const u = s / DUR_CHOQUE;
        c.r = c.r0 + (c.alcance - c.r0) * sale3(u);
        c.f = c.fuerza * sale3(Math.min(1, s / 60)) * (Math.pow(1 - u, 1.5) + 0.4 * Math.sin(s * 0.02) * Math.exp(-s / 400));
      }
    }
    gestos.contraer = 0;
    gestos.suspiro = 0;
    const a = gestos.apreton;
    if (a) {
      const e = ahora - a.t0;
      if (e >= a.dur) gestos.apreton = null;
      else {
        const v = curvaApreton(a, Math.max(0, e));
        const suspira = a.tipo === 'suspiro';
        gestos.contraer = 0.07 * a.fuerza * (suspira ? 0.25 : 1) * v;
        if (suspira) gestos.suspiro = v * Math.min(1, a.fuerza);
      }
    }
    const b = gestos.barrido;
    if (b) {
      const q = (ahora - b.t0) / b.dur;
      if (q >= 1) gestos.barrido = null;
      else {
        const u = Math.max(0, q);
        b.pos = b.desde + (b.hasta - b.desde) * seno(u);
        b.a = Math.min(1, u / 0.1, (1 - u) / 0.3);
      }
    }
    gestos.hay = !!(L.length || gestos.contraer || gestos.barrido);
    return gestos;
  }

  function empujar(x, y, z) {
    let mx = 0;
    let my = 0;
    let mz = 0;
    const S = cerebro.S;
    const w = ANCHO_CHOQUE * S;
    const amp = EMPUJE * S;
    const ct = Math.cos(giro.tilt);
    const ex = -Math.sin(giro.ang) * ct;
    const ey = Math.sin(giro.tilt);
    const ez = Math.cos(giro.ang) * ct;
    for (const c of gestos.choques) {
      let dx = x - c.x;
      let dy = y - c.y;
      let dz = z - c.z;
      const h = dx * ex + dy * ey + dz * ez;
      dx -= ex * h;
      dy -= ey * h;
      dz -= ez * h;
      const l = Math.hypot(dx, dy, dz);
      const u = (l - c.r) / w;
      const k = (Math.exp(-u * u) - 0.4 * Math.exp(-(u + 1.7) * (u + 1.7))) * c.f * amp / Math.max(l, 1);
      mx += dx * k;
      my += dy * k;
      mz += dz * k;
    }
    const b = gestos.barrido;
    if (b && b.a > 0) {
      const u = (x * b.nx + y * b.ny + z * b.nz - b.pos) / (ANCHO_CORTINA * S);
      const k = Math.exp(-u * u) * b.a * 0.85 * amp * 0.45;
      mx += b.nx * k;
      my += b.ny * k;
      mz += b.nz * k;
    }
    const c = gestos.contraer;
    if (c) {
      mx += (giro.cx - x) * c;
      my += (giro.cy - y) * c;
      mz -= z * c;
    }
    EMP[0] = x + mx;
    EMP[1] = y + my;
    EMP[2] = z + mz;
    return EMP;
  }

  function cortinaEn(n) {
    const b = gestos.barrido;
    if (!b || b.a <= 0 || !cerebro) return 0;
    const u = (n.x * b.nx + n.y * b.ny + (n.z || 0) * b.nz - b.pos) / (ANCHO_CORTINA * cerebro.S);
    return Math.exp(-u * u) * b.a * 0.85;
  }

  const rgbFoco = new Map();
  function estadoActividad(ahora) {
    bufFoco.fill(0);
    bufFocoCol.fill(0);
    actividad.focos = actividad.focos.filter(f => ahora - f.t0 < f.dur);
    let energia = 0;
    const fv = cerebro && completo() ? fundidoIntro(INTRO.clima + 600, 900, ahora) : 0;
    const tope = neuronasGL ? neuronasGL.focos : 12;
    const nVida = fv > 0 ? vida.focos.length : 0;
    const nAct = Math.min(actividad.focos.length, Math.max(6, tope - nVida));
    const salta = actividad.focos.length - nAct;
    actividad.focos.forEach((f, j) => {
      const edad = ahora - f.t0;
      const sube = Math.min(1, edad / 180);
      const baja = Math.exp(-Math.max(0, edad - 180) / (f.dur * 0.35));
      energia += f.fuerza * sube * baja;
      if (j < salta) return;
      const i = j - salta;
      const r = f.ruta;
      if (r) {
        const u = sale3(Math.min(1, edad / f.viaje));
        bufFoco.set([puntoCurva(r[0], r[3], r[6], u), puntoCurva(r[1], r[4], r[7], u), puntoCurva(r[2], r[5], r[8], u), f.radio], i * 4);
      } else bufFoco.set([f.x, f.y, f.z, f.radio], i * 4);
      bufFocoCol.set([f.c[0], f.c[1], f.c[2], f.fuerza * sube * baja], i * 4);
    });
    if (fv > 0) {
      for (let j = 0, i = nAct; j < vida.focos.length && i < tope; j++, i++) {
        const v = vida.focos[j];
        let c = rgbFoco.get(v.color);
        if (!c) rgbFoco.set(v.color, c = hexARgb(v.color));
        bufFoco.set([v.x, v.y, v.z, 110 * cerebro.S], i * 4);
        bufFocoCol.set([c[0], c[1], c[2], (v.fuerza || 0.2) * fv], i * 4);
        energia += (v.fuerza || 0.2) * fv;
      }
    }
    bufOnda.fill(0);
    bufOndaCol.fill(0);
    const o = actividad.onda;
    if (o) {
      const edad = ahora - o.t0;
      if (edad > o.dur) actividad.onda = null;
      else {
        const q = edad / o.dur;
        bufOnda.set([o.x, o.y, o.z, o.alcance * q]);
        bufOndaCol.set([o.c[0], o.c[1], o.c[2], o.fuerza * (1 - q)]);
        energia += o.fuerza * (1 - q);
      }
    }
    bufHuella.fill(0);
    bufHuellaCol.fill(0);
    if (cerebro) {
      const radio = 170 * cerebro.S;
      let k = 0;
      for (const n of brasas.lista) {
        const b = n._brasa;
        if (!b) continue;
        const f = 0.85 * (1 - Math.exp(-0.55 * calorBrasa(b, ahora)));
        if (f < 0.01) continue;
        bufHuella[k * 4] = n.x;
        bufHuella[k * 4 + 1] = n.y;
        bufHuella[k * 4 + 2] = n.z || 0;
        bufHuella[k * 4 + 3] = radio;
        bufHuellaCol[k * 4] = b.c[0];
        bufHuellaCol[k * 4 + 1] = b.c[1];
        bufHuellaCol[k * 4 + 2] = b.c[2];
        bufHuellaCol[k * 4 + 3] = f;
        k++;
      }
    }
    actualizarGestos(ahora);
    bufChoque.fill(0);
    bufChoqueF.fill(0);
    gestos.choques.forEach((c, i) => {
      bufChoque[i * 4] = c.x;
      bufChoque[i * 4 + 1] = c.y;
      bufChoque[i * 4 + 2] = c.z;
      bufChoque[i * 4 + 3] = Math.max(1, c.r);
      bufChoqueF[i * 4] = c.c[0];
      bufChoqueF[i * 4 + 1] = c.c[1];
      bufChoqueF[i * 4 + 2] = c.c[2];
      bufChoqueF[i * 4 + 3] = c.f;
      energia += Math.abs(c.f) * 0.5;
    });
    if (gestos.barrido) energia += gestos.barrido.a * 0.6;
    return { focos: bufFoco, colores: bufFocoCol, onda: bufOnda, ondaCol: bufOndaCol, huellas: bufHuella, huellasCol: bufHuellaCol, choques: bufChoque, choquesF: bufChoqueF, energia };
  }

  const vida = { chispas: [], focos: [], efecto: null, extra: 0 };
  function asegurarVida() {
    if (!cerebro || !cerebro.vecinos.length || !completo() || !graficoListo || estado.vista !== 'grafo') return;
    if (!vida.efecto || !anim.efectos.includes(vida.efecto)) {
      vida.efecto = { tipo: 'vida', t0: performance.now(), dur: 1e12 };
      anim.efectos.push(vida.efecto);
      programarCuadro();
    }
  }
  DIBUJO_EFECTO.vida = e => {
    if (!completo() || !cerebro) { e.dur = 1e-6; return; }
    const ahora = performance.now();
    const dt = Math.min(100, ahora - (e.tPrev || ahora));
    e.tPrev = ahora;
    if (tiempoIntro(ahora) < INTRO.clima + 300) return;
    const px = cerebro.px;
    const pares = cerebro.vecinos;
    if (vida.chispas.length < 90 + 50 * vida.extra && Math.random() < dt * (1 + 2.5 * vida.extra) / (240 * (1 + 0.8 * ritmo.sueno))) {
      const par = pares[Math.floor(Math.random() * pares.length)];
      vida.chispas.push({ a: par[0], b: par[1], t0: ahora, color: px[par[0]].c, saltos: 0, max: 3 + Math.floor(Math.random() * 4) });
    }
    for (const foco of vida.focos) {
      if (vida.chispas.length >= 160 || Math.random() > dt / foco.cada) continue;
      for (let i = 0; i < 18; i++) {
        const par = pares[Math.floor(Math.random() * pares.length)];
        const A = px[par[0]];
        if ((A.x - foco.x) ** 2 + (A.y - foco.y) ** 2 < foco.r2) {
          vida.chispas.push({ a: par[0], b: par[1], t0: ahora, color: foco.color, saltos: 0, max: 6 });
          break;
        }
      }
    }
    const tr = transformacion;
    const nuevas = [];
    const empuja = gestos.hay && !!neuronasGL;
    const ver = q => empuja ? (empujar(q.x, q.y, q.z), proyectar(EMP[0], EMP[1], EMP[2])) : proyectar(q.x, q.y, q.z);
    vida.chispas = vida.chispas.filter(s => {
      const p = (ahora - s.t0) / 460;
      if (p < 0) return true;
      if (p >= 1) {
        const sig = cerebro.ady[s.b];
        if (s.saltos < s.max && sig.length && Math.random() < 0.82) {
          nuevas.push({ a: s.b, b: sig[Math.floor(Math.random() * sig.length)], t0: ahora, color: s.color, saltos: s.saltos + 1, max: s.max });
        }
        return false;
      }
      const pa = ver(px[s.a]);
      const pb = ver(px[s.b]);
      const ax = pa.x * tr.k + tr.x;
      const ay = pa.y * tr.k + tr.y;
      const x = ax + (pb.x - pa.x) * p * tr.k;
      const y = ay + (pb.y - pa.y) * p * tr.k;
      const luz = (1 - s.saltos / (s.max + 1)) * (0.35 + 0.65 * limitar((pa.d + giro.R) / (2 * giro.R)));
      pctx.globalAlpha = 0.8 * luz;
      pctx.strokeStyle = s.color;
      pctx.lineWidth = 1.6;
      pctx.beginPath();
      pctx.moveTo(ax, ay);
      pctx.lineTo(x, y);
      pctx.stroke();
      if (/^#[0-9a-f]{6}$/i.test(s.color)) {
        pctx.globalAlpha = luz * (anim.oscuro ? 1 : 0.6);
        pctx.drawImage(sprite(s.color, 'brillo'), x - 9, y - 9, 18, 18);
      }
      pctx.globalAlpha = luz;
      pctx.fillStyle = '#ffffff';
      pctx.beginPath();
      pctx.arc(x, y, 1.7, 0, TAU);
      pctx.fill();
      return true;
    });
    vida.chispas.push(...nuevas);
  };

  lienzo.addEventListener('contextmenu', ev => { if (neuronasGL) ev.preventDefault(); });
  lienzo.addEventListener('pointerdown', ev => {
    if (!neuronasGL || !cerebro || !completo() || ev.button !== 0 || ev.shiftKey || ev.pointerType === 'touch') return;
    const r = lienzo.getBoundingClientRect();
    if (nodoEn(ev.clientX - r.left, ev.clientY - r.top)) return;
    giro.arrastre = { x: ev.clientX, y: ev.clientY, t: performance.now(), v: 0, vy: 0, id: ev.pointerId };
    giro.inercia = 0;
    giro.inerciaV = 0;
    camara.toque = giro.arrastre.t;
    try { lienzo.setPointerCapture(ev.pointerId); } catch (e) {}
    lienzo.style.cursor = 'grabbing';
    programarCuadro();
  });
  lienzo.addEventListener('pointermove', ev => {
    const a = giro.arrastre;
    if (!a || ev.pointerId !== a.id || !completo()) return;
    const ahora = performance.now();
    const d = (ev.clientX - a.x) * 0.0065;
    const dt = Math.max(1, ahora - a.t);
    const paso = -(ev.clientY - a.y) * 0.0065;
    let dv;
    if (estado.seleccionado) {
      const antes = giro.tilt;
      giro.tilt = topeInclina(antes + paso);
      dv = giro.tilt - antes;
    } else {
      const antes = giro.inclina;
      giro.inclina = topeInclina(antes + paso);
      dv = giro.inclina - antes;
      giro.tilt = topeInclina(giro.tilt + dv);
    }
    giro.tiltFondo += dv;
    a.v = a.v * 0.6 + (d / dt) * 0.4;
    a.vy = a.vy * 0.6 + (dv / dt) * 0.4;
    a.x = ev.clientX;
    a.y = ev.clientY;
    a.t = ahora;
    giro.ang += d;
    programarCuadro();
  });
  const soltarGiro = ev => {
    const a = giro.arrastre;
    if (!a || ev.pointerId !== a.id) return;
    giro.arrastre = null;
    camara.toque = performance.now();
    if (performance.now() - a.t < 90 && Math.abs(a.v) > giro.vel) {
      giro.inercia = Math.max(-0.006, Math.min(0.006, a.v));
      giro.dir = Math.sign(a.v);
    }
    if (performance.now() - a.t < 90 && Math.abs(a.vy) > giro.vel) giro.inerciaV = Math.max(-0.003, Math.min(0.003, a.vy));
    if (!giro.inerciaV) guardarInclina();
    try { lienzo.releasePointerCapture(ev.pointerId); } catch (e) {}
    lienzo.style.cursor = '';
    programarCuadro();
  };
  lienzo.addEventListener('pointerup', soltarGiro);
  lienzo.addEventListener('pointercancel', soltarGiro);
  lienzo.addEventListener('dblclick', ev => {
    if (!neuronasGL || !cerebro) return;
    const r = lienzo.getBoundingClientRect();
    if (nodoEn(ev.clientX - r.left, ev.clientY - r.top)) return;
    giro.inclina = 0;
    giro.inerciaV = 0;
    guardarInclina();
    camara.toque = performance.now();
    programarCuadro();
  });
  const botonGirar = document.getElementById('girar');
  const TEXTO_CAMARA = {
    seguir: ['Seguir', 'Sigue la acción: cuando Claude trabaja y no tocaste nada por 15 s, gira hacia su nota, se acerca y la enfoca. Clic: que solo gire'],
    girar: ['Girar', 'Gira solo, sin seguir a Claude. Clic: dejarlo quieto'],
    quieto: ['Quieto', 'Quieto: no gira solo. Clic: que siga la acción']
  };
  function pintarBotonCamara() {
    camara.filmando = camara.activo;
    if (!botonGirar) return;
    const [texto, ayuda] = TEXTO_CAMARA[camara.modo];
    botonGirar.textContent = texto;
    botonGirar.title = camara.activo ? 'Filmando: sigue a Claude. Si tocás el cerebro, te devuelve el control. Clic: que solo gire' : ayuda;
    botonGirar.setAttribute('aria-label', 'Cámara: ' + texto.toLowerCase());
    botonGirar.setAttribute('aria-pressed', String(giro.activo));
    botonGirar.dataset.modo = camara.modo;
    botonGirar.classList.toggle('filmando', camara.activo);
  }
  if (botonGirar) {
    pintarBotonCamara();
    botonGirar.addEventListener('click', () => {
      camara.modo = MODOS_CAMARA[(MODOS_CAMARA.indexOf(camara.modo) + 1) % MODOS_CAMARA.length];
      giro.activo = camara.modo !== 'quieto';
      pintarBotonCamara();
      try { localStorage.setItem('cerebro-giro', camara.modo); } catch (e) {}
      programarCuadro();
    });
  }

  function prepararPosiciones() {
    armarCerebro();
    grupos.forEach(g => {
      const a = cerebro.anclas[g.id] || cerebro.porDefecto;
      g.ax = a[0];
      g.ay = a[1];
      g._rx = a[2];
      g._ry = a[3];
    });
    nodos.forEach(n => {
      const g = grupoPorId.get(n.grupo);
      const azar = azarConSemilla(hashTexto(n.id));
      let tx = g.ax;
      let ty = g.ay;
      for (let i = 0; i < 40; i++) {
        const ang = azar() * TAU;
        const d = Math.sqrt(azar());
        const x = g.ax + Math.cos(ang) * d * g._rx;
        const y = g.ay + Math.sin(ang) * d * g._ry;
        if (ctxForma.isPointInPath(cerebro.todo, x, y)) { tx = x; ty = y; break; }
      }
      n._tx = tx;
      n._ty = ty;
      n.x = tx;
      n.y = ty;
      const w = cerebro.anchoMundo(tx, ty);
      const piso = ctxForma.isPointInPath(cerebro.cuerpo, tx, ty) ? Math.min(w * 0.85, cerebro.grieta * 1.8) : 0;
      n.z = (azar() < 0.5 ? -1 : 1) * Math.max(piso, w * (0.3 + 0.55 * azar()));
    });
  }

  function actualizarSimulacion(calor) {
    if (!sim) return;
    sim.nodes(nodosVisibles);
    fuerzaEnlaces.links(aristasFuerza);
    sim.alpha(Math.max(sim.alpha(), calor == null ? 0.3 : calor)).restart();
  }

  function anchoPanel() {
    return !esMovil() && panel.classList.contains('abierto') ? panel.offsetWidth : 0;
  }

  function encuadrar(animar) {
    if (!graficoListo || !nodosVisibles.length) return;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    nodosVisibles.forEach(n => {
      if (n.x < x0) x0 = n.x;
      if (n.x > x1) x1 = n.x;
      if (n.y < y0) y0 = n.y;
      if (n.y > y1) y1 = n.y;
    });
    if (cerebro) {
      x0 = Math.min(x0, -440 * cerebro.S);
      x1 = Math.max(x1, 460 * cerebro.S);
      y0 = Math.min(y0, -300 * cerebro.S);
      y1 = Math.max(y1, 370 * cerebro.S);
    }
    const util = Math.max(120, ancho - anchoPanel());
    const lados = 44;
    const tapaTodo = presenta.cine ? null : vivo.tapaPanel;
    const tapaArriba = !!tapaTodo && tapaTodo[1] < alto * 0.2 && tapaTodo[0] > ancho * 0.15;
    const tapa = tapaArriba ? null : tapaTodo;
    const arriba = tapaArriba ? Math.max(Math.min(64, alto * 0.12), Math.min(tapaTodo[3] + 8, alto * 0.3)) : Math.min(64, alto * 0.12);
    const abajo = presenta.cine ? Math.min(130, alto * 0.16) : Math.min(52, alto * 0.1);
    const anchoM = Math.max(1, x1 - x0);
    const altoM = Math.max(1, y1 - y0);
    const panelAncho = tapa && tapa[2] - tapa[0] > ancho * 0.6;
    const encima = tapa && esMovil() && panelAncho && tapa[1] < alto - abajo ? Math.max(60, alto * 0.35, tapa[1] - arriba - 8) : 0;
    const altoUtil = Math.min(Math.max(60, alto - arriba - abajo), encima || Infinity);
    const kLleno = Math.min((util - lados * 2) / anchoM, altoUtil / altoM);
    let k = kLleno;
    let izq = lados;
    const yFondo = arriba + altoUtil / 2 + altoM * kLleno / 2;
    if (tapa && !encima && !(esMovil() && panelAncho) && tapa[1] < yFondo - 24 && tapa[2] + 16 > lados) {
      izq = tapa[2] + 16;
      k = Math.max(kLleno * 0.82, Math.min((util - lados - izq) / anchoM, altoUtil / altoM));
    }
    k = Math.max(0.08, Math.min(2.2, k));
    const anchoB = anchoM * k;
    let xIzq = (izq + util - lados) / 2 - anchoB / 2;
    if (xIzq + anchoB > util - lados) xIzq = util - lados - anchoB;
    if (xIzq < Math.min(lados, (util - anchoB) / 2)) xIzq = Math.min(lados, (util - anchoB) / 2);
    const t = D3.zoomIdentity.translate(xIzq - k * x0, arriba + altoUtil / 2 - k * (y0 + y1) / 2).scale(k);
    if (animar && anim.modo !== 'suave') seleccionLienzo.transition().duration(650).call(zoom.transform, t);
    else seleccionLienzo.call(zoom.transform, t);
  }

  let temporizadorEncuadre = null;
  function encuadrarLuego() {
    if (!graficoListo) return;
    clearTimeout(temporizadorEncuadre);
    temporizadorEncuadre = setTimeout(() => encuadrar(true), 450);
    sim.on('end.luego', () => {
      sim.on('end.luego', null);
      encuadrar(true);
    });
  }

  function cancelarEncuadre() {
    clearTimeout(temporizadorEncuadre);
    temporizadorEncuadre = null;
    if (sim) sim.on('end.luego', null);
  }

  function centrarEn(n) {
    if (!graficoListo) { centroPendiente = n; return 0; }
    const k = Math.max(transformacion.k, 1.3);
    const util = Math.max(120, ancho - anchoPanel());
    const p0 = proyectar(n.x, n.y, n.z || 0, 0, 0, 1);
    const t = D3.zoomIdentity.translate(util / 2 - k * p0.x, alto / 2 - k * p0.y).scale(k);
    let dur = 600;
    if (anim.modo === 'suave') dur = 0;
    else if (completo()) {
      const d = Math.hypot(util / 2 - (n.x * transformacion.k + transformacion.x), alto / 2 - (n.y * transformacion.k + transformacion.y));
      dur = Math.min(900, Math.max(350, 320 + d * 0.45));
    }
    if (dur) seleccionLienzo.transition().duration(dur).ease(D3.easeCubicInOut).call(zoom.transform, t);
    else seleccionLienzo.call(zoom.transform, t);
    return dur;
  }

  function iniciarGrafo() {
    if (sim || !window.d3 || typeof window.d3.forceSimulation !== 'function') return;
    D3 = window.d3;
    estado.d3 = true;
    mostrarAvisoLibs();
    document.querySelector('[data-vista="grafo"]').disabled = false;
    transformacion = D3.zoomIdentity;
    prepararPosiciones();

    fuerzaEnlaces = D3.forceLink()
      .distance(l => CLASES[l.clase].distancia * 1.6)
      .strength(l => 0.3 * CLASES[l.clase].fuerza / Math.max(1, Math.min(l.source._cuenta, l.target._cuenta)));

    sim = D3.forceSimulation()
      .randomSource(azarConSemilla(20260928))
      .velocityDecay(0.42)
      .alphaDecay(0.028)
      .alphaMin(0.002)
      .force('enlaces', fuerzaEnlaces)
      .force('carga', D3.forceManyBody().strength(n => n.tipo === 'handoff' ? -10 : -34 - 4 * Math.sqrt(n.grado)).distanceMax(320).theta(0.9))
      .force('choque', D3.forceCollide(n => n.r * 1.6 + 8).iterations(2))
      .force('x', D3.forceX(n => n._tx !== undefined ? n._tx : grupoPorId.get(n.grupo).ax).strength(n => n.tipo === 'handoff' ? 0.16 : 0.14))
      .force('y', D3.forceY(n => n._ty !== undefined ? n._ty : grupoPorId.get(n.grupo).ay).strength(n => n.tipo === 'handoff' ? 0.16 : 0.14))
      .force('cerebro', fuerzaCerebro())
      .stop();
    sim.nodes(nodosVisibles);
    fuerzaEnlaces.links(aristasFuerza);
    for (let i = 0; i < 90; i++) sim.tick();
    sim.on('tick', pedirDibujo);

    seleccionLienzo = D3.select(lienzo);
    zoom = D3.zoom()
      .scaleExtent([0.06, 7])
      .filter(ev => {
        if (ev.type === 'wheel' || String(ev.type).startsWith('touch')) return true;
        if (ev.type === 'dblclick') return false;
        return ev.button === 1 || ev.button === 2 || (ev.button === 0 && (ev.shiftKey || !neuronasGL));
      })
      .on('zoom', ev => {
        transformacion = ev.transform;
        if (ev.sourceEvent) {
          usuarioMovio = true;
          camara.toque = performance.now();
          cancelarEncuadre();
          clearTimeout(anim.tDisparo);
          clearTimeout(anim.tHover);
        }
        ocultarTooltip();
        pedirDibujo();
      });

    let movido = false;
    const arrastre = D3.drag()
      .container(lienzo)
      .subject(ev => {
        const n = nodoEn(ev.x, ev.y);
        return n ? { nodo: n, x: n._sx, y: n._sy } : null;
      })
      .on('start', ev => {
        movido = false;
        cursorNota = null;
        arrastrando = ev.subject.nodo;
        cancelarEncuadre();
        clearTimeout(anim.tHover);
        ocultarTooltip();
      })
      .on('drag', ev => {
        const n = ev.subject.nodo;
        if (!movido) {
          movido = true;
          usuarioMovio = true;
          sim.alphaTarget(0.25).restart();
        }
        cursorNota = [ev.x, ev.y];
        const q = desproyectar(transformacion.invertX(ev.x), transformacion.invertY(ev.y), n.z || 0);
        n.fx = q[0];
        n.fy = q[1];
        pedirDibujo();
      })
      .on('end', ev => {
        const n = ev.subject.nodo;
        if (movido) sim.alphaTarget(0);
        n.fx = null;
        n.fy = null;
        cursorNota = null;
        arrastrando = null;
        pedirDibujo();
      });

    seleccionLienzo.call(arrastre).call(zoom).on('dblclick.zoom', null);

    lienzo.addEventListener('mousemove', ev => {
      if (arrastrando) return;
      const r = lienzo.getBoundingClientRect();
      const n = nodoEn(ev.clientX - r.left, ev.clientY - r.top);
      if (n !== estado.hover) {
        estado.hover = n;
        lienzo.style.cursor = n ? 'pointer' : '';
        clearTimeout(anim.tHover);
        if (n && completo() && anim.nivel === 2) anim.tHover = setTimeout(() => chispa(n), 160);
        pedirDibujo();
      }
      mostrarTooltip(n, ev);
    });
    lienzo.addEventListener('mouseleave', () => {
      clearTimeout(anim.tHover);
      estado.hover = null;
      ocultarTooltip();
      pedirDibujo();
    });
    lienzo.addEventListener('click', ev => {
      const r = lienzo.getBoundingClientRect();
      const n = nodoEn(ev.clientX - r.left, ev.clientY - r.top);
      if (n) irA(n.id, false);
      else cerrarPanel();
    });

    const zoomBoton = f => {
      cancelarEncuadre();
      camara.toque = performance.now();
      if (anim.modo === 'suave') seleccionLienzo.call(zoom.scaleBy, f);
      else seleccionLienzo.transition().duration(220).call(zoom.scaleBy, f);
    };
    $('#zoom-mas').addEventListener('click', () => zoomBoton(1.4));
    $('#zoom-menos').addEventListener('click', () => zoomBoton(1 / 1.4));
    $('#encuadrar').addEventListener('click', () => { cancelarEncuadre(); camara.toque = performance.now(); encuadrar(true); });
    $('#reacomodar').addEventListener('click', () => { sim.alpha(0.7).restart(); });

    graficoListo = true;
    $('#estado-grafo').hidden = true;
    $('#estado-grafo').classList.remove('error');
    $('#controles-grafo').hidden = estado.vista !== 'grafo';
    encuadrar(false);
    sim.on('end.encuadre', () => {
      sim.on('end.encuadre', null);
      if (!usuarioMovio && !centroPendiente && !estado.seleccionado) encuadrar(true);
    });
    sim.alpha(Math.max(sim.alpha(), 0.12)).restart();
    anim.tsListo = performance.now();
    let conIntro = false;
    if (completo() && estado.vista === 'grafo') {
      const ahora = performance.now();
      conIntro = !!(neuronasGL && cerebro && cerebro.gl && cerebro.nido) && anim.nivel === 2;
      if (conIntro) {
        cerebro.introT0 = ahora;
        cerebro.introPaso = 0;
        anim.efectos.push({ tipo: 'intro', t0: ahora, dur: INTRO.explota + 650 });
        nacerPorLobulos(ahora + INTRO.clima);
        anim.encendido = ahora + INTRO.nombres - 850;
        anim.escenaHasta = ahora + INTRO.fin + 100;
      } else {
        const t0 = ahora + 60;
        let i = 0;
        porImportancia.forEach(n => { if (n._visible && n.tipo !== 'handoff') n._nace = t0 + Math.min(500, i++ * 4); });
        const hand = nodosVisibles.filter(n => n.tipo === 'handoff').sort((a, b) => a.modificado.localeCompare(b.modificado));
        hand.forEach((n, j) => { n._nace = t0 + 550 + Math.round(j * 350 / Math.max(1, hand.length - 1)); });
        anim.encendido = t0;
        anim.escenaHasta = t0 + 1300;
      }
      const sel = centroPendiente || estado.seleccionado;
      if (sel) sel._nace = 0;
    } else if (anim.modo === 'suave' && estado.vista === 'grafo' && lienzo.animate) {
      lienzo.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 200, easing: 'ease-out' });
    }
    if (centroPendiente) {
      const n = centroPendiente;
      centroPendiente = null;
      const dur = centrarEn(n);
      if (completo()) anim.tDisparo = setTimeout(() => disparar(n), Math.max(dur, conIntro ? INTRO.fin : 1300) + 20);
    }
    pedirDibujo();
    programarAmbiente(2500);
    setTimeout(mostrarVisita, conIntro ? INTRO.fin + 300 : 1200);
  }

  function sinGrafo() {
    if (graficoListo) return;
    estado.d3 = false;
    const e = $('#estado-grafo');
    e.textContent = 'No se pudo cargar d3, así que el grafo no está disponible. La lista y el detalle de cada nota funcionan igual.';
    e.classList.add('error');
    mostrarAvisoLibs();
    document.querySelector('[data-vista="grafo"]').disabled = true;
    cambiarVista('lista', true);
  }

  function mostrarVisita() {
    if (presenta.cine || presenta.anonimo || DATOS.compartido === true || !nodos.length) return;
    try {
      if (localStorage.getItem('cerebro-visita')) return;
      localStorage.setItem('cerebro-visita', '1');
    } catch (e) { return; }
    const items = ['<li><b>Las figuras con nombre son tus notas.</b> Tocá una para leerla.</li>'];
    if (!$('#en-vivo').hidden) items.push('<li><b>«Ahora»</b>, abajo a la izquierda, muestra lo que hace Claude. Tocá <b>Probar</b> para ver cómo se ve.</li>');
    items.push('<li><b>«' + esc($('#ir-salud').textContent) + '»</b>, arriba, es lo que dice el médico de la memoria. <b>?</b> explica todo lo demás.</li>');
    $('#visita-lista').innerHTML = items.join('');
    $('#visita').hidden = false;
  }

  function mostrarAvisoLibs() {
    const partes = [];
    if (estado.d3 === false) partes.push('d3 (el grafo)');
    if (estado.markedOk === false) partes.push('marked (el formato de las notas)');
    const caja = $('#aviso-libs');
    if (!partes.length) { caja.hidden = true; return; }
    caja.hidden = false;
    caja.textContent = 'No pude cargar ' + partes.join(' ni ') + ' desde internet. ¿Estás sin conexión? Todo lo demás funciona; volvé a abrir la página cuando tengas red.';
  }

  function d3Completo() {
    const d = window.d3;
    return !!(d && USA_D3.every(f => d[f]) && d.selection && typeof d.selection.prototype.transition === 'function');
  }

  async function cargarD3(alCargar) {
    if (!d3Completo()) {
      for (const url of URLS_D3) {
        if (!await cargarScript(url, () => {})) return false;
      }
    }
    if (!d3Completo()) return false;
    alCargar();
    return true;
  }

  function cargarScript(url, alCargar) {
    const yaEsta = url === URL_MARKED ? !!window.marked : false;
    if (yaEsta) return new Promise(resolver => setTimeout(() => { alCargar(); resolver(true); }, 0));
    return new Promise(resolver => {
      let listo = false;
      const fin = ok => { if (!listo) { listo = true; resolver(ok); } };
      const s = document.createElement('script');
      if (INTEGRIDAD[url]) {
        s.integrity = INTEGRIDAD[url];
        s.crossOrigin = 'anonymous';
      }
      s.src = url;
      s.async = true;
      s.onload = () => { fin(true); alCargar(); };
      s.onerror = () => fin(false);
      setTimeout(() => fin(false), ESPERA_LIBS);
      document.head.appendChild(s);
    });
  }

  function alCambiarTema() {
    const oscuro = temaEfectivo() === 'dark';
    const boton = $('#alternar-tema');
    boton.innerHTML = oscuro
      ? '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" style="fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M4.6 4.6l1.6 1.6M17.8 17.8l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.6 19.4l1.6-1.6M17.8 6.2l1.6-1.6"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" style="fill:none;stroke:currentColor;stroke-width:2;stroke-linejoin:round"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5z"/></svg>';
    boton.title = oscuro ? 'Pasar a tema claro' : 'Pasar a tema oscuro';
    anim.oscuro = oscuro;
    anim.sprites.clear();
    leerColores();
    pedirDibujo();
  }

  function temaEfectivo() {
    const t = document.documentElement.getAttribute('data-theme');
    if (t === 'light' || t === 'dark') return t;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function leerHash() {
    const m = /^#n=(.+)$/.exec(location.hash || '');
    if (!m) return null;
    try { return decodeURIComponent(m[1]); } catch (e) { return null; }
  }

  const NO_ESCRIBIBLES = new Set(['checkbox', 'radio', 'button', 'submit', 'reset', 'range', 'color']);
  const esCampo = el => el && ((el.tagName === 'INPUT' && !NO_ESCRIBIBLES.has(el.type)) || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT' || el.isContentEditable);

  function olvidarTextos() {
    nodos.forEach(n => { n._etq = null; n._w = 0; n._wf = 0; });
    grupos.forEach(g => { g._cartel = null; g._wc = 0; });
    if (cerebro) cerebro.rotulos = null;
    tooltip._nodo = null;
    anim.efectos = anim.efectos.filter(e => e.tipo !== 'satelite' && e.tipo !== 'cartelSueno');
    pedirDibujo();
  }

  function guardarPresenta(clave, activo) {
    try { localStorage.setItem(clave, activo ? 'si' : 'no'); } catch (e) {}
  }

  function ponerCine(activo, guardar, pantalla) {
    presenta.cine = activo;
    document.body.classList.toggle('cine', activo);
    escalaTexto = activo ? 1.4 : 1;
    FUENTE_ROTULO = '600 ' + +(11 * escalaTexto).toFixed(1) + LETRA;
    FUENTE_TOQUES = '500 ' + +(10 * escalaTexto).toFixed(1) + LETRA;
    FUENTE_CARTEL = '650 ' + +(12 * escalaTexto).toFixed(1) + LETRA;
    if (activo) {
      cerrarPanel();
      ocultarTooltip();
      if (lateral.classList.contains('abierto')) cerrarLateral();
      if (estado.vista !== 'grafo') cambiarVista('grafo', true);
      if (pantalla && document.fullscreenEnabled && !document.fullscreenElement) {
        try {
          const p = document.documentElement.requestFullscreen();
          presenta.pantalla = true;
          if (p && p.catch) p.catch(() => { presenta.pantalla = false; });
        } catch (e) { presenta.pantalla = false; }
      }
    } else {
      if (vivo.apagarZocalo) vivo.apagarZocalo();
      if (document.fullscreenElement && presenta.pantalla) {
        presenta.pantalla = false;
        try { const p = document.exitFullscreen(); if (p && p.catch) p.catch(() => {}); } catch (e) {}
      }
    }
    if (guardar) guardarPresenta('cerebro-cine', activo);
    olvidarTextos();
    ajustarLienzo();
    if (!introCorriendo() && !estado.seleccionado) {
      cancelarEncuadre();
      encuadrar(true);
    }
    if (guardar && activo) aviso('Modo cine: Esc sale y A pone los nombres genéricos.');
  }

  function ponerAnonimo(activo, guardar) {
    if (!activo && DATOS.compartido === true) return;
    presenta.anonimo = activo;
    document.body.classList.toggle('anonimo', activo);
    $('#marca-anonimo').hidden = !activo;
    buscador.disabled = activo;
    buscador.placeholder = activo ? 'Apagado en modo anónimo' : 'Buscá una nota…';
    document.querySelectorAll('[data-vista="lista"]').forEach(b => { b.disabled = activo; });
    const irSalud = $('#ir-salud');
    if (irSalud) {
      irSalud.disabled = activo;
      irSalud.title = activo ? 'Apagado en modo anónimo' : 'Ver el panel de salud: lo que encontró el médico de la memoria';
    }
    if (activo) {
      if (buscador.value) { buscador.value = ''; actualizarBusqueda(''); }
      if (estado.saludAbierta) abrirSalud(null);
      cerrarPanel();
      if (location.hash) try { history.replaceState(null, '', location.pathname + location.search); } catch (e) {}
      if (estado.vista !== 'grafo') cambiarVista('grafo', true);
    }
    ocultarTooltip();
    construirFiltros();
    sincronizarCasillas();
    actualizarBandaLocal();
    olvidarTextos();
    if (vivo.refrescarNombres) vivo.refrescarNombres();
    if (guardar) {
      guardarPresenta('cerebro-anonimo', activo);
      aviso(activo ? 'Modo anónimo: notas, chats, archivos y agentes con nombres genéricos. Ojo: cerebro.html nunca es anónimo, compartí solo capturas o video.' : 'Volvieron los nombres reales.');
    }
  }

  function iniciarPresenta() {
    let q = null;
    try { q = new URLSearchParams(location.search); } catch (e) {}
    const leer = clave => { try { return localStorage.getItem(clave); } catch (e) { return null; } };
    const anonimo = DATOS.compartido === true || (q && q.has('anonimo')) || leer('cerebro-anonimo') === 'si';
    if (DATOS.compartido === true) {
      const marca = $('#marca-anonimo');
      marca.textContent = 'Copia sin notas';
      marca.title = 'Esta copia no lleva el texto ni los nombres de las notas';
      marca.disabled = true;
    }
    const cine = (q && q.has('cine')) || leer('cerebro-cine') === 'si';
    $('#pie-cine-notas').textContent = nodos.length + (nodos.length === 1 ? ' nota' : ' notas');
    if (anonimo) ponerAnonimo(true, false);
    if (cine) ponerCine(true, false, false);
    $('#marca-anonimo').addEventListener('click', () => ponerAnonimo(false, true));
    document.addEventListener('fullscreenchange', () => {
      ajustarLienzo();
      if (!document.fullscreenElement && presenta.pantalla) {
        presenta.pantalla = false;
        if (presenta.cine) ponerCine(false, true, false);
        return;
      }
      if (!introCorriendo() && !estado.seleccionado) {
        cancelarEncuadre();
        encuadrar(true);
      }
    });
  }

  function conectarEventos() {
    let temporizadorBusqueda = null;
    buscador.addEventListener('input', () => {
      clearTimeout(temporizadorBusqueda);
      temporizadorBusqueda = setTimeout(() => actualizarBusqueda(buscador.value), 120);
    });
    buscador.addEventListener('keydown', ev => {
      if (ev.key === 'Enter') {
        ev.preventDefault();
        clearTimeout(temporizadorBusqueda);
        const valor = buscador.value;
        const abrirPrimero = () => {
          const primero = estado.resultados[0];
          if (buscador.value !== valor) return;
          if (!primero) {
            if (busq.entidad) abrirResultado(busq.entidad.notas[0].nodo.id, '');
            return;
          }
          const s0 = primero.secciones && primero.secciones[0];
          abrirResultado(primero.n.id, s0 && s0.titulo ? limpiarTitulo(s0.titulo) : '');
        };
        if (valor === busq.consulta && !busq.control) abrirPrimero();
        else actualizarBusqueda(valor).then(abrirPrimero);
      } else if (ev.key === 'Escape') {
        ev.preventDefault();
        ev.stopPropagation();
        if (buscador.value) {
          buscador.value = '';
          clearTimeout(temporizadorBusqueda);
          actualizarBusqueda('');
        } else {
          buscador.blur();
        }
      }
    });

    lateral.addEventListener('change', ev => {
      const t = ev.target;
      if (t.dataset.grupo !== undefined) {
        if (t.checked) estado.gruposOn.add(t.dataset.grupo); else estado.gruposOn.delete(t.dataset.grupo);
      } else if (t.dataset.proyecto !== undefined) {
        if (t.checked) estado.proyectosOn.add(t.dataset.proyecto); else estado.proyectosOn.delete(t.dataset.proyecto);
      } else if (t.dataset.tipo !== undefined) {
        if (t.checked) estado.tiposOn.add(t.dataset.tipo); else estado.tiposOn.delete(t.dataset.tipo);
      } else if (t.dataset.etiqueta !== undefined) {
        if (t.checked) estado.etiquetasOn.add(t.dataset.etiqueta); else estado.etiquetasOn.delete(t.dataset.etiqueta);
      } else if (t.dataset.clase !== undefined) {
        if (t.checked) estado.clasesOn.add(t.dataset.clase); else estado.clasesOn.delete(t.dataset.clase);
      } else {
        return;
      }
      aplicarFiltros();
    });

    lateral.addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b || !lateral.contains(b)) return;
      const conjuntos = { grupos: ['gruposOn', grupos.map(g => g.id)], proyectos: ['proyectosOn', proyectos.map(p => p.id)], tipos: ['tiposOn', Object.keys(TIPOS)], etiquetas: ['etiquetasOn', clavesEtiquetas()], clases: ['clasesOn', ORDEN_CLASES] };
      if (b.dataset.todos || b.dataset.ninguno) {
        const c = conjuntos[b.dataset.todos || b.dataset.ninguno];
        estado[c[0]] = new Set(b.dataset.todos ? c[1] : []);
        sincronizarCasillas();
        aplicarFiltros();
      } else if (b.dataset.soloGrupo !== undefined) {
        estado.gruposOn = new Set([b.dataset.soloGrupo]);
        sincronizarCasillas();
        aplicarFiltros();
        encuadrarLuego();
      } else if (b.dataset.soloProyecto !== undefined) {
        estado.proyectosOn = new Set([b.dataset.soloProyecto]);
        sincronizarCasillas();
        aplicarFiltros();
        encuadrarLuego();
      } else if (b.dataset.soloTipo !== undefined) {
        estado.tiposOn = new Set([b.dataset.soloTipo]);
        sincronizarCasillas();
        aplicarFiltros();
        encuadrarLuego();
      } else if (b.dataset.soloEtiqueta !== undefined) {
        estado.etiquetasOn = new Set([b.dataset.soloEtiqueta]);
        sincronizarCasillas();
        aplicarFiltros();
        encuadrarLuego();
      } else if (b.dataset.salud) {
        abrirSalud(b.dataset.salud);
      } else if (b.dataset.plegar !== undefined) {
        const abierta = b.getAttribute('aria-expanded') !== 'true';
        b.setAttribute('aria-expanded', String(abierta));
        b.textContent = (abierta ? 'Ocultar ' : 'Ver ') + b.textContent.replace(/^(Ver|Ocultar) /, '');
        const extras = b.nextElementSibling;
        if (extras) extras.hidden = !abierta;
        if (abierta) busq.abiertas.add(b.dataset.plegar); else busq.abiertas.delete(b.dataset.plegar);
      } else if (b.hasAttribute('data-sobre')) {
        pedirSobre(b);
      } else if (b.hasAttribute('data-volver')) {
        cerrarSobre();
        renderResultados();
      } else if (b.dataset.id !== undefined) {
        if (b.closest('#resultados')) abrirResultado(b.dataset.id, b.dataset.seccion || '');
        else {
          irA(b.dataset.id, true);
          if (esMovil()) cerrarLateral();
        }
      }
    });

    $('#totales').addEventListener('click', ev => {
      if (!ev.target.closest('#ir-salud')) return;
      if (esMovil()) abrirLateral();
      const gravedad = s => s.tono === 'peligro' ? 0 : 1;
      const primero = SALUD.filter(s => problemasDe(s) > 0).sort((a, b) => gravedad(a) - gravedad(b))[0];
      if (!primero) $('#bloque-salud').scrollIntoView({ behavior: menosMovimiento.matches ? 'auto' : 'smooth', block: 'start' });
      else if (estado.saludAbierta !== primero.clave) abrirSalud(primero.clave);
      else mostrarListaSalud();
      if (ev.detail === 0) {
        const tarjeta = primero ? $('#salud [data-salud="' + primero.clave + '"]') : $('#salud .salud-item');
        if (tarjeta) tarjeta.focus({ preventScroll: true });
      }
    });

    document.querySelectorAll('[data-vista]').forEach(b => b.addEventListener('click', () => cambiarVista(b.dataset.vista)));
    $('#orden-lista').addEventListener('change', renderLista);
    $('#lista').addEventListener('scroll', pedirTramoLista, { passive: true });
    window.addEventListener('resize', () => { if (listaVirtual.entradas && estado.vista === 'lista') renderLista(); });
    $('#lista').addEventListener('click', ev => {
      const f = ev.target.closest('[data-id]');
      if (f) irA(f.dataset.id, true);
    });

    $('#banda-local').addEventListener('click', ev => {
      const b = ev.target.closest('button');
      if (!b || !estado.local) return;
      if (b.dataset.saltos) {
        estado.local.saltos = Number(b.dataset.saltos) === 2 ? 2 : 1;
        aplicarFiltros();
        encuadrarLuego();
      } else if (b.hasAttribute('data-salir-local')) {
        salirLocal();
      }
    });

    panel.addEventListener('click', ev => {
      const enlace = ev.target.closest('a[data-nodo]');
      if (enlace) {
        ev.preventDefault();
        irA(enlace.getAttribute('data-nodo'), true);
        return;
      }
      const roto = ev.target.closest('a.enlace-roto, .enlace-ambiguo');
      if (roto) { ev.preventDefault(); aviso(roto.getAttribute('title') || 'Enlace roto'); return; }
      const entidad = ev.target.closest('.item-entidad[data-entidad]');
      if (entidad) { marcarEntidad(entidad.dataset.entidad); return; }
      const mas = ev.target.closest('#panel-nombra .ver-mas[data-tipo]');
      if (mas) {
        panelNombra.abiertos.add(mas.dataset.tipo);
        if (estado.seleccionado) pintarNombra(estado.seleccionado);
        return;
      }
      const b = ev.target.closest('.item-nodo[data-id]');
      if (b) irA(b.dataset.id, true);
    });
    $('#panel-cerrar').addEventListener('click', cerrarPanel);
    $('#panel-volver').addEventListener('click', () => {
      const id = pila.pop();
      if (id) irA(id, true, true);
    });
    $('#abrir-obsidian').addEventListener('click', () => {
      const enlace = estado.seleccionado ? enlaceObsidian(estado.seleccionado) : '';
      if (enlace) location.href = enlace;
    });
    $('#copiar-ruta').addEventListener('click', async () => {
      if (!estado.seleccionado) return;
      const ok = await copiar(estado.seleccionado.ruta);
      aviso(ok ? 'Ruta copiada.' : 'No pude copiar; seleccioná la ruta a mano.');
    });
    $('#copiar-contexto').addEventListener('click', async () => {
      const n = estado.seleccionado;
      if (!n) return;
      const rutas = [n.ruta];
      n.salientes.forEach(l => rutas.push(l.target.ruta));
      n.entrantes.forEach(l => rutas.push(l.source.ruta));
      const unicas = Array.from(new Set(rutas.filter(Boolean)));
      const ok = await copiar(unicas.join('\n'));
      aviso(ok ? 'Copié ' + unicas.length + (unicas.length === 1 ? ' ruta.' : ' rutas.') : 'No pude copiar.');
    });
    $('#ver-local').addEventListener('click', () => {
      const n = estado.seleccionado;
      if (!n) return;
      if (estado.local && estado.local.id === n.id) salirLocal();
      else activarLocal(n);
      if (estado.vista === 'grafo' && esMovil()) cerrarPanel();
    });

    $('#abrir-lateral').addEventListener('click', abrirLateral);
    $('#cerrar-lateral').addEventListener('click', cerrarLateral);
    $('#velo').addEventListener('click', () => { cerrarLateral(); if (esMovil()) cerrarPanel(); });
    movil.addEventListener('change', () => {
      if (!esMovil()) lateral.classList.remove('abierto');
      centro.classList.toggle('con-panel', !esMovil() && panel.classList.contains('abierto'));
      actualizarVelo();
    });

    $('#alternar-tema').addEventListener('click', () => {
      const nuevo = temaEfectivo() === 'dark' ? 'light' : 'dark';
      const cambiar = () => {
        document.documentElement.setAttribute('data-theme', nuevo);
        try { localStorage.setItem('cerebro-tema', nuevo); } catch (e) {}
        alCambiarTema();
        dibujarYa();
      };
      if (anim.modo !== 'nada' && document.startViewTransition && !document.hidden) document.startViewTransition(cambiar);
      else cambiar();
    });
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', alCambiarTema);

    $('#alternar-animaciones').addEventListener('click', () => {
      anim.pref = !anim.pref;
      if (anim.pref) {
        anim.nivel = 2;
        anim.resplandor = true;
        anim.enfoque = true;
        anim.aristasLivianas = false;
        anim.muestras = anim.malas = 0;
        anim.msVentana = anim.msSano = anim.subidas = 0;
        anim.bajadas = [];
        anim.esperaSubir = 20000;
        anim.dtBase = Infinity;
        anim.lentosSeguidos = 0;
        anim.escala = 1;
        ajustarLienzo();
      }
      try { localStorage.setItem('cerebro-animaciones', anim.pref ? 'si' : 'no'); } catch (e) {}
      aplicarModo();
    });
    menosMovimiento.addEventListener('change', aplicarModo);

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        detenerVida();
        vaciarEfectos();
        return;
      }
      anim.tsPrevio = 0;
      anim.encadenado = false;
      ritmo.t = 0;
      programarAmbiente(1500);
      pedirDibujo();
    });
    ['pointermove', 'pointerdown', 'wheel', 'keydown', 'touchstart'].forEach(tipo => document.addEventListener(tipo, marcarActividad, { passive: true, capture: true }));
    panel.addEventListener('pointerenter', () => { anim.sobrePanel = true; });
    panel.addEventListener('pointerleave', () => { anim.sobrePanel = false; });

    const alPasar = ev => {
      if (esMovil() || estado.vista !== 'grafo') return;
      const el = ev.target.closest('.item-nodo[data-id], .resultado[data-id]');
      ponerPrevia(el ? el.dataset.id : null);
    };
    const alSalir = () => ponerPrevia(null);
    [panel, lateral].forEach(caja => {
      caja.addEventListener('mouseover', alPasar);
      caja.addEventListener('focusin', alPasar);
      caja.addEventListener('mouseleave', alSalir);
      caja.addEventListener('focusout', alSalir);
    });

    const ayuda = $('#ayuda-dialogo');
    const cuerpoAyuda = $('#ayuda-cuerpo');
    const ATAJOS = [
      ['?', 'abre y cierra esta ayuda'],
      ['/', 'busca una nota'],
      ['Enter', 'en la búsqueda, va al primer resultado'],
      ['C', 'modo cine: solo el cerebro, en pantalla completa y con subtítulos grandes'],
      ['A', 'modo anónimo: notas, chats, archivos y agentes con nombres genéricos'],
      ['P', 'baja una foto del cerebro (PNG)'],
      ['G', 'graba 30 s de video; otra G lo corta antes'],
      ['Esc', 'cierra lo que esté abierto y sale del modo cine'],
      ['Doble clic', 'en el fondo, pone el cerebro de frente'],
      ['Shift + arrastrar', 'mueve el cerebro (también con el botón derecho)'],
      ['Rueda', 'acerca y aleja']
    ];
    const QUE_VES = [
      ['Nota', 'cada figura es una nota .md: la forma dice el tipo (abajo) y el tamaño, cuántas conexiones tiene; con un clic la abrís'],
      ['Nombre', 'las notas más conectadas lo llevan al lado; las demás lo muestran al acercarte o al pasar el ratón'],
      ['Tejido', 'los puntitos y las ramas que no son figuras son el tejido del cerebro: de adorno, no son notas'],
      ['Lóbulo', 'cada zona junta las notas de uno o más grupos; su rótulo cuenta los toques de la última media hora'],
      ['Luz', 'donde Claude lee o edita ahora mismo'],
      ['Brasa', 'lo que tocó en los últimos minutos; se apaga despacio'],
      ['En la cabeza', 'aro quieto del color del chat: lo que ese chat leyó y todavía tiene cargado (más tenue si leyó una parte o si es de un agente); al comprimir su memoria lo repasa y se apaga'],
      ['Penumbra', 'lo que nadie toca, con el modo en vivo'],
      ['Sueño', 'si nadie lo usa por dos minutos se duerme y sueña con recorridos reales de los chats']
    ];
    function pintarAyuda() {
      const punto = c => '<span class="punto" style="--c:' + c + '"></span>';
      const item = (antes, nombre, texto, clase) => '<li>' + antes + '<b' + (clase ? ' class="' + clase + '"' : '') + '>' + esc(nombre) + '</b><span>' + esc(texto) + '</span></li>';
      const lista = items => '<ul class="ayuda-lista">' + items.join('') + '</ul>';
      const lobulos = ANATOMIA.lobulos.map(l => {
        const g = grupoPorId.get(l.grupo);
        return item(punto(g ? g.color : 'var(--texto-3)'), l.anatomico, publico('texto', l, textoDelLobulo(l)), '');
      });
      const colores = vivo.leyenda
        ? '<p>El color del verbo dice qué hizo. En cada fila, el primer puntito es el color del chat y el segundo, el del agente.</p>'
          + lista(vivo.leyenda().map(([nombre, color, texto]) => item(punto(color), nombre, texto, 'verbo')))
        : '<p>El panel «Ahora» aparece cuando abrís el mapa con <code>/neuromapa:abrir</code> (sin el plugin, <code>sh bin/neuromapa abrir</code> o <code>bin\\neuromapa.cmd abrir</code>), que levanta el servidor.</p>';
      const formas = Object.keys(TIPOS).filter(t => nodos.some(n => n.tipo === t))
        .map(t => item(muestraTipo(t), nombreTipo(t), publico('texto', t, TIPOS[t].ayuda) || '', ''));
      cuerpoAyuda.innerHTML =
        '<h3>El cerebro</h3>' + lista(QUE_VES.map(([n, t]) => item('', n, t, ''))) +
        (formas.length ? '<h3>La forma de cada nota</h3>' + lista(formas) : '') +
        '<h3>Lóbulos</h3>' + lista(lobulos) +
        '<h3>Atajos</h3>' + lista(ATAJOS.map(([k, t]) => '<li><kbd>' + esc(k) + '</kbd><span>' + esc(t) + '</span></li>')) +
        '<details><summary>Colores de «Ahora»: qué hizo cada verbo</summary>' + colores + '</details>' +
        '<details><summary>Conexiones: qué es cada trazo</summary>' + lista(ORDEN_CLASES.map(c => item(muestraLinea(c), CLASES[c].nombre, CLASES[c].ayuda, ''))) + '</details>' +
        '<h3>Para compartir</h3>' +
        '<p>Abajo, <b>Foto</b> baja un PNG del cerebro, <b>Mi día</b> arma una tarjeta con las cifras del día (nunca el texto de tus mensajes) y <b>Grabar 30 s</b> baja un video; el botón de al lado elige horizontal (16:9) o vertical (4:5). Todo se guarda en tu compu y no se sube a ningún lado. Si el modo anónimo está apagado, te avisa antes de bajar.</p>' +
        '<p><b>Sin notas</b> baja una copia del mapa que sí se puede pasar: las mismas neuronas y conexiones, con nombres genéricos y sin el texto, las rutas ni el panel de salud de tus notas.</p>' +
        '<p>También podés abrir la página con <code>?cine</code> o <code>?anonimo</code> al final de la dirección. El modo anónimo cambia lo que se ve en pantalla: el lienzo, los carteles, el subtítulo, los tooltips y el panel «Ahora». Apaga el buscador, la lista, el panel de la nota y los bloques «Lo que hizo por vos», «Salud» y «Lo que aprendió».</p>' +
        '<p class="ayuda-nota"><b>Compartir <code>cerebro.html</code> NUNCA es anónimo:</b> el archivo lleva adentro el texto de todas las notas, con nombres, rutas y todo lo que anotaste. Para mostrar el cerebro, compartí una captura o un video hecho en modo anónimo, o la copia de <b>Sin notas</b>.</p>';
      const parrafos = document.querySelectorAll('.bloque.ayuda p');
      if (parrafos.length) {
        const mas = document.createElement('details');
        const titulo = document.createElement('summary');
        titulo.textContent = 'Contame más';
        mas.appendChild(titulo);
        parrafos.forEach(p => mas.appendChild(p.cloneNode(true)));
        cuerpoAyuda.appendChild(mas);
      }
    }
    function abrirAyuda() {
      if (ayuda.open) return;
      $('#visita').hidden = true;
      pintarAyuda();
      if (typeof ayuda.showModal === 'function') ayuda.showModal();
      else ayuda.setAttribute('open', '');
      cuerpoAyuda.scrollTop = 0;
    }
    function cerrarAyuda() {
      if (typeof ayuda.close === 'function') ayuda.close();
      else ayuda.removeAttribute('open');
    }
    $('#abrir-ayuda').addEventListener('click', abrirAyuda);
    $('#visita-ok').addEventListener('click', () => { $('#visita').hidden = true; });
    $('#cerrar-ayuda').addEventListener('click', cerrarAyuda);
    ayuda.addEventListener('click', ev => { if (ev.target === ayuda) cerrarAyuda(); });

    document.addEventListener('keydown', ev => {
      if (ev.repeat && ev.key.length === 1) return;
      if (ev.key === '?' && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        if (ayuda.open) cerrarAyuda();
        else abrirAyuda();
      } else if (ayuda.open) {
        if (ev.key === 'Escape' && typeof ayuda.showModal !== 'function') cerrarAyuda();
      } else if (compartir.dialogo && compartir.dialogo.open) {
        return;
      } else if ((ev.key === 'p' || ev.key === 'P') && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        sacarFoto();
      } else if ((ev.key === 'g' || ev.key === 'G') && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        alternarGrabacion();
      } else if ((ev.key === 'c' || ev.key === 'C') && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        ponerCine(!presenta.cine, true, true);
      } else if ((ev.key === 'a' || ev.key === 'A') && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        ponerAnonimo(!presenta.anonimo, true);
      } else if (ev.key === 'Escape' && !$('#visita').hidden) {
        $('#visita').hidden = true;
      } else if (ev.key === 'Escape' && presenta.cine) {
        ponerCine(false, true, false);
      } else if (ev.key === '/' && !esCampo(ev.target) && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        if (esMovil()) abrirLateral();
        buscador.focus();
        buscador.select();
      } else if (ev.key === 'Escape') {
        if (esMovil() && lateral.classList.contains('abierto')) cerrarLateral();
        else if (panel.classList.contains('abierto')) cerrarPanel();
        else if (estado.local) salirLocal();
      }
    });

    window.addEventListener('hashchange', () => {
      const id = leerHash();
      if (id && porId.has(id) && (!estado.seleccionado || estado.seleccionado.id !== id)) irA(id, true);
    });

    if (typeof ResizeObserver === 'function') {
      new ResizeObserver(ajustarLienzo).observe(centro);
      new ResizeObserver(medirBanda).observe($('#banda-local'));
    } else {
      window.addEventListener('resize', () => { ajustarLienzo(); medirBanda(); });
    }
  }

  construirCabecera();
  construirFiltros();
  construirSalud();
  construirAprendido();
  recalcularVisibles();
  actualizarContador();
  leerColores();
  alCambiarTema();
  try { anim.pref = localStorage.getItem('cerebro-animaciones') !== 'no'; } catch (e) {}
  anim.ultimaActividad = performance.now();
  aplicarModo();
  conectarEventos();
  if (hayProyectos) {
    const modoColor = $('#modo-color');
    modoColor.hidden = false;
    modoColor.querySelector('[data-color="proyectos"]').hidden = false;
    let colorGuardado = null;
    try { colorGuardado = new URLSearchParams(location.search).get('color') || localStorage.getItem('cerebro-color'); } catch (e) {}
    estado.porProyecto = colorGuardado === 'proyectos';
    marcarColor();
  }
  $('#modo-color').addEventListener('click', ev => {
    const b = ev.target.closest('button[data-color]');
    if (!b) return;
    if (vivo.ponerColor) vivo.ponerColor(b.dataset.color === 'uso');
    if (b.dataset.color !== 'uso') ponerVistaDeColor(b.dataset.color);
  });
  iniciarPresenta();
  iniciarCompartir();
  ajustarLienzo();
  actualizarVelo();

  let vistaGuardada = null;
  try { vistaGuardada = localStorage.getItem('cerebro-vista'); } catch (e) {}
  cambiarVista(vistaGuardada === 'lista' ? 'lista' : 'grafo', true);

  const inicial = leerHash();
  if (inicial && porId.has(inicial)) irA(inicial, true, true);

  cargarD3(iniciarGrafo).then(ok => {
    if (!ok && !graficoListo) sinGrafo();
  });
  cargarScript(URL_MARKED, () => {
    estado.markedOk = !!(window.marked && (typeof window.marked.parse === 'function' || typeof window.marked === 'function'));
    mostrarAvisoLibs();
    if (estado.seleccionado) renderizarContenido(estado.seleccionado);
  }).then(ok => {
    if (ok) return;
    estado.markedOk = false;
    mostrarAvisoLibs();
    if (estado.seleccionado) renderizarContenido(estado.seleccionado);
  });

