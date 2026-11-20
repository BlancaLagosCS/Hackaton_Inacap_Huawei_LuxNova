const dmConfig = document.getElementById('comunidad-tools');
const dmDrawer = document.getElementById('dmDrawer');
const dmEstado = { usuario: null, ocupado: false, enviando: false, avalesEnviando: new Set() };
let dmFocoAnterior = null;

// Recibe ID opcional de persona; abre el drawer sin depender de Bootstrap y carga sus conversaciones o el destinatario indicado.
async function dmMostrar(usuarioId = null) {
  if (dmDrawer.hidden) dmFocoAnterior = document.activeElement;
  dmDrawer.hidden = false;
  dmDrawer.classList.add('show');
  dmDrawer.setAttribute('aria-modal', 'true');
  document.body.classList.add('dm-abierto');
  if (!document.getElementById('dm-overlay')) {
    const fondo = document.createElement('div');
    fondo.id = 'dm-overlay'; fondo.className = 'dm-overlay';
    fondo.addEventListener('click', dmCerrar);
    document.body.append(fondo);
  }
  (dmEstado.usuario ? document.getElementById('dm-ver-perfil') : document.getElementById('dm-buscar')).focus();
  try {
    if (usuarioId) {
      const datos = await lnJSON(dmURL(usuarioId));
      await dmAbrirHilo(datos.usuario);
    }
    const conversaciones = await dmCargarConversaciones();
    if (!dmEstado.usuario && dmEstado.pendientes > 0) {
      const sistema = conversaciones.find(dmEsOficial);
      if (sistema) await dmAbrirHilo(sistema);
    } else if (dmEstado.usuario) await dmCargarHilo();
  } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
}

// No recibe argumentos; cierra el diálogo, retira su fondo y devuelve el foco al acceso usado.
function dmCerrar() {
  dmDrawer.classList.remove('show');
  dmDrawer.hidden = true;
  dmDrawer.removeAttribute('aria-modal');
  document.body.classList.remove('dm-abierto');
  document.getElementById('dm-overlay')?.remove();
  if (dmFocoAnterior && document.contains(dmFocoAnterior)) dmFocoAnterior.focus();
}

// Recibe clic en accesos globales o cierre; abre mensajes por ID o cierra el drawer y evita navegar si JavaScript está activo.
function dmAccionGlobal(evento) {
  const abrir = evento.target.closest('[data-dm-open]');
  if (abrir) { evento.preventDefault(); dmMostrar(abrir.dataset.dmUsuario || null); }
  if (evento.target.closest('[data-dm-close]')) dmCerrar();
}

// Recibe una tecla; cierra con Escape y mantiene el recorrido de Tab dentro del diálogo visible.
function dmTeclado(evento) {
  if (dmDrawer.hidden) return;
  if (evento.key === 'Escape') { evento.preventDefault(); dmCerrar(); return; }
  if (evento.key !== 'Tab') return;
  const elementos = [...dmDrawer.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled])')].filter(dmElementoVisible);
  if (!elementos.length) { evento.preventDefault(); dmDrawer.focus(); return; }
  const primero = elementos[0], ultimo = elementos[elementos.length - 1];
  if (evento.shiftKey && document.activeElement === primero) { evento.preventDefault(); ultimo.focus(); }
  if (!evento.shiftKey && document.activeElement === ultimo) { evento.preventDefault(); primero.focus(); }
}

// Recibe un control DOM; devuelve si está visible y puede participar en el recorrido del teclado.
function dmElementoVisible(elemento) { return !elemento.hidden && elemento.getClientRects().length > 0; }

// Recibe ID de interlocutor y acción opcional; devuelve la URL interna construida desde la ruta resuelta por Django.
function dmURL(id, accion = '') { return dmConfig.dataset.dmHilo.replace('/0/', `/${Number(id)}/`) + accion; }

// Recibe URL y campos de formulario; devuelve JSON de un POST autenticado con token CSRF de la página.
async function dmPOST(url, campos = {}) {
  const datos = new FormData();
  for (const [clave, valor] of Object.entries(campos)) datos.append(clave, valor);
  return lnJSON(url, { method: 'POST', headers: { 'Accept': 'application/json', 'X-CSRFToken': dmConfig.querySelector('[name=csrfmiddlewaretoken]').value }, body: datos });
}

// Recibe fecha ISO opcional y devuelve una hora relativa legible, sin modificar el DOM.
function dmHoraRelativa(fecha) {
  if (!fecha) return '';
  const minutos = Math.round((new Date(fecha).getTime() - Date.now()) / 60000);
  return new Intl.RelativeTimeFormat('es', { numeric: 'auto' }).format(Math.abs(minutos) < 60 ? minutos : Math.round(minutos / 60), Math.abs(minutos) < 60 ? 'minute' : 'hour');
}

// Recibe un mensaje del hilo y el ID del último envío leído; devuelve una burbuja segura con texto, hora y Visto cuando corresponde.
function dmBurbuja(mensaje, ultimoVisto) {
  const caja = document.createElement('div');
  caja.className = mensaje.propio ? 'dm-fila dm-propio' : 'dm-fila';
  const burbuja = document.createElement('div');
  burbuja.className = 'dm-burbuja';
  burbuja.textContent = mensaje.contenido;
  const pie = document.createElement('small');
  pie.textContent = new Date(mensaje.fecha).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' });
  if (mensaje.id === ultimoVisto) pie.textContent += ' · Visto';
  caja.append(burbuja, pie);
  if (mensaje.aval) {
    const estado = document.createElement('p');
    estado.className = 'small mt-2 mb-1';
    estado.textContent = `Aval para ${mensaje.aval.club}: ${mensaje.aval.estado.toLowerCase()}`;
    burbuja.append(estado);
    if (mensaje.aval.pendiente) {
      const acciones = document.createElement('div');
      acciones.className = 'd-flex flex-wrap gap-2 mt-2';
      acciones.append(dmBotonAval(mensaje.aval, 'ACEPTADO', 'Aceptar aval'), dmBotonAval(mensaje.aval, 'RECHAZADO', 'Rechazar aval'));
      burbuja.append(acciones);
    }
  }
  return caja;
}

// Recibe aval autorizado, decisión y etiqueta; devuelve un botón seguro que responde por POST con CSRF y evita doble envío.
function dmBotonAval(aval, decision, etiqueta) {
  const boton = document.createElement('button');
  boton.type = 'button';
  boton.className = 'btn btn-sm ' + (decision === 'ACEPTADO' ? 'btn-primary' : 'btn-outline-dark');
  boton.textContent = etiqueta;
  boton.disabled = dmEstado.avalesEnviando.has(aval.id);
  // Recibe clic del destinatario; guarda su respuesta, actualiza hilo/contador y comunica errores sin enviar mensajes humanos.
  async function responderAval() {
    if (dmEstado.avalesEnviando.has(aval.id)) return;
    dmEstado.avalesEnviando.add(aval.id);
    boton.disabled = true;
    try {
      await dmPOST(aval.url, { decision });
      await dmCargarHilo();
      await dmCargarConversaciones();
    } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
    finally { dmEstado.avalesEnviando.delete(aval.id); boton.disabled = false; }
  }
  boton.addEventListener('click', responderAval);
  return boton;
}

// Recibe un perfil público; selecciona ese hilo, configura el bloqueo oficial y devuelve una promesa de carga de mensajes.
async function dmAbrirHilo(usuario) {
  dmPintarAvales([]);
  dmEstado.usuario = usuario;
  dmDrawer.classList.add('dm-hilo-abierto');
  document.getElementById('dm-nombre').textContent = `${usuario.nom_usu || usuario.username} · @${usuario.username}${usuario.oficial ? ' ✓ Oficial' : ''}`;
  document.getElementById('dm-perfil').href = usuario.perfil_url;
  document.getElementById('dm-ver-perfil').href = usuario.perfil_url;
  document.getElementById('dm-ver-perfil').hidden = false;
  document.getElementById('dm-avatar').replaceChildren(lnAvatar(usuario));
  document.getElementById('dm-texto').disabled = usuario.oficial;
  document.getElementById('dm-enviar-boton').disabled = usuario.oficial;
  document.getElementById('dm-enviar').classList.toggle('d-none', usuario.oficial);
  document.getElementById('dm-texto').value = '';
  document.getElementById('dm-canal-oficial').hidden = !usuario.oficial;
  document.getElementById('dm-estado').textContent = '';
  document.getElementById('dm-resultados').replaceChildren();
  document.getElementById('dm-buscar').value = '';
  document.getElementById('dm-mensajes').replaceChildren();
  (usuario.oficial ? document.getElementById('dm-ver-perfil') : document.getElementById('dm-texto')).focus();
  try { await dmCargarHilo(true); } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
}

// Recibe flag de scroll; obtiene mensajes propios, los muestra y marca recibidos observados mediante POST/CSRF, devolviendo una promesa.
async function dmCargarHilo(forzarScroll = false) {
  if (!dmEstado.usuario || !dmDrawer.classList.contains('show')) return;
  const id = dmEstado.usuario.id;
  const datos = await lnJSON(dmURL(id));
  if (!dmEstado.usuario || dmEstado.usuario.id !== id || !dmDrawer.classList.contains('show')) return;
  dmPintarAvales(datos.avales_pendientes || []);
  const caja = document.getElementById('dm-mensajes');
  const alFinal = caja.scrollHeight - caja.scrollTop - caja.clientHeight < 70;
  const posicion = caja.scrollTop;
  const leidos = datos.mensajes.filter(dmEsPropioLeido);
  const ultimoVisto = leidos.length ? leidos[leidos.length - 1].id : null;
  caja.replaceChildren();
  for (const mensaje of datos.mensajes) caja.append(dmBurbuja(mensaje, ultimoVisto));
  if (!datos.mensajes.length) caja.textContent = dmEstado.usuario.oficial ? 'Tus notificaciones del sistema aparecerán aquí.' : 'Aún no hay mensajes. Comienza una conversación.';
  caja.scrollTop = forzarScroll || alFinal ? caja.scrollHeight : posicion;
  const recibidos = datos.mensajes.filter(dmEsRecibidoPendiente);
  if (recibidos.length) {
    await dmPOST(dmURL(id, 'leer/'), { hasta_id: recibidos[recibidos.length - 1].id });
    await dmCargarConversaciones();
  }
}

// Recibe avales pendientes autorizados; los fija encima del historial, incluso si el mensaje original es antiguo.
function dmPintarAvales(avales) {
  const panel = document.getElementById('dm-avales');
  panel.hidden = avales.length === 0;
  const firma = JSON.stringify(avales);
  if (panel.dataset.firma === firma) return;
  panel.dataset.firma = firma;
  panel.replaceChildren();
  if (!avales.length) return;
  const titulo = document.createElement('h3');
  titulo.className = 'h6'; titulo.textContent = `Solicitudes de aval pendientes (${avales.length})`;
  panel.append(titulo);
  for (const aval of avales) {
    const tarjeta = document.createElement('article'); tarjeta.className = 'dm-aval-tarjeta';
    const nombre = document.createElement('strong'); nombre.textContent = aval.club;
    const detalle = document.createElement('p'); detalle.className = 'small mb-2';
    detalle.textContent = `${aval.solicitante} solicita tu apoyo para crear este club.`;
    const acciones = document.createElement('div'); acciones.className = 'd-flex flex-wrap gap-2';
    acciones.append(dmBotonAval(aval, 'ACEPTADO', 'Aceptar aval'), dmBotonAval(aval, 'RECHAZADO', 'Rechazar aval'));
    tarjeta.append(nombre, detalle, acciones); panel.append(tarjeta);
  }
}

// Recibe un mensaje; devuelve si fue enviado por el usuario actual y su destinatario ya lo leyó.
function dmEsPropioLeido(mensaje) { return mensaje.propio && mensaje.leido; }

// Recibe un mensaje; devuelve si fue recibido y todavía no se marcó como leído.
function dmEsRecibidoPendiente(mensaje) { return !mensaje.propio && !mensaje.leido; }

// No recibe argumentos; actualiza badge y lista ordenada recibida del servidor y devuelve sus perfiles en una promesa.
async function dmCargarConversaciones() {
  const datos = await lnJSON(dmConfig.dataset.conversacionesUrl);
  dmEstado.pendientes = datos.avales_pendientes || 0;
  const badge = document.getElementById('dm-no-leidos');
  badge.hidden = datos.no_leidos === 0;
  badge.textContent = datos.no_leidos;
  badge.setAttribute('aria-label', `${datos.no_leidos} mensajes no leídos`);
  const caja = document.getElementById('dm-conversaciones');
  caja.replaceChildren();
  for (const usuario of datos.conversaciones) {
    const boton = lnResultadoUsuario(usuario, dmAbrirHilo);
    boton.classList.add('dm-conversacion');
    if (dmEstado.usuario && dmEstado.usuario.id === usuario.id) boton.classList.add('seleccionada');
    const detalle = document.createElement('span');
    detalle.className = 'dm-extracto';
    detalle.textContent = `${usuario.oficial ? '✓ Oficial · ' : ''}${usuario.extracto}`;
    const hora = document.createElement('small');
    hora.textContent = dmHoraRelativa(usuario.fecha);
    boton.append(detalle, hora);
    if (usuario.no_leidos) {
      const punto = document.createElement('span');
      punto.className = 'dm-punto';
      punto.setAttribute('aria-label', `${usuario.no_leidos} sin leer`);
      boton.append(punto);
    }
    caja.append(boton);
  }
  return datos.conversaciones;
}

// Recibe un perfil público de conversación; devuelve si corresponde al canal oficial del sistema.
function dmEsOficial(usuario) { return usuario.oficial; }

// No recibe argumentos; actualiza cada cinco segundos con página visible, evita consultas simultáneas y devuelve una promesa.
async function dmActualizar() {
  if (document.hidden || dmEstado.ocupado) return;
  dmEstado.ocupado = true;
  try {
    const usuarios = await dmCargarConversaciones();
    if (dmDrawer.classList.contains('show')) {
      if (dmEstado.usuario) await dmCargarHilo();
    }
  } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
  finally { dmEstado.ocupado = false; }
}

// Recibe submit del formulario; envía el texto, conserva errores y actualiza el hilo y lecturas, devolviendo una promesa.
async function dmEnviarMensaje(evento) {
  evento.preventDefault();
  if (!dmEstado.usuario || dmEstado.usuario.oficial || dmEstado.enviando) return;
  const entrada = document.getElementById('dm-texto');
  const texto = entrada.value.trim();
  if (!texto) return;
  const id = dmEstado.usuario.id;
  dmEstado.enviando = true;
  document.getElementById('dm-enviar-boton').disabled = true;
  try {
    await dmPOST(dmURL(id, 'enviar/'), { cont_mens: texto });
    if (dmEstado.usuario && dmEstado.usuario.id === id) { entrada.value = ''; await dmCargarHilo(true); }
    await dmCargarConversaciones();
    document.getElementById('dm-estado').textContent = '';
  } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
  finally {
    dmEstado.enviando = false;
    document.getElementById('dm-enviar-boton').disabled = !dmEstado.usuario || dmEstado.usuario.oficial;
  }
}

// No recibe argumentos; vuelve a la lista en móvil y evita marcar lecturas de un hilo que dejó de estar visible.
function dmVolverALista() {
  dmDrawer.classList.remove('dm-hilo-abierto');
  dmEstado.usuario = null;
  document.getElementById('dm-ver-perfil').hidden = true;
  document.getElementById('dm-texto').disabled = true;
  document.getElementById('dm-enviar-boton').disabled = true;
  document.getElementById('dm-enviar').classList.remove('d-none');
  document.getElementById('dm-nombre').textContent = 'Selecciona una conversación';
  document.getElementById('dm-perfil').removeAttribute('href');
  document.getElementById('dm-avatar').replaceChildren();
  document.getElementById('dm-mensajes').replaceChildren();
  document.getElementById('dm-texto').value = '';
  document.getElementById('dm-canal-oficial').hidden = true;
  document.getElementById('dm-estado').textContent = '';
  dmPintarAvales([]);
  document.getElementById('dm-buscar').focus();
}

document.getElementById('dm-enviar').addEventListener('submit', dmEnviarMensaje);
document.getElementById('dm-volver').addEventListener('click', dmVolverALista);
document.addEventListener('click', dmAccionGlobal);
document.addEventListener('keydown', dmTeclado);
lnConectarBusqueda(document.getElementById('dm-buscar'), document.getElementById('dm-resultados'), false, dmAbrirHilo);
setInterval(dmActualizar, 5000);
dmActualizar();
const dmPagina = document.getElementById('mensajeria-page');
if (dmPagina) dmMostrar(dmPagina.dataset.usuarioId || null);
