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

## Versión 3 (v3) · Foro por sede e iniciativas al buzón

Objetivo: habilitar Ahora Mismo, comentarios cronológicos y canalización automática de iniciativas a Líderes/DAE, unificando el documento maestro y la hoja de ruta v1–v6.

Archivos modificados:

- `CONTEXTO.md`: sustituido por el contenido maestro proporcionado para INACAP Smart, con narrativa, reglas, nueve entidades y alcance progresivo v1–v6. Mantiene literalmente el stack objetivo indicado (Python 3.12 / Django 5.x). **Diferencia del entorno real:** el venv existente ejecuta Python 3.14.7 y Django 6.1.3; no se cambiaron versiones ni dependencias en este sprint. Resolver esta diferencia por consenso antes de modificar el entorno; `requirements.txt` conserva las dependencias instaladas.
- `core/forms.py`: PublicacionForoForm admite solo etiq_publ, tit_publ, cont_publ e img_publ (opcional y validada con Pillow); ComentarioForoForm admite únicamente cont_come. Autor, sede y relaciones se asignan exclusivamente en servidor.
- `core/views.py`: foro_ahora_mismo exige login, permite GET/POST y filtra por sede_publ_id = request.user.sede_usu_id, con orden descendente de fech_publ y pk. El parámetro etiqueta admite solo AHORA_MISMO, NOTICIA e INICIATIVA; otros valores muestran todas. Usuarios sin sede ven un aviso y no pueden publicar ni comentar. Se precargan autores y comentarios, ordenados ascendentemente por fech_come/pk. comentar_publicacion exige POST, CSRF y misma sede, rechaza texto vacío y conserva errores visibles. El POST válido redirige para evitar reenvío accidental por recarga.
- `core/urls.py`: `/foro/` y `/foro/<publ_id>/comentar/`; `/ahora-mismo/` redirige al foro por compatibilidad.
- `templates/base.html`: Ahora Mismo enlaza directamente al foro y señala la sección activa.
- `static/js/animaciones.js`: añade vista previa local de imagen con URL.createObjectURL y libera la URL previa al cambiar archivo. Reutiliza IntersectionObserver, entrada desde los costados y respeto de movimiento reducido. El muro se actualiza mediante recarga normal, sin WebSockets ni librerías adicionales.
- `core/management/commands/cargar_datos_demo.py`: si Rancagua no tiene publicaciones, crea una AHORA_MISMO y una INICIATIVA ficticias. La iniciativa genera sus avisos por la misma función que utiliza la vista. Repetir la carga no duplica publicaciones ni mensajes; si ya existe cualquier publicación de Rancagua se omite ese sembrado inicial.
- `core/tests.py`: ajusta la comprobación de la antigua ruta para seguir su redirección al foro.
- `CONTEXTO_VERSIONES.md`: registra esta implementación y su validación.

Archivos creados:

- `templates/foro.html`: caja multipart con foto opcional y vista previa, filtros por etiqueta, feed animado, nombre/rol/carrera/fecha del autor, contenido escapado, imagen, comentarios y formularios rápidos con IDs únicos. No muestra corr_usu ni tel_usu de autores.
- `core/services.py`: notificar_iniciativa recibe la publicación guardada y crea MensajeInbox solo para usuarios de su sede con rol LIDER_ESTUDIANTIL o DAE. Establece remi_inbo=None, tipo_inbo=INICIATIVA_BUZON, publ_inbo, asunto con título o Sin título (limitado a los 255 caracteres migrados), cuerpo con iniciativa y nom_usu/carr_usu/corr_usu/tel_usu. Retorna el número de destinatarios. La vista guarda publicación y mensajes en una transacción; si falla el envío a BD no queda una publicación parcial. La demo también se ejecuta dentro de una transacción.
- `core/test_foro.py`: ocho pruebas nuevas de autenticación, filtros y orden, aislamiento entre sedes, imposición de autor/sede, destinatarios exactos, contacto privado, validaciones, comentarios, CSRF, subida de imagen válida/inválida, rollback e idempotencia demo. Utiliza imágenes temporales y datos ficticios.

Validación: `manage.py check` sin errores; `manage.py migrate --noinput` sin migraciones pendientes; `manage.py makemigrations --check --dry-run --noinput` sin cambios; `manage.py test core --noinput` con 13 pruebas aprobadas (5 de v2 + 8 de v3). No se crearon apps ni migraciones ni se alteraron modelos. El comando demo se ejecuta para dejar las dos publicaciones y los avisos en PostgreSQL. No se realizó inspección visual en navegador.

Siguiente paso (v4): construir Mi Perfil propio y público en `/perfil/` y `/perfil/<id>/`, foto circular, biografía editable, rol, carrera, año, sede, historial de eventos y resumen de actividad. Aplicar privacidad del teléfono según rol. En v3 se conservan los destinos básicos de Perfil e Inbox existentes de v2; no se implementaron las funcionalidades completas de v4, v5 ni el Panel DAE de v6.

Commit previsto: `v3: foro ahora mismo por sede, iniciativas a buzon y contexto maestro v1-v6`. Destino solicitado: `origin main`.
