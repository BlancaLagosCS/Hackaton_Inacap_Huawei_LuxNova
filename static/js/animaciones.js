// Recibe las entradas del observador y su instancia; muestra las tarjetas visibles y deja de observarlas, sin devolver valor.
function revelarTarjetas(entradas, observador) {
  for (const entrada of entradas) {
    if (entrada.isIntersecting) {
      entrada.target.classList.remove('reveal-pending');
      observador.unobserve(entrada.target);
    }
  }
}

// No recibe argumentos; prepara IntersectionObserver para animar tarjetas al entrar en pantalla, sin devolver valor.
function iniciarAnimaciones() {
  if (!('IntersectionObserver' in window) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const observador = new IntersectionObserver(revelarTarjetas, { threshold: 0.08 });
  for (const tarjeta of document.querySelectorAll('.event-reveal')) {
    tarjeta.classList.add('reveal-pending');
    observador.observe(tarjeta);
  }
}

iniciarAnimaciones();

// Recibe un cambio del selector de imagen; muestra una vista previa local y libera la URL anterior, sin devolver valor.
function previsualizarImagen(evento) {
  const entrada = evento.currentTarget;
  const imagen = document.getElementById(entrada.dataset.previewInput);
  if (!imagen) return;
  if (imagen.dataset.objectUrl) URL.revokeObjectURL(imagen.dataset.objectUrl);
  imagen.removeAttribute('src');
  delete imagen.dataset.objectUrl;
  imagen.hidden = true;
  const archivo = entrada.files[0];
  if (!archivo || !archivo.type.startsWith('image/')) return;
  const url = URL.createObjectURL(archivo);
  imagen.dataset.objectUrl = url;
  imagen.src = url;
  imagen.hidden = false;
}

// No recibe argumentos; conecta selectores de foto a su vista previa sin subir archivos y no devuelve valor.
function iniciarVistasPrevias() {
  for (const entrada of document.querySelectorAll('[data-preview-input]')) {
    entrada.addEventListener('change', previsualizarImagen);
  }
}

iniciarVistasPrevias();

// Recibe la sección de gestión y métricas autorizadas; actualiza texto y filas sin insertar HTML de usuarios, sin retorno.
function pintarResumen(seccion, resumen) {
  seccion.querySelector('[data-resumen-vacio]').hidden = Boolean(resumen);
  seccion.querySelector('[data-resumen-contenido]').hidden = !resumen;
  if (!resumen) return;
  seccion.querySelector('[data-resumen-titulo]').textContent = resumen.titulo;
  seccion.querySelector('[data-resumen-fecha]').textContent = resumen.fecha;
  seccion.querySelector('[data-resumen-total]').textContent = resumen.total;
  const cuerpo = seccion.querySelector('[data-resumen-asistentes]');
  cuerpo.replaceChildren();
  for (const asistente of resumen.asistentes) {
    const fila = document.createElement('tr');
    const nombre = document.createElement('td');
    const enlace = document.createElement('a');
    enlace.href = asistente.url;
    enlace.textContent = asistente.nombre;
    nombre.append(enlace);
    fila.append(nombre);
    for (const texto of [asistente.carrera, asistente.telefono || 'Privado']) {
      const celda = document.createElement('td');
      celda.textContent = texto;
      fila.append(celda);
    }
    cuerpo.append(fila);
  }
  if (!resumen.asistentes.length) {
    const fila = cuerpo.insertRow();
    const celda = fila.insertCell();
    celda.colSpan = 3;
    celda.textContent = 'Sin preinscritos todavía.';
  }
}

// No recibe argumentos; consulta métricas cada 20 segundos mientras la página sea visible y devuelve una promesa sin valor.
async function actualizarResumenPerfil() {
  const seccion = document.querySelector('[data-perfil-resumen]');
  if (!seccion || document.hidden || seccion.dataset.cargando) return;
  seccion.dataset.cargando = 'true';
  try {
    const respuesta = await fetch(seccion.dataset.perfilResumen, { headers: { Accept: 'application/json' }, cache: 'no-store' });
    if (!respuesta.ok || respuesta.redirected) throw new Error('Sin acceso');
    const datos = await respuesta.json();
    pintarResumen(seccion, datos.resumen);
    seccion.querySelector('[data-resumen-estado]').textContent = 'Datos actualizados.';
  } catch {
    seccion.querySelector('[data-resumen-estado]').textContent = 'No se pudo actualizar. Se conserva la última información.';
  } finally {
    delete seccion.dataset.cargando;
  }
}

if (document.querySelector('[data-perfil-resumen]')) setInterval(actualizarResumenPerfil, 20000);
