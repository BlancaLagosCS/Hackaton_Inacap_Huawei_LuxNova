// No recibe argumentos; activa la diapositiva de un evento enlazado por hash y desplaza la vista cuando termina su transición.
function mostrarEventoEnCarrusel() {
  if (!/^#evento-\d+$/.test(location.hash)) return;
  const destino = document.getElementById(location.hash.slice(1));
  const elemento = destino?.closest('.carousel-item');
  const carrusel = elemento?.closest('.carousel');
  if (!carrusel) return;
  // No recibe argumentos; desplaza al evento visible sin animación forzada ni alterar el foco del usuario.
  function enfocarEventoVisible() { destino.scrollIntoView({ block: 'start', behavior: 'auto' }); }
  if (elemento.classList.contains('active')) { enfocarEventoVisible(); return; }
  if (!window.bootstrap?.Carousel) return;
  const indice = [...carrusel.querySelectorAll('.carousel-item')].indexOf(elemento);
  carrusel.addEventListener('slid.bs.carousel', enfocarEventoVisible, { once: true });
  bootstrap.Carousel.getOrCreateInstance(carrusel, { interval: false }).to(indice);
}

window.addEventListener('hashchange', mostrarEventoEnCarrusel);
mostrarEventoEnCarrusel();
