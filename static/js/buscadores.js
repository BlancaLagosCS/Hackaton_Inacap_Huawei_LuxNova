// Recibe una URL y opciones fetch; devuelve JSON validado o lanza un error legible si falla la sesión o la petición.
async function lnJSON(url, opciones = {}) {
  const respuesta = await fetch(url, { credentials: 'same-origin', cache: 'no-store', ...opciones });
  if (respuesta.redirected) throw new Error('Tu sesión terminó. Vuelve a iniciar sesión.');
  if (!(respuesta.headers.get('Content-Type') || '').includes('application/json')) throw new Error('No se pudo completar la operación. Inténtalo de nuevo.');
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new Error(datos.error || 'No se pudo completar la operación.');
  return datos;
}

// Recibe texto y flag de sede; devuelve perfiles públicos encontrados por el mismo endpoint usado en todos los buscadores.
async function lnBuscarUsuarios(texto, soloSede = false) {
  const config = document.getElementById('comunidad-tools');
  const url = new URL(config.dataset.buscarUrl, location.origin);
  url.searchParams.set('q', texto);
  url.searchParams.set('solo_sede', soloSede ? '1' : '0');
  return (await lnJSON(url)).usuarios;
}

// Recibe perfil público y elemento opcional; devuelve un avatar seguro con foto o inicial, sin interpolar HTML del usuario.
function lnAvatar(usuario) {
  const avatar = document.createElement('span');
  avatar.className = 'dm-avatar';
  if (usuario.foto_url) {
    const foto = document.createElement('img');
    foto.src = usuario.foto_url;
    foto.alt = '';
    avatar.append(foto);
  } else avatar.textContent = (usuario.nom_usu || usuario.username).slice(0, 1).toUpperCase();
  return avatar;
}

// Recibe un perfil público y callback; devuelve un botón de resultado accesible que ejecuta esa selección.
function lnResultadoUsuario(usuario, seleccionar) {
  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'busqueda-persona';
  boton.append(lnAvatar(usuario));
  const texto = document.createElement('span');
  texto.textContent = `${usuario.nom_usu || usuario.username} · @${usuario.username}`;
  if (usuario.oficial) {
    const verificado = document.createElement('span');
    verificado.className = 'badge category-badge ms-1';
    verificado.textContent = '✓';
    verificado.setAttribute('aria-label', 'Cuenta oficial verificada');
    texto.append(verificado);
  }
  boton.append(texto);
  // Recibe el clic del resultado; ejecuta la selección del perfil asociado y no devuelve valor.
  function elegirPersona() { seleccionar(usuario); }
  boton.addEventListener('click', elegirPersona);
  return boton;
}

// Recibe input, contenedor, flag de sede y callback; conecta búsqueda con espera breve y descarta respuestas antiguas, sin retorno.
function lnConectarBusqueda(entrada, contenedor, soloSede, seleccionar) {
  let temporizador;
  let version = 0;
  // Recibe el cambio del input; programa la consulta más reciente y no devuelve valor.
  function programarBusqueda() {
    clearTimeout(temporizador);
    const actual = ++version;
    const texto = entrada.value.trim();
    contenedor.replaceChildren();
    if (!texto) return;
    // No recibe argumentos; consulta perfiles y muestra resultados si la entrada sigue vigente, devolviendo una promesa.
    async function consultarPersonas() {
      try {
        const usuarios = await lnBuscarUsuarios(texto, soloSede);
        if (actual !== version) return;
        contenedor.replaceChildren();
        if (!usuarios.length) contenedor.textContent = 'Sin resultados.';
        for (const usuario of usuarios) contenedor.append(lnResultadoUsuario(usuario, seleccionar));
      } catch (error) { if (actual === version) contenedor.textContent = error.message; }
    }
    temporizador = setTimeout(consultarPersonas, 250);
  }
  entrada.addEventListener('input', programarBusqueda);
}

// Recibe un select autorizado de avales; lo mejora progresivamente con buscador, cuatro chips e inputs ocultos, sin retorno.
function lnPrepararAvales(selector) {
  const elegidos = new Map();
  for (const opcion of selector.selectedOptions) elegidos.set(Number(opcion.value), { id: Number(opcion.value), nom_usu: opcion.text, username: '' });
  const caja = document.createElement('div');
  const entrada = document.createElement('input');
  entrada.type = 'search';
  entrada.className = 'form-control buscador-pildora';
  entrada.placeholder = 'Busca a tus compañeros por nombre o @nickname';
  entrada.setAttribute('aria-label', 'Buscar compañeros de tu sede para avales');
  const chips = document.createElement('div');
  chips.className = 'avales-chips d-flex flex-wrap gap-2 my-2';
  const estado = document.createElement('p');
  estado.className = 'form-text';
  estado.setAttribute('role', 'status');
  const resultados = document.createElement('div');
  resultados.className = 'busqueda-resultados';
  caja.append(entrada, chips, estado, resultados);
  selector.after(caja);
  selector.hidden = true;
  selector.disabled = true;
  // No recibe argumentos; actualiza chips, contador e IDs enviados, sin devolver valor.
  function dibujarElegidos() {
    chips.replaceChildren();
    estado.textContent = `${elegidos.size}/4 compañeros seleccionados`;
    for (const usuario of elegidos.values()) {
      const chip = document.createElement('span');
      chip.className = 'aval-chip';
      const etiqueta = document.createElement('span');
      etiqueta.textContent = usuario.nom_usu || usuario.username;
      const quitar = document.createElement('button');
      quitar.type = 'button';
      quitar.textContent = '×';
      quitar.setAttribute('aria-label', `Quitar ${etiqueta.textContent}`);
      // Recibe el clic de una etiqueta; quita ese estudiante de los IDs del formulario y no devuelve valor.
      function quitarElegido() { elegidos.delete(usuario.id); dibujarElegidos(); }
      quitar.addEventListener('click', quitarElegido);
      const id = document.createElement('input');
      id.type = 'hidden'; id.name = selector.name; id.value = usuario.id;
      chip.append(etiqueta, quitar, id);
      chips.append(chip);
    }
  }
  // Recibe un perfil local; agrega hasta cuatro estudiantes únicos y actualiza el formulario sin devolver valor.
  function agregarElegido(usuario) {
    if (elegidos.has(usuario.id)) return;
    if (elegidos.size >= 4) { estado.textContent = 'Ya seleccionaste cuatro. Quita uno para cambiarlo.'; return; }
    elegidos.set(usuario.id, usuario);
    entrada.value = ''; resultados.replaceChildren(); dibujarElegidos();
  }
  lnConectarBusqueda(entrada, resultados, true, agregarElegido);
  dibujarElegidos();
}

// Recibe un perfil del buscador global; abre su ruta pública y no devuelve valor.
function lnVisitarPerfil(usuario) { location.assign(usuario.perfil_url); }

const lnEntradaGlobal = document.querySelector('[data-buscar-perfiles]');
if (lnEntradaGlobal) lnConectarBusqueda(lnEntradaGlobal, document.querySelector('[data-resultados-perfiles]'), false, lnVisitarPerfil);
for (const lnSelector of document.querySelectorAll('[data-avales-picker]')) lnPrepararAvales(lnSelector);
