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
* **Restricción de Privacidad y Datos:** No utilizar datos personales reales. Todos los usuarios, RUTs, correos y teléfonos en fixtures/pruebas son **100% ficticios**, y el teléfono del estudiante (`tel_usu`) es **privado** (solo visible para Líderes Estudiantiles, Delegados, Jefatura y DAE).

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
* **Paleta Institucional INACAP:** Rojo primario `#E30613`, Negro/Carbón `#1A1A1A`, Blanco `#FFFFFF`. *(Mantener reservado `<!-- ESPACIO LOGO INSTITUCIONAL AQUI -->` en `templates/base.html` hasta integrar el logo oficial).*

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
- v4 — Perfiles Estilo Instagram (Propio y Público) + Métricas de Asistencia [PENDIENTE]:
  - Alcance: Rutas /perfil/ y /perfil/<id>/ con foto circular, bio editable, insignia de rol, carrera, año, sede, privacidad estricta de tel_usu (solo visible para Líderes, Delegados, Jefatura y DAE), historial público de eventos asistidos/organizados y tarjeta resumen en vivo del próximo evento para Líderes/DAE.
- v5 — Inbox del Sistema (Chat Oficial + Confirmación de 4 Avales + Buzón Iniciativas) [PENDIENTE]:
  - Alcance: Ruta /inbox/ con badge de no leídos, mensajes oficiales del Sistema con botones Aceptar / Rechazar Aval (al llegar a 4 avales aceptados, el Club escala automáticamente a PENDIENTE_DAE y notifica a la DAE) y pestaña Buzón de Iniciativas visible solo para Líderes y DAE.
- v6 — Postulación a Club, Reserva de Espacios (Sin Solapamientos) y Panel/Auditoría DAE [VERSIÓN FINAL - PENDIENTE]:
  - Alcance: Formularios integrados en Mi Perfil según rol: (1) Postulación a Club seleccionando 4 compañeros de sede; (2) Solicitud de Reserva de Espacio/Evento; (3) Panel DAE/Admin para aprobar clubes (ascendiendo al creador a LIDER_ESTUDIANTIL + aviso Inbox), aprobar eventos validando no solapamiento de espacio/fecha/sede, editar roles de usuarios y visualizar la tabla de RegistroAuditoria.
