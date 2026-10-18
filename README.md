# TicketFlow

TicketFlow es un sistema de gestión de tickets internos para una
organización. Permite que los empleados reporten incidencias o
solicitudes, que esas solicitudes se asignen automáticamente a un
responsable de la Área correspondiente, que las partes involucradas
reciban notificaciones de cada evento relevante, y que la organización
cuente con reportes básicos de seguimiento (volumen, estados, tiempos
de resolución) para tomar decisiones.

Es un proyecto académico desarrollado de forma incremental en 11
bloques de trabajo, ya cerrados. Este documento describe el estado
**final** del proyecto, no un estado intermedio.

## Alcance formal aprobado

Según el Enunciado del Alcance del proyecto (25/08/2026):

### Requisitos funcionales

| Requisito | Importancia |
|---|---|
| Creación de tickets por parte de los empleados, con descripción y categoría (TI, Mantenimiento, RRHH) | Alta |
| Asignación automática (por reglas) o manual de tickets al área correspondiente | Alta |
| Seguimiento del estado de la solicitud (pendiente → en proceso → resuelto) | Alta |
| Notificaciones automáticas ante cambios de estado del ticket | Media |
| Dashboard de reportes: cantidad de solicitudes por área y tiempo promedio de resolución | Alta |
| Autenticación de usuarios con roles diferenciados | Alta |
| Historial de solicitudes por empleado | Media |
| Panel de administración de usuarios, áreas y categorías | Media |

### Criterios de aceptación formales

1. El sistema permite crear, categorizar y asignar tickets sin errores.
2. El estado de cada solicitud se actualiza correctamente y es visible
   para el empleado en tiempo real.
3. El sistema envía notificaciones ante cada cambio de estado.
4. El dashboard de reportes refleja datos reales y actualizados por
   área.
5. El sistema ha sido probado y aprobado por el docente/patrocinador
   antes de la entrega final.

Ver [`docs/casos-de-uso.md`](./docs/casos-de-uso.md) para el detalle de
cómo se verificó cada criterio contra el código y los tests, y su
estado real (el criterio 5 depende de la sustentación, no es algo que
el equipo de desarrollo pueda autoevaluar).

### Exclusiones formales

Fuera de alcance, por definición del proyecto: integración con nómina,
ERP u otros sistemas externos; aplicación móvil nativa; facturación o
gestión financiera; soporte multiempresa; chat en vivo entre empleado y
encargado. Ninguna de estas cinco exclusiones está implementada en el
sistema.

## Funcionalidades adicionales implementadas

Además del alcance formal, se implementaron tres mejoras de apoyo,
ninguna de las cuales reemplaza ni modifica las exclusiones formales:

- **Comentarios en tickets** (Bloque 9): notas asíncronas dentro de un
  ticket, para trazabilidad y comunicación contextual. No son un chat
  en vivo (sin mensajería en tiempo real) y no forman parte del alcance
  formal.
- **Recuperación de contraseña** (Bloque 9): apoyo a la autenticación,
  para cuando un usuario no puede iniciar sesión.
- **Paginación y `seed_demo`**: mejoras de soporte (usabilidad de
  listas largas, datos de prueba), no funcionalidades del alcance.

Detalle completo en [`docs/casos-de-uso.md`](./docs/casos-de-uso.md).

## Qué problema resuelve

Antes de TicketFlow, reportar un problema interno (una impresora rota,
una solicitud de RR.HH., un pedido a Mantenimiento) no tenía un canal
único: no había forma sistemática de saber quién era responsable de
atenderlo, en qué estado estaba, ni cuánto tardaba en resolverse.
TicketFlow le da a la organización:

- Un único punto de entrada para que cualquier empleado reporte una
  incidencia o solicitud, clasificada por categoría y enrutada
  automáticamente al área correspondiente.
- Asignación automática (Round Robin) del ticket a un responsable del
  área, sin intervención manual, más la posibilidad de reasignar
  manualmente cuando haga falta.
- Visibilidad del estado del ticket (`Pendiente` → `En proceso` →
  `Resuelto`) y de su historial completo, tanto para quien lo reportó
  como para quien lo atiende.
- Notificaciones internas automáticas ante cada evento relevante
  (asignación, reasignación, cambio de estado — y, como funcionalidad
  adicional, nuevo comentario).
- Métricas agregadas (por estado, por área, tiempo promedio de
  resolución) para que Administración y Gerencia hagan seguimiento sin
  necesidad de revisar ticket por ticket.

## Stack tecnológico

- **Backend:** Python 3.12 + Django 5.0 (LTS-compatible).
- **Base de datos:** PostgreSQL. No se usa SQLite en ningún entorno, ni
  siquiera en desarrollo o en los tests.
- **Frontend:** Django Templates + Bootstrap 5.3.3 (vía CDN) + JavaScript
  básico. Sin React ni ningún framework SPA. Sistema visual basado en
  los diseños de Google Stitch (guía en `docs/diseno-referencia.md`): CSS propio en
  `static/css/ticketflow.css` sobre las variables de Bootstrap,
  tipografía Inter e iconos Material Symbols (Google Fonts).
- **Autenticación:** sesiones nativas de Django
  (`django.contrib.auth` + `django.contrib.sessions`). Sin JWT ni
  autenticación por token.
- **Email:** únicamente para la recuperación de contraseña (vistas
  nativas de `django.contrib.auth`). Las notificaciones de tickets son
  siempre internas (dentro de la aplicación), nunca por correo.
- **Configuración:** variables de entorno vía `python-dotenv` y un
  archivo `.env` local no versionado. Sin credenciales ni secretos
  hardcodeados en el código.
- **Arquitectura:** monolito modular — un único proyecto Django
  dividido en apps con responsabilidades claras, sin microservicios ni
  una API independiente.

Ver [`docs/documentacion-tecnica.md`](./docs/documentacion-tecnica.md)
para el detalle de arquitectura, modelo de datos, permisos y
decisiones técnicas, y [`CLAUDE.md`](./CLAUDE.md) para las reglas y
restricciones del proyecto.

## Estructura de apps

El proyecto es un único paquete Django (`ticketflow/`) con seis apps,
cada una con sus propios `models.py`, `views.py`, `urls.py`,
`forms.py` (donde aplica), `admin.py` y `migrations/`:

| App | Responsabilidad |
|---|---|
| `users` | Modelo de usuario personalizado (`users.User`) con roles (`employee`, `area_manager`, `admin`, `management`) y relación con `Area`. Login/logout y recuperación de contraseña. |
| `administration` | Gestión organizacional: Áreas, Categorías (siempre asociadas a un Área) y administración de usuarios (alta, edición de rol/área/estado). Acceso restringido a `admin`. |
| `tickets` | Ciclo de vida del ticket: creación, máquina de estados (`PENDING` → `IN_PROCESS` → `RESOLVED`, terminal), historial de estados y comentarios append-only. |
| `assignment` | Asignación automática por Round Robin y reasignación manual, con su propio historial append-only. |
| `notifications` | Notificaciones internas (bandeja de entrada por usuario) generadas por eventos de `tickets`/`assignment`. |
| `reports` | Dashboard con métricas agregadas por rol (conteos por estado/área, tiempo promedio de resolución, tickets recientes). |

Cada app expone sus urls en `ticketflow/urls.py` únicamente si tiene
funcionalidad real que exponer (ninguna app "vacía" queda registrada).

## Requisitos previos

- Python 3.12 (el proyecto se desarrolló y probó con esta versión;
  cualquier 3.11+ debería funcionar).
- PostgreSQL 14 o superior (probado con PostgreSQL 17), instalado y en
  ejecución localmente.
- `pip` y `venv` (incluidos con Python).

Ver [`docs/instalacion.md`](./docs/instalacion.md) para una guía de
instalación completa, paso a paso y con solución de problemas
comunes — pensada para levantar el proyecto sin ayuda del equipo.

## Instalación rápida

```bash
# 1. Crear y activar un entorno virtual
py -m venv venv
.\venv\Scripts\Activate.ps1        # Windows PowerShell

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
copy .env.example .env             # Windows
# cp .env.example .env             # macOS/Linux
# Editar .env con los valores reales de tu entorno local (ver abajo).

# 4. Crear la base de datos en PostgreSQL (deben coincidir con .env)
#    Ejemplo desde psql:
#    CREATE ROLE ticketflow_user WITH LOGIN PASSWORD 'tu_password' CREATEDB;
#    CREATE DATABASE ticketflow_db OWNER ticketflow_user;

# 5. Aplicar migraciones
python manage.py migrate

# 6. Crear el primer usuario administrador (ver sección siguiente)
python manage.py createsuperuser

# 7. Levantar el servidor de desarrollo
python manage.py runserver
```

Luego abrir `http://127.0.0.1:8000/` en el navegador.

## Configuración de variables de entorno

Todas las variables se definen en `.env` (nunca versionado; usar
`.env.example` como plantilla, sin valores reales). El listado completo
con su significado está en
[`docs/instalacion.md`](./docs/instalacion.md#archivo-env); resumen:

| Variable | Para qué es |
|---|---|
| `SECRET_KEY` | Clave secreta de Django. Generar una aleatoria propia, nunca reutilizar la del repositorio. |
| `DEBUG` | `True` en desarrollo, `False` en producción. |
| `ALLOWED_HOSTS` | Hosts permitidos, separados por comas. |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. |
| `DB_SSLMODE` | Modo SSL de la conexión: `prefer` (por defecto) para local, `require` para Supabase. |
| `EMAIL_BACKEND` y demás `EMAIL_*` | Envío de los correos de recuperación de contraseña (por defecto, backend de consola: los imprime en la terminal en vez de enviarlos). |
| `DEFAULT_FROM_EMAIL` | Remitente de esos correos. |

## Usar Supabase (opcional)

La instalación principal sigue siendo PostgreSQL local. Si se prefiere
un PostgreSQL gestionado, el proyecto funciona con Supabase cambiando
solo `.env`:

1. Respaldar la configuración local: `Copy-Item .env .env.local`
   (PowerShell). `.env.local` está en `.gitignore`.
2. Crear un proyecto en Supabase → botón **Connect** → pestaña
   **Direct** → método **Session pooler** (funciona por IPv4).
3. Copiar host, puerto, usuario y base de datos al `.env` (por ejemplo
   `DB_HOST=aws-0-<región>.pooler.supabase.com`,
   `DB_USER=postgres.<id-de-tu-proyecto>`, `DB_NAME=postgres`,
   `DB_PORT=5432`), junto con la contraseña, y poner
   `DB_SSLMODE=require`.
4. `python manage.py migrate` y crear el primer Admin como en local.

Para volver a la base local: `Copy-Item .env.local .env`. Los tests se
corren contra la base local, no contra Supabase. El plan gratuito pausa
el proyecto tras una semana sin uso. Pasos completos en
[`docs/instalacion.md`](./docs/instalacion.md#13-usar-supabase-opcional).

## Cómo crear el primer usuario administrador

El primer usuario del sistema se crea con el comando nativo de Django,
**no** desde la interfaz (todavía no hay ningún usuario que pueda
entrar a `/administration/` para crear a los demás):

```bash
python manage.py createsuperuser
```

Va a pedir usuario, email (opcional) y contraseña. Este comando crea el
usuario con `role=admin` automáticamente (ver
`users.TicketFlowUserManager`), y además con `is_staff=True` /
`is_superuser=True`, por lo que también puede entrar al Django Admin
(`/admin/`). Con ese usuario ya se puede iniciar sesión en la
aplicación y, desde `Administración → Usuarios`, crear el resto de las
cuentas (empleados, encargados de área, otros administradores,
gerencia) sin volver a usar la consola.

Para cargar datos de ejemplo completos (útiles para probar el sistema
o para una demostración) ver
[`docs/demostracion.md`](./docs/demostracion.md), que documenta el
comando `python manage.py seed_demo` y sus credenciales.

## Cómo correr el servidor

```bash
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/`. La sesión se mantiene mediante cookies
de sesión nativas de Django (sin tokens).

## Cómo correr los tests

```bash
python manage.py test
```

El proyecto tiene 300 tests automatizados repartidos en cada app
(`<app>/tests.py`), cubriendo modelos, permisos, la máquina de
estados, Round Robin, notificaciones, reportes, paginación y un test
de aceptación end-to-end del flujo completo de un ticket. Además:

```bash
python manage.py check                          # chequeo de configuración
python manage.py makemigrations --check --dry-run  # confirma que no faltan migraciones
```

Ver [`docs/pruebas-manuales.md`](./docs/pruebas-manuales.md) para el
checklist de pruebas manuales de interfaz (lo que los tests
automatizados no cubren: aspecto visual, flujo real de clics).

## Estado actual del proyecto

Los 11 bloques de trabajo planificados están cerrados:

1–8. Base del proyecto, usuarios y roles, áreas/categorías, tickets,
   asignación (Round Robin), estados e historial, notificaciones,
   dashboard y reportes, administración y permisos.
9. Comentarios en tickets, recuperación de contraseña, paginación.
10. Batería de pruebas ampliada (permisos, asignación, estados,
    notificaciones, consultas N+1, aceptación end-to-end) y protección
    del último Admin activo del sistema.
11. Documentación y entrega (este bloque): README, documentación
    técnica, guía de instalación, manual de usuario, limitaciones
    conocidas, casos de uso y preparación de la demostración.

El sistema es funcional de punta a punta para los cuatro roles
(`employee`, `area_manager`, `admin`, `management`). Las limitaciones
conocidas y las decisiones de alcance deliberadamente descartadas están
documentadas en
[`docs/limitaciones-conocidas.md`](./docs/limitaciones-conocidas.md) y
en [`docs/casos-de-uso.md`](./docs/casos-de-uso.md) (criterios de
aceptación con su estado real).

## Documentación completa

| Documento | Contenido |
|---|---|
| [`CLAUDE.md`](./CLAUDE.md) | Reglas y restricciones del proyecto (referencia para quien lo siga desarrollando). |
| [`docs/instalacion.md`](./docs/instalacion.md) | Guía de instalación reproducible, paso a paso, con solución de problemas comunes. |
| [`docs/documentacion-tecnica.md`](./docs/documentacion-tecnica.md) | Arquitectura, modelo de datos, permisos, flujos principales y decisiones técnicas. |
| [`docs/limitaciones-conocidas.md`](./docs/limitaciones-conocidas.md) | Limitaciones conocidas, su origen, impacto y por qué no se resolvieron. |
| [`docs/manual-usuario.md`](./docs/manual-usuario.md) | Manual para empleados de la organización, por rol. |
| [`docs/casos-de-uso.md`](./docs/casos-de-uso.md) | Alcance formal aprobado vs. funcionalidades adicionales, con cada criterio de aceptación mapeado a su evidencia. |
| [`docs/pruebas-manuales.md`](./docs/pruebas-manuales.md) | Checklist de pruebas manuales de interfaz. |
| [`docs/demostracion.md`](./docs/demostracion.md) | Datos de prueba (`seed_demo`), guion de demostración y preguntas probables. |
