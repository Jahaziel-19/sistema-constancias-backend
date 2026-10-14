# Backend - Sistema de Constancias Universidad Hispana

API REST en Django/DRF para la generación y gestión de documentos académicos (constancias, kardex, diplomas, etc.).

## Requisitos

- Python 3.13+
- PostgreSQL (opcional para desarrollo local; por defecto usa SQLite)

## Entornos

| Entorno | Descripción | Settings | Variables |
|---|---|---|---|
| Desarrollo | Local, SQLite, storage local | `config.settings` | `backend/.env` |
| Render | Render + PostgreSQL + disco persistente | `config.settings_render` | Estándar + `DATABASE_URL` |
| Demo | Railway + Neon + Cloudinary | `config.settings_demo` | Prefijo `DEMO_` |

## Inicio rápido (desarrollo)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py importar_fixtures_csv
.venv\Scripts\python manage.py runserver 0.0.0.0:8000
```

## Endpoints principales

- JWT: `POST /api/auth/token/`, `POST /api/auth/refresh/`
- Verificación pública: `GET /api/public/documentos/{folio}/`
- API: `GET/POST /api/documentos/` y catálogos bajo `/api/`

## Despliegue

- **Render**: Web Service manual con Root Directory `backend`, Build Command
  `pip install -r requirements.txt`, Start Command
  `bash start.sh config.settings_render`. Media en Cloudinary; base de datos
  PostgreSQL (Render inyecta `DATABASE_URL`). Ver [DEPLOY.md](../DEPLOY.md).
- Ver [DEPLOY.md](../DEPLOY.md) del repositorio monorepo original para instrucciones detalladas.
