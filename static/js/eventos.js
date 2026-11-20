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

const reservaPanel = document.getElementById('disponibilidad');
const reservaLugar = document.getElementById('id_esp_even');
const reservaMes = document.getElementById('id_mes_reserva');
const reservaDia = document.getElementById('id_dia_even');
let reservaConsulta = 0;

// Recibe una fecha ISO; devuelve una etiqueta local sin convertir la fecha a UTC ni cambiarla al día anterior.
function etiquetaDia(fecha) {
  const [anio, mes, dia] = fecha.split('-');
  return `${dia}/${mes}/${anio}`;
}

// Recibe los días del mes; dibuja un calendario con botones solo para días disponibles y estados visibles para los bloqueados.
function dibujarCalendario(datos) {
  const calendario = document.getElementById('calendario-reserva');
  calendario.replaceChildren();
  for (const nombre of ['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do']) {
    const cabecera = document.createElement('span');
    cabecera.className = 'calendario-semana'; cabecera.textContent = nombre;
    calendario.append(cabecera);
  }
  const [anio, mes] = datos.mes.split('-').map(Number);
  const inicio = (new Date(anio, mes - 1, 1).getDay() + 6) % 7;
  for (let i = 0; i < inicio; i += 1) calendario.append(document.createElement('span'));
  for (const dia of datos.dias) {
    const boton = document.createElement('button');
    const estado = { DISPONIBLE: 'Disponible', EN_REVISION: 'En revisión', RESERVADO: 'Reservado', PASADO: 'Día pasado' }[dia.estado];
    boton.type = 'button'; boton.textContent = dia.dia;
    boton.className = `calendario-dia ${dia.estado.toLowerCase()}`;
    boton.dataset.fecha = dia.fecha;
    boton.disabled = dia.estado !== 'DISPONIBLE';
    boton.setAttribute('aria-label', `${etiquetaDia(dia.fecha)} · ${estado}`);
    boton.title = estado;
    // Recibe clic de un día libre; actualiza el selector que se enviará al servidor y el estado visual de selección.
    function elegirDia() { reservaDia.value = dia.fecha; marcarDiaReserva(); }
    boton.addEventListener('click', elegirDia);
    calendario.append(boton);
  }
  calendario.hidden = false;
  marcarDiaReserva();
}

// No recibe argumentos; sincroniza calendario con el día seleccionado en el menú y no modifica disponibilidad.
function marcarDiaReserva() {
  for (const boton of document.querySelectorAll('.calendario-dia')) {
    const seleccionado = boton.dataset.fecha === reservaDia.value;
    boton.classList.toggle('seleccionado', seleccionado);
    boton.setAttribute('aria-pressed', seleccionado ? 'true' : 'false');
  }
}

// Recibe cambio opcional de lugar/mes; carga disponibilidad de su sede, descarta respuestas antiguas y ofrece solo días libres.
async function cargarDisponibilidad(evento) {
  if (!reservaPanel || !reservaLugar || !reservaMes || !reservaDia) return;
  const consulta = ++reservaConsulta;
  const seleccionado = evento ? '' : reservaDia.value;
  const estado = document.getElementById('disponibilidad-estado');
  reservaDia.replaceChildren(new Option('Selecciona un lugar y un día libre', ''));
  reservaDia.disabled = true;
  document.getElementById('calendario-reserva').hidden = true;
  if (!reservaLugar.value || !reservaMes.value) { estado.textContent = 'Selecciona un lugar y un mes para ver sus días libres.'; return; }
  estado.textContent = 'Consultando disponibilidad…';
  try {
    const url = new URL(reservaPanel.dataset.url, location.origin);
    url.searchParams.set('espacio', reservaLugar.value); url.searchParams.set('mes', reservaMes.value);
    const datos = await lnJSON(url);
    if (consulta !== reservaConsulta) return;
    for (const dia of datos.disponibles) reservaDia.append(new Option(etiquetaDia(dia), dia));
    reservaDia.disabled = datos.disponibles.length === 0;
    if (datos.disponibles.includes(seleccionado)) reservaDia.value = seleccionado;
    estado.textContent = datos.disponibles.length ? `${datos.disponibles.length} días libres. Reservados y en revisión no se pueden seleccionar.` : 'Este lugar no tiene días libres en este mes. Selecciona otro mes o lugar.';
    dibujarCalendario(datos);
  } catch (error) { if (consulta === reservaConsulta) estado.textContent = error.message; }
}

if (reservaPanel) {
  reservaLugar.addEventListener('change', cargarDisponibilidad);
  reservaMes.addEventListener('change', cargarDisponibilidad);
  reservaDia.addEventListener('change', marcarDiaReserva);
  cargarDisponibilidad();
}
