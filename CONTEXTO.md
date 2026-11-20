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
* **Almacenamiento Multimedia:** `Pillow` + `ImageField` en `media/` local (nunca escribir rutas de archivos a mano para permitir migración directa a **Huawei OBS** con `django-storages`).
* **Frontend:** HTML5 + **Bootstrap 5 (CDN)** + CSS3 (`static/css/estilos.css`) + **JavaScript Vanilla puro** (`static/js/animaciones.js`).
* **Diseño oficial Blanca (vigente desde v5):** Fondo general `#9D1916` con texto `#FFFFFF`; botones/acento/bordes `#E61E28` con texto blanco; acento suave y buscador `#E9A0A2` con texto `#1A1A1A`. Tarjetas, formularios, modales y superficies de contenido blancos con texto negro. Roboto Regular 400 para texto, Light 300 para metadatos, Italic 400 para cursivas; títulos y destacados `'Myriad Pro', 'Roboto', sans-serif` en 700. Roboto se importa desde Google Fonts; Myriad Pro usa la instalación local si existe, sin distribuir fuentes licenciadas.
* **Header y navegación v5:** Buscador funcional `?q=` en Home o Foro, avatar circular con exactamente “Mi cuenta”, “Mis publicaciones” y “Log Out” (POST), título de vista centrado y LogoInacap a la derecha con `width: 20%`. Conservar `<!-- ESPACIO LOGO INSTITUCIONAL AQUI (LogoInacap 20% width) -->` hasta recibir el logo. Navbar inferior con margen lateral 5% por lado y cuatro enlaces: Inicio (`/`), Foro (`/foro/`), Actividades (`/#actividades`) y Buzón de sugerencias (`/inbox/`, badge de no leídos).

### 4.2. Estructura del Repositorio
```text
Hackaton_Inacap_Huawei_LuxNova/
├── config/                  # settings.py, urls.py, wsgi.py
├── core/                    # Única app MVT: models.py, views.py, forms.py, urls.py, admin.py
│   └── management/commands/ # cargar_datos_demo.py (datos ficticios)
├── templates/               # base.html, home.html, login.html, registro.html, foro.html, perfil.html, inbox.html
├── static/                  # css/estilos.css, js/animaciones.js
├── media/                   # Archivos subidos en local
├── CONTEXTO.md              # Este documento maestro
├── CONTEXTO_VERSIONES.md    # Bitácora acumulativa de versiones (v1 a v6)
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
5. Evento: tit_even, desc_even, ban_even (ImageField), cat_even (TODO_PUBLICO, CARRERAS_AFINES), alc_even (SEDE, INTERSEDE), sede_even (FK Sede), esp_even (espacio solicitado), fech_even, crea_even (FK Usuario), est_even (PENDIENTE_DAE, APROBADO, RECHAZADO), asis_even (M2M Usuario).
6. PublicacionForo: aut_publ (FK Usuario), sede_publ (FK Sede), etiq_publ (AHORA_MISMO, NOTICIA, INICIATIVA), tit_publ, cont_publ, img_publ (ImageField), fech_publ.
7. ComentarioForo: publ_come (FK PublicacionForo), aut_come (FK Usuario), cont_come, fech_come.
8. MensajeInbox: dest_inbo (FK Usuario), remi_inbo (FK Usuario nullable; None = Sistema Oficial INACAP), tipo_inbo (SISTEMA, SOLICITUD_AVAL, INICIATIVA_BUZON), asun_inbo, cuer_inbo, club_inbo (FK Club nullable), publ_inbo (FK PublicacionForo nullable), leid_inbo, fech_inbo.
9. RegistroAuditoria: dae_audi (FK Usuario), acc_audi, det_audi, fech_audi.
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
- v6 — Postulación a Club, Reserva de Espacios (Sin Solapamientos) y Panel/Auditoría DAE [VERSIÓN FINAL - PENDIENTE]:
  - Alcance: Formularios integrados en Mi Perfil según rol: (1) Postulación a Club seleccionando 4 compañeros de sede; (2) Solicitud de Reserva de Espacio/Evento; (3) Panel DAE/Admin para aprobar clubes (ascendiendo al creador a LIDER_ESTUDIANTIL + aviso Inbox), aprobar eventos validando no solapamiento de espacio/fecha/sede, editar roles de usuarios y visualizar la tabla de RegistroAuditoria.

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

Perfil: `/perfil/` permite solo al dueño editar foto/bio; `/perfil/<id>/` es una consulta para usuarios autenticados. `?formato=json` devuelve un resumen autorizado del evento aprobado próximo o más reciente del organizador; JS Vanilla lo actualiza cada 20 segundos. Los contadores e historial “Eventos Asistidos” representan la relación de preinscripción existente: todavía no hay control de asistencia efectiva. Los botones v6 están deshabilitados y rotulados como pendientes.

Memoria técnica acumulativa: [CONTEXTO_VERSIONES.md](CONTEXTO_VERSIONES.md).

## 6. Inbox, avales y dominios institucionales (v5)

Registro: corr_usu se normaliza a minúsculas y admite exclusivamente dominios exactos `inacapmail.cl` e `inacap.cl`. Se rechazan dominios externos, subdominios y sufijos engañosos, además de duplicados. Demo: estudiantes/líder en @inacapmail.cl y DAE en @inacap.cl; datos siempre sintéticos. No se modifican automáticamente las cuentas ajenas a la demo.

`/inbox/` muestra exclusivamente mensajes recibidos por el usuario. Al abrir, marca avisos del sistema y solicitudes resueltas como leídos; solicitudes con AvalClub pendiente siguen sin leer y destacadas. La pestaña de iniciativas solo se consulta y renderiza para LIDER_ESTUDIANTIL, DELEGADO, JEFATURA, DAE o ADMIN, con mensajes dirigidos al usuario y publicación de su sede actual. La generación automática del foro conserva los destinatarios de v3: Líderes y DAE de esa sede. Los demás roles autorizados solo ven iniciativas si fueron destinatarios; no se concede acceso general a mensajes ajenos.

`/inbox/aval/<id>/` solo acepta POST con CSRF y dueño del aval en la misma sede del club. Se almacena una única respuesta ACEPTADO/RECHAZADO con fecha; no se puede cambiar una respuesta ni actuar sobre clubes cerrados. Una transacción con bloqueo del club serializa las respuestas concurrentes. Exactamente cuatro estudiantes distintos, de la sede y diferentes del creador, deben aceptar para pasar a PENDIENTE_DAE; se notifica una sola vez al creador y a cada DAE de la sede. Rechazar avisa al creador y deja el club en espera de avales, sin aprobación automática.

La demo agrega un club de est1 y solicita aval a est2–est5; repetir la carga no reinicia respuestas ni duplica avales o mensajes. V6 sigue pendiente: postulación a club desde Mi Perfil, reserva/evento y Panel de Aprobaciones/Auditoría DAE.
