import json
import os

path = "fixtures/dev_data.json"
size = os.path.getsize(path)
print(f"File size: {size} bytes ({size/1024:.1f} KB)")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total records: {len(data)}")

apps = {}
for r in data:
    app = r["model"].split(".")[0]
    apps[app] = apps.get(app, 0) + 1

print("\nRecords per app:")
for app in sorted(apps):
    print(f"  {app}: {apps[app]}")

# Check first record structure
first = data[0]
print(f"\nFirst record:")
print(f"  Model: {first['model']}")
print(f"  PK: {first['pk']}")
print(f"  Fields: {list(first['fields'].keys())}")

# Check for natural keys
has_natural = any("pk" not in r or isinstance(r.get("pk"), str) for r in data[:50])
print(f"\nHas natural keys in first 50: {has_natural}")

# Check specific models for natural keys
for check_model in ["auth.user", "auth.permission", "contenttypes.contenttype"]:
    found = [r for r in data if r["model"] == check_model][:2]
    for r in found:
        print(f"  {check_model} pk={r['pk']} type={type(r['pk']).__name__}")
