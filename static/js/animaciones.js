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
