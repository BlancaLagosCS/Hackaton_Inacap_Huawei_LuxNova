# Bitácora técnica acumulativa · LuxNova

## Versión 1 (v1) · Arquitectura y base relacional

Objetivo: establecer arquitectura Django MVT y PostgreSQL `hackaton_luxnova`.

Se auditó el directorio y Git; no existía una app core parcial. Se creó `core/` con nueve modelos: Sede, Usuario (AbstractUser), Club, AvalClub, Evento, PublicacionForo, ComentarioForo, MensajeInbox y RegistroAuditoria. Se conservaron los nombres españoles de los campos, sus relaciones, estados y opciones. `core/admin.py` registra las nueve entidades.

Archivos: `core/models.py`, `core/admin.py`, `core/apps.py`, `.gitignore`, `CONTEXTO.md`, `requirements.txt` y `core/migrations/0001_initial.py`. `config/settings.py` conecta PostgreSQL, registra core, configura `AUTH_USER_MODEL`, templates, static y media. Las carpetas vacías se conservan en Git mediante `.gitkeep`.

La migración inicial se resolvió leyendo DATABASES desde settings, verificando el nombre `hackaton_luxnova` y reiniciando explícitamente el esquema public mediante psycopg2 (`DROP SCHEMA public CASCADE; CREATE SCHEMA public;`). Luego se ejecutaron `makemigrations core --noinput` y `migrate --noinput`. Se verificaron las nueve tablas en PostgreSQL; Django también crea tablas auxiliares de autenticación y relaciones ManyToMany. Este reinicio destructivo fue exclusivo de v1 y no se repite en v2.

## Versión 2 (v2) · Identidad INACAP, acceso y eventos

Objetivo: una entrada funcional a la comunidad con registro, login, eventos por sede/intersede y datos demo.

- `templates/base.html`: Bootstrap 5 CDN, navbar con cuatro secciones, sede, contador real de mensajes propios no leídos y logout por POST. Placeholder fijo del logo con comentario institucional.
- `static/css/estilos.css`: rojo #E30613, oscuro #1A1A1A y blanco, tarjetas adaptables, perfil básico y formularios.
- `static/js/animaciones.js`: IntersectionObserver con entrada desde los costados, respeto de movimiento reducido y contenido visible cuando no hay JS.
- `core/forms.py`: RegistroForm valida alta y correo único sin distinguir mayúsculas, exige sede y año válido, confirma contraseña con validadores Django y fija rol ESTUDIANTE. No restringe dominios de correo porque no se definió una lista institucional autorizada. LoginForm acepta username o corr_usu, con prioridad de username exacto.
- `core/views.py`: registro inicia sesión automáticamente; home separa eventos aprobados futuros de la sede y eventos intersede, anota total de asistentes y estado de inscripción. Preinscripción/cancelación exige POST, CSRF y autenticación, controla alcance/sede/estado/fecha y usa transacción con bloqueo del evento.
- `templates/home.html`, `login.html`, `registro.html` y parciales `partials/evento.html` / `partials/formulario.html`: bienvenida pública, acceso y tarjetas con banner o placeholder CSS y botón funcional de inscripción.
- `core/context_processors.py`: contador de mensajes no leídos limitado al destinatario actual.
- `core/urls.py` y `config/urls.py`: `/`, `/registro/`, `/login/`, `/logout/`, `/eventos/<id>/preinscripcion/`, `/ahora-mismo/`, `/inbox/`, `/perfil/` y `/admin/`. Media se sirve en DEBUG. Idioma es-cl y zona horaria America/Santiago.
- `ahora_mismo.html`, `inbox.html` y `perfil.html`: destinos básicos de lectura del navbar. La creación de publicaciones, respuestas, gestión de avales, aprobaciones DAE y acciones por rol quedan para versiones posteriores. Visitar Inbox no marca mensajes como leídos.
- `core/management/commands/cargar_datos_demo.py`: carga no interactiva y transaccional con get_or_create; crea tres sedes, dae_rancagua, lider_rancagua y est1 a est5 con contraseña inicial 1234 y dos eventos aprobados a 7/14 días. No duplica ni sobrescribe cuentas o eventos existentes al repetirse. Las fechas se asignan al crear: repetir el comando no reactiva eventos vencidos. RUT y teléfonos demo son sintéticos. DAE es un rol de negocio, sin acceso staff al admin Django.
- `core/tests.py`: pruebas de registro/rol, correo duplicado, login por username/correo, logout POST, filtrado temporal/estado/sede, contador y permisos de preinscripción.

Flujo conectado: visitante → registro/login → home de sede/intersede → POST de preinscripción o cancelación → home con contador actualizado. La v2 utiliza el esquema v1 sin nuevas migraciones.

Validación: `manage.py check` sin errores, `manage.py makemigrations --check --dry-run --noinput` sin cambios, cinco pruebas con `manage.py test core --noinput` (incluida protección CSRF) y `manage.py cargar_datos_demo` ejecutado dos veces para verificar idempotencia. Resultado demo: 3 sedes, 7 cuentas, 2 eventos aprobados y contraseñas verificadas. No se realizó inspección visual en navegador. Commit solicitado: `home y login sin branding aun` (el código sí incluye la identidad base INACAP solicitada). Destino: `origin main`.

Integración Git: el primer push detectó dos commits remotos anteriores (`f80f841`, `424221e`) de un prototipo `inacap_smart` con modelo Imagen. Se incorporó ese historial mediante merge, resolviendo los conflictos en favor de la implementación v1/v2 solicitada (core, migración inicial, manage.py y requirements). La configuración activa es exclusivamente `config.settings` y la base activa es PostgreSQL; `inacap_smart/` y `db.sqlite3` se conservan como archivos históricos remotos sin uso en esta aplicación. Los cachés remotos se retiraron del índice para respetar `.gitignore`. No se utilizó push forzado.
