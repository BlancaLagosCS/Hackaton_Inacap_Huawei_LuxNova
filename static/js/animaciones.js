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
