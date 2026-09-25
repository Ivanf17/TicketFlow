# CLAUDE.md

Guía de referencia para trabajar en TicketFlow. Léela antes de proponer o
implementar cambios.

## Objetivo de TicketFlow

TicketFlow es un sistema de gestión de tickets internos para una
organización. Permite que los empleados reporten incidencias/solicitudes,
que se asignen a responsables por área, que se notifique a las partes
involucradas y que se generen reportes básicos de seguimiento. Es un
proyecto académico pensado para desarrollarse en 13 semanas.

**Estado: proyecto cerrado.** Los 11 bloques de trabajo planificados
están implementados, probados (264 tests) y documentados. Este archivo
describe el estado final del sistema, no un estado intermedio. El
detalle completo de arquitectura, modelo de datos y decisiones técnicas
vive en `docs/documentacion-tecnica.md`; las limitaciones conocidas, en
`docs/limitaciones-conocidas.md`.

## Arquitectura

**Monolítica modular.** Un único proyecto Django dividido en apps
(módulos) con responsabilidades claras, en lugar de microservicios.
Cada módulo puede evolucionar de forma relativamente independiente,
pero se despliega y ejecuta como una sola aplicación.

### Stack tecnológico

- **Backend:** Python + Django (última versión 5.x LTS-compatible).
- **Base de datos:** PostgreSQL. No se usa SQLite en ningún entorno,
  ni siquiera en desarrollo.
- **Frontend:** Django Templates + Bootstrap 5 (vía CDN) + JavaScript
  básico solo cuando sea estrictamente necesario. No se introduce React
  ni ningún framework SPA.
- **Autenticación:** sesiones nativas de Django
  (`django.contrib.auth` + `django.contrib.sessions`). No se usa
  JWT ni autenticación por token salvo que se decida explícitamente
  en el futuro.
- **Gestión de configuración:** variables de entorno vía `python-dotenv`
  y un archivo `.env` local (no versionado). Nunca se hardcodean
  credenciales, claves secretas ni contraseñas en el código.
- **Email:** se usa exclusivamente para la recuperación de contraseña,
  con las vistas nativas de `django.contrib.auth`. Las notificaciones
  de tickets siguen siendo internas únicamente (modelo
  `notifications.Notification`); no se envía correo por eventos de
  tickets. `EMAIL_BACKEND` y el resto de la configuración de correo
  salen de variables de entorno; en desarrollo y en los tests se usa
  por defecto el backend de consola de Django.

## Estructura de módulos (apps de Django)

Ubicadas en la raíz del proyecto, junto al paquete de configuración
`ticketflow/`:

- `users/` — usuarios y autenticación. Modelo de usuario personalizado
  (`users.User`, `AUTH_USER_MODEL`) con roles (`employee`,
  `area_manager`, `admin`, `management`) y relación con `Area`.
- `tickets/` — ciclo de vida de los tickets: creación, estados
  (`PENDING` → `IN_PROCESS` → `RESOLVED`, `RESOLVED` terminal) y
  comentarios append-only (`TicketComment`), visibles bajo la misma
  regla de visibilidad del ticket (`tickets.permissions
  .get_visible_tickets`).
- `assignment/` — asignación automática de tickets por Round Robin
  (`assignment.services.pick_next_area_manager`, cursor persistente por
  área en `AreaAssignmentCursor`) y reasignación manual
  (`assign_ticket`), ambas con historial append-only
  (`TicketAssignmentHistory`).
- `notifications/` — notificaciones internas (bandeja de entrada por
  usuario, modelo `Notification`) generadas por eventos de
  `tickets`/`assignment`: asignación, reasignación, cambio de estado y
  nuevo comentario. Sin email ni push, solo dentro de la aplicación.
- `reports/` — dashboard con métricas agregadas por rol: conteos por
  estado, por área, tiempo promedio de resolución y tickets recientes.
  Management ve solo agregados globales, nunca tickets individuales.
- `administration/` — gestión organizacional: `Area`, `Category`
  (siempre asociada a un `Area`) y administración de usuarios (alta,
  edición de rol/área/estado), todo restringido a `role=admin`. Incluye
  la protección del último Admin activo del sistema (no puede
  desactivarse, cambiar de rol, ni eliminarse si es el único admin
  activo que queda).

Cada módulo mantiene sus propios `models.py`, `views.py`, `urls.py`,
`admin.py` y `migrations/`; la lógica de negocio no trivial vive en un
`services.py` por app (`tickets`, `assignment`, `notifications`,
`administration`), separada de las vistas. Las urls de cada app se
incluyen desde `ticketflow/urls.py` — todas las apps ya tienen
funcionalidad real y están registradas.

## Reglas principales del sistema

- No se implementa lógica de negocio de un módulo antes de que se
  autorice explícitamente ese bloque de trabajo.
- Los roles de usuario (`employee`, `area_manager`, `admin`,
  `management`) se definen en `users.User.Role`. Los permisos
  funcionales de cada rol están completamente implementados y
  verificados server-side (nunca solo ocultos en el template); la
  matriz de permisos real está documentada en
  `docs/documentacion-tecnica.md`.
- Todo usuario puede estar asociado a un `Area` (`users.User.area`);
  `employee` y `area_manager` la requieren siempre (constraint a nivel
  de base de datos), `admin` y `management` pueden no tenerla. Esa
  relación es la que usan `assignment` y `reports` para filtrar/enrutar
  tickets.
- La autenticación es siempre por sesión de Django. No se agregan
  mecanismos de autenticación alternativos sin decisión explícita.
- PostgreSQL es la única base de datos soportada, en todos los
  entornos. La configuración de conexión sale siempre de variables de
  entorno (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).
- No se agregan dependencias, frameworks o infraestructuras
  (microservicios, colas, cachés, SPA, etc.) que no sean necesarias
  para el alcance académico del proyecto.
- `users.User.email` se mantiene deliberadamente opcional y no único
  (sin `unique=True`, sin `blank=False`) para este MVP: alcanza para
  que la recuperación de contraseña nativa de Django funcione, y evita
  una migración de datos para verificar correos duplicados o vacíos en
  usuarios ya existentes. Un usuario sin correo cargado simplemente no
  podrá recuperar su contraseña por este medio, sin que eso se revele
  como un error distinto al de un correo inexistente (el formulario de
  recuperación nunca indica si una cuenta existe o no).
- Las listas principales (tickets, usuarios, notificaciones, áreas,
  categorías) usan paginación simple con `django.core.paginator
  .Paginator` y un tamaño de página compartido (`settings.PAGE_SIZE`).

## Cómo ejecutar el proyecto

1. Crear y activar un entorno virtual:
   - Windows (PowerShell): `py -m venv venv` y luego
     `.\venv\Scripts\Activate.ps1`
2. Instalar dependencias: `pip install -r requirements.txt`
3. Copiar `.env.example` a `.env` y completar los valores reales
   (credenciales de PostgreSQL local, `SECRET_KEY`, etc.).
4. Crear la base de datos y el usuario en PostgreSQL si no existen
   (deben coincidir con los valores puestos en `.env`).
5. Aplicar migraciones: `python manage.py migrate`
6. Crear un superusuario (primer Admin del sistema):
   `python manage.py createsuperuser`
7. Levantar el servidor de desarrollo: `python manage.py runserver`
8. Abrir `http://127.0.0.1:8000/` en el navegador.

Guía completa, con solución de problemas comunes, en
`docs/instalacion.md`. Para cargar datos de ejemplo (útiles para
desarrollo o demostración): `python manage.py seed_demo` (ver
`docs/demostracion.md` para las credenciales que genera).

## Cómo ejecutar las pruebas

```
python manage.py test
```

Cada módulo mantiene sus propias pruebas en `<app>/tests.py`. El
proyecto tiene 264 tests automatizados: modelos, permisos (positivos y
negativos, por rol), la máquina de estados, Round Robin, notificaciones,
paginación, consultas N+1 (`assertNumQueries`) y un test de aceptación
end-to-end que recorre el ciclo de vida completo de un ticket a través
de `self.client` con sesiones reales por rol. El checklist de pruebas
manuales de interfaz (lo que la suite automatizada no cubre) está en
`docs/pruebas-manuales.md`.

## Reglas para futuros cambios

- Antes de tocar código, revisar el estado real del repositorio
  (`git status`, `git diff`) y el entorno (versión de Python,
  disponibilidad de PostgreSQL) para evitar asumir un estado que no
  existe.
- Respetar el alcance del bloque de trabajo autorizado. Si una tarea
  requiere una decisión arquitectónica no definida aquí (por ejemplo,
  cambiar el mecanismo de autenticación, agregar una cola de tareas,
  introducir un framework de frontend), detenerse y preguntar antes
  de implementarla.
- No hardcodear credenciales, claves ni secretos. Toda configuración
  sensible va en variables de entorno, documentada (sin valores reales)
  en `.env.example`.
- Mantener la solución simple: evitar abstracciones, capas o
  dependencias que no estén justificadas por un requisito real del
  proyecto.
- Actualizar este archivo y `README.md` cuando se agregue un módulo,
  se cambie una decisión arquitectónica o se modifique el flujo de
  ejecución/pruebas del proyecto.
