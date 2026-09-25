# Casos de uso y criterios de aceptación — TicketFlow

Este documento distingue explícitamente dos cosas: el **alcance formal
aprobado** (Enunciado del Alcance, 25/08/2026) y las
**funcionalidades adicionales** que el equipo implementó por encima de
ese alcance. Ningún criterio se marca como cumplido sin evidencia
directa en el código y los tests.

## 1. Alcance formal aprobado

### 1.1 Requisitos formales

| Requisito | Importancia | Estado | Evidencia |
|---|---|---|---|
| Creación de tickets por parte de los empleados, con descripción y categoría (TI, Mantenimiento, RRHH) | Alta | **Cumplido** | `tickets.views.ticket_create` (restringido a `role=employee`), `TicketCreateForm` (título, descripción, categoría). Las tres áreas y sus categorías (Hardware/Software/Redes en TI; Eléctrico/Plomería en Mantenimiento; Vacaciones/Licencias en RRHH) se administran desde `administration` y se cargan como ejemplo en `seed_demo`. Tests: `TicketPermissionTests.test_employee_can_create_ticket`. |
| Asignación automática (por reglas) o manual de tickets al área correspondiente | Alta | **Cumplido** | Automática: `assignment.services.pick_next_area_manager` (Round Robin por área). Manual: `assignment.services.assign_ticket`, acotada a la misma área del ticket. Tests: `RoundRobinTests` (todas), `ReassignmentTests`, `AreaRestrictionTests`. |
| Seguimiento del estado de la solicitud (pendiente → en proceso → resuelto) | Alta | **Cumplido** | `tickets.services.change_ticket_status` + `ALLOWED_TRANSITIONS`, sin saltos ni retrocesos posibles (verificado también contra POST manipulado). Tests: `TicketStatusTransitionTests`, `TicketStatusViewTests`. |
| Notificaciones automáticas ante cambios de estado del ticket | Media | **Cumplido** | `notifications.services.notify_ticket_status_changed`, invocada dentro de la misma transacción que el cambio de estado. Tests: `TicketStatusNotificationTests`. |
| Dashboard de reportes: cantidad de solicitudes por área y tiempo promedio de resolución | Alta | **Cumplido** | `reports.views.dashboard`: conteo agrupado por `category__area` y promedio de resolución vía subquery sobre `TicketHistory`. Tests: `DashboardByAreaTests`, `DashboardResolutionTimeTests`. |
| Autenticación de usuarios con roles diferenciados | Alta | **Cumplido** | Sesiones nativas de `django.contrib.auth`; `users.User.Role` con los cuatro roles, permisos verificados server-side en cada vista. |
| Historial de solicitudes por empleado | Media | **Cumplido** | `tickets.TicketHistory` (historial de estados) y `ticket_list`/`ticket_detail`, visibles para el empleado sobre sus propios tickets vía `get_visible_tickets`. Tests: `TicketPermissionTests.test_employee_can_view_own_ticket`. |
| Panel de administración de usuarios, áreas y categorías | Media | **Cumplido** | App `administration` completa (alta/edición/baja de Área, Categoría y Usuario), restringida a `role=admin`, con protección adicional del último Admin activo del sistema (Bloque 10). Tests: `AdministrationAccessTests`, `AreaAdministrationTests`, `CategoryAdministrationTests`, `UserAdministrationTests`, `LastActiveAdminProtectionTests`. |

### 1.2 Criterios de aceptación formales

**1. El sistema permite crear, categorizar y asignar tickets sin errores.**
**Cumplido.** `TicketCreateForm` valida título/descripción/categoría
server-side (incluida la exclusión de categorías inactivas, aun con un
POST manipulado); `Ticket.objects.create_ticket` crea el ticket y su
historial inicial en una única transacción; `auto_assign_ticket` se
invoca inmediatamente después. Evidencia:
`TicketAssignmentViewTests.test_ticket_creation_triggers_automatic_assignment`,
`InactiveCategoryTicketCreationTests` (Bloque 10).

**2. El estado de cada solicitud se actualiza correctamente y es visible para el empleado en tiempo real.**
**Cumplido**, con una aclaración sobre "tiempo real": cada vez que el
empleado carga o recarga la página del ticket
(`tickets.views.ticket_detail`), la vista consulta el estado vigente
directamente en la base de datos — nunca un valor cacheado ni
desactualizado. **No hay actualización automática por WebSockets ni
polling**: si el estado cambia mientras el empleado ya tiene la página
abierta, necesita recargarla para verlo. "Tiempo real" se cumple en el
sentido de "siempre el dato vigente al consultar", no en el sentido de
"la pantalla se actualiza sola sin que el usuario haga nada". Evidencia:
`TicketStatusViewTests` (los cambios de estado persisten y se leen
correctamente en la siguiente consulta).

**3. El sistema envía notificaciones ante cada cambio de estado.**
**Cumplido.** `notify_ticket_status_changed` se genera exactamente una
vez por transición válida, dentro de la misma transacción del cambio;
ninguna transición inválida genera notificación. Evidencia:
`TicketStatusNotificationTests` (incluye
`test_invalid_transition_generates_no_notification` y
`test_resolved_reopen_attempt_generates_no_notification`).

**4. El dashboard de reportes refleja datos reales y actualizados por área.**
**Cumplido.** El dashboard no cachea nada: cada request recalcula los
conteos y el promedio de resolución sobre el queryset vigente, filtrado
por rol y por los filtros de fecha/área de esa request. Evidencia:
`DashboardByAreaTests`, `DashboardStatusCountsTests`,
`DashboardResolutionTimeTests`.

**5. El sistema ha sido probado y aprobado por el docente/patrocinador antes de la entrega final.**
**PENDIENTE.** El sistema está probado internamente (264 tests
automatizados — modelos, permisos, máquina de estados, Round Robin,
notificaciones, N+1, un test de aceptación end-to-end — más el
checklist de pruebas manuales de `docs/pruebas-manuales.md`), pero la
aprobación formal por el docente/patrocinador es un paso posterior a
esta entrega, que depende de la sustentación y no es algo que el equipo
de desarrollo pueda autoevaluar ni marcar como cumplido por sí mismo.

### 1.3 Exclusiones formales

Ninguna de las siguientes está implementada, consistente con el
alcance formal:

| Exclusión | Estado |
|---|---|
| Integración con nómina, ERP u otros sistemas externos | No implementado |
| Aplicación móvil nativa | No implementado (solo interfaz web) |
| Facturación o gestión financiera | No implementado |
| Soporte multiempresa | No implementado (una sola organización, un solo árbol de Áreas) |
| Chat en vivo entre empleado y encargado | No implementado. Los comentarios en tickets (sección 2) son asíncronos y no constituyen chat en vivo — ver esa sección para la distinción. |

## 2. Funcionalidades adicionales implementadas

Funcionalidades que **no** forman parte del alcance formal aprobado,
implementadas como mejoras de apoyo. Ninguna reemplaza ni reinterpreta
una exclusión formal.

### Comentarios en tickets

Implementados en el **Bloque 9** como funcionalidad adicional al
alcance formal. Apoyan la trazabilidad y la comunicación contextual
dentro de un ticket: cualquiera que pueda ver el ticket (el empleado
que lo creó, el encargado de su área, o un Admin) puede dejar una nota
visible para el resto. Son **asíncronos** — se escriben, quedan
guardados en el ticket, y generan una notificación a la otra parte — y
quedan guardados permanentemente (append-only, sin edición ni borrado).

**No son un chat en vivo** y no modifican ni reemplazan la exclusión
formal de "chat en vivo entre empleado y encargado": no hay mensajería
en tiempo real, no hay indicador de "escribiendo...", no hay entrega
inmediata — es una nota que se lee la próxima vez que alguien abre el
ticket. No se presentan como requisito formal en ningún punto de esta
documentación.

### Recuperación de contraseña

Funcionalidad adicional (**Bloque 9**) de apoyo a la autenticación
(requisito formal "Autenticación de usuarios con roles diferenciados").
Permite a un usuario que no puede iniciar sesión (contraseña olvidada)
recuperar el acceso por correo, sin revelar si una cuenta existe. No
estaba en el enunciado formal, pero es un complemento necesario de
cualquier sistema de autenticación real.

### Paginación y `seed_demo`

Mejoras de soporte, no funcionalidades del alcance:

- **Paginación** (Bloque 9): usabilidad de las listas principales
  (tickets, usuarios, notificaciones, áreas, categorías) cuando crecen
  más allá de una pantalla. No cambia ningún dato ni regla de negocio.
- **`seed_demo`** (Bloque 11): comando de carga de datos de ejemplo
  para desarrollo y demostración (ver `docs/demostracion.md`). Es
  código de soporte para probar el sistema, no una funcionalidad que
  use la organización en producción.
