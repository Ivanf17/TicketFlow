# Manual de usuario — TicketFlow

Guía para usar TicketFlow según tu rol dentro de la organización. No
hace falta ningún conocimiento técnico: acá se explica qué vas a ver en
pantalla y qué tenés que hacer en cada caso.

Para entrar al sistema, abrí la dirección que te haya dado tu
administrador en el navegador. Vas a ver una pantalla de "Iniciar
sesión" donde ingresás tu usuario y tu contraseña.

Si te olvidaste tu contraseña, hacé clic en "¿Olvidaste tu contraseña?"
debajo del botón de ingreso, escribí tu correo electrónico y vas a
recibir instrucciones para elegir una nueva. Si no te llega nada,
puede ser que tu cuenta no tenga un correo cargado — pedile a un
Administrador que te lo agregue.

Una vez adentro, en la parte de arriba de cualquier pantalla vas a ver
un menú con las opciones que te correspondan según tu rol, tu nombre de
usuario, y un botón "Cerrar sesión" para salir.

---

## Para Empleados

Como empleado, tu trabajo en el sistema es reportar problemas o
solicitudes, y hacer seguimiento de los que ya reportaste.

### Crear una solicitud (ticket)

1. En el menú de arriba, hacé clic en "Tickets".
2. Hacé clic en el botón "Nuevo ticket".
3. Completá:
   - **Título:** un resumen corto del problema (ej. "La impresora del
     piso 2 no enciende").
   - **Descripción:** el detalle completo de lo que pasa.
   - **Categoría:** elegí la que mejor describe tu solicitud (por
     ejemplo, "Hardware" dentro del área de TI). El sistema usa la
     categoría para saber a qué área y a qué responsable enviar tu
     ticket — no hace falta que elijas el área vos mismo.
4. Hacé clic en el botón para guardar. Vas a ver la pantalla de detalle
   de tu ticket recién creado, con el número que se le asignó (por
   ejemplo `TK-000123`) y el estado "Pendiente".

El sistema asigna automáticamente tu ticket a un responsable del área
correspondiente — no necesitás hacer nada más en este paso.

### Consultar el estado de tus solicitudes

1. Hacé clic en "Tickets" en el menú.
2. Vas a ver la lista de todas las solicitudes que **vos** creaste, con
   su número, título, categoría, área, estado actual, quién la creó,
   quién la está atendiendo y cuándo se creó.
3. Hacé clic en cualquier fila (en el número del ticket) para ver el
   detalle completo.

Los estados posibles son: **Pendiente** (todavía no la empezaron a
atender), **En proceso** (alguien la está resolviendo) y **Resuelto**
(ya se solucionó). Una vez que un ticket queda "Resuelto", no vuelve a
cambiar de estado.

### Ver el historial completo de un ticket

Dentro del detalle de cualquiera de tus tickets vas a encontrar dos
secciones:

- **Historial de estados:** todos los cambios de estado que tuvo el
  ticket, con fecha y quién hizo el cambio.
- **Historial de asignación:** a quién se le asignó (y reasignó, si
  pasó) el ticket a lo largo del tiempo.

### Comentar en un ticket

Al final del detalle de cualquier ticket que puedas ver (los tuyos)
hay una sección de "Comentarios". Podés escribir un comentario y
enviarlo — por ejemplo, para agregar información adicional o preguntar
por el avance. El responsable que atiende tu ticket recibe una
notificación cuando comentás. Los comentarios se pueden agregar incluso
en tickets ya resueltos, y no cambian el estado del ticket.

### Ver tus notificaciones

Hacé clic en "Notificaciones" en el menú (vas a ver un número al lado,
que indica cuántas notificaciones sin leer tenés). Ahí vas a recibir un
aviso cada vez que:

- Se le asigna un responsable a tu ticket.
- Cambia el estado de tu ticket.
- El responsable comenta en tu ticket.

Podés marcar una notificación como leída, o usar "Marcar todas como
leídas" para limpiar todo de una vez.

---

## Para Encargados de Área (Area Manager)

Como encargado de área, tu trabajo es atender los tickets que le
corresponden a tu área: asignártelos o reasignarlos, y avanzar su
estado hasta resolverlos.

### Ver los tickets de tu área

Hacé clic en "Tickets" en el menú. Vas a ver **todos** los tickets de tu
área (no solo los que te asignaron a vos), con su estado y quién los
está atendiendo actualmente.

### Asignarte o reasignar un ticket

1. Entrá al detalle del ticket (haciendo clic en su número desde la
   lista).
2. Si el ticket no tiene responsable, o si querés cambiarlo, hacé clic
   en "Asignar" (o "Reasignar" si ya tiene uno).
3. Elegí, de la lista, a qué encargado de tu área se lo asignás (podés
   elegirte a vos mismo).
4. Confirmá. El nuevo responsable recibe una notificación
   automáticamente.

Cuando se crea un ticket nuevo en tu área, el sistema ya lo asigna
automáticamente de forma rotativa entre los encargados activos del
área — la asignación manual es para los casos en que necesites
cambiar eso.

### Cambiar el estado de un ticket

1. Entrá al detalle del ticket.
2. Vas a ver un botón con el único siguiente estado posible (por
   ejemplo, si está "Pendiente", el botón va a decir algo como
   "Marcar como En proceso").
3. Hacé clic para confirmar el cambio.

El sistema no te va a dejar saltear pasos (por ejemplo, pasar
directamente de "Pendiente" a "Resuelto") ni volver atrás una vez que
un ticket quedó "Resuelto" — esos casos simplemente no aparecen como
opción.

### Comentar en un ticket

Igual que para los empleados: al final del detalle del ticket hay una
sección de comentarios. Cuando comentás, se le avisa al empleado que
creó el ticket.

### Consultar tu dashboard

Hacé clic en "Dashboard" en el menú. Vas a ver, acotado siempre a tu
propia área:

- Cuántos tickets hay en total, y cuántos en cada estado.
- El tiempo promedio que tarda en resolverse un ticket.
- Dos gráficos: uno por estado y otro por área (en tu caso, va a
  mostrar solo la tuya).
- Una tabla con los tickets más recientes de tu área.

Podés filtrar por rango de fechas para ver el período que te interese.

---

## Para Administradores

Como administrador, tu trabajo es mantener la configuración
organizacional del sistema: qué áreas y categorías existen, y qué
usuarios tienen acceso.

### Entrar a Administración

Hacé clic en "Administración" en el menú (esta opción solo la ven los
administradores). Ahí vas a encontrar tres secciones: Áreas,
Categorías y Usuarios.

### Administrar Áreas

1. Entrá a "Áreas" para ver el listado (con cuántas categorías tiene
   cada una y si está activa).
2. "Nueva área" para crear una: nombre, una descripción opcional, y si
   queda activa.
3. Desde el listado podés "Editar" cualquier área, o "Eliminar" — si
   la vas a eliminar y todavía tiene categorías asociadas, el sistema
   te va a avisar que no se puede y por qué, en vez de fallar.

### Administrar Categorías

Igual que las áreas, pero cada categoría siempre tiene que pertenecer
a un área (se elige al crearla o editarla). Una categoría marcada como
inactiva deja de aparecer como opción cuando un empleado crea un
ticket nuevo, pero los tickets ya existentes con esa categoría no se
ven afectados.

### Crear un usuario nuevo

1. Entrá a "Usuarios" → "Crear usuario".
2. Completá: nombre de usuario, correo electrónico (opcional, pero
   recomendado si esa persona va a necesitar recuperar su contraseña
   alguna vez), el **rol** (Empleado, Encargado de área,
   Administrador o Gerencia), el área (obligatoria para Empleado y
   Encargado de área; no aplica para Administrador o Gerencia), y una
   contraseña inicial.
3. Guardá. La persona ya puede iniciar sesión con esa contraseña (y
   cambiarla más adelante si se le olvida, con "¿Olvidaste tu
   contraseña?").

### Editar o desactivar un usuario

Desde el listado de "Usuarios", "Editar" te permite cambiar el rol, el
área, o desactivar la cuenta (sin borrarla) para que esa persona ya no
pueda iniciar sesión. "Eliminar" borra la cuenta por completo — si esa
persona ya tiene tickets o historial asociado, el sistema no va a
permitir borrarla (para no perder ese historial) y te va a sugerir
desactivarla en su lugar.

**Importante:** el sistema no te va a dejar desactivar, cambiar de rol,
ni eliminar al **único** Administrador activo que quede — ni siquiera
a vos mismo si sos el único. Esto es para evitar que la organización se
quede sin nadie que pueda entrar a Administración. Si necesitás dejar
de ser administrador, primero creá o activá a otro Administrador.

---

## Para Gerencia (Management)

Como Gerencia, tu vista del sistema es de métricas generales, no de
tickets individuales — no vas a ver el contenido de ningún ticket en
particular, solo números agregados de toda la organización.

### Consultar el dashboard

Hacé clic en "Dashboard" en el menú. Ahí vas a ver, para **toda la
organización** (todas las áreas juntas, o filtrado por una en
particular si elegís una del selector):

- El total de tickets y cuántos hay en cada estado (Pendiente, En
  proceso, Resuelto).
- El tiempo promedio de resolución.
- Un gráfico de tickets por estado y otro por área.

Podés filtrar por área específica y por rango de fechas para acotar el
período o el sector que te interese analizar.

No vas a encontrar una lista de tickets individuales ni un botón para
ver el detalle de uno en particular: esa vista está reservada para
quienes efectivamente atienden los tickets (Encargados de área y
Administradores).

### Notificaciones

Como Gerencia también tenés acceso a "Notificaciones" en el menú,
aunque en general no vas a recibir avisos ahí (las notificaciones son
sobre eventos de tickets puntuales, que no forman parte de tu rol).
