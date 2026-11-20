# CONTEXTO MAESTRO DEL PROYECTO: INACAP Smart — Equipo LuxNova (Hackatón INACAP - Huawei)

> **INSTRUCCIÓN CRÍTICA PARA AGENTES IA Y DESARROLLADORES:**
> Este archivo es la **única fuente de verdad** del repositorio `Hackaton_Inacap_Huawei_LuxNova`. Antes de crear o editar cualquier archivo, lee este documento y `CONTEXTO_VERSIONES.md`. No dividas el proyecto en múltiples apps ni alteres los nombres de columnas ya migrados en PostgreSQL.

---

## 1. Problema, Solución y Diferenciador (Clave para el Pitch)

* **Problemática:** Los estudiantes de INACAP no tienen una forma centralizada y sencilla de crear comunidad, proponer iniciativas ni enterarse a tiempo de las actividades y eventos de su sede. La información está dispersa y la relación operativa entre la DAE y los estudiantes es distante.
* **Solución (INACAP Smart):** Plataforma web institucional segmentada por **Sede** (con soporte de actividades **Intersede**) que centraliza:
  1. **Cartelera de Eventos (Sede e Intersede):** Eventos aprobados por la DAE organizados por DAE, Jefaturas de Carrera y Líderes Estudiantiles, con pre-inscripción en 1 clic.
  2. **Muro "Ahora Mismo" (Foro en vivo por Sede):** Publicaciones cronológicas inversas con foto opcional, comentarios y etiquetas (`#AhoraMismo`, `#Noticia`, `#Iniciativa`).
  3. **Postulación a Clubes con Aval de Pares (4 Estudiantes):** Para ser Líder Estudiantil y crear un club, el estudiante postula en su perfil inscribiendo a **4 compañeros de su sede**, quienes reciben una solicitud en su Inbox interno. Solo cuando los 4 confirman el aval, la solicitud pasa a aprobación de la DAE.
  4. **Reserva de Espacios, Aprobación y Auditoría DAE:** Líderes, Delegados y Jefaturas solicitan espacios y eventos; la DAE aprueba verificando disponibilidad (sin solapamiento de espacio/fecha en la misma sede) y todo queda registrado en una tabla de **Auditoría**.
  5. **Inbox Oficial del Sistema y Buzón de Iniciativas:** Mensajería interna unificada para notificaciones automáticas del sistema, confirmación de avales y recepción de `#Iniciativa` (con contacto privado del estudiante dirigido solo a Líderes y DAE).
* **Diferenciador:** Es una solución **específica por sede y centrada en la vida estudiantil activa** (aval entre pares + iniciativas directas a líderes/DAE), sin reemplazar los sistemas académicos formales de INACAP.
* **Antes vs. Después (Narrativa de Demo):**
  * *Antes:* Información fragmentada en afiches/redes externas, baja participación, procesos lentos o informales para levantar clubes y sin trazabilidad de iniciativas estudiantiles.
  * *Después:* Todo ocurre en un solo portal por sede con validación comunitaria, aprobación trazable por DAE y visibilidad inmediata para todos los estudiantes.
* **Restricción de Privacidad y Datos:** No utilizar datos personales reales. Los datos de demo/pruebas son sintéticos. El teléfono (`tel_usu`) solo es visible para su propietario o un visitante con rol LIDER_ESTUDIANTIL, DELEGADO, JEFATURA, DAE o ADMIN. Aplicar esta regla tanto en HTML como en JSON y tablas de asistentes.

---

## 2. Equipo y Roles
* **Blanca Lagos** — Líder de Equipo
* **Álvaro Contardo** — Arquitectura, Orquestación IA & Desarrollo
* **Integrante 3** — Frontend / Datos de prueba / QA
* **Integrante 4** — Negocio / Métricas de impacto / Pitch

---

## 3. Método de Evaluación (Rúbrica Oficial INACAP - Huawei — 100 Ptos.)
> **Nota del jurado:** En la demo en vivo se evalúa el funcionamiento real en *Solidez técnica* y la claridad de exposición en *Pitch y equipo*.

1. **Relevancia del desafío (25 Ptos.):** Entender qué falla hoy en la relación DAE-Estudiantes, a quién afecta y dónde interviene la solución. Sustentar con contexto y mantener foco en una parte concreta del problema.
2. **Solidez técnica (30 Ptos.):** Demostrar el flujo principal completo funcionando (*Registro/Login -> Eventos -> Foro/Iniciativa -> Postulación Club + 4 Avales -> Aprobación DAE -> Creación de Evento*), diferenciar lo real de lo simulado, justificar arquitectura relacional en **PostgreSQL** (escalable a **Huawei Cloud RDS** y **Huawei OBS**) y proteger datos sensibles.
3. **Impacto y viabilidad (25 Ptos.):** Valor concreto para la institución (aumento de participación, trazabilidad DAE, ahorro de tiempos de gestión) con indicadores medibles y definición de un piloto viable en sede.
4. **Pitch y equipo (20 Ptos.):** Historia clara, guía paso a paso de la demo en vivo, dominio técnico ante preguntas y coordinación del equipo.

---

## 4. Stack Tecnológico y Arquitectura del Proyecto

### 4.1. Stack Oficial (No cambiar sin consenso)
* **Python 3.12** (entorno virtual `venv/` en la raíz).
* **Django 5.x** bajo patrón estricto **MVT** en una única aplicación central (`core/`).
* **Base de Datos:** **PostgreSQL** local (`hackaton_luxnova` conectado en `config/settings.py` vía `psycopg2-binary`), preparado para migrar a **Huawei Cloud RDS for PostgreSQL**.
* **Almacenamiento Multimedia (v7):** `Pillow` + `ImageField` con `MEDIA_ROOT = BASE_DIR / 'Galeria'`, `MEDIA_URL = '/media/'` y subcarpetas perfiles/, eventos/, foro/. Conservar `.url` de ImageField para permitir futura migración a Huawei OBS; nunca construir rutas manuales. El antiguo media/ queda como copia histórica, sin borrar archivos.
* **Frontend:** HTML5 + **Bootstrap 5 (CDN)** + **Bootstrap Icons 1.11.3 (CDN)** + CSS3 (`static/css/estilos.css`) + **JavaScript Vanilla puro** (`static/js/animaciones.js`, `buscadores.js`, `dm_drawer.js`).
* **Diseño oficial Blanca (vigente desde v5):** Fondo general `#9D1916` con texto `#FFFFFF`; botones/acento/bordes `#E61E28` con texto blanco; acento suave y buscador `#E9A0A2` con texto `#1A1A1A`. Tarjetas, formularios, modales y superficies de contenido blancos con texto negro. Roboto Regular 400 para texto, Light 300 para metadatos, Italic 400 para cursivas; títulos y destacados `'Myriad Pro', 'Roboto', sans-serif` en 700. Roboto se importa desde Google Fonts; Myriad Pro usa la instalación local si existe, sin distribuir fuentes licenciadas.
* **Header y navegación vigentes (v8):** Navbar blanco #FFFFFF en una sola fila de escritorio, texto #1A1A1A, borde inferior de 3px #E61E28 y sombra suave. Logo de Galeria/logo.png a la izquierda enlaza al Home; a la derecha Inicio, Foro, Actividades y Buzón de sugerencias (badge rojo/blanco), seguido por avatar circular con exactamente “Mi cuenta”, “Mis publicaciones” y “Log Out” (POST). Visitantes ven Iniciar sesión/Registrarse. Bootstrap navbar-expand-lg pliega el menú en pantallas menores a 992px; el logo queda limitado a 46px de alto y ancho automático. Sin buscador en el header; el backend conserva `?q=` para enlaces existentes. El título de vista es blanco dentro de main, fuera del navbar. Las rutas conservan el namespace core.

### 4.2. Estructura del Repositorio
```text
Hackaton_Inacap_Huawei_LuxNova/
├── config/                  # settings.py, urls.py, wsgi.py
├── core/                    # Única app MVT: models.py, views.py, forms.py, urls.py, admin.py
│   └── management/commands/ # cargar_datos_demo.py (datos ficticios)
├── templates/               # base.html, home.html, login.html, registro.html, foro.html, perfil.html, inbox.html
├── static/                  # css/estilos.css, js/animaciones.js
├── Galeria/                 # Logo e imágenes: perfiles/, eventos/, foro/ (MEDIA_ROOT)
├── media/                   # Archivos históricos conservados como respaldo
├── CONTEXTO.md              # Este documento maestro
├── CONTEXTO_VERSIONES.md    # Bitácora acumulativa de versiones (v1 a v11)
└── requirements.txt         # Dependencias instaladas

````
1. Una sola app (core/): No crear nuevas apps (usuarios, foro, etc.) para evitar conflictos de migraciones entre agentes. Todo vive de forma modular dentro de core/.
2. Nomenclatura Obligatoria de Campos (core/models.py): Todos los atributos de base de datos llevan el formato [3-4 primeras letras del campo]_[3-4 primeras letras de la tabla] en minúsculas (ej. nom_usu, rut_usu, sede_even, est_club). No renombrar columnas existentes.
3. Comentarios Obligatorios: Antes de CADA clase y CADA función/método (en Python y JS), incluir un comentario claro explicando qué hace realmente, qué recibe y qué devuelve.
4. Prohibiciones Técnicas: No usar TypeScript, React, Vue, C ni django-channels/WebSockets (usar JS Vanilla fetch / recarga ligera). No ejecutar comandos interactivos en terminal (usar --noinput).
5. Reglas de Git y Calidad:
   - Antes de empezar: git pull origin main.
   - Antes de hacer commit: verificar venv\Scripts\python.exe manage.py check y migrate sin errores, y actualizar CONTEXTO_VERSIONES.md.
   - Si se instala un paquete: actualizar requirements.txt y avisar al equipo.
1. Sede: nom_sede (único), dir_sede.
2. Usuario (AUTH_USER_MODEL): Hereda de AbstractUser + nom_usu, rut_usu (único), corr_usu (único), tel_usu (privado), sede_usu (FK Sede), carr_usu (carrera), anio_usu (año ingreso), rol_usu (ESTUDIANTE, DELEGADO, LIDER_ESTUDIANTIL, JEFATURA, DAE, ADMIN), foto_usu (ImageField), bio_usu.
3. Club: nom_club, cat_club (VIDA_ESTUDIANTIL, DESARROLLO_ACADEMICO, OTRO), desc_club, sede_club (FK Sede), lid_club (FK Usuario), est_club (PENDIENTE_AVALES, PENDIENTE_DAE, APROBADO, RECHAZADO), fech_club.
4. AvalClub: club_aval (FK Club), estu_aval (FK Usuario), est_aval (PENDIENTE, ACEPTADO, RECHAZADO), fech_aval.
5. Evento: tit_even, desc_even, ban_even (ImageField), cat_even (TODO_PUBLICO, CARRERAS_AFINES), alc_even (SEDE, INTERSEDE), sede_even (FK Sede), esp_even (espacio solicitado), fech_even (inicio), ffin_even (término nullable para históricos, obligatorio en formulario/demo), crea_even (FK Usuario), est_even (PENDIENTE_DAE, APROBADO, RECHAZADO), asis_even (M2M Usuario).
6. PublicacionForo: aut_publ (FK Usuario), sede_publ (FK Sede), etiq_publ (AHORA_MISMO, NOTICIA, INICIATIVA), tit_publ, cont_publ, img_publ (ImageField), fech_publ.
7. ComentarioForo: publ_come (FK PublicacionForo), aut_come (FK Usuario), cont_come, fech_come.
8. MensajeInbox: dest_inbo (FK Usuario), remi_inbo (FK Usuario nullable; None = Sistema Oficial INACAP), tipo_inbo (SISTEMA, SOLICITUD_AVAL, INICIATIVA_BUZON), asun_inbo, cuer_inbo, club_inbo (FK Club nullable), publ_inbo (FK PublicacionForo nullable), leid_inbo, fech_inbo.
9. RegistroAuditoria: dae_audi (FK Usuario), acc_audi, det_audi, fech_audi.
10. MensajeDirecto: emi_mens (FK Usuario, dms_enviados), rec_mens (FK Usuario, dms_recibidos), cont_mens, leid_mens (default False), fech_mens (auto_now_add). Conversaciones privadas por pareja de participantes.
Regla para Agentes IA: Ejecutar estrictamente una versión a la vez siguiendo este orden. No implementar funcionalidades de versiones futuras antes de cerrar, probar (manage.py check) y documentar la versión actual en CONTEXTO_VERSIONES.md.
- v1 — Base de Datos Relacional y Arquitectura MVT [COMPLETADA]:
  - Alcance: Creación de app única core/, configuración PostgreSQL (hackaton_luxnova), migración de las 9 tablas relacionales con nomenclatura [campo]_[tabla], core/admin.py y .gitignore.
- v2 — Identidad Visual INACAP, Registro, Login y Home de Eventos [COMPLETADA]:
  - Alcance: Paleta institucional (#E30613, #1A1A1A, #FFFFFF), base.html con Navbar de 4 enlaces y espacio reservado para logo, registro por sede/carrera/año, login/logout, home.html (Eventos Sede + Intersede + Pre-inscripción), animaciones.js (IntersectionObserver), cargar_datos_demo.py y CONTEXTO_VERSIONES.md.
- v3 — Foro "Ahora Mismo" por Sede y Disparo Automático de Iniciativas [COMPLETADA]:
  - Alcance: Ruta /foro/ filtrada por sede_usu, publicaciones cronológicas con foto opcional, comentarios y regla automática: al publicar con etiqueta INICIATIVA, se envía un MensajeInbox (INICIATIVA_BUZON) con correo y teléfono del autor a todos los LIDER_ESTUDIANTIL y DAE de la sede.
- v4 — Perfiles Estilo Instagram (Propio y Público) + Métricas de Asistencia [COMPLETADA]:
  - Alcance: Rutas /perfil/ y /perfil/<id>/ con foto circular, bio editable, insignia de rol, carrera, año, sede, privacidad estricta de tel_usu (solo visible para Líderes, Delegados, Jefatura y DAE), historial público de eventos asistidos/organizados y tarjeta resumen en vivo del próximo evento para Líderes/DAE.
- v5 — Inbox del Sistema (Chat Oficial + Confirmación de 4 Avales + Buzón Iniciativas) [COMPLETADA]:
  - Alcance: Ruta /inbox/ con badge de no leídos, mensajes oficiales del Sistema con botones Aceptar / Rechazar Aval (al llegar a 4 avales aceptados, el Club escala automáticamente a PENDIENTE_DAE y notifica a la DAE) y pestaña Buzón de Iniciativas visible solo para Líderes y DAE.
- v6 — Postulación a Club, Reserva de Espacios (Sin Solapamientos) y Panel/Auditoría DAE [COMPLETADA — VERSIÓN FINAL]:
  - Alcance: Formularios integrados en Mi Perfil según rol: (1) Postulación a Club seleccionando 4 compañeros de sede; (2) Solicitud de Reserva de Espacio/Evento; (3) Panel DAE/Admin para aprobar clubes (ascendiendo al creador a LIDER_ESTUDIANTIL + aviso Inbox), aprobar eventos validando no solapamiento de espacio/fecha/sede, editar roles de usuarios y visualizar la tabla de RegistroAuditoria.
- v7 — Navbar y centralización de imágenes [COMPLETADA — PRIMERAS CORRECCIONES UI Y GALERÍA]:
  - Alcance: Navbar blanco en una fila, menú móvil plegable, título en main, Galeria como MEDIA_ROOT y guías de dimensiones con validación de tamaño/formato de imágenes.
- v8 — Header/Nav blanco lineal e intervalos reales de eventos [COMPLETADA]:
  - Alcance: Header y nav blancos con respaldo inline, logo compacto de 46px, menú expand-lg, ffin_even y validación de inicio/término, disponibilidad por intersección real y rangos visibles en Home/Perfil/panel DAE.
- v9 — DM, buscadores y dashboards de participación [COMPLETADA]:
  - Alcance: Drawer DM privado con Visto y canal @sistema, búsqueda común por nombre/nickname y avalistas con chips, DAE solo aprueba, gráficos de participación y RUTs enmascarados por rol/sede.
- v10 — Administración de cuentas y configuración con engranaje [COMPLETADA]:
  - Alcance: Altas institucionales por ADMIN/superusuario, configuración propia en página dedicada, perfil estudiantil centrado en próximos inscritos, postulación de club separada y DM global de 58px.

## 5. Registro y catálogo oficial de carreras (v4)

`core/models.py` define CARRERAS_CHOICES y conserva carr_usu como CharField(max_length=255). Valores y etiquetas exactos:

- Ing. Informática (4 años)
- Ing. Diseño (4 años)
- Ing. Mecánica (4 años)
- Técnico Analista Programador
- Técnico Enfermería
- Técnico Mecánica
- Técnico Diseño
- Técnico Gastronomía

El registro usa un selector cerrado. Las ingenierías indican 4 años; los técnicos mantienen las etiquetas exactas solicitadas sin inventar duraciones. La migración 0002 no elimina ni transforma valores históricos; la carga demo sí actualiza sus siete cuentas a una carrera válida.

`validar_rut_chileno` limpia puntos/espacios, acepta DV numérico o K, verifica Módulo 11 y devuelve cuerpo-DV (sin ceros iniciales, K mayúscula). El formulario exige RUT válido y comprueba unicidad de rut_usu y corr_usu sin distinguir mayúsculas; el correo se guarda en minúsculas. La vista repite consultas de duplicados y captura IntegrityError dentro de una transacción para mostrar un error Bootstrap si hay una inserción concurrente. Se conservan las restricciones unique existentes en PostgreSQL. Datos históricos ajenos a la demo no se reescriben automáticamente.

Perfil: `/perfil/` y `/perfil/<id>/` son vistas de lectura para usuarios autenticados. Desde v10, solo el dueño configura foto/bio, nickname, correo y contraseña en `/perfil/configuracion/` mediante el engranaje de su cabecera. `?formato=json` devuelve un resumen autorizado del evento aprobado próximo o más reciente del organizador; JS Vanilla lo actualiza cada 20 segundos. Los contadores e historial “Eventos Asistidos” representan la relación de preinscripción existente: todavía no hay control de asistencia efectiva. El perfil propio conserva gestión según rol, pero la postulación de club vive únicamente en su página dedicada.

Memoria técnica acumulativa: [CONTEXTO_VERSIONES.md](CONTEXTO_VERSIONES.md).

## 6. Inbox, avales y dominios institucionales (v5)

Registro: corr_usu se normaliza a minúsculas y admite exclusivamente dominios exactos `inacapmail.cl` e `inacap.cl`. Se rechazan dominios externos, subdominios y sufijos engañosos, además de duplicados. Demo: estudiantes/líder en @inacapmail.cl y DAE en @inacap.cl; datos siempre sintéticos. No se modifican automáticamente las cuentas ajenas a la demo.

`/inbox/` muestra exclusivamente mensajes recibidos por el usuario. Al abrir, marca avisos del sistema y solicitudes resueltas como leídos; solicitudes con AvalClub pendiente siguen sin leer y destacadas. La pestaña de iniciativas solo se consulta y renderiza para LIDER_ESTUDIANTIL, DELEGADO, JEFATURA, DAE o ADMIN, con mensajes dirigidos al usuario y publicación de su sede actual. La generación automática del foro conserva los destinatarios de v3: Líderes y DAE de esa sede. Los demás roles autorizados solo ven iniciativas si fueron destinatarios; no se concede acceso general a mensajes ajenos.

`/inbox/aval/<id>/` solo acepta POST con CSRF y dueño del aval en la misma sede del club. Se almacena una única respuesta ACEPTADO/RECHAZADO con fecha; no se puede cambiar una respuesta ni actuar sobre clubes cerrados. Una transacción con bloqueo del club serializa las respuestas concurrentes. Exactamente cuatro estudiantes distintos, de la sede y diferentes del creador, deben aceptar para pasar a PENDIENTE_DAE; se notifica una sola vez al creador y a cada DAE de la sede. Rechazar avisa al creador y deja el club en espera de avales, sin aprobación automática.

La demo agrega un club de est1 y solicita aval a est2–est5; repetir la carga no reinicia respuestas ni duplica avales o mensajes. La v6 conecta postulación a club desde Mi Perfil, reserva/evento y Panel de Aprobaciones/Auditoría DAE.

## 7. Cierre funcional v6 (vigente)

La v6 completa los flujos pendientes de las versiones anteriores. Desde Mi cuenta, ESTUDIANTE postula clubes con exactamente cuatro compañeros activos ESTUDIANTE de su sede; se crean avales y solicitudes en Inbox dentro de una transacción. El perfil muestra estados y contador de avales. Tras cuatro aceptaciones, DAE/ADMIN resuelven el club desde el panel local; aprobar promueve a LIDER_ESTUDIANTIL únicamente si el creador era ESTUDIANTE. Cada resolución notifica y se registra en RegistroAuditoria; reenviar una resolución terminal no duplica efectos.

Desde v9, solo Líderes, Delegados, Jefatura y ADMIN solicitan eventos con banner opcional e intervalo futuro. DAE tiene gestión/aprobación, sin formulario ni acceso a crear eventos. Los espacios del selector son Auditorio Principal, Sala Multiuso 101, Laboratorio Computación 3, Patio Central / Ágora y Cancha Deportiva. La sede y creador se asignan en servidor. Gestores normales quedan PENDIENTE_DAE; ADMIN crea directamente APROBADO solo si está libre, dejando auditoría. DAE/ADMIN resuelven solicitudes locales ya enviadas por los organizadores.

Disponibilidad vigente desde v8: comparar eventos APROBADO de la misma sede y espacio sin distinguir mayúsculas con `otro.fech_even < evento.ffin_even` y `otro.ffin_even > evento.fech_even`. Los intervalos contiguos (término == siguiente inicio) no chocan. Se conserva bloqueo de Sede dentro de una transacción en creación directa y aprobación para evitar carreras concurrentes. Las solicitudes sin término o con término <= inicio no se aprueban. Las reservas aprobadas históricas sin término se tratan conservadoramente como abiertas desde su inicio hasta corregir el dato. No usar ORM/admin Django para eludir el control de aplicación.

En el perfil propio DAE/ADMIN: tres métricas locales (relaciones de preinscripción en eventos aprobados, iniciativas únicas publicadas en la sede y eventos aprobados), bandejas de clubes/eventos, gestión de rol_usu y auditoría. Todas las acciones requieren POST/CSRF, DAE/ADMIN y objeto de su sede. Cambiar rol_usu no cambia is_staff/is_superuser. JEFATURA ve Líderes/Delegados de su sede y cantidad de eventos aprobados organizados. Las vistas públicas no exponen paneles de gestión.

Logo oficial: `Galeria/logo.png`, disponible como `{% static 'logo.png' %}` porque STATICFILES_DIRS incluye static/ y Galeria/. El header conserva ancho 20% y muestra INACAP blanco si falla la imagen. El pie explica datos ficticios y notificaciones externas simuladas vía Inbox.

Cuentas y guion de presentación: [CREDENCIALES.md](CREDENCIALES.md). cargar_datos_demo usa update_or_create para nueve cuentas de Rancagua, restablece sus roles y contraseñas según ese archivo, conserva relaciones y no reinicia decisiones de clubes/avales/eventos. Las antiguas contraseñas 1234 ya no aplican. Solo root_admin tiene flags Django is_staff/is_superuser. RUTs demo son identificadores sintéticos con DV válido, sin afirmar identidad de personas reales. Ejecutar la carga antes de la demostración; no entre el ascenso de est1 y la creación de su evento.

Rutas finales: `/club/postular/`, `/evento/solicitar/`, `/panel/club/<id>/<aprobar|rechazar>/`, `/panel/evento/<id>/<aprobar|rechazar>/`, `/panel/usuario/<id>/rol/`. Formularios y panel se integran en `/perfil/`. Nube Huawei sigue como destino arquitectónico; esta instancia usa PostgreSQL y archivos locales. No se ha implementado verificación de asistencia presencial.

## 8. Correcciones de interfaz y galería (v7 vigente)

Galeria/ centraliza todas las imágenes, sin ignorarse en Git. STATICFILES_DIRS mantiene `[BASE_DIR / 'static', BASE_DIR / 'Galeria']`: logo.png se resuelve como estático, mientras las subidas conservan `/media/perfiles/...`, `/media/eventos/...` y `/media/foro/...`. Se prepararon las tres subcarpetas con .gitkeep. El directorio media/ anterior contenía solo .gitkeep; no había imágenes pendientes de copia ni se eliminó ningún archivo. Para futuras copias, conservar rutas relativas y no sobrescribir colisiones con contenido diferente.

Guías visibles bajo cada campo (form-text text-muted): perfil 400 × 400 px, cuadrado 1:1 y máximo 2 MB; banner 1200 × 400 px, horizontal 3:1 y máximo 3 MB; foro 1080 × 720 px, horizontal o cuadrada y máximo 3 MB. Los selectores admiten PNG, JPEG y WebP; el servidor verifica el formato real después de Pillow y los límites en bytes (1 MB = 1024² bytes). Las dimensiones son recomendaciones, no requisitos de validación. No se redimensiona ni recorta el archivo: CSS realiza el encuadre visual.

`.avatar-perfil`: 130 × 130 px, círculo, object-fit cover, borde rojo de 3px. `.banner-evento`: ancho completo, aspect-ratio 3/1, alto máximo 240px y object-fit cover. `.foto-foro`: conserva proporciones con object-fit contain y altura limitada. Se mantiene la vista previa Vanilla JS del foro. El fallback del logo es oscuro para conservar contraste sobre el nuevo navbar blanco.

Estado de publicación: v6/v7 tienen commits locales. El push de v6 fue rechazado por la revisión automática por contraseñas en CREDENCIALES.md; el mismo contenido sigue en su historial. No reenviar esa publicación mediante una ruta alternativa. La v7 puede desarrollarse y probarse localmente; el push queda pendiente de una solución publicable sin credenciales.

## 9. Header lineal e intervalos reales (v8 vigente)

Header único `.header-institucional` y nav `.navbar.navbar-expand-lg.navbar-light.bg-white.px-4.py-2`, ambos con fondo blanco !important y respaldo inline. Logo izquierdo max-height 46px/width auto, navegación y control de usuario en un mismo ul a la derecha; plegado móvil bajo 992px. Enlaces oscuros con hover/activo rojo #E61E28, badge rojo/blanco y título blanco en main. No existe buscador en la cabecera. Se mantienen rutas con namespace core.

La migración 0003 agrega ffin_even DateTimeField(null=True, blank=True) sin borrar registros ni asumir duraciones históricas. SolicitarEventoForm exige ambos datetime-local y término posterior al inicio, interpretados en America/Santiago. Inicio debe ser futuro, como en v6. Home, historial de perfiles, solicitudes, panel DAE y resumen en vivo muestran Inicio/Término; históricos sin término muestran “Sin definir”. Auditoría incluye ambos extremos de las resoluciones.

El comando demo asigna a sus dos eventos intervalos explícitos de dos horas, conserva los inicios existentes y completa términos ausentes/inválidos. No asigna término a eventos ajenos a la demo. Si una reserva aprobada histórica no tiene término, hay que completarlo desde administración antes de liberar automáticamente su espacio para nuevas reservas; no se inventa un fin de dos horas para datos reales.

V8 queda con commit local y documentación actualizada. El push continúa bloqueado por la revisión automática que rechazó las contraseñas del historial v6; no se ha resuelto ni se ha intentado eludir esa restricción.

## 10. Mensajería y participación (v9 vigente)

Cuenta oficial @sistema: nom_usu LuxNova Sistema, corr_usu sistema@inacap.cl, RUT reservado 00000000-0, rol ADMIN, activa, sin sede ni flags Django y con contraseña inutilizable. Es una excepción técnica al RUT de registro; no es una cuenta humana. post_migrate y cargar_datos_demo garantizan su existencia. No aparece en búsqueda ni selección de avales; el registro reserva su nickname en cualquier combinación de mayúsculas. No puede enviar mensajes humanos ni recibir respuestas de usuarios.

`enviar_notificacion_sistema(usuario_destino, texto_mensaje)` crea un MensajeDirecto oficial. Registro da bienvenida; avisos nuevos de Inbox se reflejan mediante post_save (sin duplicar al cambiar leído). Los avisos creados con bulk_create se conectan explícitamente en los flujos de cuarto aval e iniciativas. Cambios de aval, resolución de club/evento y publicación directa ADMIN generan DM. El contacto de iniciativas queda en el Inbox protegido por rol: el DM solo anuncia que hay una iniciativa. No se migran retroactivamente avisos antiguos a DM.

APIs autenticadas sin caché: `/api/buscar-usuarios/?q=...&solo_sede=0|1`, `/api/dm/conversaciones/`, `/api/dm/<id>/`, `/api/dm/<id>/enviar/` y `/api/dm/<id>/leer/`. Búsqueda por nombre O username (quita @ inicial), activos, excluye cuenta propia y sistema; solo_sede=1 restringe a estudiantes de la misma sede. Respuesta pública sin RUT/correo/teléfono. Devolver máximo 20 resultados, 100 conversaciones y 100 últimos mensajes por hilo para acotar el piloto; no hay paginación de historial antiguo en esta versión.

Hilos y lectura siempre se consultan desde el usuario autenticado, nunca desde un ID de emisor proporcionado por cliente. Enviar/leer requiere POST y CSRF. Enviar admite 1–5000 caracteres y marca recibidos del hilo como leídos; abrirlo hace fetch GET seguido de POST de lectura hasta el último mensaje recibido observado. La interfaz muestra Visto debajo del último envío leído. GET no modifica lectura. Historial y contador se actualizan por polling cada 5 segundos con página visible, sin WebSockets. @sistema está fijado primero, verificado y con input bloqueado.

UI: acceso Buscar personas en el navbar abre buscador compacto por nombre/@nickname. El drawer usa el mismo endpoint. La postulación añade hasta cuatro chips removibles e IDs ocultos; el servidor conserva su validación de cuatro pares autorizados. Sin JS sigue disponible el select original; no permite eludir controles de sede/rol. Bootstrap maneja offcanvas/modal y CSS mantiene la paleta; no se añadió framework ni librería de gráficos.

DAE/ADMIN no se preinscriben (botón oculto y POST rechazado). Sus tarjetas de eventos locales muestran gráficos CSS de inscritos por carrera y **distribución por año de ingreso**. La relación M2M no conserva fecha de inscripción: no se inventan fechas ni se presenta el gráfico como historial de altas. Consultar RUTs muestra nombre/carrera y solo cuerpo del RUT con últimos cuatro dígitos ocultos y sin DV. No se muestran estadísticas identificables de sedes ajenas, aunque el evento sea intersede.

Dashboard propio: DAE/ADMIN ve participaciones por carrera en eventos aprobados de su sede; Jefatura ve participaciones por evento solo de su carrera y los Líderes/Delegados locales. Participación significa relación de preinscripción, no asistencia efectiva, y una persona en varios eventos cuenta varias participaciones. El panel DAE distingue solicitudes de clubes y de eventos/reservas; DAE no crea eventos. El rol ADMIN conserva esa facultad. El bloqueo de publicación del historial con contraseñas sigue pendiente y no se elude desde v9.

## 11. Cuentas, engranaje y perfil limpio (v10 vigente)

`/perfil/configuracion/`: solo edita al usuario autenticado (sin aceptar un ID de dueño). ConfiguracionCuentaForm permite foto_usu, bio_usu, username y corr_usu, más nueva_password/confirmar_password opcionales. Foto con guía 400 × 400 px y validación 2 MB/formato de v7. Nickname único sin distinguir mayúsculas y sin ningún espacio, excluyendo el propio PK; sistema sigue reservado. Correo institucional normalizado y único excluyendo al dueño. Si se cambia contraseña, ambos campos coinciden y tienen mínimo seis caracteres; se usa set_password y update_session_auth_hash para conservar sesión. No se editan rol, RUT, sede, carrera ni flags Django. `/perfil/` ya no acepta POST de edición.

`/panel-admin/crear-cuenta/`: solo rol ADMIN o is_superuser; cuenta técnica sistema excluida. CrearCuentaInstitucionalForm pide nombre, nickname único, RUT Módulo 11 único, correo institucional único, teléfono, sede, carrera del catálogo, rol limitado a DAE/JEFATURA/DELEGADO/LIDER_ESTUDIANTIL/ADMIN y contraseña inicial (mínimo seis caracteres). No crea ESTUDIANTE por esta ruta ni concede is_staff/is_superuser. La sede se selecciona en el formulario; esta facultad administrativa puede crear cuentas en cualquier sede disponible, mientras aprobaciones/cambios de rol existentes siguen segmentados por sede. Cuenta, bienvenida @sistema y auditoría “Creó cuenta institucional” se guardan en una transacción. La sesión del administrador no se sustituye por la cuenta recién creada. Las contraseñas no se incluyen en el DM ni la auditoría.

La cabecera del perfil propio muestra engranaje Bootstrap Icons hacia configuración. No contiene el formulario viejo de foto/bio. Estudiantes ven primero “Próximos eventos a los que me inscribí” (aprobados y fecha de inicio futura), con inicio/término, sede, espacio, enlace al evento y cancelación POST que vuelve al perfil. La única acción de club es el enlace secundario “Solicitar creación de club estudiantil”. `/club/postular/` contiene el formulario con chips/buscador de cuatro pares y estado de todas las postulaciones propias; tras enviar redirige a la misma página. No se duplica ese formulario ni su listado en el perfil.

DM global: base.html carga Bootstrap Icons CDN y los scripts autenticados compartidos; incluye un único drawer al final de body dentro del condicional de sesión. Botón fijo: bottom/right 24px, 58 × 58px, z-index 1060, círculo rojo/blanco con icono bi-chat-dots-fill. Aparece en Inicio, Foro, Buzón, Perfil, Configuración y Postular Club (también en el panel de alta institucional). Se mantienen polling cada 5 segundos, CSRF y privacidad de v9. No se modifican modelos ni migraciones en v10. Continúa pendiente la publicación del historial rechazado por contraseñas.

## 12. Perfiles ordenados y mensajes visibles (v11 vigente)

La portada de TODOS los roles comparte el mismo orden: cabecera compacta de identidad/configuración, **Eventos a los que me preinscribí**, **Publicaciones realizadas por mí** y herramientas de participación. Perfiles ajenos conservan ese orden con títulos en tercera persona y botón **Enviar mensaje**. Se muestran inicialmente tres próximas preinscripciones y cuatro publicaciones; el resto se despliega con botones nativos details/summary. Las publicaciones y su contador respetan la sede del visitante. Historial y clubes quedan plegados en “Trayectoria y clubes”. No hay formularios de creación ni paneles administrativos incrustados en el perfil.

Los accesos **Crear evento** y **Eventos que estoy organizando** comparten el mismo bloque de herramientas. `/evento/solicitar/` contiene el formulario de evento y redirige a `/perfil/organizacion/` tras éxito. Esta última muestra exclusivamente eventos creados por el usuario autenticado, de cualquier estado, y sus preinscritos plegados por evento, con enlaces a perfil/mensaje y teléfono según los permisos existentes. DAE sigue sin crear eventos y DAE/ADMIN siguen sin preinscribirse; mostrar una sección vacía no concede permisos.

`/perfil/gestion/` concentra métricas, aprobaciones, roles y auditoría según rol/sede. Las listas largas DAE quedan plegadas. Resolver clubes/eventos o cambiar roles regresa a este panel; si el actor se cambia a ESTUDIANTE, regresa al perfil para evitar un destino 403. El formulario ADMIN de cuentas también tiene página dedicada en `/panel-admin/crear-cuenta/` y retorna a gestión. Configuración y postulación de clubes conservan sus páginas v10.

Mensajería: botón fijo rojo **Mensajes** con texto y SVG incluido en HTML, disponible en todas las páginas autenticadas, más acceso Mensajes en navbar y herramientas del perfil. Ya no depende de una fuente de iconos ni del JavaScript de Bootstrap para abrir/cerrar el drawer: `dm_drawer.js` maneja apertura, fondo, cierre, Escape, foco y Tab en Vanilla JS. Buscar por nombre/@nickname abre una conversación; el encabezado muestra **Ver perfil**. Desde cualquier perfil ajeno, **Enviar mensaje** abre directamente su hilo. `/mensajes/?usuario=<id>` es una entrada autenticada con autoapertura; GET solo renderiza, sin enviar ni marcar lecturas. Se conservan POST/CSRF, polling, cuenta oficial sin respuestas y las APIs v9. CSS/scripts propios llevan `?v=perfil11-final` para renovar caché. Se comprobó que Cloudflare entregaba una copia anterior del JS con la primera clave de versión; la clave final devuelve el mismo texto que los archivos locales.

Validación v11: 63 pruebas aprobadas, check y migraciones sin pendientes. Navegador Edge en 1366px, 1024px y 390px: perfil, búsqueda est2, apertura por botón, hilo móvil, Ver perfil y Enviar mensaje; sin enviar mensajes de prueba a personas. El servidor local permanece activo. El usuario indicó https://luxnova.cl: ese nombre sin www no devuelve dirección A/AAAA y el navegador muestra DNS_PROBE_FINISHED_NXDOMAIN. **https://www.luxnova.cl sí responde HTTP 200 y sirve los cambios actuales**, comprobados con sesión demo en el perfil y apertura real del drawer; CSS/JS públicos coinciden en texto con los locales al usar la versión final. Se conserva el túnel cloudflared existente sin cambiar su configuración ni DNS. El funcionamiento público a través del túnel es independiente del push Git, que sigue bloqueado por la revisión previa y no se reintentó.
