# CLAUDE.md

Guía de referencia para trabajar en TicketFlow. Léela antes de proponer o
implementar cambios.

## Objetivo de TicketFlow

TicketFlow es un sistema de gestión de tickets internos para una
organización. Permite que los empleados reporten incidencias/solicitudes,
que se asignen a responsables por área, que se notifique a las partes
involucradas y que se generen reportes básicos de seguimiento. Es un
proyecto académico pensado para desarrollarse en 13 semanas.

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

## Estructura de módulos (apps de Django)

Ubicadas en la raíz del proyecto, junto al paquete de configuración
`ticketflow/`:

- `users/` — usuarios y autenticación. Modelo de usuario personalizado
  (`users.User`, `AUTH_USER_MODEL`) con roles (`employee`,
  `area_manager`, `admin`, `management`) y relación con `Area`.
- `tickets/` — ciclo de vida de los tickets (creación, estados,
  comentarios). Estructura preparada, sin lógica funcional todavía.
- `assignment/` — asignación de tickets a responsables/áreas.
  Estructura preparada, sin lógica funcional todavía.
- `notifications/` — notificaciones a usuarios sobre eventos de
  tickets. Estructura preparada, sin lógica funcional todavía.
- `reports/` — reportes y métricas de seguimiento. Estructura
  preparada, sin lógica funcional todavía.
- `administration/` — configuración organizacional (por ahora solo el
  modelo `Area`) y futuras pantallas de administración.

Cada módulo debe mantener sus propios `models.py`, `views.py`,
`urls.py`, `admin.py` y `migrations/`. Las urls de cada app se incluyen
desde `ticketflow/urls.py` únicamente cuando el módulo tenga
funcionalidad real que exponer.

## Reglas principales del sistema

- No se implementa lógica de negocio de un módulo antes de que se
  autorice explícitamente ese bloque de trabajo.
- Los roles de usuario (`employee`, `area_manager`, `admin`,
  `management`) se definen en `users.User.Role`, pero los permisos
  funcionales asociados a cada rol se implementan progresivamente,
  módulo por módulo.
- Todo usuario puede estar asociado a un `Area` (`users.User.area`),
  relación que módulos futuros (asignación, reportes) usarán para
  filtrar/enrutar tickets.
- La autenticación es siempre por sesión de Django. No se agregan
  mecanismos de autenticación alternativos sin decisión explícita.
- PostgreSQL es la única base de datos soportada, en todos los
  entornos. La configuración de conexión sale siempre de variables de
  entorno (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`).
- No se agregan dependencias, frameworks o infraestructuras
  (microservicios, colas, cachés, SPA, etc.) que no sean necesarias
  para el alcance académico del proyecto.

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
6. (Opcional) Crear un superusuario: `python manage.py createsuperuser`
7. Levantar el servidor de desarrollo: `python manage.py runserver`
8. Abrir `http://127.0.0.1:8000/` en el navegador.

## Cómo ejecutar las pruebas

```
python manage.py test
```

Cada módulo debe incluir sus propias pruebas en `<app>/tests.py` (o un
paquete `tests/`) a medida que se implementa su funcionalidad. En este
primer bloque no existen pruebas todavía porque no hay lógica de
negocio que probar.

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
