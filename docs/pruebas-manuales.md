# Pruebas manuales de interfaz — TicketFlow

Checklist para validar en el navegador lo que las pruebas automatizadas
no cubren directamente (aspecto visual, flujo real de clics, mensajes
en pantalla). Sirve de insumo para el Bloque 11 (documentación y
entrega) y para la sustentación del proyecto.

Cómo usar este documento: para cada fila, ejecutar los pasos con el rol
indicado, comparar contra el resultado esperado y marcar la casilla de
resultado real (`[ ] OK` / `[ ] Falla`, con una nota si falla).

> **Nota sobre la sección 5 (Comentarios):** los comentarios en tickets
> (`tickets.TicketComment`) son una **funcionalidad adicional** al
> alcance formal aprobado (Enunciado del Alcance, 25/08/2026),
> implementada en el Bloque 9. Son asíncronos, no un chat en vivo, y no
> modifican ni reemplazan la exclusión formal de "chat en vivo entre
> empleado y encargado" (ver `docs/casos-de-uso.md`, sección 2, para la
> distinción completa). Se mantiene esta sección del checklist porque la
> funcionalidad existe, está probada (`tickets/tests.py`, clases
> `TicketCommentTests`/`TicketCommentNotificationTests`) y es parte del
> sistema entregado.

## 1. Autenticación

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 1.1 | Login exitoso | Employee | Ir a `/accounts/login/`, ingresar usuario/contraseña válidos, enviar | Redirige a `/` (home); la barra superior muestra usuario y rol, el menú lateral muestra "Mis solicitudes" y "Nuevo ticket" | [ ] OK &nbsp; [ ] Falla |
| 1.2 | Login exitoso | Area Manager | Igual que 1.1 con un usuario area_manager | Igual que 1.1; el menú lateral muestra "Tickets de mi área", "Mis tickets" y "Dashboard del área" | [ ] OK &nbsp; [ ] Falla |
| 1.3 | Login exitoso | Admin | Igual que 1.1 con un usuario admin | El menú lateral muestra "Panel admin", "Usuarios", "Áreas", "Categorías" y "Dashboard" | [ ] OK &nbsp; [ ] Falla |
| 1.4 | Login exitoso | Management | Igual que 1.1 con un usuario management | El menú lateral muestra solo "Dashboard ejecutivo" (y "Notificaciones"), NO muestra opciones de administración ni de tickets | [ ] OK &nbsp; [ ] Falla |
| 1.5 | Login fallido | Cualquiera | Ingresar contraseña incorrecta | Mensaje de error genérico, no revela si el usuario existe | [ ] OK &nbsp; [ ] Falla |
| 1.6 | Logout | Cualquiera | Click en "Cerrar sesión" | Redirige a home, que vuelve a mostrar la tarjeta con el botón "Iniciar sesión" | [ ] OK &nbsp; [ ] Falla |
| 1.7 | Recuperar contraseña | Cualquiera | Ir a login → "¿Olvidaste tu contraseña?", ingresar un email válido | Pantalla "Revisa tu correo"; el backend de consola imprime el email en la terminal del servidor | [ ] OK &nbsp; [ ] Falla |
| 1.8 | Recuperar contraseña — email inexistente | Cualquiera | Repetir 1.7 con un email que no existe | Misma pantalla "Revisa tu correo" (no revela si el correo existe) | [ ] OK &nbsp; [ ] Falla |
| 1.9 | Restablecer contraseña | Cualquiera | Usar el enlace impreso en consola, definir nueva contraseña | Pantalla de éxito; login funciona con la nueva contraseña | [ ] OK &nbsp; [ ] Falla |

## 2. Creación y consulta de tickets

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 2.1 | Crear ticket | Employee | "Nuevo ticket", completar título/descripción/categoría, enviar | Redirige al detalle del ticket, estado "Pendiente" | [ ] OK &nbsp; [ ] Falla |
| 2.2 | Ver mis tickets | Employee | Ir a "Tickets" | Lista solo los tickets propios, con paginación si hay más de 20 | [ ] OK &nbsp; [ ] Falla |
| 2.3 | No ver tickets ajenos | Employee | Intentar abrir por URL el detalle de un ticket de otro empleado | Página 404 | [ ] OK &nbsp; [ ] Falla |
| 2.4 | Ver tickets del área | Area Manager | Ir a "Tickets" | Lista todos los tickets de su área (no de otras) | [ ] OK &nbsp; [ ] Falla |
| 2.5 | Ver todos los tickets | Admin | Ir a "Tickets" | Lista tickets de todas las áreas | [ ] OK &nbsp; [ ] Falla |
| 2.6 | Management sin acceso a tickets | Management | Ir a "Tickets" o intentar abrir un detalle por URL | Lista vacía / detalle 404 (Management no ve contenido individual) | [ ] OK &nbsp; [ ] Falla |
| 2.7 | Categoría inactiva no aparece | Employee | Abrir "Nuevo ticket" | El select de categoría no ofrece categorías desactivadas | [ ] OK &nbsp; [ ] Falla |

## 3. Asignación

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 3.1 | Asignación automática | Employee | Crear un ticket en un área con al menos un Area Manager activo | El ticket queda asignado automáticamente (ver "Asignado a" en el detalle) | [ ] OK &nbsp; [ ] Falla |
| 3.2 | Sin responsables disponibles | Employee | Crear un ticket en un área sin Area Managers activos | El ticket queda "Sin asignar", sin error | [ ] OK &nbsp; [ ] Falla |
| 3.3 | Reasignación manual | Admin o Area Manager (su propia área) | Abrir el detalle de un ticket, click "Reasignar", elegir otro responsable del área, enviar | El ticket queda asignado al nuevo responsable; aparece en el historial de asignación | [ ] OK &nbsp; [ ] Falla |
| 3.4 | Reasignación fuera de área bloqueada | Area Manager | Intentar reasignar un ticket de otra área (por URL) | Página 404 | [ ] OK &nbsp; [ ] Falla |

## 4. Cambio de estado

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 4.1 | PENDING → IN_PROCESS | Area Manager (su área) o Admin | Detalle del ticket, click "Marcar como En proceso" | Estado cambia, aparece en el historial de estados | [ ] OK &nbsp; [ ] Falla |
| 4.2 | IN_PROCESS → RESOLVED | Area Manager o Admin | Repetir con el siguiente estado | Estado cambia a "Resuelto" | [ ] OK &nbsp; [ ] Falla |
| 4.3 | RESOLVED es terminal | Area Manager o Admin | Abrir el detalle de un ticket ya resuelto | No se ofrece ninguna acción de cambio de estado | [ ] OK &nbsp; [ ] Falla |
| 4.4 | Employee no puede cambiar estado | Employee | Abrir el detalle de su propio ticket | No aparece ningún botón de cambio de estado | [ ] OK &nbsp; [ ] Falla |

## 5. Comentarios

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 5.1 | Agregar comentario | Employee (ticket propio) | Detalle del ticket, escribir un comentario, enviar | El comentario aparece en la lista, con autor y fecha | [ ] OK &nbsp; [ ] Falla |
| 5.2 | Comentar ticket resuelto | Area Manager | Comentar un ticket en estado RESOLVED | El comentario se agrega y el estado sigue en RESOLVED | [ ] OK &nbsp; [ ] Falla |
| 5.3 | Notificación de comentario | Employee / Area Manager | Uno comenta, el otro revisa su bandeja | El otro lado recibe una notificación de "Nuevo comentario" | [ ] OK &nbsp; [ ] Falla |

## 6. Notificaciones

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 6.1 | Ver notificaciones | Cualquiera con notificaciones | Ir a "Notificaciones" | Se listan solo las propias, con contador de no leídas en la campana de la barra superior y en el menú lateral | [ ] OK &nbsp; [ ] Falla |
| 6.2 | Marcar como leída | Cualquiera | Click "Marcar como leída" en una notificación | Desaparece el resaltado, el contador baja en 1 | [ ] OK &nbsp; [ ] Falla |
| 6.3 | Marcar todas como leídas | Cualquiera con varias sin leer | Click "Marcar todas como leídas" | Contador queda en 0 | [ ] OK &nbsp; [ ] Falla |

## 7. Dashboard / reportes por rol

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 7.1 | Dashboard de área | Area Manager | Ir a "Dashboard" | Métricas y "tickets recientes" acotados a su propia área, sin selector de área | [ ] OK &nbsp; [ ] Falla |
| 7.2 | Dashboard global | Admin | Ir a "Dashboard" | Selector de área disponible; ve tickets recientes de cualquier área | [ ] OK &nbsp; [ ] Falla |
| 7.3 | Dashboard sin contenido individual | Management | Ir a "Dashboard" | Ve métricas agregadas; NO ve la sección "Tickets recientes" | [ ] OK &nbsp; [ ] Falla |
| 7.4 | Filtro por fecha | Admin o Management | Ingresar rango de fechas válido, filtrar | Métricas se recalculan según el rango | [ ] OK &nbsp; [ ] Falla |
| 7.5 | Filtro de fecha inválido | Admin o Management | Ingresar fecha inicial posterior a la final | Mensaje de aviso, filtros ignorados, no rompe la página | [ ] OK &nbsp; [ ] Falla |

## 8. Administración (áreas, categorías, usuarios)

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 8.1 | Acceso restringido | Employee / Area Manager / Management | Intentar abrir `/administration/` por URL | Página 403 | [ ] OK &nbsp; [ ] Falla |
| 8.2 | Crear área | Admin | "Panel admin → Áreas → Nueva área" | El área aparece en el listado | [ ] OK &nbsp; [ ] Falla |
| 8.3 | Crear categoría | Admin | "Panel admin → Categorías → Nueva categoría", asociarla a un área | La categoría aparece en el listado con su área | [ ] OK &nbsp; [ ] Falla |
| 8.4 | Crear usuario | Admin | "Panel admin → Usuarios → Crear usuario", completar rol/área/contraseña | El usuario aparece en el listado y puede iniciar sesión | [ ] OK &nbsp; [ ] Falla |
| 8.5 | Editar usuario | Admin | Editar rol/área/estado de un usuario existente | Cambios reflejados en el listado | [ ] OK &nbsp; [ ] Falla |
| 8.6 | Proteger al último Admin activo — desactivar | Admin (siendo el único activo) | Intentar desactivarse a sí mismo, o al único otro Admin activo | Formulario rechaza el cambio con un mensaje explicando que es el único Admin activo | [ ] OK &nbsp; [ ] Falla |
| 8.7 | Proteger al último Admin activo — cambiar rol | Admin (siendo el único activo) | Intentar cambiar su propio rol (o el del único otro Admin activo) a otro distinto de Admin | Formulario rechaza el cambio con el mismo mensaje | [ ] OK &nbsp; [ ] Falla |
| 8.8 | Proteger al último Admin activo — eliminar | Admin (siendo el único activo) | Intentar eliminar al único Admin activo | Se rechaza con un mensaje, el usuario sigue existiendo y activo | [ ] OK &nbsp; [ ] Falla |
| 8.9 | Eliminar/editar un Admin cuando hay otro activo | Admin | Con 2+ Admins activos, desactivar/cambiar rol/eliminar a uno de ellos | Se permite sin error | [ ] OK &nbsp; [ ] Falla |
| 8.10 | Paginación de listados | Admin | Con más de 20 áreas/categorías/usuarios, navegar entre páginas | Controles de paginación funcionan, no se rompe con `?page=` fuera de rango | [ ] OK &nbsp; [ ] Falla |

## 9. Interfaz (rediseño basado en Google Stitch)

| # | Flujo | Rol | Pasos | Resultado esperado | Resultado real |
|---|-------|-----|-------|---------------------|-----------------|
| 9.1 | Menú lateral en móvil | Cualquiera | Abrir el sitio en un ancho < 992 px (o modo responsive del navegador) y tocar ☰ | El menú lateral se abre como panel deslizable y se cierra con la X o Esc | [ ] OK &nbsp; [ ] Falla |
| 9.2 | Rail de iconos en tablet | Cualquiera | Ancho entre 992 y 1279 px | El menú lateral se reduce a iconos (72 px); cada icono muestra su nombre al pasar el mouse | [ ] OK &nbsp; [ ] Falla |
| 9.3 | Tablas en móvil | Employee / Area Manager | Ver "Mis solicitudes" / "Tickets de mi área" en < 768 px | Cada ticket se muestra como tarjeta apilada con etiquetas por campo, sin scroll horizontal de la página | [ ] OK &nbsp; [ ] Falla |
| 9.4 | Filtros del listado | Employee / Area Manager / Admin | Usar las tarjetas de métricas, los filtros de estado/asignación y el buscador; luego paginar | La lista se filtra (nunca muestra tickets fuera de la visibilidad del rol) y la paginación conserva los filtros | [ ] OK &nbsp; [ ] Falla |
| 9.5 | Desplegable de notificaciones | Cualquiera con notificaciones | Clic en la campana de la barra superior | Muestra las últimas 5 notificaciones propias; "Marcar todas como leídas" vuelve a la misma página con el contador en 0 | [ ] OK &nbsp; [ ] Falla |
| 9.6 | Navegación por teclado | Cualquiera | Recorrer la página con Tab / Shift+Tab; usar "Saltar al contenido" (primer Tab) | Todos los enlaces/botones reciben foco visible (contorno azul); el enlace de salto lleva al contenido principal | [ ] OK &nbsp; [ ] Falla |
| 9.7 | Confirmación de eliminación | Admin | Clic en "Eliminar" de un usuario/área/categoría | Aparece un diálogo de confirmación; al cancelar no se envía nada, al aceptar el servidor aplica sus reglas (puede rechazar) | [ ] OK &nbsp; [ ] Falla |
| 9.8 | Páginas de error | Cualquiera | Abrir una URL no permitida (403) o, con `DEBUG=False`, una inexistente (404) | Se muestran las páginas de error con el diseño del portal y un botón "Volver al inicio" | [ ] OK &nbsp; [ ] Falla |

## Registro de ejecución

| Fecha | Ejecutado por | Entorno (navegador/SO) | Observaciones |
|-------|----------------|--------------------------|----------------|
|       |                |                          |                |
