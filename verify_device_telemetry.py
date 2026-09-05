import requests

BASE = "http://192.168.29.244:8000"
DEVICE = "edge_node_telemetry_001"

url = f"{BASE}/api/v1/edge/devices/{DEVICE}/telemetry"

print("DEVICE TELEMETRY TEST")
print("=" * 60)
print("DEVICE:", DEVICE)
print("URL:", url)
print()

response = requests.get(
    url,
    timeout=10
)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(response.text)
