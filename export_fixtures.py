import sqlite3
import json

conn = sqlite3.connect("db.sqlite3")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

app_map = {
    "alumnos": "uh_academico",
    "autoridades": "uh_core",
    "carreras": "uh_core",
    "catalogo_materias": "uh_academico",
    "categorias_documento": "uh_documentos",
    "ciclos_escolares": "uh_academico",
    "configuracion_institucional": "uh_core",
    "datos_contacto": "uh_core",
    "destinatarios_polimorficos": "uh_core",
    "documentos_emitidos": "uh_documentos",
    "domicilios": "uh_core",
    "estatus_academico": "uh_core",
    "externos": "uh_core",
    "inscripciones_periodo": "uh_academico",
    "perfiles_usuario": "uh_usuarios",
    "periodos_academicos": "uh_academico",
    "planes_estudio": "uh_academico",
    "plantel_autoridades": "uh_core",
    "planteles": "uh_core",
    "roles": "uh_usuarios",
    "tipos_documento": "uh_documentos",
    "tipos_documento_categorias": "uh_documentos",
    "tipos_periodo": "uh_academico",
    "trayectoria_academica": "uh_academico",
    "calificaciones_detalle": "uh_academico",
    "auditoria_sistema": "uh_auditoria",
    "auth_group": "auth",
    "auth_group_permissions": "auth",
    "auth_permission": "auth",
    "auth_user": "auth",
    "auth_user_groups": "auth",
    "auth_user_user_permissions": "auth",
    "django_content_type": "contenttypes",
}

django_tables = {"sqlite_sequence", "django_admin_log", "django_migrations", "django_session"}

fixtures = []
seen_pks = {}

for table in tables:
    if table in django_tables:
        continue
    if table not in app_map:
        continue

    app_label = app_map[table]
    cursor.execute(f"SELECT * FROM [{table}]")
    rows = cursor.fetchall()

    for row in rows:
        row_dict = dict(row)
        pk = row_dict.get("id")
        if pk is None:
            continue
        model_key = f"{app_label}.{table}"
        pk_key = f"{model_key}:{pk}"

        if pk_key in seen_pks:
            continue
        seen_pks[pk_key] = True

        fixture_entry = {
            "model": model_key,
            "pk": pk,
            "fields": {},
        }

        for col, val in row_dict.items():
            if isinstance(val, bytes):
                fixture_entry["fields"][col] = val.hex()
            else:
                fixture_entry["fields"][col] = val

        fixtures.append(fixture_entry)

conn.close()

with open("fixtures/dev_data.json", "w", encoding="utf-8") as f:
    json.dump(fixtures, f, ensure_ascii=False, indent=2)

print(f"Wrote {len(fixtures)} records to fixtures/dev_data.json")
