# Backend - Sistema de Constancias Universidad Hispana

API REST en Django/DRF para la generación y gestión de documentos académicos (constancias, kardex, diplomas, etc.).

## Requisitos

- Python 3.13+
- PostgreSQL (opcional para desarrollo local; por defecto usa SQLite)

## Entornos

| Entorno | Descripción | Settings | Variables |
|---|---|---|---|
| Desarrollo | Local, SQLite, storage local | `config.settings` | `backend/.env` |
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

Ver [DEPLOY.md](../DEPLOY.md) del repositorio monorepo original para instrucciones detalladas.
