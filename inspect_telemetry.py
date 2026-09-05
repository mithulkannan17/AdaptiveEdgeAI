import requests
import json

BASE = "http://192.168.29.244:8000"
DEVICE = "edge_node_telemetry_001"

url = f"{BASE}/api/v1/edge/devices/{DEVICE}/telemetry"

response = requests.get(url, timeout=10)

print("STATUS:", response.status_code)

data = response.json()

print()
print("TOP-LEVEL FIELDS:")
for key in data:
    print(" -", key)

print()
print("HARDWARE HEALTH:")
print(json.dumps(
    data.get("hardware_health"),
    indent=2
))

print()
print("DEVICE STATUS:")
print(json.dumps(
    data.get("device_status"),
    indent=2
))

print()
print("LOCATION:")
print(json.dumps(
    data.get("location"),
    indent=2
))
