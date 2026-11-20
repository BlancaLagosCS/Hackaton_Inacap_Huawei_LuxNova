const dmConfig = document.getElementById('comunidad-tools');
const dmDrawer = document.getElementById('dmDrawer');
const dmEstado = { usuario: null, ocupado: false, enviando: false };

// Recibe ID de interlocutor y acción opcional; devuelve la URL interna construida desde la ruta resuelta por Django.
function dmURL(id, accion = '') { return dmConfig.dataset.dmHilo.replace('/0/', `/${Number(id)}/`) + accion; }

// Recibe URL y campos de formulario; devuelve JSON de un POST autenticado con token CSRF de la página.
async function dmPOST(url, campos = {}) {
  const datos = new FormData();
  for (const [clave, valor] of Object.entries(campos)) datos.append(clave, valor);
  return lnJSON(url, { method: 'POST', headers: { 'X-CSRFToken': dmConfig.querySelector('[name=csrfmiddlewaretoken]').value }, body: datos });
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
  return caja;
}

// Recibe un perfil público; selecciona ese hilo, configura el bloqueo oficial y devuelve una promesa de carga de mensajes.
async function dmAbrirHilo(usuario) {
  dmEstado.usuario = usuario;
  dmDrawer.classList.add('dm-hilo-abierto');
  document.getElementById('dm-nombre').textContent = `${usuario.nom_usu || usuario.username} · @${usuario.username}${usuario.oficial ? ' ✓ Oficial' : ''}`;
  document.getElementById('dm-perfil').href = usuario.perfil_url;
  document.getElementById('dm-avatar').replaceChildren(lnAvatar(usuario));
  document.getElementById('dm-texto').disabled = usuario.oficial;
  document.getElementById('dm-enviar-boton').disabled = usuario.oficial;
  document.getElementById('dm-texto').value = '';
  document.getElementById('dm-canal-oficial').hidden = !usuario.oficial;
  document.getElementById('dm-estado').textContent = '';
  document.getElementById('dm-resultados').replaceChildren();
  document.getElementById('dm-buscar').value = '';
  document.getElementById('dm-mensajes').replaceChildren();
  try { await dmCargarHilo(true); } catch (error) { document.getElementById('dm-estado').textContent = error.message; }
}

// Recibe flag de scroll; obtiene mensajes propios, los muestra y marca recibidos observados mediante POST/CSRF, devolviendo una promesa.
async function dmCargarHilo(forzarScroll = false) {
  if (!dmEstado.usuario || !dmDrawer.classList.contains('show')) return;
  const id = dmEstado.usuario.id;
  const datos = await lnJSON(dmURL(id));
  if (!dmEstado.usuario || dmEstado.usuario.id !== id || !dmDrawer.classList.contains('show')) return;
  const caja = document.getElementById('dm-mensajes');
  const alFinal = caja.scrollHeight - caja.scrollTop - caja.clientHeight < 70;
  const posicion = caja.scrollTop;
  const leidos = datos.mensajes.filter(dmEsPropioLeido);
  const ultimoVisto = leidos.length ? leidos[leidos.length - 1].id : null;
  caja.replaceChildren();
  for (const mensaje of datos.mensajes) caja.append(dmBurbuja(mensaje, ultimoVisto));
  if (!datos.mensajes.length) caja.textContent = 'Aún no hay mensajes. Comienza una conversación.';
  caja.scrollTop = forzarScroll || alFinal ? caja.scrollHeight : posicion;
  const recibidos = datos.mensajes.filter(dmEsRecibidoPendiente);
  if (recibidos.length) {
    await dmPOST(dmURL(id, 'leer/'), { hasta_id: recibidos[recibidos.length - 1].id });
    await dmCargarConversaciones();
  }
}

// Recibe un mensaje; devuelve si fue enviado por el usuario actual y su destinatario ya lo leyó.
function dmEsPropioLeido(mensaje) { return mensaje.propio && mensaje.leido; }

// Recibe un mensaje; devuelve si fue recibido y todavía no se marcó como leído.
function dmEsRecibidoPendiente(mensaje) { return !mensaje.propio && !mensaje.leido; }

// No recibe argumentos; actualiza badge y lista ordenada recibida del servidor y devuelve sus perfiles en una promesa.
async function dmCargarConversaciones() {
  const datos = await lnJSON(dmConfig.dataset.conversacionesUrl);
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

// No recibe argumentos; actualiza cada cinco segundos con página visible, evita consultas simultáneas y devuelve una promesa.
async function dmActualizar() {
  if (document.hidden || dmEstado.ocupado) return;
  dmEstado.ocupado = true;
  try {
    const usuarios = await dmCargarConversaciones();
    if (dmDrawer.classList.contains('show')) {
      if (!dmEstado.usuario && usuarios.length) await dmAbrirHilo(usuarios[0]);
      else await dmCargarHilo();
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
function dmVolverALista() { dmDrawer.classList.remove('dm-hilo-abierto'); dmEstado.usuario = null; }

document.getElementById('dm-enviar').addEventListener('submit', dmEnviarMensaje);
document.getElementById('dm-volver').addEventListener('click', dmVolverALista);
dmDrawer.addEventListener('shown.bs.offcanvas', dmActualizar);
lnConectarBusqueda(document.getElementById('dm-buscar'), document.getElementById('dm-resultados'), false, dmAbrirHilo);
setInterval(dmActualizar, 5000);
dmActualizar();
