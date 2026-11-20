# Contexto del Proyecto - Hackatón INACAP - Huawei

## 1. Equipo y Problemática
* **Equipo:** LuxNova (Blanca Lagos [Líder], Álvaro Contardo, Integrante 3, Integrante 4).
* **Problemática:** Desconexión entre la Dirección de Asuntos Estudiantiles (DAE), Jefaturas de Carrera y los Estudiantes respecto a la participación estudiantil, difusión de eventos y gestión de iniciativas en cada sede de INACAP.
* **Solución (Plataforma Web):** Portal centralizado por Sede con eventos (locales e intersede), muro en tiempo real ("Ahora mismo" e "Iniciativas"), flujo de postulación para crear Clubes Estudiantiles con aval de pares, reserva de espacios con aprobación DAE y buzón/inbox interno del sistema.

---

## 2. Cómo será evaluado (Rúbrica INACAP - Huawei - 100 Ptos.)
* **Relevancia del desafío (25 Ptos.):** Entender bien qué falla hoy, a quién afecta y en qué momento del flujo interviene la solución. Sustentar con contexto y enfocarse en una parte concreta del problema.
* **Solidez técnica (30 Ptos.):** Demostrar el flujo principal completo (entrada -> procesamiento -> resultado útil) diferenciando lo real de lo simulado. Justificar arquitectura nube (Huawei Cloud RDS PostgreSQL) y abordar riesgos/validaciones de datos.
* **Impacto y viabilidad (25 Ptos.):** Mostrar valor concreto para la institución (mayor participación, trazabilidad de aprobaciones DAE, ahorro de tiempo) con indicadores claros y alcance de piloto.
* **Pitch y equipo (20 Ptos.):** Historia clara, demostración en vivo fluida del recorrido completo (Estudiante -> Postulación/Avales -> Aprobación DAE -> Creación de Evento) y dominio técnico.

---

## 3. Reglas de Arquitectura y Código (Obligatorias)
* **Stack:** Python + Django (MVT), Base de datos **PostgreSQL** (`hackaton_luxnova`), Frontend con **HTML5 + Bootstrap (CDN) + CSS3 + JavaScript Vanilla (puro)**.
* **Prohibido:** No usar TypeScript, React, Vue, C ni Django Channels/WebSockets (el efecto tiempo real se resuelve con JS `fetch` / AJAX ligero).
* **Estilo Visual y Movilidad:** Estética moderna tipo app (perfiles estilo Instagram con foto, bio y etiqueta de rol; tarjetas dinámicas con animaciones suaves en JS `IntersectionObserver` deslizando `div` desde los costados hacia el centro al hacer scroll).
* **Base de Datos Relacional:** Todos los modelos en `models.py` deben seguir estrictamente un diseño relacional normalizado con llaves foráneas limpias (`ForeignKey`) y segmentación por `Sede`.
* **Nomenclatura Obligatoria de Campos en Base de Datos (`models.py`):**
  * Todos los atributos/columnas de los modelos deben nombrarse en español siguiendo estrictamente el formato `[3-4 primeras letras del campo]_[3-4 primeras letras de la tabla]` en minúsculas (ej. `nom_usu` = nombre en tabla Usuario, `dir_sede` = dirección en tabla Sede, `tit_even` = título en tabla Evento, `est_club` = estado en tabla Club).
  * Las llaves foráneas (`ForeignKey`) deben seguir la misma lógica indicando la relación (ej. `sede_usu`, `lid_club`, `crea_even`, `aut_publ`).
* **Comentarios Obligatorios:** **Antes de CADA clase y CADA función** (en Python y en JavaScript), se debe escribir un comentario claro explicando **qué es lo que realmente hace**, qué recibe y qué devuelve.

---

## 4. Estructura de Navegación (Navbar) y Roles
* **Navbar Principal (4 secciones):**
  1. `Inicio / Eventos`: Próximos eventos filtrados automáticamente por la **Sede del usuario** + pestaña/sección de **Eventos Intersede** (abiertos a todos). Permite pre-inscripción con 1 clic.
  2. `Ahora Mismo (Foro)`: Muro cronológico inverso (lo más reciente arriba) exclusivo de la **Sede del usuario**. Permite subir foto + texto con etiqueta `#AhoraMismo`, `#Noticia` o `#Iniciativa`, y comentar.
  3. `Inbox / Buzón`: Chat/bandeja oficial del **Sistema** (notificaciones automáticas, solicitudes de aval para clubes, respuestas de la DAE) y **Buzón de Iniciativas** (visible solo para Líderes Estudiantiles y DAE de la sede, mostrando el teléfono/correo del estudiante proponente).
  4. `Mi Perfil`: Vista estilo Instagram (foto, biografía, etiqueta de rol, carrera, año, sede e historial público de eventos asistidos/organizados). Incluye botones dinámicos según rol:
     * *Estudiante:* Botón "Postular a Crear Club / Líder Estudiantil".
     * *Líder Estudiantil / Delegado / Jefatura:* Botón "Solicitar Reserva de Espacio / Crear Evento" + resumen en vivo del próximo evento y total de pre-inscritos.
     * *DAE / Admin:* Acceso al "Panel de Aprobaciones y Auditoría" (aprobar clubes, reservar espacios/eventos, gestionar roles de usuarios).

---

## 5. Flujos Críticos de Negocio
1. **Iniciativas en Foro:** Si un estudiante publica con etiqueta `#Iniciativa`, además de mostrarse en el muro de su sede, se envía automáticamente al Inbox de los Líderes Estudiantiles y la DAE de esa sede con los datos de contacto del estudiante.
2. **Creación de Club y Rol Líder:** Un estudiante completa el formulario (Nombre del club, categoría, descripción y selección de 4 estudiantes de su sede). El sistema envía una notificación al Inbox de esos 4 compañeros. **Solo cuando los 4 confirman/aceptan el aval**, la solicitud pasa a la bandeja de la DAE. Cuando la DAE aprueba, el usuario pasa a rol `LIDER_ESTUDIANTIL`, recibe notificación del Sistema en su Inbox y se desbloquea "Crear Evento" en su perfil.
3. **Reserva de Espacios y Eventos:** Líderes, Delegados o Jefatura envían solicitud de evento (título, descripción, banner horizontal, categoría público/carrera, alcance Sede o Intersede y espacio solicitado). La DAE aprueba y el evento se publica automáticamente en `Inicio / Eventos`, quedando registrado en la tabla de **Auditoría**.

---

## 6. Dependencias y Librerías
* `Python 3.x`
* `Django`
* `psycopg2-binary` (Conector PostgreSQL)
* `Pillow` (Para manejo de imágenes: fotos de perfil, banners de eventos y fotos del foro)

## Bitácora de versiones
La memoria técnica acumulativa se encuentra en [CONTEXTO_VERSIONES.md](CONTEXTO_VERSIONES.md). Consultarla antes de continuar nuevas iteraciones.
