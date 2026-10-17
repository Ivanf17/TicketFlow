# Documentación técnica — TicketFlow

Documento de referencia técnica del sistema tal como quedó
implementado al cierre del proyecto (Bloque 11). Complementa a
`CLAUDE.md` (reglas y restricciones) con el detalle de arquitectura,
modelo de datos, permisos, flujos y decisiones.

## 4.1 Arquitectura

### Por qué monolito modular y no microservicios ni SPA + API

TicketFlow es un único proyecto Django dividido en seis apps
(`users`, `administration`, `tickets`, `assignment`, `notifications`,
`reports`), cada una con responsabilidad propia, pero desplegado y
ejecutado como una sola aplicación, con una sola base de datos.

- **Escala real del problema:** el sistema resuelve la gestión de
  tickets de una organización, no un producto de alto tráfico ni
  multi-tenant. No hay ningún requisito (actual ni previsible dentro
  del proyecto) que justifique escalar componentes de forma
  independiente.
- **Complejidad operativa:** microservicios exigen orquestación,
  comunicación entre servicios (colas, HTTP interno), y normalmente
  bases de datos separadas con los problemas de consistencia que eso
  trae. Ninguno de esos costos se justifica para el alcance del
  proyecto, y el tiempo de desarrollo es la restricción más dura
  (13 semanas).
- **Equipo y plazo:** un monolito modular permite trabajar por bloques
  (como efectivamente se hizo, 11 bloques) sin la sobrecarga de
  coordinar despliegues y contratos de API entre servicios.
- La separación en apps ya da la modularidad que hace falta:
  cada una puede evolucionar con sus propios modelos, vistas y tests,
  sin necesitar el aislamiento (y el costo) de un proceso separado.

### Responsabilidad de cada app

| App | Responsabilidad |
|---|---|
| `users` | Modelo de usuario (`User`, `AUTH_USER_MODEL`), roles, login/logout, recuperación de contraseña. |
| `administration` | Áreas, Categorías, administración de usuarios. Único punto de gestión organizacional. |
| `tickets` | Modelo `Ticket`, máquina de estados, historial de estados, comentarios. Dueño de "qué es un ticket y en qué estado está". |
| `assignment` | Quién es responsable de cada ticket: Round Robin automático, reasignación manual, historial de asignación. |
| `notifications` | Bandeja de entrada interna por usuario. No decide *cuándo* notificar (eso lo deciden `tickets`/`assignment`), solo *cómo* almacenar y mostrar. |
| `reports` | Lectura agregada de datos de `tickets` para el dashboard. No escribe nada; es puramente de consulta. |

### Cómo se comunican entre sí

No hay HTTP interno ni colas: todo es importación directa de Python
entre apps, dentro del mismo proceso.

- `tickets.services.change_ticket_status` importa
  `notifications.services.notify_ticket_status_changed` para notificar
  al crear el cambio, dentro de la misma transacción.
- `assignment.services.assign_ticket` importa
  `notifications.services.notify_ticket_assigned` /
  `notify_ticket_reassigned`, también en la misma transacción.
- `tickets.views.ticket_comment_create` importa
  `notifications.services.notify_ticket_comment_added`.
- `assignment` depende de `tickets.models.Ticket` (FK) y de
  `users.models.User` (para encontrar Area Managers elegibles).
- `reports` depende de `tickets.permissions.get_visible_tickets` (la
  reutiliza tal cual para admin/area_manager) y de `tickets.models`.
- `administration` depende de `users.models.User` (para administrar
  cuentas) y es la única app "de configuración" de la que dependen
  `tickets`/`users` (a través de `Area`/`Category`, referenciadas por
  string: `"administration.Area"`, `"administration.Category"`, para
  evitar imports circulares).

Ninguna app importa `django.contrib.admin` más allá del registro
estándar en su propio `admin.py`; el Django Admin (`/admin/`) es un
canal aparte, no parte de la arquitectura de la aplicación en sí (ver
`docs/limitaciones-conocidas.md`, sección 5.2).

### Separación de responsabilidades (vistas, servicios, permisos, formularios)

Patrón consistente en todas las apps con lógica de negocio:

- **`models.py`** — estructura de datos y las invariantes que Django
  puede expresar en el modelo mismo (`clean()`, `Meta.constraints`,
  `on_delete`).
- **`services.py`** — la única fuente de verdad para cualquier regla de
  negocio no trivial (`tickets.services.change_ticket_status`,
  `assignment.services.assign_ticket`/`pick_next_area_manager`,
  `notifications.services.create_notification` y sus wrappers por
  evento, `administration.services.is_last_active_admin`). Las vistas
  llaman a estas funciones; nunca reimplementan la regla.
- **`permissions.py`** — funciones puras que responden "¿puede este
  usuario hacer X?" o devuelven el queryset ya filtrado
  (`get_visible_tickets`, `can_manage_ticket_status`,
  `can_manage_ticket_assignment`, `can_access_administration`,
  `can_access_dashboard`, `get_dashboard_tickets_queryset`). Se
  reutilizan entre vistas en vez de duplicarse (por ejemplo,
  `ticket_comment_create` reutiliza literalmente
  `get_visible_tickets`, la misma función que usa `ticket_detail`).
- **`forms.py`** — validación de entrada y, cuando corresponde, la
  misma regla de negocio aplicada también del lado del formulario (por
  ejemplo `UserAdminForm.clean()` reutiliza
  `is_last_active_admin` en vez de reimplementar el conteo).
- **`views.py`** — orquesta: llama a `permissions`, arma el `form`,
  invoca `services`, renderiza. No contiene reglas de negocio propias.

### Capa de presentación (interfaz)

La interfaz sigue el sistema visual exportado desde Google Stitch
(`docs/diseno-referencia.md`: azul marino/índigo, turquesa,
ámbar, tipografía Inter, tarjetas de 12 px de radio) implementado
**sobre Bootstrap 5.3.3**, sin Tailwind ni pasos de compilación:

- **`static/css/ticketflow.css`** — tokens de diseño en variables CSS
  (`--tf-*`) que además sobrescriben las variables de Bootstrap
  (`--bs-*`), y un conjunto pequeño de componentes `tf-*`: layout con
  menú lateral (260 px; rail de iconos de 72 px entre 992 y 1279 px;
  panel deslizable `offcanvas-lg` por debajo de 992 px), barra superior,
  tarjetas de métricas, badges de estado, tablas que en móvil se apilan
  como tarjetas, filtros segmentados, línea de tiempo, stepper del flujo
  lineal, barras y donut del dashboard, páginas de autenticación y de
  error.
- **`static/js/ticketflow.js`** — solo mejoras progresivas: mostrar/ocultar
  contraseña, confirmación antes de eliminar, vista previa del área de
  destino al elegir categoría y atajo de teclado del buscador. Ninguna
  regla de negocio vive en JavaScript.
- **`templates/base.html` + `templates/partials/`** — una única plantilla
  base: con sesión iniciada renderiza el portal (menú lateral por rol,
  barra superior con buscador, desplegable de notificaciones y menú de
  cuenta); sin sesión, el layout centrado de autenticación. Parciales
  reutilizables: `sidebar`, `topbar`, `messages`, `pagination` (conserva
  los filtros activos), `status_badge`, `form_field`, `form_errors`,
  `admin_tabs`, `admin_header`, `notification_icon`. Páginas de error
  `403.html`, `404.html` y `500.html` (esta última autónoma).
- **`ticketflow/templatetags/ui.py`** (biblioteca `ui`, registrada en
  `TEMPLATES["OPTIONS"]["libraries"]`) — filtros de presentación:
  `ui_field` (clases de Bootstrap e `is-invalid` según el widget y los
  errores del servidor), `role_label`/`es_label` (etiquetas en español a
  partir de `users/presentation.py`, sin tocar los `choices` del modelo,
  para no generar migraciones), `initials`, `display_name`, `age` y la
  etiqueta `query_replace` para la paginación con filtros.
- **Iconos y tipografía:** Inter y un subconjunto de Material Symbols
  Outlined desde Google Fonts (la lista `icon_names` de `base.html` debe
  ampliarse si una plantilla usa un icono nuevo).

Los cambios de vistas asociados al rediseño son solo de lectura y
siempre parten del queryset ya filtrado por rol: filtros opcionales
(`status`, `assignment`, `q`) y conteos por estado en `ticket_list`;
pasos del flujo lineal calculados desde `TicketHistory` en
`ticket_detail`; conteos del panel en `administration_home`; pestañas
por tipo/no leídas en `notification_list`; y un parámetro `next`
validado con `url_has_allowed_host_and_scheme` en las acciones de
marcar notificaciones como leídas (no hay redirección abierta). Los
valores desconocidos de cualquier filtro se ignoran.

## 4.2 Modelo de datos

### Entidades y atributos principales

- **`users.User`** (extiende `AbstractUser`): `username`, `email`
  (opcional, no único — ver `docs/limitaciones-conocidas.md` 5.2),
  `password` (hash), `role` (`employee` / `area_manager` / `admin` /
  `management`), `area` (FK a `Area`, nullable), más los campos nativos
  de Django (`is_staff`, `is_superuser`, `is_active`, etc.).
- **`administration.Area`**: `name` (único), `description`,
  `is_active`.
- **`administration.Category`**: `name`, `area` (FK, obligatoria),
  `is_active`.
- **`tickets.Ticket`**: `ticket_number` (único, autogenerado
  `TK-000001`), `title`, `description`, `category` (FK), `created_by`
  (FK a User), `assigned_to` (FK a User, nullable), `status`
  (`PENDING`/`IN_PROCESS`/`RESOLVED`), `created_at`, `updated_at`.
  `area` **no es una columna**: es una `@property` que devuelve
  `self.category.area` (ver limitación 5.1).
- **`tickets.TicketHistory`**: log append-only de cambios de estado.
  `ticket` (FK), `previous_status` (nullable, `None` en la entrada
  inicial), `status`, `changed_by` (FK a User), `created_at`.
- **`tickets.TicketComment`**: `ticket` (FK), `author` (FK a User),
  `content`, `created_at`. Append-only (sin campos de edición ni
  soft-delete).
- **`assignment.AreaAssignmentCursor`**: `area` (OneToOne),
  `last_assigned_to` (FK a User, nullable) — el estado persistente del
  Round Robin, uno por área.
- **`assignment.TicketAssignmentHistory`**: log append-only de
  asignaciones. `ticket` (FK), `previous_assigned_to` (FK, nullable),
  `new_assigned_to` (FK, nullable), `changed_by` (FK, nullable — `None`
  identifica una asignación automática), `created_at`.
- **`notifications.Notification`**: `recipient` (FK a User), `ticket`
  (FK), `notification_type` (`TICKET_ASSIGNED` / `TICKET_REASSIGNED` /
  `TICKET_STATUS_CHANGED` / `TICKET_COMMENT_ADDED`), `title`,
  `message`, `is_read`, `created_at`, `read_at`.

### Diagrama entidad-relación

```mermaid
erDiagram
    AREA ||--o{ CATEGORY : "contiene"
    AREA ||--o{ USER : "empleados/managers de"
    AREA ||--o| AREA_ASSIGNMENT_CURSOR : "cursor Round Robin"
    CATEGORY ||--o{ TICKET : "clasifica"
    USER ||--o{ TICKET : "crea (created_by)"
    USER ||--o{ TICKET : "atiende (assigned_to, nullable)"
    TICKET ||--o{ TICKET_HISTORY : "historial de estado"
    USER ||--o{ TICKET_HISTORY : "changed_by"
    TICKET ||--o{ TICKET_COMMENT : "comentarios"
    USER ||--o{ TICKET_COMMENT : "author"
    TICKET ||--o{ TICKET_ASSIGNMENT_HISTORY : "historial de asignación"
    USER ||--o{ TICKET_ASSIGNMENT_HISTORY : "previous/new/changed_by"
    TICKET ||--o{ NOTIFICATION : "genera"
    USER ||--o{ NOTIFICATION : "recibe"

    AREA {
        string name UK
        text description
        bool is_active
    }
    CATEGORY {
        string name
        int area_id FK
        bool is_active
    }
    USER {
        string username UK
        string email "opcional, no unico"
        string role
        int area_id FK "nullable"
    }
    TICKET {
        string ticket_number UK
        string title
        text description
        int category_id FK
        int created_by_id FK
        int assigned_to_id FK "nullable"
        string status
    }
    TICKET_HISTORY {
        int ticket_id FK
        string previous_status "nullable"
        string status
        int changed_by_id FK
    }
    TICKET_COMMENT {
        int ticket_id FK
        int author_id FK
        text content
    }
    AREA_ASSIGNMENT_CURSOR {
        int area_id FK UK
        int last_assigned_to_id FK "nullable"
    }
    TICKET_ASSIGNMENT_HISTORY {
        int ticket_id FK
        int previous_assigned_to_id FK "nullable"
        int new_assigned_to_id FK "nullable"
        int changed_by_id FK "nullable = automatico"
    }
    NOTIFICATION {
        int recipient_id FK
        int ticket_id FK
        string notification_type
        bool is_read
    }
```

### Claves foráneas y reglas `on_delete`

La regla general: **`PROTECT`** en toda referencia que sea parte de un
registro histórico o de negocio que no debe poder desaparecer
silenciosamente; **`SET_NULL`** donde perder la referencia es un estado
válido del negocio ("sin asignar", "sin área"); **`CASCADE`** solo
donde el registro dependiente no tiene ningún valor sin su padre.

| Relación | `on_delete` | Por qué |
|---|---|---|
| `Category.area` → `Area` | `PROTECT` | Una categoría nunca queda "sin área"; hay que reasignarla o borrarla explícitamente primero. |
| `Ticket.category` → `Category` | `PROTECT` | Un ticket nunca pierde su clasificación; borrar la categoría rompería el reporting histórico. |
| `Ticket.created_by` → `User` | `PROTECT` | El creador de un ticket es un dato histórico: no se puede perder quién lo reportó. |
| `Ticket.assigned_to` → `User` | `SET_NULL` | "Sin asignar" es un estado válido (por ejemplo, si el responsable se da de baja); el ticket sigue existiendo. |
| `TicketHistory.ticket` → `Ticket` | `CASCADE` | El historial no tiene sentido sin el ticket al que pertenece. |
| `TicketHistory.changed_by` → `User` | `PROTECT` | Quién hizo cada cambio de estado es un dato de auditoría que no se pierde. |
| `TicketComment.ticket` → `Ticket` | `CASCADE` | Igual que el historial de estado. |
| `TicketComment.author` → `User` | `PROTECT` | El autor de un comentario es un dato de auditoría. |
| `AreaAssignmentCursor.area` → `Area` | `CASCADE` | El cursor no tiene sentido sin el área. |
| `TicketAssignmentHistory.ticket` → `Ticket` | `CASCADE` | Igual que el historial de estado. |
| `TicketAssignmentHistory.previous/new_assigned_to` → `User` | `SET_NULL` | El historial se conserva aunque el usuario referenciado se borre; solo se pierde la referencia puntual. |
| `TicketAssignmentHistory.changed_by` → `User` | `SET_NULL` | Idéntico razonamiento; además ya es `nullable` por diseño (`None` = Round Robin). |
| `Notification.recipient` → `User` | `CASCADE` | Una bandeja de entrada personal no tiene valor independiente del usuario. |
| `Notification.ticket` → `Ticket` | `CASCADE` | Una notificación sobre un ticket que ya no existe no tiene sentido. |
| `User.area` → `Area` | `SET_NULL` | Ver limitación 5.1: desactivar/borrar un área no debe romper usuarios existentes. |

Consecuencia práctica visible en la interfaz: `administration` captura
`ProtectedError` en los `_delete` de Área/Categoría/Usuario y lo
convierte en un mensaje ("no se puede eliminar porque tiene ... "), en
vez de un error 500.

### Restricciones a nivel de base de datos

Además de `clean()`/`full_clean()` en Python (que **no** corre en un
`.save()` directo, en `.objects.create()`, ni en `createsuperuser`),
hay una restricción real en PostgreSQL:

```python
# users/models.py — User.Meta.constraints
CheckConstraint(
    check=~(
        Q(role__in=["employee", "area_manager"]) & Q(area__isnull=True)
    ),
    name="user_area_required_for_employee_and_area_manager",
)
```

Garantiza, a nivel de motor de base de datos, que ninguna fila de
`users_user` pueda existir con `role` en (`employee`, `area_manager`) y
`area_id` nulo — sin importar por qué camino se haya intentado escribir
esa fila (ORM, `shell`, una migración de datos futura, etc.). Es la
única forma de que esta regla sea imposible de saltarse, en vez de
"difícil de saltarse si se usa el formulario correcto".

Otras restricciones de base de datos: `Area.name` único,
`Ticket.ticket_number` único, `AreaAssignmentCursor.area` único (un
cursor por área, forzado por ser `OneToOneField`).

## 4.3 Roles y permisos

### Matriz de permisos real (implementada)

| Acción | Employee | Area Manager | Admin | Management |
|---|---|---|---|---|
| Crear ticket | **Sí** (propio) | No | No | No |
| Ver lista de tickets | Solo propios | Solo de su área | Todos | Ninguno (lista vacía) |
| Ver detalle de un ticket | Solo propios (404 si no) | Solo de su área (404 si no) | Cualquiera | Ninguno (404 siempre) |
| Comentar un ticket | En los que puede ver | En los que puede ver | En cualquiera | No (no puede ver ninguno) |
| Asignar/reasignar | No | Solo su área | Cualquiera | No |
| Cambiar estado | No | Solo su área | Cualquiera | No |
| Ver notificaciones propias | Sí | Sí | Sí | Sí (su propia bandeja, aunque en la práctica no recibe eventos de tickets) |
| Ver dashboard | **No** | Sí, acotado a su área (sin selector) | Sí, global (con selector de área) | Sí, global (con selector de área) |
| Ver "tickets recientes" del dashboard | — | Sí (de su área) | Sí (global/filtrado) | **No** (widget deliberadamente ausente) |
| Administrar Áreas/Categorías/Usuarios | No | No | **Sí** | No |
| Entrar a `/admin/` (Django Admin) | Depende de `is_staff`, no de `role` — ver 4.3 y limitación 5.2 | | | |

### Cómo se protege cada operación en servidor

Ninguna restricción de esta matriz depende de que el template oculte
un botón: cada vista vuelve a verificar del lado del servidor.

- **Visibilidad de tickets:** `tickets.permissions.get_visible_tickets(user)`
  devuelve el queryset ya filtrado por rol; toda vista que necesita "un
  ticket que este usuario puede ver" hace
  `get_object_or_404(get_visible_tickets(request.user), pk=pk)`. Si el
  ticket no está en ese queryset, la respuesta es **404**, no 403 — así
  no se filtra ni siquiera si el ticket existe.
- **Creación de tickets:** `tickets.views.ticket_create` compara
  `request.user.role != Role.EMPLOYEE` y lanza `PermissionDenied` (403)
  explícitamente.
- **Asignación/cambio de estado:** `can_manage_ticket_assignment` /
  `can_manage_ticket_status` se evalúan *después* de confirmar que el
  usuario puede ver el ticket (si no puede verlo, ya es 404 antes de
  llegar a este chequeo); si puede verlo pero no gestionarlo, es 403.
- **Notificaciones:** cada consulta incluye
  `recipient=request.user` directamente en el `filter`/`get_object_or_404`
  — un usuario ni siquiera puede confirmar que una notificación ajena
  existe (404, no 403).
- **Dashboard:** `can_access_dashboard(user)` (allowlist de roles) más
  `get_dashboard_tickets_queryset(user)`, que reutiliza
  `get_visible_tickets` para admin/area_manager y da acceso global solo
  a management.
- **Administración:** `administration.views._require_admin(request)` es
  un guard compartido por **todas** las vistas del módulo
  (`can_access_administration`, allowlist de un solo rol: `admin`).
- **Último Admin activo:** `administration.services.is_last_active_admin`
  se evalúa en `UserAdminForm.clean()` (edición, incluida
  auto-edición) y en `user_delete` (eliminación) — ver
  `docs/limitaciones-conocidas.md` y el detalle del Bloque 10 en el
  historial de commits.

### El dashboard restringido por rol, explicado

El dashboard (`reports.views.dashboard`) construye **un único
queryset base** por request
(`get_dashboard_tickets_queryset(request.user)`) y deriva de él
absolutamente todo lo demás (conteos, agrupación por área, promedio de
resolución, tickets recientes). Esto es deliberado: evita que una
métrica quede calculada sobre un conjunto de tickets distinto al de
otra en la misma página.

La diferencia entre roles no está en la plantilla sino en qué devuelve
ese queryset base:

- `area_manager` / `admin` → exactamente lo mismo que verían en la
  lista de tickets (`get_visible_tickets`).
- `management` → **todos** los tickets del sistema (única excepción:
  Management no tiene acceso a tickets individuales en ningún otro
  lugar, pero sí necesita ver el total real de la organización para
  que las métricas agregadas sean correctas).

Sobre esa base, el widget "tickets recientes" se **omite por completo**
para `management` (`show_recent_tickets = request.user.role !=
Role.MANAGEMENT`, y el queryset ni siquiera se construye —
`Ticket.objects.none()`, no una consulta real que luego se oculta).
Esto es intencional: mostrarle a Gerencia una tabla con título,
descripción y responsable de cada ticket sería exactamente el
contenido individual que el proyecto decidió que Management no debe
ver, aunque las métricas agregadas sí sean visibles para ese rol.

## 4.4 Flujos principales

### Creación y categorización de un ticket

1. Un `employee` completa el formulario (`TicketCreateForm`): título,
   descripción, categoría. El campo `category` solo ofrece categorías
   con `is_active=True` (y lo valida también si se manipula el POST
   directamente, no solo en el `<select>`).
2. `Ticket.objects.create_ticket(...)` (manager method) crea el ticket
   con `status=PENDING` y, en la misma transacción, la primera entrada
   de `TicketHistory` (sin `previous_status`, marcando "así nació el
   ticket").
3. El área del ticket **no se guarda**: siempre se deriva de
   `ticket.category.area` (ver limitación 5.1).
4. Inmediatamente después, la vista llama a
   `assignment.services.auto_assign_ticket(ticket)` (paso siguiente).

### Asignación automática (Round Robin) y manual

- **Automática:** `pick_next_area_manager(area)` calcula el siguiente
  Area Manager activo del área usando un cursor persistente
  (`AreaAssignmentCursor.last_assigned_to`), no un conteo de tickets
  (así una reasignación manual no distorsiona el reparto). Bajo
  `select_for_update()` dentro de una transacción, para que dos
  creaciones simultáneas no elijan al mismo manager dos veces. Si el
  área no tiene ningún Area Manager activo, el ticket queda sin asignar
  (`assigned_to=None`) sin error.
- **Manual:** `assign_ticket(ticket, assigned_to, changed_by)` valida
  que el nuevo responsable pertenezca al área del ticket (mismo chequeo
  que ya hace `Ticket.clean()`), es un no-op si se "reasigna" a quien
  ya lo tenía, y **nunca toca el cursor de Round Robin** — una
  reasignación manual no puede hacer que la asignación automática
  pierda el hilo de a quién le toca después.
- Ambos caminos registran una entrada en `TicketAssignmentHistory` y
  notifican al nuevo responsable (`TICKET_ASSIGNED` si no tenía
  responsable previo, `TICKET_REASSIGNED` si reemplaza a otro), dentro
  de la misma transacción que el resto del cambio.

### Transiciones de estado e historial

`tickets.services.ALLOWED_TRANSITIONS` es la única fuente de verdad:
`PENDING → IN_PROCESS → RESOLVED`, un paso a la vez.
`change_ticket_status` relee el estado actual con
`select_for_update()` dentro de una transacción (protegido contra
carreras), rechaza cualquier transición que no sea exactamente la
siguiente permitida (`StatusTransitionError`), y si es válida escribe
el nuevo estado, una entrada de `TicketHistory` y la notificación al
creador del ticket, todo atómicamente. `RESOLVED` no tiene ninguna
transición de salida definida: es terminal por construcción, no por un
chequeo adicional.

### Generación de notificaciones

Punto único de entrada: `notifications.services.create_notification`.
Cada evento de negocio tiene su propia función wrapper
(`notify_ticket_assigned`, `notify_ticket_reassigned`,
`notify_ticket_status_changed`, `notify_ticket_comment_added`), que
decide el destinatario y el mensaje, y se invoca siempre dentro de la
transacción del evento que la origina (si la transacción se revierte,
la notificación tampoco se crea). Reglas de destinatario:

- Asignación/reasignación → el nuevo responsable.
- Cambio de estado → el creador del ticket.
- Comentario → el "otro lado": si comenta el creador, se notifica al
  responsable asignado (si existe); si comenta cualquier otro (area
  manager o admin), se notifica al creador. Nunca se autonotifica, y no
  se crea nada si no hay un destinatario válido.

### Cálculo de métricas del dashboard

Todo se deriva del mismo queryset base filtrado por rol y por los
filtros de fecha/área de la request:

- **Conteos por estado:** una sola consulta agrupada
  (`.values_list("status").annotate(Count("id"))`).
- **Conteo por área:** una sola consulta agrupada por
  `category__area` (el área no es una columna propia del ticket, así
  que se agrupa a través de la relación).
- **Tiempo promedio de resolución:** subquery correlacionada contra
  `TicketHistory` que busca la entrada `IN_PROCESS → RESOLVED` de cada
  ticket (no se usa `Ticket.updated_at`, que puede reflejar cualquier
  guardado posterior, no solo la resolución), y promedia la diferencia
  contra `created_at`.
- **Tickets recientes:** los últimos 10 del queryset base, con
  `select_related` para no generar una consulta extra por fila (ver
  Bloque 10), omitido por completo para `management`.

## 4.5 Decisiones técnicas relevantes

| Decisión | Alternativas consideradas | Por qué se descartaron | Por qué se eligió esta |
|---|---|---|---|
| **Monolito modular sobre microservicios** | Servicios separados por dominio (tickets, notificaciones, reportes) con su propia base de datos. | Complejidad de orquestación, comunicación entre servicios y consistencia distribuida injustificada para el volumen real del problema; el plazo de 13 semanas es la restricción dominante del proyecto. | Un único despliegue, una única base de datos, apps como unidad de modularidad — igual separación de responsabilidades, sin el costo operativo. |
| **Django Templates sobre React/SPA** | Frontend desacoplado (React/Vue) consumiendo una API REST. | Duplica el trabajo de autenticación/permisos (una vez en el backend, otra en el cliente), exige una capa de API completa, y no hay ningún requisito de interactividad que lo justifique. | Django Templates + Bootstrap + JS mínimo cubre toda la interacción necesaria (formularios, listas, un dashboard con 2 gráficos) sin esa duplicación. |
| **Jerarquía Área → Categoría** en vez de una sola entidad | Una única tabla "Categoría" con un campo de texto libre para el área, o sin categorías (ticket directo a un área). | Un campo de texto libre no permite validar ni reportar de forma confiable; sin categorías, se pierde la clasificación fina que sí pide el alcance (reportar *qué tipo* de incidencia es). | `Category.area` como FK obligatoria da una jerarquía consistente y consultable, y el ticket deriva su área de forma automática y sin duplicación. |
| **`CheckConstraint` en base de datos, además de `clean()` en Python** | Confiar solo en `clean()`/`full_clean()` (validación a nivel de formulario/modelo). | `clean()` no corre en `.save()` directo, `.objects.create()`, ni en `createsuperuser` — cualquier código (o consola de administración) que no pase por `full_clean()` podría crear una fila inconsistente. | El `CheckConstraint` lo hace imposible a nivel de motor de base de datos, sin importar el camino de escritura. Mismo razonamiento aplicado luego a por qué el último-Admin-activo **no** usa un constraint (ver más abajo): ahí la regla depende del conteo de *otras* filas, que un `CheckConstraint` no puede ver. |
| **Round Robin como regla de asignación** | Asignación manual siempre; o por carga actual (menor cantidad de tickets abiertos). | Manual siempre no escala con el volumen esperado y depende de que alguien esté disponible para asignar. Por carga actual es más "justo" en teoría, pero requiere recalcular sobre todo el historial en cada asignación y es más difícil de razonar/testear que un cursor. | Un cursor persistente por área da una distribución predecible, testeable de forma determinística, y no se ve afectado por reasignaciones manuales posteriores. |
| **No construir una API (Bloque 9)** | Exponer una API REST (Django REST Framework) para desacoplar un futuro cliente móvil o integración externa. | Ningún requisito del proyecto pide un consumidor externo; agregarla habría sido la definición misma de scope creep contra la prioridad de Tiempo, y contra la regla explícita del proyecto de no introducir infraestructura no justificada. | Se evaluó explícitamente en el precheck del Bloque 9 y se descartó: cero señales de necesidad real. |
| **Protección del último Admin en servicio/formulario, no en `CheckConstraint`** | Una restricción de base de datos que impida dejar la tabla `users_user` sin ningún `role=admin, is_active=True`. | Un `CheckConstraint` de PostgreSQL solo evalúa la fila que se está escribiendo; no puede expresar "y ninguna otra fila de esta tabla cumple tal condición". No es la herramienta adecuada para una regla que depende del estado agregado de la tabla. | `administration.services.is_last_active_admin` centraliza el conteo una sola vez, y se invoca tanto desde `UserAdminForm.clean()` (edición) como desde la vista `user_delete` (que no tiene formulario) — la regla vive en un solo lugar, aplicada en los dos puntos donde puede violarse. |
| **Gráficos del dashboard renderizados en el servidor (CSS) en vez de Chart.js** | Mantener Chart.js vía CDN (implementación original del Bloque 7). | Una librería JS adicional para dos gráficos simples; los valores solo existían dentro de un `<canvas>`, sin texto accesible. | Barras horizontales y un donut (`conic-gradient`) calculados en la plantilla con los mismos datos de la vista: sin dependencia extra, legibles por lectores de pantalla y fieles al diseño de Stitch. |
