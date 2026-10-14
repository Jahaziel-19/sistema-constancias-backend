"""
Configuración del backend para desplegar en Render.

Diferencias con los otros entornos:

- Variables sin prefijo (nombres estándar, iguales que en desarrollo).
- Base de datos vía ``DATABASE_URL`` (Render la inyecta automáticamente al
  conectar un PostgreSQL); las variables ``DB_*`` funcionan como respaldo.
- ``ALLOWED_HOSTS`` incluye ``RENDER_EXTERNAL_HOSTNAME`` de forma automática.
- Archivos estáticos con WhiteNoise (``STATIC_ROOT`` + ``collectstatic``).
- Media en Cloudinary (``DEFAULT_FILE_STORAGE``). ``MEDIA_ROOT`` se mantiene
  local solo para que el pipeline de PDF lea los logos (se copian a
  ``media/logos/`` en cada arranque en ``start.sh``); los archivos subidos
  (fotos, firmas, documentos) se almacenan en Cloudinary.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(f"Variable de entorno requerida no configurada: {name}")
    return value


SECRET_KEY = _env("DJANGO_SECRET_KEY", required=True)
DEBUG = _env("DJANGO_DEBUG", "false").strip().lower() in {"1", "true", "yes", "y", "on"}

ALLOWED_HOSTS = [h.strip() for h in _env("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
_render_hostname = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _render_hostname and _render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_render_hostname)

DOCUMENT_TEMPLATES_DIR = Path(os.environ.get("DOCUMENT_TEMPLATES_DIR", BASE_DIR / "document_templates"))
DJANGO_TEMPLATES_DIR = Path(os.environ.get("DJANGO_TEMPLATES_DIR", BASE_DIR / "Plantillas propuestas"))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'storages',
    'cloudinary',
    'uh_core',
    'uh_academico',
    'uh_documentos',
    'uh_auditoria',
    'uh_usuarios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [DJANGO_TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Base de datos: DATABASE_URL (Render) con respaldo de variables DB_*

_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=60,
            conn_health_checks=True,
        ),
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': _env("DB_ENGINE", "django.db.backends.postgresql"),
            'NAME': _env("DB_NAME", required=True),
            'USER': _env("DB_USER", required=True),
            'PASSWORD': _env("DB_PASSWORD", ""),
            'HOST': _env("DB_HOST", required=True),
            'PORT': _env("DB_PORT", "5432"),
            'CONN_MAX_AGE': 60,
            'OPTIONS': {
                'connect_timeout': 10,
            },
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True


# Archivos estáticos (WhiteNoise los sirve desde STATIC_ROOT)

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'logos']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media: los archivos subidos (fotos, firmas, documentos) van a Cloudinary.
# MEDIA_ROOT se mantiene local solo para que el pipeline de PDF lea los logos
# copiados en media/logos/ por start.sh.
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': _env("CLOUDINARY_CLOUD_NAME", required=True),
    'API_KEY': _env("CLOUDINARY_API_KEY", required=True),
    'API_SECRET': _env("CLOUDINARY_API_SECRET", required=True),
}

from urllib.parse import urlparse


def _sanitize_cors_origin(origin: str) -> str:
    """Normaliza un origen CORS a esquema + host (sin path ni barra final).

    django-cors-headers rechaza orígenes con path (ej: ...vercel.app/).
    """
    origin = origin.strip()
    if not origin:
        return ""
    parsed = urlparse(origin if "://" in origin else f"//{origin}")
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return origin.rstrip("/")


_raw_cors = _env("CORS_ALLOWED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = [
    o for o in (_sanitize_cors_origin(x) for x in _raw_cors.split(",")) if o
]
CORS_ALLOW_ALL_ORIGINS = DEBUG
CSRF_TRUSTED_ORIGINS = [o for o in CORS_ALLOWED_ORIGINS if o.startswith("https://")]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # En producción: solo JSON. El DRF browsable API (formularios HTML) queda
    # deshabilitado para no exponer la interfaz de exploración de la API.
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

SIMPLE_JWT = {
    "TOKEN_OBTAIN_SERIALIZER": "uh_usuarios.serializers_projection.}",
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'