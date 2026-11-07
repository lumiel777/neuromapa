  function prepararResplandor(gl, programa) {
    const PASADA = 'attribute vec3 aPos;\n' +
      'varying vec2 vUv;\n' +
      'void main() { vUv = aPos.xy * 0.5 + 0.5; gl_Position = vec4(aPos.xy, 0.0, 1.0); }\n';
    try {
      const desenfoque = programa(PASADA, PRECISION_ALTA +
        'uniform sampler2D uTex; uniform vec2 uDir;\n' +
        'varying vec2 vUv;\n' +
        'void main() {\n' +
        '  vec2 d1 = uDir * 1.3846154; vec2 d2 = uDir * 3.2307692;\n' +
        '  vec4 c = texture2D(uTex, vUv) * 0.2270270;\n' +
        '  c += (texture2D(uTex, vUv + d1) + texture2D(uTex, vUv - d1)) * 0.3162162;\n' +
        '  c += (texture2D(uTex, vUv + d2) + texture2D(uTex, vUv - d2)) * 0.0702703;\n' +
        '  gl_FragColor = c;\n' +
        '}\n', ['uTex', 'uDir']);
      const mezcla = programa(PASADA, PRECISION_ALTA +
        'uniform sampler2D uEscena, uBrillo, uBrillo2;\n' +
        'uniform float uEsc, uFuerza, uConEscena;\n' +
        'varying vec2 vUv;\n' +
        'vec3 tono(vec3 c) {\n' +
        '  float m = max(c.r, max(c.g, c.b));\n' +
        '  if (m <= 0.62) return c;\n' +
        '  float t = 0.62 + 0.38 * (1.0 - exp((0.62 - m) / 0.38));\n' +
        '  return mix(c * (t / m), vec3(t), 0.18 * (1.0 - t / m));\n' +
        '}\n' +
        'void main() {\n' +
        '  vec4 b = (texture2D(uBrillo, vUv) * 0.6 + texture2D(uBrillo2, vUv) * 0.9) * uFuerza;\n' +
        '  vec4 s = texture2D(uEscena, vUv) * (uEsc * uConEscena);\n' +
        '  vec4 c = s + b;\n' +
        '  if (uConEscena > 0.5) c.rgb = tono(c.rgb);\n' +
        '  float g = (fract(52.9829189 * fract(dot(gl_FragCoord.xy, vec2(0.06711056, 0.00583715)))) - 0.5) * 0.006 * step(0.004, c.a);\n' +
        '  gl_FragColor = vec4(max(c.rgb + g, 0.0), min(c.a, 1.0));\n' +
        '}\n', ['uEscena', 'uBrillo', 'uBrillo2', 'uEsc', 'uFuerza', 'uConEscena']);
      const hf = gl.getExtension('OES_texture_half_float');
      gl.getExtension('EXT_color_buffer_half_float');
      return { desenfoque, mezcla, hf, escena: null, a1: null, t1: null, a2: null, t2: null, esc: 1, w: 0, h: 0, falla: false, fuerza: 0, tF: 0 };
    } catch (e) {
      console.warn('Neuromapa: sin resplandor', e);
      return null;
    }
  }

  function objetivoGL(gl, o, w, h, tipo, filtro) {
    if (!o) {
      o = { tex: gl.createTexture(), fb: gl.createFramebuffer(), w: 0, h: 0, tipo: 0, ok: false };
      gl.bindTexture(gl.TEXTURE_2D, o.tex);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filtro);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filtro);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }
    if (o.w === w && o.h === h && o.tipo === tipo) return o;
    gl.bindTexture(gl.TEXTURE_2D, o.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, w, h, 0, gl.RGBA, tipo, null);
    gl.bindFramebuffer(gl.FRAMEBUFFER, o.fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, o.tex, 0);
    o.ok = gl.checkFramebufferStatus(gl.FRAMEBUFFER) === gl.FRAMEBUFFER_COMPLETE;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.bindTexture(gl.TEXTURE_2D, null);
    o.w = w;
    o.h = h;
    o.tipo = tipo;
    return o;
  }

  function objetivosResplandor(G, w, h) {
    const R = G.brillo;
    if (!R || R.falla || !anim.resplandor || anim.nivel !== 2) return null;
    const gl = G.gl;
    if (R.w !== w || R.h !== h || !R.a1) {
      const w2 = Math.max(1, Math.ceil(w / 2));
      const h2 = Math.max(1, Math.ceil(h / 2));
      const w4 = Math.max(1, Math.ceil(w / 4));
      const h4 = Math.max(1, Math.ceil(h / 4));
      R.a1 = objetivoGL(gl, R.a1, w2, h2, gl.UNSIGNED_BYTE, gl.LINEAR);
      R.t1 = objetivoGL(gl, R.t1, w2, h2, gl.UNSIGNED_BYTE, gl.LINEAR);
      R.a2 = objetivoGL(gl, R.a2, w4, h4, gl.UNSIGNED_BYTE, gl.LINEAR);
      R.t2 = objetivoGL(gl, R.t2, w4, h4, gl.UNSIGNED_BYTE, gl.LINEAR);
      R.w = w;
      R.h = h;
      if (!R.a1.ok || !R.t1.ok || !R.a2.ok || !R.t2.ok) {
        R.falla = true;
        console.warn('Neuromapa: sin resplandor (el framebuffer no quedó completo)');
        return null;
      }
    }
    if (anim.oscuro) {
      if (R.hf) {
        R.escena = objetivoGL(gl, R.escena, w, h, R.hf.HALF_FLOAT_OES, gl.NEAREST);
        if (!R.escena.ok) R.hf = null;
      }
      if (!R.hf) R.escena = objetivoGL(gl, R.escena, w, h, gl.UNSIGNED_BYTE, gl.NEAREST);
      if (!R.escena.ok) {
        R.falla = true;
        console.warn('Neuromapa: sin resplandor (la escena no entra en un framebuffer)');
        return null;
      }
      R.esc = R.escena.tipo === gl.UNSIGNED_BYTE ? 2 : 1;
    }
    return R;
  }

  function desenfocarResplandor(G, R) {
    const gl = G.gl;
    const P = R.desenfoque;
    gl.disable(gl.BLEND);
    gl.useProgram(P.p);
    gl.bindBuffer(gl.ARRAY_BUFFER, G.fondo.buf);
    gl.enableVertexAttribArray(P.aPos);
    gl.vertexAttribPointer(P.aPos, 3, gl.FLOAT, false, 0, 0);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(P.u.uTex, 0);
    const paso = (de, a, dx, dy) => {
      gl.bindFramebuffer(gl.FRAMEBUFFER, a.fb);
      gl.viewport(0, 0, a.w, a.h);
      gl.bindTexture(gl.TEXTURE_2D, de.tex);
      gl.uniform2f(P.u.uDir, dx / de.w, dy / de.h);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };
    paso(R.a1, R.t1, 1, 0);
    paso(R.t1, R.a1, 0, 1);
    paso(R.a1, R.t2, 1.6, 0);
    paso(R.t2, R.a2, 0, 1.6);
    gl.bindTexture(gl.TEXTURE_2D, null);
    gl.disableVertexAttribArray(P.aPos);
    gl.enable(gl.BLEND);
  }

  function mezclarResplandor(G, R, w, h, fuerza) {
    const gl = G.gl;
    const M = R.mezcla;
    const conEscena = anim.oscuro && R.escena;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, w, h);
    gl.useProgram(M.p);
    gl.bindBuffer(gl.ARRAY_BUFFER, G.fondo.buf);
    gl.enableVertexAttribArray(M.aPos);
    gl.vertexAttribPointer(M.aPos, 3, gl.FLOAT, false, 0, 0);
    const texturas = [conEscena ? R.escena.tex : R.a1.tex, R.a1.tex, R.a2.tex];
    texturas.forEach((t, i) => { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, t); });
    gl.uniform1i(M.u.uEscena, 0);
    gl.uniform1i(M.u.uBrillo, 1);
    gl.uniform1i(M.u.uBrillo2, 2);
    gl.uniform1f(M.u.uEsc, conEscena ? R.esc : 0);
    gl.uniform1f(M.u.uConEscena, conEscena ? 1 : 0);
    gl.uniform1f(M.u.uFuerza, fuerza);
    if (anim.oscuro) gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_COLOR, gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    for (let i = 2; i >= 0; i--) { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, null); }
    gl.disableVertexAttribArray(M.aPos);
  }

  function subirNeuronas(px, pares, fibras) {
    const G = neuronasGL;
    if (!G) return null;
    const gl = G.gl;
    const pos = new Float32Array(px.length * 3);
    const col = new Float32Array(px.length * 4);
    const extra = new Float32Array(px.length * 2);
    const norm = new Float32Array(px.length * 4);
    px.forEach((p, i) => {
      pos.set([p.x, p.y, p.z], i * 3);
      const c = hexARgb(p.c);
      col.set([c[0], c[1], c[2], p.a], i * 4);
      extra.set([p.r, (i * 2.399) % TAU], i * 2);
      norm.set([p.nx || 0, p.ny || 0, p.nz || 0, p.nw || 0], i * 4);
    });
    const lpos = new Float32Array(pares.length * 6);
    const lcol = new Float32Array(pares.length * 8);
    pares.forEach(([i, j], n) => {
      const a = px[i];
      const b = px[j];
      lpos.set([a.x, a.y, a.z, b.x, b.y, b.z], n * 6);
      const c = hexARgb(a.c);
      lcol.set([c[0], c[1], c[2], 0.2, c[0], c[1], c[2], 0.2], n * 8);
    });
    const buf = datos => {
      const b = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, b);
      gl.bufferData(gl.ARRAY_BUFFER, datos, gl.STATIC_DRAW);
      return b;
    };
    const inicio = new Float32Array(px.length * 4);
    const azarI = azarConSemilla(4242);
    const N = cerebro.nido;
    let dmax = 1;
    px.forEach((p, i) => {
      const d = Math.hypot(p.x - N[0], p.y - N[1], p.z - N[2]);
      inicio[i * 4 + 3] = d;
      if (d > dmax) dmax = d;
    });
    px.forEach((p, i) => {
      const u = inicio[i * 4 + 3] / dmax;
      const th = u * TAU * 2.2 + azarI() * 0.9;
      const rr = giro.R * (0.03 + 0.1 * azarI());
      inicio[i * 4] = N[0] + Math.cos(th) * rr;
      inicio[i * 4 + 1] = N[1] - u * giro.R * 0.3 + (azarI() - 0.5) * giro.R * 0.04;
      inicio[i * 4 + 2] = N[2] + Math.sin(th) * rr;
      inicio[i * 4 + 3] = INTRO.explota + Math.pow(u, 0.9) * INTRO.reparto + azarI() * INTRO.azar;
    });
    return { pos: buf(pos), col: buf(col), extra: buf(extra), norm: buf(norm), inicio: buf(inicio), n: px.length, lpos: buf(lpos), lcol: buf(lcol), nl: pares.length * 2,
             fpos: fibras ? buf(fibras.pos) : null, fcol: fibras ? buf(fibras.col) : null, nf: fibras ? fibras.n : 0, dmax };
  }

  function limpiarNeuronas() {
    if (!neuronasGL || neuronasGL.perdido) return;
    const gl = neuronasGL.gl;
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
  }

  const LUZ_FIBRAS = [0.85, 0.9];
  const LUZ_BASE = [-0.45, -0.62, 0.64];
  const luzVol = { x: LUZ_BASE[0], y: LUZ_BASE[1], z: LUZ_BASE[2], t: 0 };
  function moverLuz(ahora) {
    const L = luzVol;
    const dt = L.t ? Math.max(0, Math.min(100, ahora - L.t)) : 1e9;
    L.t = ahora;
    let mx = LUZ_BASE[0];
    let my = LUZ_BASE[1];
    let mz = LUZ_BASE[2];
    const focos = vida.focos;
    if (focos.length && cerebro && completo()) {
      let sx = 0;
      let sy = 0;
      let sz = 0;
      for (const f of focos) {
        const p = proyectar(f.x, f.y, f.z || 0);
        sx += (p.x - giro.px - giro.cx) / p.f;
        sy += (p.y - giro.py - giro.cy) / p.f;
        sz += Math.max(0, p.d);
      }
      const k = 1 / (focos.length * giro.R);
      mx = mx * 0.35 + sx * k - 0.15 * camara.peso;
      my = my * 0.35 + sy * k - 0.25 - 0.3 * camara.peso;
      mz = mz * 0.35 + sz * k + 0.5;
    }
    const m = Math.hypot(mx, my, mz) || 1;
    const a = anim.nivel === 0 ? 1 : 1 - Math.exp(-dt / 260);
    L.x += (mx / m - L.x) * a;
    L.y += (my / m - L.y) * a;
    L.z += (mz / m - L.z) * a;
    const n = Math.hypot(L.x, L.y, L.z) || 1;
    L.x /= n;
    L.y /= n;
    L.z /= n;
    return L;
  }

  function pintarNeuronas(ahora) {
    const G = neuronasGL;
    if (!G || G.perdido || !cerebro || !cerebro.gl) return;
    const gl = G.gl;
    if (gl.isContextLost()) { G.perdido = true; return; }
    captura.glEn = captura.cuadro;
    const w = Math.round(ancho * dpr);
    const h = Math.round(alto * dpr);
    if (G.cv.width !== w || G.cv.height !== h) {
      G.cv.width = w;
      G.cv.height = h;
      G.cv.style.width = ancho + 'px';
      G.cv.style.height = alto + 'px';
    }
    gl.viewport(0, 0, w, h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    const t = transformacion;
    const tIntro = tiempoIntro(ahora);
    gl.enable(gl.BLEND);
    if (G.fondo && anim.nivel === 2) {
      const F = G.fondo;
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.useProgram(F.p);
      gl.uniform1f(F.u.uVela, sale3(limitar((tIntro - 300) / 2600)));
      const c = proyectar(giro.cx, giro.cy, 0);
      gl.uniform2f(F.u.uRes, w, h);
      gl.uniform2f(F.u.uCentro, (c.x * t.k + t.x) * dpr, h - (c.y * t.k + t.y) * dpr);
      gl.uniform1f(F.u.uRadio, Math.max(40, giro.R * t.k * dpr * 1.15));
      gl.uniform1f(F.u.uGiro, giro.ang);
      gl.uniform1f(F.u.uTilt, giro.tiltFondo);
      gl.uniform1f(F.u.uFase, (ahora * 0.0019) % TAU);
      gl.uniform1f(F.u.uDeriva, DERIVA_FONDO * Math.sin(ahora * 0.000012 / DERIVA_FONDO));
      gl.uniform1f(F.u.uNoche, anim.oscuro ? 1 : 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, F.buf);
      gl.enableVertexAttribArray(F.aPos);
      gl.vertexAttribPointer(F.aPos, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.disableVertexAttribArray(F.aPos);
    }
    const fz = limitar((3.4 - t.k) / 1.5);
    if (fz <= 0) return;
    if (anim.oscuro) gl.blendFunc(gl.ONE, gl.ONE);
    else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
    const B = cerebro.gl;
    const conRitmo = completo();
    const Rp = ritmo.pesos;
    const ondaK = TAU / (700 * cerebro.S);
    const usar = (P, luz) => {
      gl.useProgram(P.p);
      if (conRitmo) gl.uniform4f(P.u.uRitmo, Rp[0], Rp[1], Rp[2], Rp[3]);
      else gl.uniform4f(P.u.uRitmo, 0, 0, 0, 0);
      gl.uniform1f(P.u.uLuzReposo, conRitmo ? ritmo.luz : 1);
      gl.uniform3f(P.u.uDirOnda, ondaK * 0.97, ondaK * 0.2425, 0);
      gl.uniform1f(P.u.uTr, ahora % 60000);
      gl.uniform1f(P.u.uAng, giro.ang);
      gl.uniform1f(P.u.uF, giro.F);
      gl.uniform1f(P.u.uCx, giro.cx);
      gl.uniform1f(P.u.uCy, giro.cy);
      gl.uniform1f(P.u.uK, t.k);
      gl.uniform1f(P.u.uTx, t.x + giro.px * t.k);
      gl.uniform1f(P.u.uTy, t.y + giro.py * t.k);
      gl.uniform1f(P.u.uW, ancho);
      gl.uniform1f(P.u.uH, alto);
      gl.uniform1f(P.u.uR, giro.R);
      gl.uniform1f(P.u.uTilt, giro.tilt);
      gl.uniform1f(P.u.uEsc, giro.esc);
      gl.uniform1f(P.u.uLuz, luz * fz);
      gl.uniform1f(P.u.uNoche, anim.oscuro ? 1 : 0);
      if (P.u.uDof) {
        gl.uniform1f(P.u.uFocoProf, camara.prof);
        gl.uniform1f(P.u.uDof, camara.dof);
      }
    };
    const atributo = (lugar, buffer, tam) => {
      if (lugar < 0) return;
      gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
      gl.enableVertexAttribArray(lugar);
      gl.vertexAttribPointer(lugar, tam, gl.FLOAT, false, 0, 0);
    };
    const act = estadoActividad(ahora);
    const ponerActividad = P => {
      gl.uniform4fv(P.u.uFoco, G.vFoco);
      gl.uniform4fv(P.u.uFocoCol, G.vFocoCol);
      gl.uniform4fv(P.u.uOnda, act.onda);
      gl.uniform4fv(P.u.uOndaCol, act.ondaCol);
      gl.uniform4fv(P.u.uHuella, act.huellas);
      gl.uniform4fv(P.u.uHuellaCol, act.huellasCol);
      gl.uniform1f(P.u.uPenumbra, brasas.activo ? 1 : 0);
      gl.uniform4fv(P.u.uChoque, act.choques);
      gl.uniform4fv(P.u.uChoqueF, act.choquesF);
      gl.uniform4f(P.u.uGestoEsc, ANCHO_CHOQUE * cerebro.S, EMPUJE * cerebro.S, ANCHO_CORTINA * cerebro.S, EMPUJE * 0.45 * cerebro.S);
      gl.uniform4f(P.u.uContraer, giro.cx, giro.cy, 0, gestos.contraer);
      const b = gestos.barrido;
      gl.uniform4f(P.u.uPlano, DIR_BARRIDO[0], DIR_BARRIDO[1], DIR_BARRIDO[2], b ? b.pos : 0);
      if (b) gl.uniform4f(P.u.uPlanoCol, b.c[0], b.c[1], b.c[2], b.a * 0.85);
      else gl.uniform4f(P.u.uPlanoCol, 0, 0, 0, 0);
    };
    const luzFibras = anim.nivel === 2 && B.nf ? (anim.oscuro ? LUZ_FIBRAS[1] : LUZ_FIBRAS[0]) * limitar((tIntro - INTRO.clima + 200) / 1200) : 0;
    const N = cerebro.nido;
    const frente = tIntro >= INTRO.fin ? 1e7 : (B.dmax + 0.15 * giro.R) * Math.pow(limitar((tIntro - INTRO.explota - 0.7 * INTRO.vuelo) / INTRO.reparto), 1 / 0.9);
    usar(G.lineas, luzFibras);
    gl.uniform4f(G.lineas.u.uFrente, N[0], N[1], N[2], frente);
    ponerActividad(G.lineas);
    if (luzFibras > 0) {
      atributo(G.lineas.aPos, B.fpos, 3);
      atributo(G.lineas.aCol, B.fcol, 4);
      gl.drawArrays(gl.LINES, 0, B.nf);
    }
    gl.uniform1f(G.lineas.u.uLuz, (anim.oscuro ? 0.8 : 0.9) * limitar((tIntro - INTRO.explota) / 500) * fz);
    atributo(G.lineas.aPos, B.lpos, 3);
    atributo(G.lineas.aCol, B.lcol, 4);
    gl.drawArrays(gl.LINES, 0, B.nl);
    if (G.lineas.aCol >= 0) gl.disableVertexAttribArray(G.lineas.aCol);
    const P = G.puntos;
    usar(P, anim.oscuro ? 0.62 : 0.9);
    gl.uniform2f(P.u.uFases, (ahora * 0.013) % TAU, (ahora * 0.011) % TAU);
    gl.uniform1f(P.u.uDpr, dpr);
    gl.uniform1f(P.u.uIntro, tIntro);
    gl.uniform4f(P.u.uNido, N[0], N[1], N[2], INTRO.remolino);
    gl.uniform1f(P.u.uPeso, 0);
    const L = moverLuz(ahora);
    gl.uniform3f(P.u.uLuzDir, L.x, L.y, L.z);
    ponerActividad(P);
    const puntos = () => {
      atributo(P.aPos, B.pos, 3);
      atributo(P.aCol, B.col, 4);
      atributo(P.aExtra, B.extra, 2);
      atributo(P.aInicio, B.inicio, 4);
      atributo(P.aNorm, B.norm, 4);
      gl.drawArrays(gl.POINTS, 0, B.n);
      [P.aPos, P.aCol, P.aExtra, P.aInicio, P.aNorm].forEach(l => { if (l >= 0) gl.disableVertexAttribArray(l); });
    };
    camara.paralaje = envolver(camara.paralaje + CAMARA.paralaje * envolver(giro.ang - camara.angPrevio));
    camara.angPrevio = giro.ang;
    const motas = () => {
      const M = G.motas;
      const a = M && anim.oscuro && anim.nivel === 2 ? camara.dof * limitar((tIntro - INTRO.fin + 500) / 1000) : 0;
      if (a <= 0.01) return;
      if (!B.motas) B.motas = armarMotas(gl);
      gl.useProgram(M.p);
      gl.uniform1f(M.u.uAng, camara.paralaje);
      gl.uniform1f(M.u.uF, giro.F);
      gl.uniform1f(M.u.uCx, giro.cx);
      gl.uniform1f(M.u.uCy, giro.cy);
      gl.uniform1f(M.u.uK, t.k);
      gl.uniform1f(M.u.uTx, t.x + giro.px * t.k);
      gl.uniform1f(M.u.uTy, t.y + giro.py * t.k);
      gl.uniform1f(M.u.uW, ancho);
      gl.uniform1f(M.u.uH, alto);
      gl.uniform1f(M.u.uR, giro.R);
      gl.uniform1f(M.u.uTilt, giro.tilt);
      gl.uniform1f(M.u.uEsc, giro.esc);
      gl.uniform1f(M.u.uDpr, dpr);
      gl.uniform1f(M.u.uMotas, a * fz);
      gl.uniform3f(M.u.uColMota, 0.74, 0.84, 1);
      gl.blendFunc(gl.ONE, gl.ONE);
      atributo(M.aPos, B.motas.pos, 3);
      atributo(M.aExtra, B.motas.extra, 2);
      gl.drawArrays(gl.POINTS, 0, B.motas.n);
      [M.aPos, M.aExtra].forEach(l => { if (l >= 0) gl.disableVertexAttribArray(l); });
    };
    const R = objetivosResplandor(G, w, h);
    if (!R) { puntos(); motas(); return; }
    const dtF = R.tF ? Math.min(100, Math.max(0, ahora - R.tF)) : 1e9;
    R.tF = ahora;
    const metaF = (anim.oscuro ? 0.75 : 0.5) * (1 + 0.7 * Math.min(1, act.energia * 0.6)) * limitar((tIntro - INTRO.explota) / 1200);
    R.fuerza += (metaF - R.fuerza) * (completo() ? 1 - Math.exp(-dtF / 350) : 1);
    gl.bindFramebuffer(gl.FRAMEBUFFER, R.a1.fb);
    gl.viewport(0, 0, R.a1.w, R.a1.h);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.blendFunc(gl.ONE, gl.ONE);
    gl.uniform1f(P.u.uPeso, anim.oscuro ? 0.1 : 0.035);
    gl.uniform1f(P.u.uDpr, dpr * 0.5);
    puntos();
    gl.uniform1f(P.u.uPeso, 0);
    gl.uniform1f(P.u.uDpr, dpr);
    if (anim.oscuro) {
      gl.bindFramebuffer(gl.FRAMEBUFFER, R.escena.fb);
      gl.viewport(0, 0, w, h);
      gl.clear(gl.COLOR_BUFFER_BIT);
      if (R.esc > 1) {
        gl.blendColor(0, 0, 0, 1 / R.esc);
        gl.blendFunc(gl.CONSTANT_ALPHA, gl.ONE);
      }
      puntos();
    }
    desenfocarResplandor(G, R);
    mezclarResplandor(G, R, w, h, R.fuerza);
    if (!anim.oscuro) {
      gl.useProgram(P.p);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      puntos();
    }
    motas();
  }

  const MOTAS = 120;
  const MOTAS_TAPA = 45;
  function armarMotas(gl) {
    const azar = azarConSemilla(7070);
    const total = MOTAS + 2 * MOTAS_TAPA;
    const pos = new Float32Array(total * 3);
    const extra = new Float32Array(total * 2);
    for (let i = 0; i < MOTAS; i++) {
      const th = azar() * TAU;
      const r = giro.R * (1.3 + 0.8 * azar());
      pos[i * 3] = giro.cx + Math.sin(th) * r;
      pos[i * 3 + 1] = giro.cy + (azar() - 0.5) * 1.7 * giro.R;
      pos[i * 3 + 2] = Math.cos(th) * r;
      extra[i * 2] = 16 + 30 * azar();
      extra[i * 2 + 1] = 0.04 + 0.04 * azar();
    }
    for (let i = MOTAS; i < total; i++) {
      const th = azar() * TAU;
      const r = giro.R * 0.6 * Math.sqrt(azar());
      pos[i * 3] = giro.cx + Math.sin(th) * r;
      pos[i * 3 + 1] = giro.cy + (i < MOTAS + MOTAS_TAPA ? 1 : -1) * giro.R * (1.3 + 0.6 * azar());
      pos[i * 3 + 2] = Math.cos(th) * r;
      extra[i * 2] = 16 + 30 * azar();
      extra[i * 2 + 1] = 0.04 + 0.04 * azar();
    }
    const buf = datos => {
      const b = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, b);
      gl.bufferData(gl.ARRAY_BUFFER, datos, gl.STATIC_DRAW);
      return b;
    };
    return { pos: buf(pos), extra: buf(extra), n: total };
  }

  const catmull = (a, b, c, d, t) => 0.5 * (2 * b + (c - a) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (3 * b - a - 3 * c + d) * t * t * t);
  function puntoEspina(pts, t, out) {
    const n = pts.length - 1;
    const s = Math.min(n - 1e-6, Math.max(0, t * n));
    const i = Math.floor(s);
    const u = s - i;
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(n, i + 2)];
    for (let k = 0; k < 3; k++) out[k] = catmull(p0[k], p1[k], p2[k], p3[k], u);
    return out;
  }

  const TRAMOS_FIBRA = 16;
  const DENSIDAD_FIBRAS = 16;
  function armarFibras(S, anchoEn, hondura) {
    const azar = azarConSemilla(5151);
    const G = 12;
    const gx0 = 80;
    const gy0 = 20;
    const gw = 76;
    const gh = 58;
    let wg = new Float32Array(gw * gh);
    for (let j = 0; j < gh; j++) for (let i = 0; i < gw; i++) wg[j * gw + i] = anchoEn(gx0 + i * G, gy0 + j * G);
    for (let pasada = 0; pasada < 2; pasada++) {
      const suave = new Float32Array(gw * gh);
      for (let j = 0; j < gh; j++) {
        for (let i = 0; i < gw; i++) {
          let s = 0;
          for (let dj = -1; dj <= 1; dj++) {
            const jj = Math.min(gh - 1, Math.max(0, j + dj)) * gw;
            for (let di = -1; di <= 1; di++) s += wg[jj + Math.min(gw - 1, Math.max(0, i + di))];
          }
          suave[j * gw + i] = s / 9;
        }
      }
      wg = suave;
    }
    const anchoSuave = (x, y) => {
      const fx = Math.min(gw - 1.001, Math.max(0, (x - gx0) / G));
      const fy = Math.min(gh - 1.001, Math.max(0, (y - gy0) / G));
      const i = Math.floor(fx);
      const j = Math.floor(fy);
      const u = fx - i;
      const v = fy - j;
      const k = j * gw + i;
      const a = wg[k] + (wg[k + 1] - wg[k]) * u;
      const b = wg[k + gw] + (wg[k + gw + 1] - wg[k + gw]) * u;
      return a + (b - a) * v;
    };
    const T = ANATOMIA.tractos;
    let fibrasTotal = 0;
    for (const t of Object.values(T)) fibrasTotal += t.n;
    const pos = new Float32Array(fibrasTotal * TRAMOS_FIBRA * 6);
    const col = new Float32Array(fibrasTotal * TRAMOS_FIBRA * 8);
    const pt = new Float32Array((TRAMOS_FIBRA + 1) * 3);
    const e = [0, 0, 0];
    let k = 0;
    const fibra = (pts, h, r, abre, t0, t1) => {
      const ang = azar() * TAU;
      const rr = r * Math.sqrt(azar());
      const ox = Math.cos(ang) * rr;
      const oy = Math.sin(ang) * rr;
      const oz = (azar() * 2 - 1) * r;
      const onda = 3 + azar() * 4;
      const fase1 = azar() * TAU;
      const fase2 = azar() * TAU;
      const alfa = 0.05 + 0.03 * azar();
      for (let i = 0; i <= TRAMOS_FIBRA; i++) {
        const t = t0 + (t1 - t0) * i / TRAMOS_FIBRA;
        puntoEspina(pts, t, e);
        const abierto = 1 + abre * (2 * t - 1) ** 2;
        const bx = e[0] + (ox + Math.sin(t * onda + fase1) * r * 0.25) * abierto;
        const by = e[1] + (oy + Math.sin(t * onda * 1.3 + fase2) * r * 0.25) * abierto;
        const tope = Math.max(12, 0.8 * anchoSuave(bx, by));
        pt[i * 3] = (bx - 520) * S;
        pt[i * 3 + 1] = (by - 330) * S;
        pt[i * 3 + 2] = tope * Math.tanh((e[2] + oz * abierto) / tope) * h * S;
      }
      for (let i = 0; i < TRAMOS_FIBRA; i++) {
        const a = i * 3;
        const dx = Math.abs(pt[a + 3] - pt[a]);
        const dy = Math.abs(pt[a + 4] - pt[a + 1]);
        const dz = Math.abs(pt[a + 5] - pt[a + 2]);
        const rojo = dz + dx * 0.1 + dy * 0.15;
        const verde = dz * 0.1 + dx + dy * 0.3;
        const azul = dz * 0.15 + dx * 0.25 + dy;
        const m = Math.max(rojo, verde, azul) || 1;
        const cr = (rojo / m) ** 2;
        const cg = (verde / m) ** 2;
        const cb = (azul / m) ** 2;
        pos.set(pt.subarray(a, a + 6), k * 6);
        col.set([cr, cg, cb, alfa, cr, cg, cb, alfa], k * 8);
        k++;
      }
    };
    for (let i = 0; i < T.calloso.n; i++) {
      puntoEspina(T.calloso.espina, azar(), e);
      const xm = e[0];
      const ym = e[1] + (azar() - 0.5) * 14;
      const punta = s => [xm + (xm - 490) * 0.45 + (azar() - 0.5) * 70, ym - 70 - azar() * 120, s * (120 + azar() * 110)];
      const izq = punta(-1);
      const der = punta(1);
      fibra([izq, [(izq[0] + xm) / 2, ym - 22, -55], [xm, ym, 0], [(der[0] + xm) / 2, ym - 22, 55], der], 1, 4, 0.5, 0, 1);
    }
    for (let i = 0; i < T.corona.n; i++) {
      let xs = 520;
      let ys = 120;
      for (let intento = 0; intento < 60; intento++) {
        xs = 260 + azar() * 500;
        ys = 70 + azar() * 120;
        if (hondura(xs, ys) >= 28) break;
      }
      const zs = 70 + azar() * 150;
      const j = azar() - 0.5;
      fibra([[xs, ys, zs], [(xs + 600) / 2 + j * 40, 280 + j * 30, zs * 0.6], [600 + (xs - 520) * 0.08 + j * 20, 405, 48 + j * 12],
             [640 + j * 10, 525, 22], [651 + j * 8, 625 + azar() * 45, 12]], i % 2 ? 1 : -1, 4, 0.4, 0, 1);
    }
    for (const t of Object.values(T)) {
      if (!t.r) continue;
      for (let i = 0; i < t.n; i++) fibra(t.espina, i % 2 ? 1 : -1, t.r, t.abre, azar() * 0.25, 1 - azar() * 0.25);
    }
    const voxel = 14 * S;
    const celdas = new Int32Array(k);
    const densidad = new Map();
    for (let i = 0; i < k; i++) {
      const a = i * 6;
      const c = Math.floor((pos[a] + pos[a + 3]) / (2 * voxel)) + 200 + (Math.floor((pos[a + 1] + pos[a + 4]) / (2 * voxel)) + 200) * 400
        + (Math.floor((pos[a + 2] + pos[a + 5]) / (2 * voxel)) + 200) * 160000;
      celdas[i] = c;
      densidad.set(c, (densidad.get(c) || 0) + 1);
    }
    for (let i = 0; i < k; i++) {
      const f = Math.min(1, DENSIDAD_FIBRAS / densidad.get(celdas[i]));
      col[i * 8 + 3] *= f;
      col[i * 8 + 7] *= f;
    }
    return { pos, col, n: k * 2 };
  }

  function armarVias(S) {
    const L = ANATOMIA.lobulos;
    const n = L.length;
    const idx = new Map(L.map((l, i) => [l.id, i]));
    const vias = new Float32Array(n * n * 3);
    const cruce = new Float32Array(n * n * 3);
    const hay = new Uint8Array(n * n);
    const e = [0, 0, 0];
    const cercano = (pts, x, y) => {
      let mejor = Infinity;
      let t = 0;
      for (let i = 0; i <= 128; i++) {
        puntoEspina(pts, i / 128, e);
        const d = (e[0] - x) ** 2 + (e[1] - y) ** 2;
        if (d < mejor) { mejor = d; t = i / 128; }
      }
      return t;
    };
    const calloso = ANATOMIA.tractos.calloso.espina;
    for (const [clave, via] of Object.entries(ANATOMIA.vias)) {
      const [a, b] = clave.split('-').map(id => idx.get(id));
      if (a === undefined || b === undefined) continue;
      const mx = (L[a].x + L[b].x) / 2;
      const my = (L[a].y + L[b].y) / 2;
      const esp = ANATOMIA.tractos[Array.isArray(via) ? via[0] : via].espina;
      puntoEspina(esp, Array.isArray(via) ? via[1] : cercano(esp, mx, my), e);
      const v = [(e[0] - 520) * S, (e[1] - 330) * S, Math.abs(e[2]) * S];
      puntoEspina(calloso, cercano(calloso, mx, my), e);
      const c = [(e[0] - 520) * S, (e[1] - 330) * S, 0];
      for (const k of [a * n + b, b * n + a]) {
        vias.set(v, k * 3);
        cruce.set(c, k * 3);
        hay[k] = 1;
      }
    }
    return { n, idx, vias, cruce, hay, corteza: Uint8Array.from(L, l => (l.id === 'cerebelo' || l.id === 'tronco' ? 0 : 1)),
             px: new Float32Array(n * n * 3), py: new Float32Array(n * n * 3), marca: new Int32Array(n * n * 3), tmp: [0, 0, 0] };
  }

  function armarCerebro() {
    const glEnCurso = neuronasGL ? null : prepararGL();
    const S = (36 * Math.sqrt(Math.max(1, nodos.length)) + 80) * 3 / 1000;
    const P = (x, y) => [(x - 520) * S, (y - 330) * S];
    const trazo = (cmds, p) => {
      p = p || new Path2D();
      for (const c of cmds) {
        if (c[0] === 'M') p.moveTo(...P(c[1], c[2]));
        else if (c[0] === 'L') p.lineTo(...P(c[1], c[2]));
        else if (c[0] === 'C') p.bezierCurveTo(...P(c[1], c[2]), ...P(c[3], c[4]), ...P(c[5], c[6]));
        else if (c[0] === 'Z') p.closePath();
      }
      return p;
    };
    const cuerpo = trazo(ANATOMIA.cuerpo);
    const cerebelo = trazo(ANATOMIA.cerebelo);
    const tronco = trazo(ANATOMIA.tronco);
    const todo = new Path2D();
    todo.addPath(cuerpo);
    todo.addPath(cerebelo);
    todo.addPath(tronco);
    const adentro = (camino, bx, by) => ctxForma.isPointInPath(camino, ...P(bx, by));

    const cubica = (a, b, c, d, t) => { const u = 1 - t; return u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d; };
    const recorrer = (cmds, cada, fn) => {
      let cx = 0, cy = 0, sx = 0, sy = 0;
      for (const c of cmds) {
        if (c[0] === 'M') { cx = sx = c[1]; cy = sy = c[2]; continue; }
        if (c[0] === 'L' || c[0] === 'Z') {
          const tx = c[0] === 'Z' ? sx : c[1];
          const ty = c[0] === 'Z' ? sy : c[2];
          const n = Math.max(1, Math.round(Math.hypot(tx - cx, ty - cy) / cada));
          for (let i = 0; i < n; i++) fn(cx + (tx - cx) * i / n, cy + (ty - cy) * i / n);
          cx = tx; cy = ty;
          continue;
        }
        const largo = Math.hypot(c[1] - cx, c[2] - cy) + Math.hypot(c[3] - c[1], c[4] - c[2]) + Math.hypot(c[5] - c[3], c[6] - c[4]);
        const n = Math.max(2, Math.round(largo / cada));
        for (let i = 0; i < n; i++) fn(cubica(cx, c[1], c[3], c[5], i / n), cubica(cy, c[2], c[4], c[6], i / n));
        cx = c[5]; cy = c[6];
      }
    };
    const campo = cmds => {
      const celda = 20;
      const puntos = [];
      recorrer(cmds, 3, (x, y) => puntos.push([x, y]));
      let gx0 = 0, gy0 = 0, ancho = 0, alto = 0;
      if (puntos.length) {
        const gxs = puntos.map(p => Math.floor(p[0] / celda));
        const gys = puntos.map(p => Math.floor(p[1] / celda));
        gx0 = Math.min(...gxs);
        gy0 = Math.min(...gys);
        ancho = Math.max(...gxs) - gx0 + 1;
        alto = Math.max(...gys) - gy0 + 1;
      }
      const celdas = new Array(ancho * alto);
      puntos.forEach(p => {
        const k = (Math.floor(p[0] / celda) - gx0) * alto + Math.floor(p[1] / celda) - gy0;
        (celdas[k] || (celdas[k] = [])).push(p);
      });
      const cerca = [0, 0];
      const medir = (x, y, tope) => {
        const gx = Math.floor(x / celda);
        const gy = Math.floor(y / celda);
        let mejor = Infinity;
        let mx = x;
        let my = y;
        const anillos = Math.ceil(tope / celda) + 1;
        for (let r = 0; r <= anillos; r++) {
          for (let dx = -r; dx <= r; dx++) {
            const cx = gx + dx - gx0;
            if (cx < 0 || cx >= ancho) continue;
            const paso = dx === -r || dx === r ? 1 : 2 * r;
            for (let dy = -r; dy <= r; dy += paso) {
              const cy = gy + dy - gy0;
              if (cy < 0 || cy >= alto) continue;
              const l = celdas[cx * alto + cy];
              if (!l) continue;
              for (const p of l) {
                const d = (p[0] - x) ** 2 + (p[1] - y) ** 2;
                if (d < mejor) { mejor = d; mx = p[0]; my = p[1]; }
              }
            }
          }
          if (mejor <= (r * celda) ** 2) break;
        }
        cerca[0] = mx;
        cerca[1] = my;
        return Math.min(Math.sqrt(mejor), tope);
      };
      medir.cerca = cerca;
      return medir;
    };
    const dCuerpo = campo(ANATOMIA.cuerpo);
    const dCerebelo = campo(ANATOMIA.cerebelo);
    const dTronco = campo(ANATOMIA.tronco);
    const dSurcos = campo([].concat(...ANATOMIA.surcos));
    const GRIETA = 16;
    const anchoCuerpo = (bx, by) => {
      const u = (bx - 520) / 460;
      return 350 * Math.sqrt(Math.min(1, dCuerpo(bx, by, 160) / 160)) * (0.78 + 0.22 * Math.max(0, 1 - u * u));
    };
    const anchoCerebelo = (bx, by) => 190 * Math.sqrt(Math.min(1, dCerebelo(bx, by, 70) / 70));
    const anchoTronco = (bx, by) => 38 * Math.sqrt(Math.min(1, dTronco(bx, by, 22) / 22));
    const anchoEn = (bx, by) => adentro(cuerpo, bx, by) ? anchoCuerpo(bx, by)
      : adentro(cerebelo, bx, by) ? anchoCerebelo(bx, by)
      : adentro(tronco, bx, by) ? anchoTronco(bx, by) : 0;

    const azar = azarConSemilla(1790);
    const colorGrupo = id => { const g = grupoPorId.get(id); return g ? g.color : '#94a3b8'; };
    const grupoCercano = (bx, by) => {
      let mejor = ANATOMIA.lobulos[0];
      let d = Infinity;
      for (const l of ANATOMIA.lobulos) {
        if (l.id === 'cerebelo' || l.id === 'tronco') continue;
        const dd = (l.x - bx) ** 2 + (l.y - by) ** 2;
        if (dd < d) { d = dd; mejor = l; }
      }
      return mejor.grupo;
    };
    const grupoDe = id => ANATOMIA.lobulos.find(l => l.id === id).grupo;
    const mezclarHex = (a, b, t) => {
      const ca = hexARgb(a);
      const cb = hexARgb(b);
      return '#' + ca.map((v, i) => Math.round((v + (cb[i] - v) * t) * 255).toString(16).padStart(2, '0')).join('');
    };
    const suave = (a, b, x) => { const t = limitar((x - a) / (b - a)); return t * t * (3 - 2 * t); };
    const hashRejilla = (i, j) => {
      let h = Math.imul(i, 374761393) ^ Math.imul(j, 668265263);
      h = Math.imul(h ^ (h >>> 13), 1274126177);
      return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
    };
    const ruido = (x, y) => {
      const i = Math.floor(x);
      const j = Math.floor(y);
      let fx = x - i;
      let fy = y - j;
      fx = fx * fx * (3 - 2 * fx);
      fy = fy * fy * (3 - 2 * fy);
      const a = hashRejilla(i, j);
      const b = hashRejilla(i + 1, j);
      const c = hashRejilla(i, j + 1);
      const d = hashRejilla(i + 1, j + 1);
      return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy;
    };
    const fbm = (x, y) => {
      let v = 0;
      let a = 0.5;
      for (let o = 0; o < 4; o++) { v += a * ruido(x, y); x *= 2.07; y *= 2.07; a *= 0.5; }
      return v;
    };
    const campoPliegue = (x, y) => fbm(x + 0.6 * fbm(x * 1.6 + 4, y * 1.6), y + 0.6 * fbm(x * 1.6, y * 1.6 + 9));
    const pliegueCuerpo = (bx, by, h) => {
      const x = bx / 120 + (h < 0 ? 37.3 : 0);
      const y = by / 120;
      const q = campoPliegue(x, y);
      const gx = (campoPliegue(x + 0.01, y) - q) / 0.01;
      const gy = (campoPliegue(x, y + 0.01) - q) / 0.01;
      const d = Math.abs(Math.sin(q * 38)) * 120 / (38 * (Math.hypot(gx, gy) + 1e-4));
      return 1 - suave(0, 3.2, d);
    };
    const surcoCuerpo = (bx, by, h) => {
      const dn = dSurcos(bx, by, 24);
      return Math.max(pliegueCuerpo(bx, by, h) * 0.85, Math.exp(-dn * dn / 60));
    };
    const FOLIA = [700, 522, 9];
    const desvioFolia = (a, r) => 7 * (ruido(a * 2.2 + r * 0.05, r * 0.11) - 0.5);
    const surcoCerebelo = (bx, by) => {
      const r = Math.hypot(bx - FOLIA[0], by - FOLIA[1]);
      return 0.5 - 0.5 * Math.cos(TAU * (r - desvioFolia(Math.atan2(by - FOLIA[1], bx - FOLIA[0]), r)) / FOLIA[2]);
    };
    const FORMAS = {
      cuerpo: { dist: dCuerpo, A: 350, T: 160, min: GRIETA, surco: surcoCuerpo, hondo: 0.09, elipse: [520, 290, 440, 260, 350], luz: 1 },
      cerebelo: { dist: dCerebelo, A: 190, T: 70, min: 7, surco: surcoCerebelo, hondo: 0.07, elipse: [815, 525, 135, 80, 190], luz: 0.65 },
      tronco: { dist: dTronco, A: 38, T: 22, min: 5, surco: null, hondo: 0, elipse: null, luz: 0.8 }
    };
    const pendiente = [0, 0];
    const anchoConPendiente = (f, bx, by) => {
      const d = f.dist(bx, by, f.T);
      let w = f.A * Math.sqrt(Math.min(1, d / f.T));
      pendiente[0] = 0;
      pendiente[1] = 0;
      if (d > 0 && d < f.T) {
        const k = f.A / (2 * Math.sqrt(f.T * Math.max(d, 1.5))) / d;
        pendiente[0] = k * (bx - f.dist.cerca[0]);
        pendiente[1] = k * (by - f.dist.cerca[1]);
      }
      if (f === FORMAS.cuerpo) {
        const u = (bx - 520) / 460;
        const g = 0.78 + 0.22 * Math.max(0, 1 - u * u);
        pendiente[0] *= g;
        pendiente[1] *= g;
        if (u * u < 1) pendiente[0] -= w * 0.44 * u / 460;
        w *= g;
      }
      return w;
    };
    const normal = [0, 0, 0];
    const superficieEn = (f, bx, by, h) => {
      const w = anchoConPendiente(f, bx, by);
      let gx = pendiente[0];
      let gy = pendiente[1];
      let W = w;
      if (f.surco) {
        const e = 2;
        const s = f.surco(bx, by, h);
        let sx = w * f.hondo * (f.surco(bx + e, by, h) - f.surco(bx - e, by, h)) / (2 * e);
        let sy = w * f.hondo * (f.surco(bx, by + e, h) - f.surco(bx, by - e, h)) / (2 * e);
        const m = Math.hypot(sx, sy);
        if (m > 1.1) { sx *= 1.1 / m; sy *= 1.1 / m; }
        W = w * (1 - f.hondo * s);
        gx = gx * (1 - f.hondo * s) - sx;
        gy = gy * (1 - f.hondo * s) - sy;
      }
      const l = Math.hypot(gx, gy, 1);
      let nx = -gx / l;
      let ny = -gy / l;
      let nz = h / l;
      if (f.elipse) {
        const [ex, ey, rx, ry, rz] = f.elipse;
        const qx = (bx - ex) / (rx * rx);
        const qy = (by - ey) / (ry * ry);
        const qz = h * W / (rz * rz);
        const lq = Math.hypot(qx, qy, qz) || 1;
        nx += 0.8 * qx / lq;
        ny += 0.8 * qy / lq;
        nz += 0.8 * qz / lq;
      }
      const ln = Math.hypot(nx, ny, nz) || 1;
      normal[0] = nx / ln;
      normal[1] = ny / ln;
      normal[2] = nz / ln;
      return W;
    };
    const px = [];
    const agregar = (bx, by, zb, grupo, r0, r1, a0, a1, clase, color) => {
      const [x, y] = P(bx, by);
      const p = { x, y, z: zb * S, r: (r0 + azar() * (r1 - r0)) * S, a: a0 + azar() * (a1 - a0), c: color || colorGrupo(grupo || grupoCercano(bx, by)), clase, nx: 0, ny: 0, nz: 0, nw: 0 };
      px.push(p);
      return p;
    };
    const iluminar = (p, peso) => {
      p.nx = normal[0];
      p.ny = normal[1];
      p.nz = normal[2];
      p.nw = peso;
    };
    const lado = () => (azar() < 0.5 ? -1 : 1);
    const superficie = (bx, by, f, grupo, r0, r1, a0, a1, lados, color) => {
      (lados === 2 ? [-1, 1] : lados ? [lados] : [lado()]).forEach(h => {
        const W = superficieEn(f, bx, by, h);
        if (W < f.min + 2) return;
        const v = 0.55 + 0.9 * azar() ** 2;
        iluminar(agregar(bx, by, h * Math.max(f.min, W * (0.95 + 0.05 * azar())), grupo, r0 * v, r1 * v, a0 * 0.85, a1 * 0.85, 'borde', color), f.luz);
      });
    };

    for (let i = 0, n = 0; i < 60000 && n < 7200; i++) {
      const bx = 90 + azar() * 870;
      const by = 35 + azar() * 520;
      if (!adentro(cuerpo, bx, by)) continue;
      const h = lado();
      if (azar() > 0.35 + 0.65 * surcoCuerpo(bx, by, h)) continue;
      const antes = px.length;
      superficie(bx, by, FORMAS.cuerpo, null, 0.8, 1.7, 0.3, 0.75, h);
      if (px.length > antes) n++;
    }
    for (let i = 0, n = 0; i < 20000 && n < 420; i++) {
      const bx = 90 + azar() * 870;
      const by = 35 + azar() * 520;
      if (!adentro(cuerpo, bx, by) || anchoCuerpo(bx, by) < GRIETA + 8) continue;
      agregar(bx, by, lado() * (GRIETA + azar() * 5), null, 0.7, 1.4, 0.04, 0.12, 'medial');
      n++;
    }
    recorrer(ANATOMIA.cuerpo, 2.6, (bx, by) => {
      if (azar() < 0.3) return;
      const l = Math.hypot(520 - bx, 300 - by) || 1;
      const d = 1 + azar() * 13;
      const x = bx + (520 - bx) / l * d;
      const y = by + (300 - by) / l * d;
      const v = azar() ** 2;
      const h = lado();
      const W = superficieEn(FORMAS.cuerpo, x, y, h);
      iluminar(agregar(x, y, h * Math.max(GRIETA, W * (0.9 + 0.1 * azar())), null, 0.5 + 1.5 * v, 0.7 + 1.7 * v, 0.16, 0.5 - 0.2 * v, 'borde'), 0.35);
    });
    ANATOMIA.surcos.forEach(s => recorrer(s, 3.4, (bx, by) => {
      superficie(bx + (azar() - 0.5) * 6, by + (azar() - 0.5) * 6, FORMAS.cuerpo, null, 0.8, 1.7, 0.5, 0.95, 2);
    }));
    for (let i = 0, n = 0; i < 120000 && n < 3600; i++) {
      const bx = 110 + azar() * 820;
      const by = 50 + azar() * 490;
      const h = lado();
      if (pliegueCuerpo(bx, by, h) < 0.7 || !adentro(cuerpo, bx, by)) continue;
      const antes = px.length;
      superficie(bx, by, FORMAS.cuerpo, null, 0.7, 1.5, 0.4, 0.8, h);
      if (px.length > antes) n++;
    }
    const gCerebelo = grupoDe('cerebelo');
    const acero = mezclarHex(colorGrupo(gCerebelo), '#a9c3e6', 0.5);
    for (let i = 0, n = 0; i < 20000 && n < 1300; i++) {
      const bx = 675 + azar() * 280;
      const by = 435 + azar() * 180;
      if (!adentro(cerebelo, bx, by)) continue;
      superficie(bx, by, FORMAS.cerebelo, gCerebelo, 0.7, 1.5, 0.3, 0.7, 0, acero);
      n++;
    }
    for (let r = FOLIA[2] * 2; r < 260; r += FOLIA[2]) {
      for (let a = -1.9; a <= 1.9; a += 3.2 / r) {
        const rr = r + desvioFolia(a, r);
        const bx = FOLIA[0] + Math.cos(a) * rr + (azar() - 0.5) * 1.6;
        const by = FOLIA[1] + Math.sin(a) * rr + (azar() - 0.5) * 1.6;
        if (adentro(cerebelo, bx, by)) superficie(bx, by, FORMAS.cerebelo, gCerebelo, 0.45, 0.95, 0.32, 0.62, 2, acero);
      }
    }
    const gTronco = grupoDe('tronco');
    for (let i = 0, n = 0; i < 8000 && n < 520; i++) {
      const bx = 585 + azar() * 125;
      const by = 495 + azar() * 200;
      if (!adentro(tronco, bx, by)) continue;
      superficie(bx, by, FORMAS.tronco, gTronco, 0.7, 1.5, 0.35, 0.75, 0);
      n++;
    }
    for (let i = 0, n = 0; i < 20000 && n < 1500; i++) {
      const bx = 90 + azar() * 870;
      const by = 35 + azar() * 660;
      const w = anchoEn(bx, by);
      if (w <= 0) continue;
      const enCuerpo = adentro(cuerpo, bx, by);
      const grupo = enCuerpo ? null : adentro(cerebelo, bx, by) ? gCerebelo : gTronco;
      let z = (azar() * 2 - 1) * w * 0.85;
      if (enCuerpo && Math.abs(z) < GRIETA + 4) z = (z < 0 ? -1 : 1) * Math.min(w * 0.85, GRIETA + 4 + Math.abs(z));
      agregar(bx, by, z, grupo, 0.6, 1.3, 0.06, 0.18, 'volumen', grupo === gCerebelo ? acero : null);
      n++;
    }

    const celda = 15 * S;
    const rejilla = new Map();
    const llave = (x, y, z) => Math.floor(x / celda) + ',' + Math.floor(y / celda) + ',' + Math.floor(z / celda);
    px.forEach((p, i) => {
      if (p.clase === 'volumen') return;
      const k = llave(p.x, p.y, p.z);
      if (!rejilla.has(k)) rejilla.set(k, []);
      rejilla.get(k).push(i);
    });
    const vecinos = [];
    const ady = px.map(() => []);
    px.forEach((p, i) => {
      if (p.clase === 'volumen') return;
      const gx = Math.floor(p.x / celda);
      const gy = Math.floor(p.y / celda);
      const gz = Math.floor(p.z / celda);
      const cerca = [];
      for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) {
        const l = rejilla.get((gx + dx) + ',' + (gy + dy) + ',' + (gz + dz));
        if (!l) continue;
        for (const j of l) {
          if (j <= i) continue;
          const d = (px[j].x - p.x) ** 2 + (px[j].y - p.y) ** 2 + (px[j].z - p.z) ** 2;
          if (d < celda * celda) cerca.push([d, j]);
        }
      }
      cerca.sort((a, b) => a[0] - b[0]);
      cerca.slice(0, 2).forEach(([, j]) => {
        vecinos.push([i, j]);
        ady[i].push(j);
        ady[j].push(i);
      });
    });

    giro.cx = 10 * S;
    giro.cy = 35 * S;
    giro.R = 460 * S;
    giro.F = 2.6 * 900 * S;

    const lobulos = ANATOMIA.lobulos.map(l => {
      const [x, y] = P(l.x, l.y);
      const [ex, ey] = P(l.ex, l.ey);
      return { ...l, wx: x, wy: y, wr: l.r * S, wex: ex, wey: ey };
    });
    const anclas = {};
    Object.entries(ANATOMIA.anclas).forEach(([id, v]) => {
      const [x, y] = P(v[0], v[1]);
      anclas[id] = [x, y, v[2] * S, (v[3] || 1) * v[2] * S];
    });
    const [dx, dy] = P(...ANATOMIA.anclaPorDefecto);
    const lTronco = lobulos.find(l => l.id === 'tronco');
    cerebro = { S, cuerpo, cerebelo, tronco, todo, lobulos, anclas, porDefecto: [dx, dy, 90 * S, 90 * S],
                nido: lTronco ? [lTronco.wx, lTronco.wy, 0] : [giro.cx, giro.cy, 0], introT0: 0, introPaso: 4,
                px, ady, vecinos, grieta: GRIETA * S, anchoMundo: (x, y) => anchoEn(x / S + 520, y / S + 330) * S,
                elipses: { cuerpo: FORMAS.cuerpo.elipse, cerebelo: FORMAS.cerebelo.elipse, tronco: [652, 600, 45, 110, 38] },
                rutas: armarVias(S) };

    if (!neuronasGL) neuronasGL = terminarGL(glEnCurso);
    if (neuronasGL) {
      cerebro.fibras = armarFibras(S, anchoEn, (bx, by) => adentro(cuerpo, bx, by) ? dCuerpo(bx, by, 40) : 0);
      cerebro.gl = subirNeuronas(px, vecinos, cerebro.fibras);
    } else {
      cerebro.baldes = baldesDe(px);
    }
  }

  function baldesDe(px) {
    const baldes = new Map();
    px.forEach((p, i) => {
      if (i % 3) return;
      const nivel = Math.min(4, Math.floor(p.a / 0.2));
      const k = p.c + '|' + nivel;
      let b = baldes.get(k);
      if (!b) baldes.set(k, b = { color: p.c, alfa: (nivel + 0.5) * 0.2, camino: new Path2D() });
      b.camino.moveTo(p.x + p.r, p.y);
      b.camino.arc(p.x, p.y, p.r, 0, TAU);
    });
    return [...baldes.values()];
  }

  function fuerzaCerebro() {
    let lista = [];
    const f = alfa => {
      if (!cerebro) return;
      for (const n of lista) {
        if (ctxForma.isPointInPath(cerebro.todo, n.x, n.y)) continue;
        const tx = n._tx !== undefined ? n._tx : grupoPorId.get(n.grupo).ax;
        const ty = n._ty !== undefined ? n._ty : grupoPorId.get(n.grupo).ay;
        n.vx += (tx - n.x) * 0.3 * alfa;
        n.vy += (ty - n.y) * 0.3 * alfa;
      }
    };
    f.initialize = ns => { lista = ns; };
    return f;
  }

  function dibujarCerebro(t, k) {
    if (!cerebro) return;
    if (neuronasGL) pintarNeuronas(performance.now());
    else if (cerebro.baldes) {
      const fz = limitar((3 - k) / 1.2);
      if (fz > 0) {
        ctx.save();
        ctx.setTransform(dpr * k, 0, 0, dpr * k, dpr * t.x, dpr * t.y);
        ctx.globalAlpha = fz;
        for (const b of cerebro.baldes) {
          ctx.fillStyle = aRgba(b.color, Math.min(1, b.alfa));
          ctx.fill(b.camino);
        }
        ctx.restore();
      }
    }
    const lado = Math.abs(Math.cos(giro.ang)) * limitar((Math.cos(giro.tilt) - 0.35) / 0.5);
    const a = limitar((1.5 - k) / 0.7) * fundidoIntro(INTRO.nombres - 300, 700);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.font = FUENTE_ROTULO;
    if (!cerebro.rotulos) {
      const antes = cerebro.rotuloPorGrupo;
      cerebro.rotulos = cerebro.lobulos.map(l => {
        const texto = l.anatomico.toUpperCase();
        const w = ctx.measureText(texto).width;
        const previo = antes && antes.get(l.grupo);
        return { l, grupo: l.grupo, texto, w, wt: w, sufijo: '', ws: 0, toques: previo ? previo.toques : 0, calor: previo ? previo.calor : 0, x: 0, y: 0, a: 0,
          base: 0, vis: previo ? previo.vis : 1, dy: previo ? previo.dy : 0 };
      });
      cerebro.rotuloPorGrupo = new Map(cerebro.rotulos.map(r => [r.grupo, r]));
    }
    const e = escalaTexto;
    const ahoraR = performance.now();
    const dtR = Math.min(64, Math.max(0, ahoraR - (anim.tRot || ahoraR)));
    anim.tRot = ahoraR;
    const fR = anim.modo === 'nada' ? 1 : 1 - Math.exp(-dtR / 220);
    for (const r of cerebro.rotulos) {
      const suf = r.toques ? (r.toques === 1 ? '1 toque' : r.toques + ' toques') : '';
      if (suf !== r.sufijo) {
        r.sufijo = suf;
        ctx.font = FUENTE_TOQUES;
        r.ws = suf ? ctx.measureText(suf).width : 0;
        ctx.font = FUENTE_ROTULO;
        r.w = r.wt + (suf ? 7 * e + r.ws : 0);
      }
      const c = neuronasGL ? gestos.contraer : 0;
      const p = proyectar(r.l.wex + (giro.cx - r.l.wex) * c, r.l.wey + (giro.cy - r.l.wey) * c, 0);
      let x = p.x * k + t.x;
      let y = p.y * k + t.y;
      const cg = centrosGrupo.get(r.grupo);
      if (cg && cg.c && lado < 1) {
        x += (cg.sx / cg.c * k + t.x - x) * (1 - lado);
        y += (cg.sy / cg.c * k + t.y - y) * (1 - lado);
      }
      const xMin = 12 + r.w / 2;
      const xMax = ancho - 12 - r.w / 2;
      r.x = xMax > xMin ? Math.min(xMax, Math.max(xMin, x)) : x;
      r.base = Math.min(alto - 12, y);
      const tp = vivo.tapaPanel;
      if (tp && r.x - r.w / 2 < tp[2] && r.x + r.w / 2 > tp[0] && r.base - 8 * e < tp[3] && r.base + 8 * e > tp[1]) {
        const dx = tp[2] + 8 + r.w / 2 - r.x;
        const dy = r.base - (tp[1] - 12);
        if (dx <= dy && tp[2] + 8 + r.w <= ancho - 12) r.x += dx;
        else if (tp[1] < 24) r.base = Math.min(alto - 12, tp[3] + 20 * e);
        else r.base = Math.max(12, tp[1] - 12);
      }
    }
    const puestas = [];
    const notas = anim.cajasNotas || [];
    const tamano = r => { const cg = centrosGrupo.get(r.grupo); return cg ? cg.c : 0; };
    for (const r of cerebro.rotulos.slice().sort((p, q) => tamano(q) - tamano(p))) {
      let meta = null;
      for (const d of [0, -15 * e, 15 * e]) {
        const caja = [r.x - r.w / 2 - 2, r.base + d - 8 * e, r.x + r.w / 2 + 2, r.base + d + 8 * e];
        if (choca(caja, puestas) || choca(caja, notas)) continue;
        puestas.push(caja);
        meta = d;
        break;
      }
      r.vis += ((meta === null ? 0 : 1) - r.vis) * fR;
      if (Math.abs(r.vis - (meta === null ? 0 : 1)) < 0.01) r.vis = meta === null ? 0 : 1;
      if (meta !== null) r.dy = Math.abs(meta - r.dy) < 0.3 ? meta : r.dy + (meta - r.dy) * fR;
      r.y = r.base + r.dy;
      r.a = a * r.vis;
      if (r.vis !== (meta === null ? 0 : 1) || (meta !== null && r.dy !== meta)) anim.escenaHasta = Math.max(anim.escenaHasta, ahoraR + 34);
    }
    if (a <= 0.02) return;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    for (const r of cerebro.rotulos) {
      const ra = r.a;
      if (ra <= 0.02) continue;
      const g = grupoPorId.get(r.grupo);
      const color = g ? g.color : colores.texto;
      const brillo = Math.min(1, r.calor / 3);
      const x0 = r.x - r.w / 2;
      if (brillo > 0.02 && /^#[0-9a-f]{6}$/i.test(color)) {
        ctx.globalAlpha = brillo * ra * (anim.oscuro ? 0.4 : 0.22);
        ctx.drawImage(sprite(color, 'brillo'), x0 - 16 * e, r.y - 17 * e, r.w + 32 * e, 34 * e);
      }
      if (anim.oscuro) {
        ctx.globalAlpha = (0.75 + 0.25 * brillo) * ra;
        ctx.fillStyle = brillo > 0.1 ? aclarar(color, Math.round(brillo * 4) * 0.08) : color;
      } else {
        ctx.globalAlpha = ra;
        ctx.lineJoin = 'round';
        ctx.lineWidth = 3;
        ctx.strokeStyle = colores.halo;
        ctx.strokeText(r.texto, x0, r.y);
        ctx.fillStyle = legibleEnClaro(color);
      }
      ctx.fillText(r.texto, x0, r.y);
      if (ra > 0.15) anim.cajasTexto.push([x0 - 2, r.y - 8 * e, x0 + r.w + 2, r.y + 8 * e, ra]);
      if (r.sufijo) {
        ctx.font = FUENTE_TOQUES;
        ctx.globalAlpha = (anim.oscuro ? 0.6 + 0.3 * brillo : 1) * ra;
        if (!anim.oscuro) ctx.strokeText(r.sufijo, x0 + r.wt + 7 * e, r.y + 0.5);
        ctx.fillText(r.sufijo, x0 + r.wt + 7 * e, r.y + 0.5);
        ctx.font = FUENTE_ROTULO;
      }
    }
    ctx.globalAlpha = 1;
  }

  const BLANCO = { x: 0, y: 0, z: 0, w: 0, ultima: null };
  function blancoCamara(ahora) {
    const chats = vivo.chats;
    if (!chats || !chats.size) return null;
    const B = BLANCO;
    B.x = B.y = B.z = B.w = 0;
    B.ultima = null;
    let tUltima = -Infinity;
    const sumar = (o, peso) => {
      const n = o.hacia;
      if (!n || !n._visible || n._sx === undefined) return;
      B.x += n.x * peso;
      B.y += n.y * peso;
      B.z += (n.z || 0) * peso;
      B.w += peso;
      if (o.t0 > tUltima) { tUltima = o.t0; B.ultima = n; }
    };
    for (const c of chats.values()) {
      if (ahora - c.tUlt > CHAT_QUIETO) continue;
      const trabaja = c.estado === 'trabajando' || c.estado === 'compactando';
      if (!trabaja && !(c.estado === 'esperando' && ahora - c.tUlt < CAMARA.esperando)) continue;
      sumar(c, 1);
      if (trabaja) for (const s of c.subs.values()) if (ahora - s.tUlt < 120000) sumar(s, 0.4);
    }
    return B.w > 0 && B.ultima ? B : null;
  }

  function elegirAngulo(phi, actual) {
    const W = CAMARA.ventana;
    const costado = a => Math.min(Math.abs(envolver(a)), Math.abs(envolver(a - Math.PI)));
    const costo = a => costado(a) + 0.5 * Math.abs(envolver(a - actual));
    let mejor = actual;
    let min = Math.abs(envolver(actual - phi)) <= W ? costo(actual) : Infinity;
    for (const lado of [0, Math.PI]) {
      const d = Math.max(-W, Math.min(W, envolver(lado - phi)));
      const a = envolver(phi + d);
      const c = costo(a);
      if (c < min) { min = c; mejor = a; }
    }
    return mejor;
  }

  function soltarCamara(conInercia) {
    if (conInercia && Math.abs(camara.vel) > giro.vel) {
      giro.inercia = camara.vel;
      giro.dir = Math.sign(camara.vel);
    }
    camara.activo = false;
    camara.vel = 0;
  }

  function dirigir(ahora) {
    const C = camara;
    const usuario = !!(giro.arrastre || arrastrando || estado.seleccionado || estado.coincidencias);
    if (usuario) C.toque = ahora;
    const libre = ahora - C.toque >= CAMARA.espera;
    const puede = C.modo === 'seguir' && libre && graficoListo && estado.vista === 'grafo'
      && !introCorriendo(ahora);
    const b = puede ? blancoCamara(ahora) : null;
    if (!b) {
      if (C.activo) soltarCamara(!giro.arrastre && !arrastrando);
      return false;
    }
    if (b.ultima !== C.nota && (!C.nota || !C.nota._visible || ahora - C.tNota >= CAMARA.foco)) {
      C.nota = b.ultima;
      C.tNota = ahora;
    }
    const n = C.nota;
    const w = b.w + 1;
    C.x = (b.x + n.x) / w;
    C.y = (b.y + n.y) / w;
    C.z = (b.z + (n.z || 0)) / w;
    const dx = C.x - giro.cx;
    const cerca = Math.hypot(dx, C.z) < 30 * cerebro.S;
    const phi = Math.atan2(-dx, C.z);
    if (!C.activo) {
      C.activo = true;
      C.vel = giro.inercia || (giro.activo ? giro.vel * (giro.dir || 1) * ritmo.giro : 0);
      giro.inercia = 0;
      C.meta = cerca ? giro.ang : elegirAngulo(phi, giro.ang);
      C.tMeta = ahora;
    } else if (!cerca && !estado.hover && ahora - C.tMeta >= CAMARA.cambio && Math.abs(envolver(C.meta - phi)) > CAMARA.ventana + 0.1) {
      C.meta = elegirAngulo(phi, giro.ang);
      C.tMeta = ahora;
    }
    return true;
  }

  function enfocar(dt, sigue) {
    const C = camara;
    const n = sigue ? C.nota : null;
    const meta = n && n._visible ? proyectar(n.x, n.y, n.z || 0).d : 0;
    C.prof += (meta - C.prof) * (1 - Math.exp(-dt / 700));
    if (Math.abs(meta - C.prof) < 0.05) C.prof = meta;
    C.dof = anim.enfoque && anim.nivel === 2 ? C.peso : 0;
  }

  function correrCamara(dt) {
    const C = camara;
    let mx = 0;
    let my = 0;
    if (C.activo && C.peso > 0.001) {
      const t = transformacion;
      const p = proyectar(C.x, C.y, C.z);
      const sx = (p.x - giro.px) * t.k + t.x;
      const sy = (p.y - giro.py) * t.k + t.y;
      const lx = CAMARA.corrimiento * ancho;
      const ly = CAMARA.corrimiento * alto;
      mx = Math.max(-lx, Math.min(lx, (ancho / 2 - sx) * 0.5)) / t.k * C.peso;
      my = Math.max(-ly, Math.min(ly, (alto / 2 - sy) * 0.5)) / t.k * C.peso;
    }
    const a = 1 - Math.exp(-dt / 900);
    giro.px += (mx - giro.px) * a;
    giro.py += (my - giro.py) * a;
    const quieta = Math.abs(mx - giro.px) < 0.02 && Math.abs(my - giro.py) < 0.02;
    if (quieta) { giro.px = mx; giro.py = my; }
    return !quieta || mx !== 0 || my !== 0;
  }

  function moverGiro(ahora) {
    const dt = Math.max(0, Math.min(64, ahora - (giro.t || ahora)));
    giro.t = ahora;
    if (!cerebro || !neuronasGL) return false;
    if (!completo()) {
      const cambio = giro.ang !== 0 || giro.tilt !== 0 || giro.esc !== 1 || giro.px !== 0 || giro.py !== 0;
      giro.ang = 0;
      giro.tilt = giro.tiltFondo = giro.inerciaV = 0;
      giro.esc = 1;
      giro.px = giro.py = 0;
      if (camara.activo) soltarCamara(false);
      camara.peso = camara.dof = camara.prof = 0;
      if (camara.filmando) pintarBotonCamara();
      return cambio;
    }
    const normalizar = () => {
      if (giro.ang > Math.PI) giro.ang -= TAU;
      if (giro.ang < -Math.PI) giro.ang += TAU;
    };
    const sigue = dirigir(ahora);
    const metaP = sigue ? 1 : 0;
    const pesoAntes = camara.peso;
    camara.peso += (metaP - camara.peso) * (1 - Math.exp(-dt / 900));
    if (Math.abs(metaP - camara.peso) < 0.002) camara.peso = metaP;
    enfocar(dt, sigue);
    const corre = correrCamara(dt);
    const quieto = estado.seleccionado || arrastrando;
    let inclinoV = false;
    if (giro.inerciaV) {
      if (quieto || giro.arrastre) giro.inerciaV = 0;
      else {
        const antes = giro.inclina;
        const cerca = Math.sign(giro.inerciaV) === Math.sign(antes) ? 1 - Math.pow(Math.abs(antes) / INCLINA_TOPE, 2) : 1;
        giro.inclina = topeInclina(antes + giro.inerciaV * cerca * dt);
        const dv = giro.inclina - antes;
        giro.tilt = topeInclina(giro.tilt + dv);
        giro.tiltFondo += dv;
        giro.inerciaV *= Math.pow(0.995, dt);
        if (Math.abs(giro.inerciaV * cerca) <= 0.00002 || Math.abs(giro.inclina) === INCLINA_TOPE) giro.inerciaV = 0;
        if (!giro.inerciaV) guardarInclina();
        inclinoV = true;
      }
    }
    const ahorro = anim.calmado && (anim.escala < 1 || anim.porSoftware || ritmo.sueno > 0.98);
    const cine = giro.activo && !quieto && !ahorro;
    const margen = Math.max(0, Math.min(1, (INCLINA_TOPE - Math.abs(giro.inclina)) / 0.2));
    const oscila = cine ? 0.2 * margen * Math.sin(ahora * TAU / 26000) : 0;
    const tiltMeta = quieto ? (giro.arrastre ? giro.tilt : 0) : topeInclina(oscila + giro.inclina);
    const fondoMeta = quieto ? (giro.arrastre ? giro.tiltFondo : 0) : giro.inclina;
    const escMeta = (cine ? 1 + 0.045 * Math.sin(ahora * TAU / 41000 + 1.3) : 1) * (1 + CAMARA.zoom * camara.peso);
    const k = Math.min(1, dt / 450);
    giro.tilt += (tiltMeta - giro.tilt) * k;
    giro.tiltFondo += (fondoMeta - giro.tiltFondo) * k;
    giro.esc += (escMeta - giro.esc) * k;
    if (Math.abs(giro.tilt - tiltMeta) < 1e-5) giro.tilt = tiltMeta;
    if (Math.abs(giro.tiltFondo - fondoMeta) < 1e-5) giro.tiltFondo = fondoMeta;
    if (Math.abs(giro.esc - escMeta) < 1e-5) giro.esc = escMeta;
    const enIntro = camaraIntro(ahora, tiltMeta, escMeta);
    const camaraMueve = enIntro || inclinoV || giro.tilt !== tiltMeta || giro.tiltFondo !== fondoMeta || giro.esc !== escMeta || cine || corre || camara.peso !== pesoAntes;
    if (camara.filmando !== camara.activo) pintarBotonCamara();
    if (giro.arrastre) { normalizar(); return true; }
    if (quieto) {
      giro.inercia = 0;
      if (giro.ang === 0) return camaraMueve;
      const paso = Math.min(Math.abs(giro.ang), dt * 0.0024);
      giro.ang -= Math.sign(giro.ang) * paso;
      if (Math.abs(giro.ang) < 1e-4) giro.ang = 0;
      return true;
    }
    if (sigue) {
      const w = CAMARA.resorte;
      const dif = envolver(camara.meta - giro.ang);
      camara.vel += (w * w * dif - 2 * w * camara.vel) * dt;
      camara.vel = Math.max(-CAMARA.tope, Math.min(CAMARA.tope, camara.vel));
      giro.ang += camara.vel * dt;
      normalizar();
      return true;
    }
    if (giro.inercia) {
      giro.ang += giro.inercia * dt;
      giro.inercia *= Math.pow(0.9965, dt);
      if (Math.abs(giro.inercia) <= (giro.activo ? giro.vel : 0.00002)) giro.inercia = 0;
    } else if (giro.activo && !ahorro) {
      giro.ang += dt * giro.vel * (giro.dir || 1) * ritmo.giro;
    } else {
      return camaraMueve;
    }
    normalizar();
    return true;
  }

  function descargar(n, fuerza) {
    if (!n || !completo() || !graficoListo) return;
    const ahora = performance.now();
    if (ahora < (n._refractaHasta || 0)) { destello(n, 0.22 * (fuerza || 1)); return; }
    anim.efectos.push({ tipo: 'descarga', n, t0: ahora, dur: 1100, fuerza: fuerza || 1 });
    n._refractaDesde = ahora + 480;
    n._refractaHasta = ahora + 1080;
    anim.escenaHasta = Math.max(anim.escenaHasta, n._refractaHasta + 40);
    programarCuadro();
  }
  DIBUJO_EFECTO.descarga = (e, p) => {
    const n = e.n;
    const d = dendritasDe(n);
    const m = n._m;
    if (!n._en || !d || !m) return;
    const color = colorDe(n);
    const hex = /^#[0-9a-f]{6}$/i.test(color);
    const f = e.fuerza;
    const x = n._sx;
    const y = n._sy;
    const brillo = p < 0.35 ? 0.25 + 0.75 * sale3(p / 0.35) : p < 0.43 ? 1 : Math.max(0, 1 - (p - 0.43) / 0.45);
    if (hex) {
      const R = n._sr * (2.4 + (1.6 + 3 * f) * brillo);
      pctx.globalAlpha = brillo * f * (anim.oscuro ? 1 : 0.6);
      pctx.drawImage(sprite(color, 'brillo'), x - R, y - R, 2 * R, 2 * R);
    }
    const s = escalaNeurona(d, n._sr);
    let cerca = 0;
    for (const o of anim.descargasVivas) if ((o._sx - x) ** 2 + (o._sy - y) ** 2 < 19600) cerca++;
    if (anim.oscuro && cerca <= 3) pctx.globalCompositeOperation = 'lighter';
    const luz = anim.oscuro ? aclarar(color, 0.6) : color;
    const grueso = d.grosor * (anim.oscuro ? 1 : 1.3);
    pctx.lineCap = 'round';
    pctx.lineJoin = 'round';
    pctx.strokeStyle = anim.oscuro ? aclarar(color, 0.35) : color;
    pctx.globalAlpha = (0.2 + 0.45 * brillo) * f * (1 - p);
    pctx.lineWidth = 2.6 * d.grosor;
    pctx.beginPath();
    trazarRamas(pctx, d.gruesas, x, y, m, s);
    pctx.stroke();
    pctx.lineWidth = 1.5 * d.grosor;
    pctx.beginPath();
    trazarRamas(pctx, d.finas, x, y, m, s);
    trazarRamas(pctx, d.axon, x, y, m, s);
    pctx.stroke();
    pctx.strokeStyle = luz;
    if (p < 0.35) {
      const frente = 1 - sale3(p / 0.35);
      pctx.globalAlpha = f * Math.min(1, p / 0.05);
      pctx.lineWidth = 3.2 * grueso;
      pctx.beginPath();
      trazarBanda(pctx, d.gruesas, x, y, m, s, frente, frente + 0.24);
      pctx.stroke();
      pctx.lineWidth = 2 * grueso;
      pctx.beginPath();
      trazarBanda(pctx, d.finas, x, y, m, s, frente, frente + 0.24);
      pctx.stroke();
    } else if (p >= 0.43) {
      const frente = 1.3 * (p - 0.43) / 0.57;
      pctx.globalAlpha = f * Math.min(1, (1 - p) / 0.12);
      pctx.lineWidth = 2.6 * grueso;
      pctx.beginPath();
      trazarBanda(pctx, d.axon, x, y, m, s, frente - 0.3, frente);
      pctx.stroke();
    }
    if (p >= 0.33 && p < 0.47) {
      const u = (p - 0.33) / 0.14;
      pctx.globalAlpha = f * 0.85 * Math.sin(Math.PI * u);
      pctx.fillStyle = aclarar(color, 0.4);
      trazarForma(n, x, y, n._sr + 1.2, pctx);
      pctx.fill();
    }
    pctx.globalCompositeOperation = 'source-over';
    if (p > 0.35) {
      const u = (p - 0.35) / 0.65;
      pctx.beginPath();
      pctx.globalAlpha = (1 - u) * f * 0.9;
      pctx.strokeStyle = aclarar(color, 0.5);
      pctx.lineWidth = 2.2;
      pctx.arc(x, y, n._sr + 4 + 26 * sale3(u) * f, 0, TAU);
      pctx.stroke();
    }
  };

  DIBUJO_EFECTO.rizo = (e, p) => {
    const l = e.lob;
    const t = transformacion;
    const q = proyectar(l.wx, l.wy, 0);
    const x = q.x * t.k + t.x;
    const y = q.y * t.k + t.y;
    const R = l.wr * 0.42 * t.k * q.f;
    const cierre = Math.min(1, (1 - p) / 0.3);
    pctx.strokeStyle = e.color;
    pctx.lineWidth = 1.6;
    for (let i = 0; i < 3; i++) {
      const u = (p * 2.4 + i / 3) % 1;
      pctx.globalAlpha = 0.55 * (1 - u) * cierre * Math.min(1, u / 0.15);
      pctx.beginPath();
      pctx.ellipse(x, y, R * (0.25 + 0.75 * u), R * 0.55 * (0.25 + 0.75 * u), 0, 0, TAU);
      pctx.stroke();
    }
  };

