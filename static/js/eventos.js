const eventoOrganizador = document.getElementById('id_orga_even');
const eventoClub = document.getElementById('id_club_even');

// Recibe cambio opcional de organizador; muestra y exige club solo al representar uno y limpia la selección al pasar a personal.
function actualizarClubEvento(evento) {
  if (!eventoOrganizador || !eventoClub) return;
  const esClub = eventoOrganizador.value === 'CLUB';
  const fila = eventoClub.closest('.mb-3');
  if (evento && !esClub) eventoClub.value = '';
  eventoClub.required = esClub;
  fila.hidden = !esClub && !fila.querySelector('[role="alert"]');
}

if (eventoOrganizador && eventoClub) {
  eventoOrganizador.addEventListener('change', actualizarClubEvento);
  actualizarClubEvento();
}
