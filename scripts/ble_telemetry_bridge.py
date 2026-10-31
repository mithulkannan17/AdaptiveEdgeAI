"""
AuraForest Sentinel — Bluetooth Low Energy (BLE) Telemetry Bridge
==================================================================

Connects your laptop/PC to the ESP32-S3 over Bluetooth Low Energy,
receives real-time sensor telemetry packets over the Nordic UART Service (NUS),
and forwards the JSON payload directly into the local FastAPI backend.

Requirements:
    pip install bleak requests

Usage:
    python scripts/ble_telemetry_bridge.py
    python scripts/ble_telemetry_bridge.py --backend http://127.0.0.1:8000
"""

import asyncio
import json
import sys
import argparse
from typing import Optional

try:
    from bleak import BleakScanner, BleakClient
except ImportError:
    print("\n[!] 'bleak' is required for Bluetooth Low Energy communication.")
    print("    Install it via: pip install bleak requests\n")
    sys.exit(1)

import requests

DEVICE_NAME = "AuraForest-Sentinel-BLE"
NUS_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
NUS_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"

buffer = ""


def handle_telemetry_json(json_str: str, backend_url: str):
    """Parse JSON and forward to FastAPI backend."""
    try:
        data = json.loads(json_str)
        dev_id = data.get("device_id", "ESP32-S3")
        ts = data.get("timestamp", 0)
        status = data.get("device_status", {})
        temp = status.get("temperature", 0)
        hum = status.get("humidity", 0)
        batt = status.get("battery_percent", 0)
        gas_mq2 = status.get("mq2_adc_voltage", 0)
        gas_mq135 = status.get("mq135_adc_voltage", 0)
        vib = "⚠️ VIBRATION" if status.get("vibration_detected") else "Nominal"

        print(f"\n[BLE RX] 📡 Packet from {dev_id} @ {ts:.1f}s:")
        print(f"         🌡️ Temp: {temp}°C | 💧 Hum: {hum}% | ⚡ Batt: {batt:.1f}%")
        print(f"         📳 Sensor: {vib} | 🧪 Gas MQ2: {gas_mq2:.2f}V | MQ135: {gas_mq135:.2f}V")

        # Forward to FastAPI backend
        endpoint = f"{backend_url.rstrip('/')}/api/v1/edge/telemetry"
        headers = {
            "Content-Type": "application/json",
            "X-Device-Token": "aura_sentry_sec_key_99",
            "X-API-Key": "aura_sentry_sec_key_99",
        }
        resp = requests.post(endpoint, json=data, headers=headers, timeout=5.0)
        if resp.status_code == 200:
            print(f"         ✅ Forwarded to Backend -> HTTP 200 OK (Dashboard Updated)")
        else:
            print(f"         ⚠️ Backend response: HTTP {resp.status_code}")
    except json.JSONDecodeError:
        print(f"[BLE RX] Raw Data: {json_str[:80]}...")
    except requests.RequestException as e:
        print(f"         ❌ Backend forward failed: {e}")


def notification_handler(sender, data: bytearray, backend_url: str):
    global buffer
    text = data.decode("utf-8", errors="ignore")
    buffer += text
    if "\n" in buffer:
        parts = buffer.split("\n")
        complete_msg = parts[0].strip()
        buffer = "\n".join(parts[1:])
        if complete_msg:
            handle_telemetry_json(complete_msg, backend_url)


async def run_bridge(backend_url: str):
    print("=" * 60)
    print(" AURAFOREST SENTINEL — BLUETOOTH BLE TELEMETRY BRIDGE")
    print("=" * 60)
    print(f"Scanning for '{DEVICE_NAME}'...")

    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and DEVICE_NAME.lower() in d.name.lower(),
        timeout=15.0,
    )

    if not device:
        print(f"❌ '{DEVICE_NAME}' not found.")
        print("   Make sure the ESP32 is powered on and within Bluetooth range (~10m).")
        return

    print(f"✅ Found {device.name} [{device.address}]. Connecting...")

    async with BleakClient(device) as client:
        print(f"🟢 Connected to {device.name}!")
        print(f"📡 Subscribing to Telemetry Stream...")
        print(f"🎯 Target Backend: {backend_url}")
        print("=" * 60)
        print("Listening for live sensor packets (Press Ctrl+C to stop)...")

        await client.start_notify(
            NUS_TX_CHAR_UUID,
            lambda sender, data: notification_handler(sender, data, backend_url),
        )

        while client.is_connected:
            await asyncio.sleep(1.0)


def main():
    parser = argparse.ArgumentParser(description="AuraForest Bluetooth BLE Bridge")
    parser.add_argument(
        "--backend",
        default="http://localhost:8000",
        help="FastAPI Backend base URL (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(run_bridge(args.backend))
    except KeyboardInterrupt:
        print("\n[!] Bridge stopped by user.")


if __name__ == "__main__":
    main()
