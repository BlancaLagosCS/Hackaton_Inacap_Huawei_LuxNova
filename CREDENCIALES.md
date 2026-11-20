# Cuentas demo · INACAP Smart / LuxNova

Datos sintéticos del piloto en **INACAP Rancagua**. Acceso: http://127.0.0.1:8000/login/ (usuario o correo).

| Rol | Usuario (username) | Contraseña | Correo Institucional | Sede | Qué flujo probar |
| --- | --- | --- | --- | --- | --- |
| ADMIN / Root | root_admin | Admin1234! | root.rancagua@inacap.cl | INACAP Rancagua | Panel DAE, roles, auditoría, creación directa; también /admin/ de Django |
| DAE | dae_rancagua | Dae1234! | dae.rancagua@inacap.cl | INACAP Rancagua | Revisar clubes/eventos, resolver solicitudes y consultar impacto/auditoría |
| JEFATURA | jefe_informatica | Jefe1234! | jefatura.informatica@inacap.cl | INACAP Rancagua | Ver líderes/delegados locales y solicitar evento |
| LIDER_ESTUDIANTIL | lider_rancagua | Lider1234! | lider.rancagua@inacapmail.cl | INACAP Rancagua | Solicitar espacio/evento, recibir iniciativas y ver preinscripciones |
| ESTUDIANTE | est1 | Est1234! | est1@inacapmail.cl | INACAP Rancagua | Postular club, publicar iniciativa, inscribirse en evento |
| ESTUDIANTE | est2 | Est1234! | est2@inacapmail.cl | INACAP Rancagua | Aceptar/rechazar aval en Inbox y preinscribirse |
| ESTUDIANTE | est3 | Est1234! | est3@inacapmail.cl | INACAP Rancagua | Confirmar segundo aval |
| ESTUDIANTE | est4 | Est1234! | est4@inacapmail.cl | INACAP Rancagua | Confirmar tercer aval |
| ESTUDIANTE | est5 | Est1234! | est5@inacapmail.cl | INACAP Rancagua | Confirmar cuarto aval y escalar a DAE |

## Preparación

Ejecutar `venv\Scripts\python.exe manage.py cargar_datos_demo` crea/actualiza las nueve cuentas, sus roles y contraseñas. **Cada ejecución restablece estas credenciales y roles demo**, incluida la cuenta est1 si fue promovida durante una demo previa. No duplica avales/mensajes ni reinicia las decisiones de clubes o eventos ya existentes. Las contraseñas anteriores (`1234`) fueron reemplazadas.

El club inicial “Club Demo de Innovación LuxNova” de est1 permite probar inmediatamente los cuatro avales en est2–est5 si aún están pendientes. Para repetir el recorrido completo sin borrar datos, crear una nueva postulación con otro nombre desde est1. Ejecutar el sembrado antes de iniciar, no entre los cuatro avales y la aprobación.

Preparar sesiones independientes (perfiles de navegador o navegadores separados) para est1, est2, est3, est4, est5 y DAE. No compartir pestañas de la misma sesión para simular usuarios distintos. Elegir una fecha futura y un espacio libre. El logo se carga desde `Galeria/logo.png`.

## Guion de presentación · 3 minutos

1. **0:00–0:25 · Problema y entrada:** En est1 mostrar Home por sede/intersede y Foro; publicar una #Iniciativa. Mostrar en la sesión DAE o líder que llegó al buzón con contacto privado. Explicar que las notificaciones son internas y que los datos son ficticios.
2. **0:25–0:55 · Comunidad:** En Mi cuenta de est1 postular un club con nombre nuevo y seleccionar est2–est5. Mostrar estado PENDIENTE_AVALES y 0/4 en el perfil.
3. **0:55–1:30 · Avales:** En las cuatro sesiones ya abiertas aceptar el aval del club nuevo. Tras el cuarto, abrir el perfil DAE: el club está PENDIENTE_DAE. Un reenvío no duplica avisos.
4. **1:30–2:00 · Aprobación:** DAE aprueba el club. En est1 recargar Mi cuenta: ahora es LIDER_ESTUDIANTIL y puede reservar espacios. Mostrar el aviso del Sistema y la auditoría DAE.
5. **2:00–2:35 · Evento útil:** Desde est1 solicitar un evento futuro en Auditorio Principal (o espacio libre). DAE lo aprueba; aparece en Inicio. Desde est2 preinscribirse y mostrar el contador en el perfil del organizador.
6. **2:35–3:00 · Control e impacto:** Mostrar las tres métricas DAE y la auditoría. Si hay tiempo, intentar aprobar una segunda solicitud en el mismo espacio/sede a una hora de diferencia: debe bloquearse por conflicto. Cerrar con el ahorro de pasos y la trazabilidad.

## Alcance real del piloto

Registro, PostgreSQL, publicaciones, avales, aprobaciones, preinscripciones y auditoría son reales. Las notificaciones externas se simulan exclusivamente mediante Inbox interno. Huawei Cloud RDS/OBS son destino de arquitectura; esta instancia usa PostgreSQL y media locales. “Eventos Asistidos” representa preinscripciones, no control presencial de asistencia. La disponibilidad usa ±2 horas inclusivas respecto de la fecha de inicio, sin un campo de duración.

El rol ADMIN de la aplicación está limitado a la sede como DAE; el superusuario root tiene además acceso administrativo Django. Cambiar `rol_usu` en el panel no modifica `is_staff` ni `is_superuser`.
