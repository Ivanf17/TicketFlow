# Preparación de la demostración — TicketFlow

## 7.1 — Datos de prueba (`seed_demo`)

```bash
python manage.py seed_demo
```

Carga un conjunto de datos realista para probar el sistema o preparar
la sustentación: 3 áreas, 7 categorías, 10 usuarios (los cuatro roles)
y 14 tickets repartidos en los tres estados, con fechas distribuidas en
los últimos 20 días y tiempos de resolución variados (2 a 48 horas),
más algunas notificaciones y comentarios generados por el propio flujo
normal del sistema (no insertados a mano: el comando llama a
`auto_assign_ticket`/`change_ticket_status`/`notify_ticket_comment_added`,
igual que lo haría un usuario real).

**Es seguro de re-ejecutar:** si detecta que los usuarios de
demostración ya existen, no crea nada nuevo — avisa y no hace nada, en
vez de duplicar datos.

> ⚠️ **Estas credenciales son solo para demostración y entornos de
> desarrollo/pruebas.** No usar esta contraseña en un entorno con datos
> reales de una organización.

### Credenciales generadas

Todas las cuentas usan la misma contraseña: **`Demo1234!`**

| Usuario | Rol | Área |
|---|---|---|
| `demo_admin` | Admin | — |
| `demo_gerencia` | Management | — |
| `demo_jefe_ti1` | Area Manager | TI |
| `demo_jefe_ti2` | Area Manager | TI |
| `demo_jefe_mant` | Area Manager | Mantenimiento |
| `demo_jefe_rrhh` | Area Manager | RRHH |
| `demo_empleado_ti1` | Employee | TI |
| `demo_empleado_ti2` | Employee | TI |
| `demo_empleado_mant1` | Employee | Mantenimiento |
| `demo_empleado_rrhh1` | Employee | RRHH |

### Qué datos crea, en detalle

- **Áreas:** TI, Mantenimiento, RRHH.
- **Categorías:** TI → Hardware, Software, Redes · Mantenimiento →
  Eléctrico, Plomería · RRHH → Vacaciones, Licencias.
- **Tickets (14):** 6 en TI (2 resueltos, 1 en proceso, 2 pendientes,
  y uno resuelto más entre los dos primeros), 4 en Mantenimiento (2
  resueltos, 1 en proceso, 1 pendiente), 4 en RRHH (1 resuelto, 1 en
  proceso, 2 pendientes) — en total 6 `Resuelto`, 3 `En proceso`, 5
  `Pendiente`, con fechas de creación entre 1 y 20 días atrás.
- Al tener dos Area Managers en TI (`demo_jefe_ti1`/`demo_jefe_ti2`),
  sus tickets muestran la alternancia del Round Robin.
- Dos comentarios de ejemplo (uno de un empleado, otro de un Area
  Manager), cada uno generando su notificación correspondiente.

## 7.2 — Guion de demostración

Duración estimada total: **12–15 minutos**. Usar los usuarios creados
por `seed_demo`.

| # | Paso | Usuario | Qué mostrar | Duración |
|---|---|---|---|---|
| 1 | Login como empleado | `demo_empleado_ti1` | Pantalla de login, mencionar sesiones nativas de Django (sin tokens). | 30 s |
| 2 | Crear un ticket nuevo | `demo_empleado_ti1` | Formulario de creación: título, descripción, categoría. Señalar que el área **no se elige**, se deriva de la categoría. | 1 min |
| 3 | Ver el ticket recién creado | `demo_empleado_ti1` | Estado `Pendiente`, número de ticket autogenerado, y que ya tiene un responsable asignado — sin haber hecho nada más: es el Round Robin automático. | 1 min |
| 4 | Ver la lista de "mis tickets" | `demo_empleado_ti1` | Solo ve sus propios tickets, no los de otros empleados. | 30 s |
| 5 | Cerrar sesión, entrar como encargado de área | `demo_jefe_ti1` | Ve todos los tickets de TI (no solo los que se le asignaron a él). | 1 min |
| 6 | Cambiar el estado de un ticket | `demo_jefe_ti1` | Abrir un ticket `Pendiente`, marcarlo `En proceso`. Señalar que solo se ofrece el único siguiente estado válido. | 1 min |
| 7 | Comentar el ticket | `demo_jefe_ti1` | Agregar un comentario. | 30 s |
| 8 | Cambiar a sesión del empleado | `demo_empleado_ti1` | Mostrar la notificación de cambio de estado y del comentario en su bandeja. | 1 min |
| 9 | Intentar ver un ticket ajeno por URL | `demo_empleado_ti2` | Cambiar el número en la URL a un ticket de otro empleado → 404. Mostrar que la protección es real, no solo de interfaz. | 1 min |
| 10 | Reasignación manual | `demo_jefe_ti1` | Reasignar un ticket a `demo_jefe_ti2`, mostrar el historial de asignación. | 1 min |
| 11 | Dashboard de área | `demo_jefe_ti1` | Métricas acotadas a TI: conteos, tiempo promedio de resolución, gráficos. | 1 min |
| 12 | Dashboard global | `demo_admin` | Mismo dashboard pero con selector de área y datos de las tres áreas. Filtrar por fecha. | 1.5 min |
| 13 | Administración | `demo_admin` | Crear una categoría nueva, mostrar que solo Admin ve esta sección. | 1.5 min |
| 14 | Intentar dejar el sistema sin Admin | `demo_admin` | Si `demo_admin` es el único Admin activo en ese momento, intentar desactivarse o cambiar su propio rol → el sistema lo rechaza con un mensaje explicando por qué. (Si hay más de un Admin, mostrarlo con otro Admin de prueba.) | 1.5 min |
| 15 | Dashboard de Gerencia | `demo_gerencia` | Mismas métricas globales, pero remarcar que **no** hay ninguna lista de tickets individuales ni forma de ver el detalle de uno. | 1.5 min |
| 16 | Recuperación de contraseña | (sin sesión) | "¿Olvidaste tu contraseña?", mostrar que el correo se imprime en la consola del servidor (backend de desarrollo) y que la pantalla es igual exista o no la cuenta. | 1 min |

## 7.3 — Preguntas probables

**¿Quién puede entrar a `/admin/` y por qué?**
`/admin/` es el Django Admin nativo, gobernado por `is_staff`
(`is_superuser` para las acciones más sensibles), un sistema totalmente
independiente de `role`. Ningún usuario creado desde
`Administración → Usuarios` de TicketFlow obtiene `is_staff`, sin
importar su rol — ese flag solo lo otorga `createsuperuser` o alguien
con acceso directo a la base de datos. Es intencional: `/admin/` no
respeta ninguna de las reglas de negocio de TicketFlow (por ejemplo, no
impide editar `Ticket.status` directamente saltándose la máquina de
estados), así que mantenerlo separado de `role=admin` evita que
cualquier Admin de negocio obtenga por accidente ese nivel de acceso
sin restricciones. Detalle completo en `docs/limitaciones-conocidas.md`
(5.2).

**¿Por qué Gerencia ve métricas pero no tickets individuales?**
Es una decisión de alcance explícita desde los primeros bloques: el rol
de Gerencia es de seguimiento agregado (volumen, tiempos, distribución
por área), no de gestión operativa. `reports.views.dashboard` construye
el widget de "tickets recientes" solo si `request.user.role !=
MANAGEMENT`, y ni siquiera arma esa consulta para Gerencia
(`Ticket.objects.none()`); además, `tickets.permissions
.get_visible_tickets` le niega el detalle de cualquier ticket (404) en
cualquier otro punto del sistema donde lo intente.

**¿Qué pasa si cambian el área de una categoría con tickets existentes?**
El área de un ticket no es una columna propia: es una propiedad
calculada (`ticket.category.area`). Si se reclasifica una categoría a
otra área, todos los tickets que la usan cambian de área
retroactivamente, incluidos los ya resueltos — afecta tanto a qué Area
Manager los ve como al desglose histórico "tickets por área" del
dashboard. Es un comportamiento conocido y documentado, no un error;
ver `docs/limitaciones-conocidas.md` (5.1) para el detalle completo,
incluida la solución que se evaluó y por qué no se implementó (una
migración de datos y de reportes, descartada por la prioridad de
Tiempo del proyecto).

**¿Cómo se garantiza que un Employee no tenga área nula?**
Con dos capas: `User.clean()` lo valida a nivel de formulario/modelo, y
además hay un `CheckConstraint` en la tabla `users_user` en PostgreSQL
que rechaza a nivel de motor de base de datos cualquier fila con
`role` en (`employee`, `area_manager`) y `area` nula — sin importar si
la escritura vino de un formulario, del shell de Django o de
`createsuperuser`. Está probado explícitamente con un `.save()` directo
que evita `full_clean()`, no solo a través del formulario.

**¿Por qué no hicieron una API?**
Se evaluó explícitamente en el precheck del Bloque 9: no hay ninguna
señal de necesidad real (sin cliente externo, sin app móvil, sin
integración de terceros mencionada en ningún momento del proyecto).
Agregar Django REST Framework u otra API hoy habría sido exactamente
el tipo de infraestructura no justificada que las reglas del proyecto
prohíben, contra una prioridad de Tiempo con fecha fija.

**¿Cómo se asigna un ticket cuando hay varios encargados en el área?**
Round Robin con un cursor persistente por área
(`AreaAssignmentCursor.last_assigned_to`): cada área "recuerda" a quién
le tocó la última asignación automática, y la siguiente le toca al
próximo Area Manager activo en orden (no al que tiene menos tickets
abiertos, ni a uno elegido al azar). Una reasignación manual posterior
nunca mueve ese cursor, así que no distorsiona el reparto futuro. Si el
área se queda sin ningún Area Manager activo, el ticket simplemente
queda sin asignar, sin error.
