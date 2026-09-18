# TicketFlow

Sistema de gestión de tickets internos (proyecto académico). Permite
reportar incidencias/solicitudes, asignarlas a responsables por área,
notificar a las partes involucradas y generar reportes básicos de
seguimiento.

> Este repositorio se está desarrollando por bloques. Este primer
> bloque construye únicamente la base del proyecto: configuración,
> PostgreSQL y el modelo de usuario con roles. La lógica de tickets,
> asignación, notificaciones y reportes se implementará en bloques
> posteriores.

## Tecnologías

- Python + Django
- PostgreSQL
- Django Templates + Bootstrap 5 + JavaScript básico
- Autenticación mediante sesiones nativas de Django
- Arquitectura monolítica modular (una sola app Django dividida en
  módulos: `users`, `tickets`, `assignment`, `notifications`,
  `reports`, `administration`)

Ver [`CLAUDE.md`](./CLAUDE.md) para el detalle de la arquitectura y las
reglas del proyecto.

## Requisitos

- Python 3.11+ (probado con 3.12)
- PostgreSQL 14+ (probado con 17) instalado y en ejecución localmente
- pip

## Instalación

```bash
# 1. Crear entorno virtual
py -m venv venv

# 2. Activar entorno virtual (PowerShell)
.\venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
```

## Configuración de variables de entorno

1. Copiar `.env.example` a `.env`:

   ```bash
   cp .env.example .env
   ```

2. Editar `.env` con los valores reales de tu entorno local. Nunca se
   sube este archivo al repositorio (está en `.gitignore`).

   | Variable        | Descripción                                   |
   |-----------------|------------------------------------------------|
   | `SECRET_KEY`    | Clave secreta de Django (usar una aleatoria)   |
   | `DEBUG`         | `True` en desarrollo, `False` en producción    |
   | `ALLOWED_HOSTS` | Hosts permitidos, separados por comas          |
   | `DB_NAME`       | Nombre de la base de datos PostgreSQL          |
   | `DB_USER`       | Usuario de PostgreSQL                          |
   | `DB_PASSWORD`   | Contraseña del usuario de PostgreSQL           |
   | `DB_HOST`       | Host de PostgreSQL (ej. `localhost`)           |
   | `DB_PORT`       | Puerto de PostgreSQL (ej. `5432`)              |

3. Crear la base de datos y el usuario en PostgreSQL (deben coincidir
   con los valores de `.env`), por ejemplo desde `psql`:

   ```sql
   CREATE ROLE ticketflow_user WITH LOGIN PASSWORD 'tu_password' CREATEDB;
   CREATE DATABASE ticketflow_db OWNER ticketflow_user;
   ```

## Ejecución local

```bash
# Aplicar migraciones
python manage.py migrate

# (Opcional) Crear un superusuario para acceder a /admin/
python manage.py createsuperuser

# Levantar el servidor de desarrollo
python manage.py runserver
```

Luego abrir `http://127.0.0.1:8000/` en el navegador.

## Pruebas

```bash
python manage.py test
```
