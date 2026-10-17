# Limitaciones conocidas — TicketFlow

Este documento enumera, de forma explícita y honesta, las limitaciones
del sistema que el equipo identificó durante el desarrollo y decidió
no resolver dentro del alcance de las 13 semanas. Ninguna de ellas es
un defecto oculto: todas fueron una decisión consciente, documentada
aquí con su razón.

## 5.1 — El área de un ticket es derivada, no propia

**Qué es:** `Ticket.area` no es una columna en la base de datos. Es una
`@property` de Python (`tickets/models.py`) que siempre devuelve
`self.category.area` en el momento en que se consulta:

```python
@property
def area(self):
    return self.category.area
```

**Por qué ocurre:** fue una decisión deliberada desde que se introdujo
la jerarquía Área → Categoría → Ticket, para evitar guardar el mismo
dato (el área) en dos lugares (`Category.area` y `Ticket.area`) que
podrían desincronizarse. "Ticket deriva su Área mediante Category →
Area" es una regla explícita del proyecto desde los primeros bloques.

**Desde qué bloque existe:** desde que se definió el modelo `Ticket`
(bloque en que se introdujo `tickets/`, con la relación a `Category` ya
establecida), y se mantuvo sin cambios en todos los bloques
posteriores.

**Qué impacto tiene:** si se reasigna una `Category` existente a una
`Area` distinta (`administration → Categorías → Editar`, cambiando el
campo `Area`), **todos los tickets que ya existían con esa categoría
cambian de área retroactivamente**, sin que se toque una sola fila de
`tickets_ticket`. Esto afecta:

- **Visibilidad de Area Manager:** un ticket viejo puede dejar de ser
  visible para el Area Manager que lo venía atendiendo (si la categoría
  se movió a otra área), o volverse visible para un Area Manager que
  nunca lo había visto.
- **Reportes históricos:** el desglose "tickets por área" del
  dashboard (`reports/views.py`, agrupado por `category__area`)
  reclasifica retroactivamente los tickets ya resueltos bajo la nueva
  área, aunque en el momento de crearse y resolverse hayan pertenecido
  a otra. Un reporte de "marzo" corrido en abril, después de mover una
  categoría, puede no coincidir con el mismo reporte corrido en marzo.

**Cuál sería la solución:** agregar una columna propia
`Ticket.area_at_creation` (o similar), asignada una sola vez al crear
el ticket (copiando `category.area` en ese momento) y nunca vuelta a
tocar, de forma que el histórico quede fijo aunque la categoría se
reclasifique después. La visibilidad de Area Manager podría seguir
usando `category.area` (el estado *actual*) o migrar también a la
columna fija, según qué comportamiento se prefiera.

**Por qué no se implementó:** la prioridad número 1 declarada del
proyecto es Tiempo, con fecha límite fija. Esta solución implica: (1)
una migración de esquema, (2) una migración de datos para poblar el
valor histórico de tickets ya existentes (con una decisión no trivial
de qué valor usar para tickets creados antes del cambio), y (3) revisar
todos los reportes y tests que hoy asumen que el área siempre se deriva
en vivo de la categoría. En la práctica, además, cambiar el área de una
categoría con tickets activos es una operación administrativa poco
frecuente (no forma parte de ningún flujo del día a día), así que el
riesgo real quedó aceptado en vez de resuelto.

## 5.2 — `role=admin` e `is_staff` son sistemas de autorización independientes

**Qué es:** TicketFlow tiene su propio sistema de roles
(`users.User.role`), completamente separado del sistema nativo de
Django que controla el acceso a `/admin/` (`is_staff`/`is_superuser`).
Un usuario con `role=admin` (creado, por ejemplo, desde
`Administración → Usuarios → Crear usuario`) puede entrar a
`/administration/` de TicketFlow, pero **no** puede entrar a `/admin/`
(el Django Admin) a menos que además tenga `is_staff=True` — y
`administration.forms.UserCreateForm` nunca expone ni activa ese campo
para ningún rol, deliberadamente.

**Por qué es una separación intencional:** son dos superficies
distintas con propósitos distintos. `/administration/` es la interfaz
de negocio para gestionar Áreas, Categorías y Usuarios, construida a
medida con las reglas propias de TicketFlow (por ejemplo, la protección
del último Admin activo). `/admin/` es una herramienta genérica de
Django pensada para inspeccionar/editar cualquier modelo directamente
en la base de datos, sin ninguna de esas reglas de negocio aplicadas
(un cambio ahí no pasa por `UserAdminForm.clean()`, por ejemplo). Fusionar
ambos conceptos habría significado que cualquier `role=admin` obtuviera
automáticamente acceso sin restricciones a todos los modelos del
sistema vía `/admin/`, incluida la capacidad de editar directamente
`Ticket.status` o borrar filas de historial saltándose toda la lógica
de `services.py` — exactamente lo que `tickets/admin.py` evita a
propósito marcando `status` como `readonly_fields`.

**Por qué no es una vulnerabilidad:** ambos accesos requieren
autenticación y están gobernados por su propio chequeo:
`/administration/` por `can_access_administration` (exige
`role=admin`), `/admin/` por el propio `AdminSite` de Django (exige
`is_staff=True`, y para las acciones más sensibles, `is_superuser`).
Un usuario nunca obtiene ninguno de los dos por accidente: `is_staff`
solo se activa hoy a través de `createsuperuser` (o manualmente por
alguien con acceso directo a la base de datos/consola de Django), nunca
a través de la interfaz de TicketFlow.

**Qué implica operativamente:** para el uso normal de la organización
(reportar tickets, atenderlos, administrar áreas/usuarios), nadie
necesita `is_staff`. Ese flag queda reservado para quien realmente
necesite depurar datos directamente desde `/admin/` (típicamente el
equipo de desarrollo/soporte técnico), y se otorga fuera de la interfaz
de la aplicación, por diseño.

## 5.3 — Otras limitaciones identificadas durante el proyecto

### 5.3.1 — Sin cambio de contraseña estando logueado

**Qué es:** un usuario autenticado no tiene forma de cambiar su propia
contraseña desde la interfaz. La única vía es el flujo de recuperación
(`/accounts/password-reset/`), pensado para cuando no se puede iniciar
sesión, no como configuración de cuenta.

**Origen:** identificado explícitamente durante el precheck del
Bloque 10, como una posible mejora de autoservicio.

**Impacto:** bajo pero real — un usuario que simplemente quiere
cambiar su contraseña (sin haberla olvidado) tiene que pasar por el
flujo de "olvidé mi contraseña" igualmente.

**Solución posible:** agregar las vistas nativas
`PasswordChangeView`/`PasswordChangeDoneView` de
`django.contrib.auth`, con un link en la navegación para usuarios
autenticados. Es una adición pequeña y de bajo riesgo.

**Por qué no se implementó:** se evaluó y se descartó explícitamente
para el Bloque 10 por decisión del responsable del proyecto, para
mantener ese bloque acotado a pruebas y evitar scope creep contra la
prioridad de Tiempo. Queda como mejora candidata para una futura
iteración fuera de este proyecto académico.

### 5.3.2 — Filtros y búsqueda en `ticket_list` (resuelta)

**Estado:** resuelta en el rediseño de la interfaz. La lista de tickets
(`/tickets/`) ahora filtra por estado (`?status=`, incluido `OPEN` =
pendientes y en proceso, usado por "Mis tickets" del Area Manager),
por asignación (`?assignment=`, ofrecido en pantalla solo al Admin) y
busca por número o título (`?q=`). Los filtros se validan server-side,
siempre parten de `get_visible_tickets` (nunca amplían la visibilidad
del rol), ignoran valores desconocidos y se conservan al paginar.
Tests: `TicketListFilterTests`, `TicketListMyTicketsTests`.

**Lo que sigue sin existir:** un filtro por área (`?area=`) en la lista
del Admin. El Admin puede acotar por área desde el dashboard de
`reports`, pero no desde `/tickets/`.

**Origen:** señalado en el precheck del Bloque 10 como posible mejora;
quedó fuera de ese bloque y se implementó después, junto con el
rediseño.

### 5.3.3 — Dos usuarios con el mismo email reciben ambos el correo de recuperación

**Qué es:** consecuencia directa de que `users.User.email` no es único
(ver `CLAUDE.md`, decisión tomada en el Bloque 9). Si dos cuentas
distintas comparten el mismo valor de `email`, el formulario nativo de
recuperación de contraseña de Django (`PasswordResetForm.get_users()`)
encuentra a ambas y les envía el enlace de recuperación a las dos.

**Origen:** riesgo identificado y aceptado explícitamente al decidir,
en el Bloque 9, no hacer `email` único ni obligatorio.

**Impacto:** bajo en la práctica (la creación de usuarios es
administrada por un Admin, no autoservicio, así que la probabilidad de
un email duplicado por error humano es baja), pero real: no hay ninguna
validación que lo impida hoy.

**Solución posible:** agregar `unique=True` a `User.email`, lo que
exige antes una migración de datos que verifique (y resuelva) cualquier
duplicado o valor vacío ya existente.

**Por qué no se implementó:** decisión explícita y ya documentada en
el Bloque 9 — se aceptó el riesgo en vez de asumir el costo de esa
migración de datos, dado el volumen de usuarios esperado y la prioridad
de Tiempo del proyecto.
