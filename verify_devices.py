import requests

BASE = "http://192.168.29.244:8000"

print("DEVICE REGISTRY TEST")
print("=" * 60)

response = requests.get(
    BASE + "/api/v1/edge/devices",
    timeout=10
)

print("STATUS:", response.status_code)
print("RESPONSE:")
print(response.text)
