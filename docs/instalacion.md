# Guía de instalación — TicketFlow

Procedimiento completo y reproducible para levantar TicketFlow desde
cero, sin ayuda del equipo de desarrollo. Pensada tanto para un
integrante nuevo del equipo como para quien evalúe el proyecto.

## 1. Versiones requeridas

| Software | Versión usada en el desarrollo | Mínimo razonable |
|---|---|---|
| Python | 3.12.4 | 3.11+ |
| PostgreSQL | 17 | 14+ |
| Django | 5.0.14 (fijado en `requirements.txt`) | — |
| pip | la que trae Python | — |

No se usa SQLite en ningún entorno, ni siquiera para probar rápido:
PostgreSQL es obligatorio desde el primer paso.

## 2. Instalar PostgreSQL

Si no está instalado, descargarlo de
[postgresql.org/download](https://www.postgresql.org/download/) e
instalarlo con sus valores por defecto. Confirmar que el servicio está
corriendo:

- Windows: buscar "Servicios" → verificar que `postgresql-x64-17` (o la
  versión instalada) esté "En ejecución".
- macOS/Linux: `pg_isready` debería responder `accepting connections`.

## 3. Clonar el repositorio y crear el entorno virtual

```bash
git clone <url-del-repositorio>
cd TicketFlow

# Crear el entorno virtual
py -m venv venv          # Windows
# python3 -m venv venv   # macOS/Linux

# Activarlo
.\venv\Scripts\Activate.ps1   # Windows PowerShell
# source venv/bin/activate    # macOS/Linux
```

El prompt de la terminal debería mostrar `(venv)` al principio una vez
activado.

## 4. Instalar dependencias

```bash
pip install -r requirements.txt
```

Instala exactamente: `Django==5.0.14`, `psycopg2-binary==2.9.13`,
`python-dotenv==1.2.3`. Si `psycopg2-binary` falla al instalar en Linux,
suele faltar `libpq-dev` (`sudo apt install libpq-dev` en Debian/Ubuntu)
o las herramientas de compilación de PostgreSQL.

## 5. Crear la base de datos en PostgreSQL

Conectarse con `psql` (usuario `postgres` u otro con permisos de
creación) y ejecutar:

```sql
CREATE ROLE ticketflow_user WITH LOGIN PASSWORD 'elegir_una_password_local' CREATEDB;
CREATE DATABASE ticketflow_db OWNER ticketflow_user;
```

El nombre de rol/base de datos puede ser cualquier otro, siempre que
coincida con lo que se ponga en `.env` en el paso siguiente.

## 6. Archivo `.env`

Copiar la plantilla y completarla con valores reales (nunca se sube al
repositorio: está en `.gitignore`):

```bash
copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
```

Variables y su significado:

| Variable | Significado | Ejemplo/valor por defecto |
|---|---|---|
| `SECRET_KEY` | Clave secreta de Django, usada para firmar sesiones/tokens. Generar una propia y aleatoria; nunca reutilizar una de ejemplo. | *(sin default seguro — generar una)* |
| `DEBUG` | `True` muestra páginas de error detalladas (solo desarrollo); `False` en cualquier entorno expuesto. | `True` en desarrollo |
| `ALLOWED_HOSTS` | Hosts desde los que Django acepta peticiones, separados por comas. | `localhost,127.0.0.1` |
| `DB_NAME` | Nombre de la base de datos PostgreSQL. | `ticketflow_db` |
| `DB_USER` | Usuario de PostgreSQL. | `ticketflow_user` |
| `DB_PASSWORD` | Contraseña de ese usuario. | *(la elegida en el paso 5)* |
| `DB_HOST` | Host del servidor PostgreSQL. | `localhost` |
| `DB_PORT` | Puerto de PostgreSQL. | `5432` |
| `DB_SSLMODE` | Modo SSL de la conexión (`sslmode` de PostgreSQL). `prefer` alcanza para PostgreSQL local; `require` para Supabase (ver sección 13). | `prefer` |
| `EMAIL_BACKEND` | Backend de correo de Django, usado solo para la recuperación de contraseña. | `django.core.mail.backends.console.EmailBackend` (imprime el correo en la terminal en vez de enviarlo — suficiente para desarrollo/demostración) |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | Configuración de un servidor SMTP real. Solo hacen falta si se cambia `EMAIL_BACKEND` a uno real (`smtp.EmailBackend`). | vacíos/no aplican con el backend de consola |
| `DEFAULT_FROM_EMAIL` | Dirección remitente de los correos de recuperación de contraseña. | `no-reply@ticketflow.local` |

Ninguna de estas variables tiene un valor real cargado en
`.env.example`: ese archivo solo documenta qué existe, no las
credenciales reales de nadie.

## 7. Aplicar migraciones

```bash
python manage.py migrate
```

Debería aplicar todas las migraciones de todas las apps sin errores.
Si falla con un error de conexión, revisar que PostgreSQL esté
corriendo y que `DB_*` en `.env` coincidan con lo creado en el paso 5.

## 8. Crear el superusuario (primer Admin)

```bash
python manage.py createsuperuser
```

Pide usuario, email (opcional) y contraseña. Este comando crea la
cuenta con `role=admin` automáticamente y con `is_staff=True` /
`is_superuser=True` (también puede entrar a `/admin/`, el Django Admin
nativo). Con este usuario ya se puede iniciar sesión en la aplicación y
crear el resto de las cuentas desde `Administración → Usuarios`.

## 9. (Opcional) Cargar datos de demostración

```bash
python manage.py seed_demo
```

Carga áreas, categorías, usuarios de los cuatro roles y tickets en
distintos estados con fechas distribuidas, útil para ver el dashboard
con datos reales sin cargar todo a mano. Ver
[`demostracion.md`](./demostracion.md) para las credenciales que genera
y para el detalle de qué datos crea. El comando es seguro de re-ejecutar
sobre la misma base (no duplica los datos de demostración).

## 10. Levantar el servidor

```bash
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` e iniciar sesión con el superusuario
creado en el paso 8 (o con las credenciales de `seed_demo`, si se
ejecutó el paso 9).

## 11. Verificar que quedó bien instalado

Checklist rápido:

- [ ] `python manage.py check` no reporta errores.
- [ ] `python manage.py makemigrations --check --dry-run` responde
      "No changes detected" (si detecta cambios, algo en el modelo no
      coincide con las migraciones aplicadas).
- [ ] `python manage.py test` corre y termina en `OK` (300 tests).
- [ ] `http://127.0.0.1:8000/` carga la página de inicio.
- [ ] Se puede iniciar sesión con el superusuario del paso 8.
- [ ] `http://127.0.0.1:8000/accounts/login/` muestra el formulario de
      login con el link "¿Olvidaste tu contraseña?".

## 12. Problemas comunes

**`django.db.utils.OperationalError: could not connect to server`**
PostgreSQL no está corriendo, o `DB_HOST`/`DB_PORT` en `.env` no
apuntan al servidor correcto. Verificar el servicio de PostgreSQL y
que el puerto (`5432` por defecto) no esté bloqueado.

**`django.db.utils.OperationalError: FATAL: password authentication failed`**
`DB_USER`/`DB_PASSWORD` en `.env` no coinciden con el rol creado en el
paso 5. Revisar ambos valores (son sensibles a mayúsculas).

**`psycopg2` no instala / falla la compilación**
Se usa `psycopg2-binary` (no requiere compilar contra `libpq` en la
mayoría de los sistemas). Si aun así falla, actualizar `pip`
(`pip install --upgrade pip`) antes de reinstalar `requirements.txt`.

**`SECRET_KEY` faltante o `.env` no se está leyendo**
Confirmar que el archivo se llama exactamente `.env` (no
`.env.txt` ni `env`) y está en la raíz del repositorio, junto a
`manage.py`. `ticketflow/settings.py` lo carga con
`load_dotenv(BASE_DIR / ".env")`.

**`No such table` / errores de esquema al iniciar sesión**
Faltan migraciones por aplicar: correr `python manage.py migrate` de
nuevo. Si el error persiste, confirmar que se está apuntando a la base
de datos correcta (`DB_NAME` en `.env`).

**El servidor arranca pero no se ven estilos (Bootstrap) o los iconos aparecen como texto**
Bootstrap se carga vía CDN y la tipografía Inter y los iconos Material
Symbols desde Google Fonts (`templates/base.html`); si no hay conexión
a internet en el entorno donde corre, los estilos no se aplican y los
iconos se ven como su nombre en texto (por ejemplo `inbox`). El sitio
sigue siendo funcional. Los estilos propios
(`static/css/ticketflow.css`) se sirven localmente. No requiere
`collectstatic` para desarrollo local.

**Quiero empezar de cero (borrar todos los datos)**
No hay un comando de "reset" en el proyecto (fuera del alcance
académico). La forma más simple es recrear la base de datos completa:
`DROP DATABASE ticketflow_db;` seguido de los pasos 5, 7 y 8 de esta
guía.

## 13. Usar Supabase (opcional)

La instalación principal sigue siendo PostgreSQL local (pasos 2 a 11).
Supabase es solo una alternativa para tener la base de datos en un
PostgreSQL gestionado; el código no cambia, solo los valores de `.env`.

1. **Respaldar la configuración local** antes de tocar `.env`:

   ```powershell
   Copy-Item .env .env.local
   ```

   `.env.local` está en `.gitignore`, igual que `.env`.

2. **Crear un proyecto** en [supabase.com](https://supabase.com) y
   anotar la contraseña de la base de datos que se elige al crearlo.
3. En el proyecto, botón **Connect** → pestaña **Direct** → método
   **Session pooler**. Se usa el pooler porque la conexión directa solo
   acepta IPv6, y el pooler funciona por IPv4.
4. **Copiar los datos de conexión al `.env`** (los valores de abajo son
   ejemplos genéricos; usar los que muestra tu proyecto):

   ```
   DB_NAME=postgres
   DB_USER=postgres.<id-de-tu-proyecto>
   DB_PASSWORD=<la contraseña de la base de datos>
   DB_HOST=aws-0-<región>.pooler.supabase.com
   DB_PORT=5432
   DB_SSLMODE=require
   ```

5. Aplicar migraciones y crear el primer Admin contra Supabase, igual
   que en local: `python manage.py migrate` y
   `python manage.py createsuperuser` (o `python manage.py seed_demo`
   para datos de ejemplo).

**Volver a la base local:**

```powershell
Copy-Item .env.local .env
```

**Tests:** se corren siempre contra la base local, no contra Supabase.
Antes de `python manage.py test`, volver a la configuración local con
el comando anterior.

**Plan gratuito:** Supabase pausa el proyecto después de una semana sin
uso. Si la conexión empieza a fallar, entrar al panel de Supabase y
reanudar el proyecto.
