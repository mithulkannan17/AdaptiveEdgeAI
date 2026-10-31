/*
  ============================================================
  AURAFOREST / ADAPTIVE EDGE AI
  ESP32-S3 EDGE NODE
  ============================================================

  Hardware:
    ESP32-S3 N16R8

  Sensors:
    DHT11       -> GPIO14
    BH1750      -> I2C GPIO8/9
    MAX17048    -> I2C GPIO8/9
    SW-420      -> GPIO16
    INMP441     -> GPIO4/5/6
    MQ-2        -> GPIO1 (ADC)
    MQ-135      -> GPIO2 (ADC)
    NEO-6M      -> UART GPIO17/18
    MicroSD     -> SPI GPIO10/11/12/13

  LEDs:
    Green       -> GPIO21
    Red         -> GPIO38

  Backend:
    FastAPI

  Telemetry:
    POST /api/v1/edge/telemetry

  Audio inference:
    POST /api/v1/edge/audio

  ============================================================
*/

#include <Arduino.h>

#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <FS.h>

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>
#include <DNSServer.h>

#include <ArduinoJson.h>
#include <DHT.h>
#include <TinyGPSPlus.h>

#include "driver/i2s.h"

// ============================================================
// DEVICE CONFIGURATION
// ============================================================

#define DEVICE_ID "edge_node_telemetry_001"
#define DEVICE_API_KEY "aura_sentry_sec_key_99"

// ============================================================
// WIFI CONFIGURATION
// ============================================================

// Hardcoded fallback credentials (can also be updated via Web Portal at http://192.168.4.1)
const char *WIFI_SSID = "HomeFiber";
const char *WIFI_PASSWORD = "kannan17";

// ============================================================
// BACKEND CONFIGURATION
// ============================================================

// Set USE_CLOUD_BACKEND to 1 to post directly to your deployed Cloud backend (Render/Koyeb)
// Set to 0 to post to your local PC IP (sub-second local network response)
#define USE_CLOUD_BACKEND 1

// Local Station PC IP & Port
const char *LOCAL_SERVER_IP = "10.106.227.65";
const uint16_t LOCAL_SERVER_PORT = 8000;

// Deployed Cloud Backend URL (Render / Koyeb / Railway)
// Replace with your live Render URL once created (e.g. "https://auraforest-backend.onrender.com")
const char *CLOUD_BACKEND_URL = "https://auraforest-backend.onrender.com";

const char *API_PATH =
    "/api/v1/edge/telemetry";

const char *AUDIO_API_PATH =
    "/api/v1/edge/audio";

// ============================================================
// DYNAMIC NVS WIFI & PORTAL CONFIGURATION
// ============================================================
Preferences preferences;
WebServer configServer(80);
DNSServer dnsServer;

String activeWiFiSSID = "HomeFiber";
String activeWiFiPassword = "kannan17";
String activeServerIP = "10.106.227.65";
uint16_t activeServerPort = 8000;
bool wifiPortalActive = false;

String getBaseURL()
{
#if USE_CLOUD_BACKEND
    String base = String(CLOUD_BACKEND_URL);
    while (base.endsWith("/"))
    {
        base.remove(base.length() - 1);
    }
    return base;
#else
    return "http://" + activeServerIP + ":" + String(activeServerPort);
#endif
}

// ============================================================
// DEMO LOCATION FALLBACK
// ============================================================

const double FALLBACK_LATITUDE = 12.2958;
const double FALLBACK_LONGITUDE = 76.6394;
const double FALLBACK_ALTITUDE = 0.0;
const double FALLBACK_ACCURACY = 0.0;

// ============================================================
// GPIO CONFIGURATION
// ============================================================

// I2C
#define PIN_SDA 8
#define PIN_SCL 9

// Microphone
#define I2S_BCLK 4
#define I2S_WS 5
#define I2S_DIN 6

// MicroSD
#define SD_CS 10
#define SD_MOSI 11
#define SD_SCK 12
#define SD_MISO 13

// Vibration
#define VIBRATION_PIN 16

// GPS
#define GPS_RX 17
#define GPS_TX 18

// LEDs
#define GREEN_LED 21
#define RED_LED 38

// DHT11
#define DHT_PIN 14

// MQ gas sensors (analog outputs)
// IMPORTANT: Use a proper voltage divider if the MQ module is powered from 5V
// so that the ESP32-S3 ADC pin never receives more than 3.3V.
#define MQ2_PIN 1
#define MQ135_PIN 2

// ============================================================
// SENSOR ADDRESSES
// ============================================================

#define MAX17048_ADDR 0x36
#define BH1750_ADDR 0x23

#define REG_VCELL 0x02
#define REG_SOC 0x04
#define REG_VERSION 0x08

// ============================================================
// AUDIO CONFIGURATION
// ============================================================

#define AUDIO_SAMPLE_RATE 16000

#define AUDIO_DURATION_SECONDS 5

#define AUDIO_SAMPLE_COUNT \
    (AUDIO_SAMPLE_RATE * AUDIO_DURATION_SECONDS)

#define AUDIO_BUFFER_BYTES \
    (AUDIO_SAMPLE_COUNT * sizeof(int16_t))

// ============================================================
// OBJECTS
// ============================================================

DHT dht(DHT_PIN, DHT11);

TinyGPSPlus gps;

HardwareSerial GPSSerial(1);

SPIClass spiSD(FSPI);

// ============================================================
// I2S CONFIGURATION
// ============================================================

#define I2S_PORT I2S_NUM_0

i2s_config_t i2sConfig = {

    .mode =
        (i2s_mode_t)(I2S_MODE_MASTER |
                     I2S_MODE_RX),

    .sample_rate =
        AUDIO_SAMPLE_RATE,

    .bits_per_sample =
        I2S_BITS_PER_SAMPLE_32BIT, // INMP441 sends 24-bit inside 32-bit slot

    .channel_format =
        I2S_CHANNEL_FMT_ONLY_LEFT,

    .communication_format =
        (i2s_comm_format_t)(I2S_COMM_FORMAT_STAND_I2S), // Philips standard I2S protocol

    .intr_alloc_flags =
        ESP_INTR_FLAG_LEVEL1,

    .dma_buf_count = 4,

    .dma_buf_len = 512, // 512 buffer size prevents DMA under-runs and static pops

    .use_apll = false,

    .tx_desc_auto_clear = false,

    .fixed_mclk = 0};

i2s_pin_config_t i2sPins = {

    .bck_io_num = I2S_BCLK,

    .ws_io_num = I2S_WS,

    .data_out_num =
        I2S_PIN_NO_CHANGE,

    .data_in_num =
        I2S_DIN};

// ============================================================
// RUNTIME VARIABLES
// ============================================================

float temperatureC = NAN;

float humidity = NAN;

float lightLux = 0.0;

float batteryPercent = 0.0;

float batteryVoltage = 0.0;

bool vibrationDetected = false;

int microphoneLevel = 0;

// ---------------- MQ-2 / MQ-135 ----------------
int mq2Raw = 0;
int mq135Raw = 0;
float mq2Voltage = 0.0f;
float mq135Voltage = 0.0f;
bool mq2OK = false;
bool mq135OK = false;

// ---------------- GPS ----------------

bool gpsFix = false;

double latitude = 0.0;

double longitude = 0.0;

double altitude = 0.0;

double gpsAccuracy = 0.0;

uint32_t gpsCharacters = 0;

uint32_t gpsSatellites = 0;

// ---------------- Hardware status ----------------

bool bh1750OK = false;

bool max17048OK = false;

bool dhtOK = false;

bool microphoneOK = false;

bool sdOK = false;

bool wifiOK = false;

bool telemetryBackendOK = false;

bool audioBackendOK = false;

// ============================================================
// LAST AI INFERENCE
// ============================================================

String predictionLabel = "Unknown";

int predictionClassID = -1;

float predictionConfidence = 0.0;

float predictionInferenceTimeMs = 0.0;

String predictionRiskLevel = "UNKNOWN";

String predictionRecommendedAction = "NONE";

bool predictionRequiresAttention = false;

bool predictionIsUnknown = false;

// ============================================================
// TIMING
// ============================================================

uint32_t lastSensorRead = 0;

uint32_t lastPost = 0;

uint32_t lastAudioInference = 0;

// ============================================================
// AUTOMATIC AUDIO INFERENCE
// ============================================================
//
// Automatically capture 5 seconds of audio, send it to the
// FastAPI AI backend, receive the inference, and repeat.

// Periodic automatic audio inference (runs every 10 seconds to leave bandwidth for snappy telemetry)
bool automaticAudioDetection = true;

const uint32_t AUDIO_INFERENCE_INTERVAL = 10000; // 10s gap between automatic audio scans

uint32_t nextAudioInference = 0;

const uint32_t SENSOR_INTERVAL = 1000; // Read sensors every 1 second

const uint32_t POST_INTERVAL = 2000; // Transmit live telemetry every 2 seconds (snappy real-time data)

// ============================================================
// AUDIO BUFFER
// ============================================================

int16_t *audioBuffer = nullptr;

// ============================================================
// I2C REGISTER READER
// ============================================================

uint16_t readMAX17048Register(
    uint8_t reg)
{
    Wire.beginTransmission(
        MAX17048_ADDR);

    Wire.write(reg);

    if (
        Wire.endTransmission(false) != 0)
    {
        return 0xFFFF;
    }

    if (
        Wire.requestFrom(
            (uint8_t)MAX17048_ADDR,
            (uint8_t)2) != 2)
    {
        return 0xFFFF;
    }

    uint8_t msb = Wire.read();

    uint8_t lsb = Wire.read();

    return (
        ((uint16_t)msb << 8) |
        lsb);
}

// ============================================================
// MAX17048
// ============================================================

bool initMAX17048()
{
    Wire.beginTransmission(
        MAX17048_ADDR);

    if (
        Wire.endTransmission() != 0)
    {
        return false;
    }

    return true;
}

void readBattery()
{
    uint16_t rawVcell =
        readMAX17048Register(
            REG_VCELL);

    uint16_t rawSoc =
        readMAX17048Register(
            REG_SOC);

    if (
        rawVcell == 0xFFFF ||
        rawSoc == 0xFFFF)
    {
        max17048OK = false;

        return;
    }

    max17048OK = true;

    batteryVoltage =
        (rawVcell >> 4) *
        0.00125f;

    batteryPercent =
        rawSoc / 256.0f;

    if (batteryPercent < 0)
    {
        batteryPercent = 0;
    }

    if (batteryPercent > 100)
    {
        batteryPercent = 100;
    }
}

// ============================================================
// BH1750
// ============================================================

bool initBH1750()
{
    Wire.beginTransmission(
        BH1750_ADDR);

    Wire.write(0x10);

    return (
        Wire.endTransmission() == 0);
}

float readBH1750()
{
    Wire.beginTransmission(
        BH1750_ADDR);

    Wire.write(0x10);

    if (
        Wire.endTransmission() != 0)
    {
        bh1750OK = false;

        return 0;
    }

    delay(180);

    if (
        Wire.requestFrom(
            (uint8_t)BH1750_ADDR,
            (uint8_t)2) != 2)
    {
        bh1750OK = false;

        return 0;
    }

    uint16_t raw =
        (((uint16_t)Wire.read() << 8) |
         Wire.read());

    bh1750OK = true;

    return raw / 1.2f;
}

// ============================================================
// DHT11
// ============================================================

void readDHT()
{
    float h =
        dht.readHumidity();

    float t =
        dht.readTemperature();

    if (
        isnan(h) ||
        isnan(t))
    {
        dhtOK = false;

        return;
    }

    dhtOK = true;

    humidity = h;

    temperatureC = t;
}

// ============================================================
// MQ-2 / MQ-135 GAS SENSORS
// ============================================================
//
// These sensors provide an analog resistance-related signal.
// The values below are intentionally reported as RAW ADC and
// ADC voltage. They are NOT ppm values until the individual
// sensors are calibrated with a known reference gas/environment.
//
// ADC pins are configured for the ESP32-S3 12-bit range:
//     0 ... 4095
//

int readAveragedADC(int pin)
{
    const int samples = 20;
    uint32_t total = 0;

    for (int i = 0; i < samples; i++)
    {
        total += analogRead(pin);
        delayMicroseconds(200);
    }

    return (int)(total / samples);
}

void readGasSensors()
{
    mq2Raw = readAveragedADC(MQ2_PIN);
    mq135Raw = readAveragedADC(MQ135_PIN);

    // Convert ADC counts to the configured ADC input voltage range.
    // This is the voltage seen by the ESP32 ADC pin, not necessarily
    // the MQ module AO voltage if a voltage divider is being used.
    mq2Voltage = (mq2Raw / 4095.0f) * 3.3f;
    mq135Voltage = (mq135Raw / 4095.0f) * 3.3f;

    mq2OK = true;
    mq135OK = true;
}

// ============================================================
// VIBRATION
// ============================================================

void readVibration()
{
    vibrationDetected =
        digitalRead(
            VIBRATION_PIN) == HIGH;
}

// ============================================================
// INMP441
// ============================================================

bool initMicrophone()
{
    esp_err_t result;

    result =
        i2s_driver_install(
            I2S_PORT,
            &i2sConfig,
            0,
            NULL);

    if (
        result != ESP_OK)
    {
        return false;
    }

    result =
        i2s_set_pin(
            I2S_PORT,
            &i2sPins);

    if (
        result != ESP_OK)
    {
        return false;
    }

    i2s_zero_dma_buffer(
        I2S_PORT);

    return true;
}

// ============================================================
// MICROPHONE LEVEL
// ============================================================

int readMicrophone()
{
    int32_t samples[64];

    size_t bytesRead = 0;

    esp_err_t result =
        i2s_read(
            I2S_PORT,
            samples,
            sizeof(samples),
            &bytesRead,
            20);

    if (
        result != ESP_OK ||
        bytesRead == 0)
    {
        microphoneOK = false;

        return 0;
    }

    microphoneOK = true;

    int count =
        bytesRead /
        sizeof(int32_t);

    if (count <= 0)
    {
        return 0;
    }

    uint64_t total = 0;

    for (
        int i = 0;
        i < count;
        i++)
    {
        int32_t sample =
            samples[i] >> 14;

        if (sample < 0)
        {
            sample = -sample;
        }

        total += sample;
    }

    int level =
        total / count;

    if (level > 32767)
    {
        level = 32767;
    }

    return level;
}

// ============================================================
// CAPTURE 5-SECOND PCM AUDIO
// ============================================================

bool captureAudio()
{
    if (!microphoneOK)
    {
        Serial.println(
            "Audio capture aborted: microphone unavailable.");

        return false;
    }

    if (audioBuffer == nullptr)
    {
        Serial.println(
            "Audio capture aborted: audio buffer unavailable.");

        return false;
    }

    Serial.println();
    Serial.println(
        "============================================================");

    Serial.println(
        "                 AUDIO CAPTURE");

    Serial.println(
        "============================================================");

    Serial.print(
        "Sample rate : ");

    Serial.println(
        AUDIO_SAMPLE_RATE);

    Serial.print(
        "Duration    : ");

    Serial.print(
        AUDIO_DURATION_SECONDS);

    Serial.println(
        " seconds");

    Serial.print(
        "Samples     : ");

    Serial.println(
        AUDIO_SAMPLE_COUNT);

    Serial.println(
        "Recording...");

    size_t samplesCaptured = 0;

    int32_t rawSamples[512];

    uint32_t startTime = millis();

    while (
        samplesCaptured <
        AUDIO_SAMPLE_COUNT)
    {
        size_t bytesRead = 0;

        esp_err_t result =
            i2s_read(
                I2S_PORT,
                rawSamples,
                sizeof(rawSamples),
                &bytesRead,
                portMAX_DELAY);

        if (
            result != ESP_OK ||
            bytesRead == 0)
        {
            Serial.println(
                "ERROR: I2S audio read failed.");

            microphoneOK = false;

            return false;
        }

        size_t rawCount =
            bytesRead /
            sizeof(int32_t);

        for (
            size_t i = 0;
            i < rawCount &&
            samplesCaptured <
                AUDIO_SAMPLE_COUNT;
            i++)
        {
            /*
              INMP441 delivers 24-bit audio
              inside a 32-bit I2S word (left-aligned).

              Shift down by 15 to obtain a balanced,
              high-dynamic-range signed PCM16 representation
              without premature saturation or excessive noise.
            */

            // Convert 32-bit (24-bit data) down to standard 16-bit PCM (amplify and truncate)
            int32_t sample =
                rawSamples[i] >> 14;

            if (sample > 32767)
            {
                sample = 32767;
            }

            if (sample < -32768)
            {
                sample = -32768;
            }

            audioBuffer[samplesCaptured] =
                (int16_t)sample;

            samplesCaptured++;
        }

        /*
          Progress indication every ~1 second.
        */

        if (
            millis() - startTime >= 1000)
        {
            float progress =
                (samplesCaptured * 100.0f) /
                AUDIO_SAMPLE_COUNT;

            Serial.print(
                "Progress: ");

            Serial.print(
                progress,
                1);

            Serial.println(
                " %");

            startTime = millis();
        }
    }

    Serial.println(
        "Recording complete.");

    Serial.print(
        "Captured samples: ");

    Serial.println(
        samplesCaptured);

    Serial.print(
        "Captured bytes: ");

    Serial.println(
        samplesCaptured *
        sizeof(int16_t));

    Serial.println(
        "============================================================");

    return true;
}

// ============================================================
// SAVE PCM AUDIO TO SD
// ============================================================

bool saveAudioToSD()
{
    if (!sdOK)
    {
        Serial.println(
            "MicroSD unavailable. Audio not saved.");

        return false;
    }

    if (audioBuffer == nullptr)
    {
        return false;
    }

    File file =
        SD.open(
            "/test_audio.pcm",
            FILE_WRITE);

    if (!file)
    {
        Serial.println(
            "ERROR: Unable to create /test_audio.pcm");

        return false;
    }

    size_t bytesWritten =
        file.write(
            (
                const uint8_t *)audioBuffer,
            AUDIO_BUFFER_BYTES);

    file.close();

    if (
        bytesWritten !=
        AUDIO_BUFFER_BYTES)
    {
        Serial.println(
            "ERROR: Incomplete PCM write.");

        return false;
    }

    Serial.println(
        "PCM audio saved to MicroSD:");

    Serial.println(
        "/test_audio.pcm");

    return true;
}

// ============================================================
// GPS
// ============================================================

void readGPS()
{
    while (
        GPSSerial.available())
    {
        char c =
            GPSSerial.read();

        gpsCharacters++;

        gps.encode(c);
    }

    if (
        gps.location.isValid())
    {
        gpsFix = true;

        latitude =
            gps.location.lat();

        longitude =
            gps.location.lng();
    }
    else
    {
        gpsFix = false;
    }

    if (
        gps.altitude.isValid())
    {
        altitude =
            gps.altitude.meters();
    }

    if (
        gps.satellites.isValid())
    {
        gpsSatellites =
            gps.satellites.value();
    }

    gpsAccuracy = 0.0;
}

// ============================================================
// WIFI
// ============================================================

// ============================================================
// NVS PREFERENCES & WEB CONFIGURATION PORTAL (http://192.168.4.1)
// ============================================================

void loadWiFiPreferences()
{
    preferences.begin("auracfg", true);
    String s_ssid = preferences.getString("ssid", "");
    String s_pass = preferences.getString("pass", "");
    String s_ip = preferences.getString("srv_ip", "");
    uint16_t s_port = preferences.getUShort("srv_port", 0);
    preferences.end();

    if (s_ssid.length() > 0)
    {
        activeWiFiSSID = s_ssid;
        activeWiFiPassword = s_pass;
        Serial.print("Loaded stored Wi-Fi from NVS: ");
        Serial.println(activeWiFiSSID);
    }
    else
    {
        activeWiFiSSID = String(WIFI_SSID);
        activeWiFiPassword = String(WIFI_PASSWORD);
        Serial.println("Using default hardcoded Wi-Fi credentials.");
    }

    if (s_ip.length() > 0)
    {
        activeServerIP = s_ip;
    }
    else
    {
        activeServerIP = String(LOCAL_SERVER_IP);
    }

    if (s_port > 0)
    {
        activeServerPort = s_port;
    }
    else
    {
        activeServerPort = LOCAL_SERVER_PORT;
    }
}

void saveWiFiPreferences(const String& ssid, const String& pass, const String& srv_ip, uint16_t srv_port)
{
    preferences.begin("auracfg", false);
    preferences.putString("ssid", ssid);
    preferences.putString("pass", pass);
    if (srv_ip.length() > 0)
    {
        preferences.putString("srv_ip", srv_ip);
    }
    if (srv_port > 0)
    {
        preferences.putUShort("srv_port", srv_port);
    }
    preferences.end();
    Serial.println("Saved new Wi-Fi credentials to NVS flash permanently.");
}

void handlePortalRoot()
{
    // Scan networks
    int n = WiFi.scanNetworks();
    String netOptions = "";
    for (int i = 0; i < n; ++i)
    {
        String ssid_item = WiFi.SSID(i);
        int32_t rssi_item = WiFi.RSSI(i);
        netOptions += "<option value='" + ssid_item + "'>" + ssid_item + " (" + String(rssi_item) + " dBm)</option>";
    }

    String html = R"rawliteral(<!DOCTYPE html>
<html>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1.0'>
  <title>AuraForest Node Setup</title>
  <style>
    body { background-color: #0b1411; color: #edf6f3; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }
    .card { max-width: 440px; margin: 0 auto; background: #13221d; border: 1px solid #1e362e; border-radius: 12px; padding: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
    h2 { color: #7cf0b2; margin-top: 0; font-size: 20px; display: flex; align-items: center; gap: 8px; }
    p { font-size: 13px; color: #8ba29a; line-height: 1.5; margin-bottom: 20px; }
    label { font-size: 12px; font-weight: 600; color: #edf6f3; display: block; margin-top: 14px; margin-bottom: 6px; }
    input, select { width: 100%; box-sizing: border-box; padding: 10px 12px; background: #080f0c; border: 1px solid #234237; border-radius: 6px; color: #fff; font-size: 14px; outline: none; }
    input:focus, select:focus { border-color: #7cf0b2; }
    .hint { font-size: 11px; color: #6f857e; margin-top: 4px; }
    .btn { width: 100%; background: #1b8a5a; color: #fff; border: none; padding: 12px; border-radius: 6px; font-size: 15px; font-weight: 700; cursor: pointer; margin-top: 22px; transition: background 0.2s; }
    .btn:hover { background: #22a86e; }
    .hotspot-box { background: rgba(242,198,109,0.08); border: 1px solid rgba(242,198,109,0.3); border-radius: 6px; padding: 10px 12px; font-size: 12px; color: #f2c66d; margin-top: 16px; }
  </style>
  <script>
    function pickSSID(val) {
      if (val) document.getElementById('ssid_inp').value = val;
    }
  </script>
</head>
<body>
  <div class='card'>
    <h2>🌲 AuraForest Sentinel</h2>
    <p>Configure the Wi-Fi or Mobile Hotspot credentials for this ESP32-S3 edge node.</p>

    <form method='POST' action='/save'>
      <label>Discovered Networks (Scan):</label>
      <select onchange='pickSSID(this.value)'>
        <option value=''>-- Tap to choose nearby network --</option>
)rawliteral";

    html += netOptions;

    html += R"rawliteral(
      </select>

      <label>Wi-Fi / Hotspot Name (SSID):</label>
      <input type='text' id='ssid_inp' name='ssid' value=')rawliteral";
    html += activeWiFiSSID;
    html += R"rawliteral(' required placeholder='e.g. MyMobileHotspot or HomeFiber'>

      <label>Wi-Fi Password:</label>
      <input type='password' name='pass' value=')rawliteral";
    html += activeWiFiPassword;
    html += R"rawliteral(' placeholder='Enter Wi-Fi password'>

      <label>Backend Server IP Address:</label>
      <input type='text' name='ip' value=')rawliteral";
    html += activeServerIP;
    html += R"rawliteral(' placeholder='e.g. 192.168.43.150 or PC IP'>
      <div class='hint'>If using a mobile hotspot, enter your laptop's hotspot IP address.</div>

      <label>Backend Port:</label>
      <input type='number' name='port' value=')rawliteral";
    html += String(activeServerPort);
    html += R"rawliteral('>

      <div class='hotspot-box'>
        📱 <b>Mobile Hotspot Tip:</b> On iPhone, enable <i>'Maximize Compatibility'</i>. On Android, select <i>'2.4 GHz Band'</i> (ESP32 only supports 2.4 GHz).
      </div>

      <button type='submit' class='btn'>💾 Save Credentials & Connect</button>
    </form>
  </div>
</body>
</html>)rawliteral";

    configServer.send(200, "text/html", html);
}

void handlePortalSave()
{
    String new_ssid = configServer.arg("ssid");
    String new_pass = configServer.arg("pass");
    String new_ip = configServer.arg("ip");
    String new_port_str = configServer.arg("port");
    uint16_t new_port = new_port_str.length() > 0 ? (uint16_t)new_port_str.toInt() : activeServerPort;

    if (new_ssid.length() > 0)
    {
        activeWiFiSSID = new_ssid;
        activeWiFiPassword = new_pass;
        if (new_ip.length() > 0) activeServerIP = new_ip;
        if (new_port > 0) activeServerPort = new_port;

        saveWiFiPreferences(activeWiFiSSID, activeWiFiPassword, activeServerIP, activeServerPort);

        String resp = R"rawliteral(<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'>
<style>body{background:#0b1411;color:#edf6f3;font-family:sans-serif;text-align:center;padding:40px;}.box{max-width:380px;margin:0 auto;background:#13221d;border:1px solid #7cf0b2;border-radius:12px;padding:24px;}</style>
</head><body><div class='box'><h2 style='color:#7cf0b2;'>✅ Credentials Saved!</h2>
<p>Connecting to <b>)rawliteral" + activeWiFiSSID + R"rawliteral(</b>...</p>
<p style='color:#8ba29a;font-size:13px;'>The node is restarting now and will join your Wi-Fi network.</p></div>
<script>setTimeout(function(){window.location.href='/';}, 8000);</script>
</body></html>)rawliteral";

        configServer.send(200, "text/html", resp);
        delay(1500);
        ESP.restart();
    }
    else
    {
        configServer.send(400, "text/plain", "SSID cannot be empty.");
    }
}

void startWiFiPortal()
{
    Serial.println();
    Serial.println("============================================================");
    Serial.println(" [WIFI SETUP PORTAL READY]");
    Serial.println("============================================================");

    WiFi.mode(WIFI_AP_STA);
    WiFi.setSleep(false);
    WiFi.softAP("AuraForest-Node-Setup");

    IPAddress myIP = WiFi.softAPIP();
    Serial.println("  Access Point SSID : AuraForest-Node-Setup");
    Serial.print("  Configuration URL : http://");
    Serial.println(myIP);
    Serial.println("  ----------------------------------------------------------");
    Serial.println("  STEPS TO CONFIGURE:");
    Serial.println("  1. Connect your phone or laptop to Wi-Fi: 'AuraForest-Node-Setup'");
    Serial.println("  2. Open any web browser and go to: http://192.168.4.1");
    Serial.println("  3. Pick your Mobile Hotspot or Wi-Fi, enter password, and save!");
    Serial.println("============================================================");

    dnsServer.start(53, "*", myIP);

    configServer.on("/", handlePortalRoot);
    configServer.on("/save", HTTP_POST, handlePortalSave);
    configServer.on("/hotspot-detect.html", handlePortalRoot);
    configServer.on("/generate_204", handlePortalRoot);
    configServer.onNotFound(handlePortalRoot);

    configServer.begin();
    wifiPortalActive = true;
}

void connectWiFi()
{
    loadWiFiPreferences();

    Serial.println();
    Serial.print("Connecting to Wi-Fi: ");
    Serial.println(activeWiFiSSID);

    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false); // Essential for mobile hotspot stability

    WiFi.begin(activeWiFiSSID.c_str(), activeWiFiPassword.c_str());

    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 15000)
    {
        delay(500);
        Serial.print(".");
    }
    Serial.println();

    if (WiFi.status() == WL_CONNECTED)
    {
        wifiOK = true;
        wifiPortalActive = false;
        Serial.println("WiFi connected successfully!");
        Serial.print("ESP32 IP        : ");
        Serial.println(WiFi.localIP());
        Serial.print("Hotspot Gateway : ");
        Serial.println(WiFi.gatewayIP());
#if USE_CLOUD_BACKEND
        Serial.print("Target Backend  : CLOUD (");
        Serial.print(getBaseURL());
        Serial.println(")");
#else
        Serial.print("Target PC Server: http://");
        Serial.print(activeServerIP);
        Serial.print(":");
        Serial.println(activeServerPort);

        IPAddress localIP = WiFi.localIP();
        IPAddress srvIP;
        if (srvIP.fromString(activeServerIP))
        {
            if (localIP[0] != srvIP[0] || localIP[1] != srvIP[1] || localIP[2] != srvIP[2])
            {
                Serial.println();
                Serial.println("************************************************************");
                Serial.println("⚠️  [CRITICAL: SUBNET MISMATCH DETECTED]");
                Serial.print  ("   ESP32 is at     : "); Serial.println(localIP);
                Serial.print  ("   Target Server at: "); Serial.println(activeServerIP);
                Serial.println("   --> The ESP32 and PC are on DIFFERENT network subnets!");
                Serial.println("   --> Telemetry POST will fail until Server IP is updated.");
                Serial.println("   QUICK FIX: In Serial Monitor, type: IP=<Your_PC_IP>");
                Serial.println("              (e.g., IP=192.168.43.150)");
                Serial.println("************************************************************");
            }
        }
#endif
    }
    else
    {
        wifiOK = false;
        Serial.println("WiFi connection failed or network not found.");
        Serial.println("Automatically launching Web Configuration Portal...");
        startWiFiPortal();
    }
}

// ============================================================
// WIFI MAINTENANCE
// ============================================================

void maintainWiFi()
{
    if (
        WiFi.status() ==
        WL_CONNECTED)
    {
        wifiOK = true;

        return;
    }

    wifiOK = false;

    telemetryBackendOK = false;

    audioBackendOK = false;

    static uint32_t lastAttempt = 0;

    if (
        millis() - lastAttempt <
        10000)
    {
        return;
    }

    lastAttempt =
        millis();

    Serial.println(
        "WiFi disconnected. Reconnecting...");

    WiFi.disconnect();

    WiFi.begin(
        activeWiFiSSID.c_str(),
        activeWiFiPassword.c_str());
}

// ============================================================
// MICROSD
// ============================================================

bool initSD()
{
    spiSD.begin(
        SD_SCK,
        SD_MISO,
        SD_MOSI,
        SD_CS);

    if (
        !SD.begin(
            SD_CS,
            spiSD))
    {
        return false;
    }

    uint8_t cardType =
        SD.cardType();

    if (
        cardType == CARD_NONE)
    {
        return false;
    }

    return true;
}

// ============================================================
// SD TELEMETRY FALLBACK
// ============================================================

void saveToSD(
    const String &json)
{
    if (!sdOK)
    {
        return;
    }

    File file =
        SD.open(
            "/runtime_events.jsonl",
            FILE_APPEND);

    if (!file)
    {
        Serial.println(
            "ERROR: Unable to open MicroSD fallback file.");

        return;
    }

    file.println(json);

    file.close();

    Serial.println(
        "Telemetry saved to MicroSD fallback.");
}

// ============================================================
// ENVIRONMENT CLASSIFICATION
// ============================================================

String getEnvironmentType()
{
    if (
        lightLux < 10)
    {
        return "Low_Light";
    }

    if (
        lightLux > 1500)
    {
        return "Bright";
    }

    return "Natural";
}

// ============================================================
// ADAPTIVE POLICY
// ============================================================

float getDetectionThreshold(
    const String &environment)
{
    if (
        environment == "Low_Light")
    {
        return 0.60;
    }

    if (
        environment == "Bright")
    {
        return 0.55;
    }

    return 0.55;
}

// ============================================================
// RISK
// ============================================================

String calculateRisk()
{
    if (
        vibrationDetected)
    {
        return "MEDIUM";
    }

    return "LOW";
}

String calculateCADIEAction(
    const String &risk)
{
    if (
        risk == "HIGH")
    {
        return "ALERT";
    }

    if (
        risk == "MEDIUM")
    {
        return "CHECK";
    }

    return "MONITOR";
}

// ============================================================
// TIMESTAMP
// ============================================================

double getTimestamp()
{
    if (
        gps.date.isValid() &&
        gps.time.isValid())
    {
        struct tm timeinfo;

        timeinfo.tm_year =
            gps.date.year() - 1900;

        timeinfo.tm_mon =
            gps.date.month() - 1;

        timeinfo.tm_mday =
            gps.date.day();

        timeinfo.tm_hour =
            gps.time.hour();

        timeinfo.tm_min =
            gps.time.minute();

        timeinfo.tm_sec =
            gps.time.second();

        timeinfo.tm_isdst = 0;

        time_t timestamp =
            mktime(&timeinfo);

        return (double)timestamp;
    }

    return millis() / 1000.0;
}

// ============================================================
// TELEMETRY JSON
// ============================================================

String createPayload()
{
    StaticJsonDocument<4096> doc;

    doc["device_id"] =
        DEVICE_ID;

    doc["timestamp"] =
        getTimestamp();

    JsonObject status =
        doc.createNestedObject(
            "device_status");

    status["battery_percent"] =
        batteryPercent;

    status["battery_voltage"] =
        batteryVoltage;

    status["temperature"] =
        temperatureC;

    status["humidity"] =
        humidity;

    status["light_level"] =
        lightLux;

    status["vibration_detected"] =
        vibrationDetected;

    status["mq2_raw"] =
        mq2Raw;

    status["mq2_adc_voltage"] =
        mq2Voltage;

    status["mq135_raw"] =
        mq135Raw;

    status["mq135_adc_voltage"] =
        mq135Voltage;

    JsonObject location =
        doc.createNestedObject(
            "location");

    if (
        gpsFix)
    {
        location["latitude"] =
            latitude;

        location["longitude"] =
            longitude;

        location["altitude"] =
            altitude;

        location["accuracy"] =
            gpsAccuracy;

        location["source"] =
            "GPS";
    }
    else
    {
        location["latitude"] =
            FALLBACK_LATITUDE;

        location["longitude"] =
            FALLBACK_LONGITUDE;

        location["altitude"] =
            FALLBACK_ALTITUDE;

        location["accuracy"] =
            FALLBACK_ACCURACY;

        location["source"] =
            "DEMO_FALLBACK";

        location["city"] =
            "Mysore";

        location["state"] =
            "Karnataka";

        location["country"] =
            "India";
    }

    JsonObject health =
        doc.createNestedObject(
            "hardware_health");

    health["INMP441"] =
        microphoneOK
            ? "WORKING"
            : "NOT_WORKING";

    health["BH1750"] =
        bh1750OK
            ? "WORKING"
            : "NOT_WORKING";

    health["MAX17048"] =
        max17048OK
            ? "WORKING"
            : "NOT_WORKING";

    health["DHT11"] =
        dhtOK
            ? "WORKING"
            : "NOT_WORKING";

    health["SW-420"] =
        "WORKING";

    health["NEO-6M"] =
        gpsFix
            ? "WORKING"
            : "NOT_WORKING";

    health["MicroSD"] =
        sdOK
            ? "WORKING"
            : "NOT_WORKING";

    health["WiFi"] =
        wifiOK
            ? "WORKING"
            : "NOT_WORKING";

    health["Telemetry_Backend"] =
        telemetryBackendOK
            ? "WORKING"
            : "NOT_WORKING";

    health["MQ-2"] =
        mq2OK
            ? "READABLE"
            : "NOT_WORKING";

    health["MQ-135"] =
        mq135OK
            ? "READABLE"
            : "NOT_WORKING";

    bool overallHardware =
        microphoneOK &&
        bh1750OK &&
        max17048OK &&
        dhtOK &&
        sdOK &&
        wifiOK;

    health["Overall_Hardware"] =
        overallHardware
            ? "WORKING"
            : "NOT_WORKING";

    String output;

    serializeJson(
        doc,
        output);

    return output;
}

// ============================================================
// UNIVERSAL IP AUTO-DISCOVERY & CONNECTION TEST
// ============================================================

bool checkIPHealth(const String &ip, uint16_t port)
{
    WiFiClient client;
    client.setTimeout(300);
    if (!client.connect(ip.c_str(), port))
    {
        return false;
    }
    client.print("GET /health HTTP/1.1\r\nHost: " + ip + "\r\nConnection: close\r\n\r\n");
    uint32_t start = millis();
    while (client.connected() && !client.available() && millis() - start < 500)
    {
        delay(10);
    }
    if (client.available())
    {
        String response = client.readString();
        client.stop();
        if (response.indexOf("200 OK") >= 0 || response.indexOf("auraforest") >= 0 || response.indexOf("healthy") >= 0)
        {
            return true;
        }
    }
    client.stop();
    return false;
}

bool autoDiscoverBackend()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        return false;
    }

    Serial.println();
    Serial.println("============================================================");
    Serial.println(" [UNIVERSAL IP AUTO-DISCOVERY] Scanning local network...");
    Serial.println("============================================================");

    IPAddress local = WiFi.localIP();
    IPAddress gw = WiFi.gatewayIP();

    // 1. Probe the Gateway (e.g. mobile hotspot host)
    if (gw != IPAddress(0, 0, 0, 0))
    {
        String gwStr = gw.toString();
        Serial.print("  Probing gateway: "); Serial.println(gwStr);
        if (checkIPHealth(gwStr, activeServerPort))
        {
            activeServerIP = gwStr;
            saveWiFiPreferences(activeWiFiSSID, activeWiFiPassword, activeServerIP, activeServerPort);
            Serial.println("  🎉 Found backend server at Gateway IP: " + activeServerIP);
            return true;
        }
    }

    // 2. Scan likely IP offsets on the local subnet (Hotspots & Home LANs)
    int myLast = local[3];
    int candidateList[] = {
        65, 244, 100, 101, 102, 103, 104, 105, 2, 3, 4, 5, 10, 20, 50, 150, 200,
        myLast - 1, myLast + 1, myLast - 2, myLast + 2
    };

    int numCandidates = sizeof(candidateList) / sizeof(candidateList[0]);
    for (int i = 0; i < numCandidates; i++)
    {
        int octet = candidateList[i];
        if (octet <= 0 || octet >= 255 || octet == myLast) continue;

        IPAddress candidate(local[0], local[1], local[2], octet);
        String candStr = candidate.toString();
        if (candStr == activeServerIP) continue;

        Serial.print("  Scanning IP: "); Serial.println(candStr);
        if (checkIPHealth(candStr, activeServerPort))
        {
            activeServerIP = candStr;
            saveWiFiPreferences(activeWiFiSSID, activeWiFiPassword, activeServerIP, activeServerPort);
            Serial.println();
            Serial.println("============================================================");
            Serial.println("  🎉 MATCH FOUND! Backend IP: " + activeServerIP);
            Serial.println("  Saved permanently to NVS flash.");
            Serial.println("============================================================");
            return true;
        }
    }

    Serial.println("  [AUTO-DISCOVERY] Completed. No backend responded on port " + String(activeServerPort));
    Serial.println("  Tip: Ensure run_system.py is running on your PC.");
    Serial.println("============================================================");
    return false;
}

bool testBackendConnection()
{
    if (
        WiFi.status() != WL_CONNECTED)
    {
        return false;
    }

    String healthURL =
        getBaseURL() + "/health";

    Serial.println();

    Serial.println(
        "Testing backend connection...");

    Serial.println(
        healthURL);

    HTTPClient http;

    http.setTimeout(10000);
    http.setReuse(false);

    WiFiClientSecure client;
    bool beginResult = false;
    if (healthURL.startsWith("https://"))
    {
        client.setInsecure();
        client.setTimeout(10);
        beginResult = http.begin(client, healthURL);
    }
    else
    {
        beginResult = http.begin(healthURL);
    }

    if (!beginResult)
    {
        http.end();

        return false;
    }

    int code =
        http.GET();

    if (
        code > 0)
    {
        String response =
            http.getString();

        Serial.println(
            "Health Response:");

        Serial.println(
            response);
    }
    else
    {
        Serial.print("[BACKEND ERROR] Could not reach ");
        Serial.println(healthURL);
        Serial.print("HTTP Client Error: ");
        Serial.println(http.errorToString(code));
        Serial.println("Hint: Make sure your PC is connected to the same hotspot and run_system.py is active.");
    }

    http.end();

    bool ok = (code >= 200 && code < 300);
#if !USE_CLOUD_BACKEND
    if (!ok)
    {
        // Automatically attempt local subnet discovery if initial connection failed
        if (autoDiscoverBackend())
        {
            return true;
        }
    }
#endif

    return ok;
}

// ============================================================
// SEND TELEMETRY TO FASTAPI
// ============================================================

bool sendToBackend(
    const String &json)
{
    if (
        WiFi.status() != WL_CONNECTED)
    {
        wifiOK = false;

        telemetryBackendOK = false;

        return false;
    }

    wifiOK = true;

    String url =
        getBaseURL() + String(API_PATH);

    HTTPClient http;

    http.setTimeout(10000);
    http.setReuse(false);

    WiFiClientSecure client;
    bool beginResult = false;
    if (url.startsWith("https://"))
    {
        client.setInsecure();
        client.setTimeout(10);
        beginResult = http.begin(client, url);
    }
    else
    {
        beginResult = http.begin(url);
    }

    if (!beginResult)
    {
        telemetryBackendOK = false;

        http.end();

        return false;
    }

    http.addHeader(
        "Content-Type",
        "application/json");

    http.addHeader(
        "Accept",
        "application/json");

    http.addHeader(
        "X-Device-Token",
        DEVICE_API_KEY);

    http.addHeader(
        "X-API-Key",
        DEVICE_API_KEY);

    int responseCode =
        http.POST(json);

    Serial.print(
        "Telemetry HTTP Response: ");

    Serial.println(
        responseCode);

    if (
        responseCode > 0)
    {
        String response =
            http.getString();

        Serial.println(
            "Telemetry Backend Response:");

        Serial.println(
            response);
    }
    else
    {
        Serial.print("[HTTP ERROR] Failed connecting to: ");
        Serial.println(url);
        Serial.print("Reason: ");
        Serial.println(http.errorToString(responseCode));
        Serial.println("Type 'I' for network info or 'IP=<PC_IP>' to update server address.");
    }

    bool success =
        responseCode >= 200 &&
        responseCode < 300;

    telemetryBackendOK =
        success;

    http.end();

    return success;
}

// ============================================================
// PARSE AI RESPONSE
// ============================================================

void parseInferenceResponse(
    const String &response)
{
    StaticJsonDocument<8192> doc;

    DeserializationError error =
        deserializeJson(
            doc,
            response);

    if (error)
    {
        Serial.print(
            "AI response JSON parse failed: ");

        Serial.println(
            error.c_str());

        return;
    }

    /*
      Expected structure from your
      current backend response:

      {
        "inference": {
          "prediction": {...},
          "unknown_discovery": {...},
          "edge_runtime": {
            "decision": {...}
          }
        }
      }
    */

    JsonObject inference =
        doc["inference"];

    if (
        inference.isNull())
    {
        /*
          Also support a response where
          "prediction" is at root level.
        */

        inference = doc.as<JsonObject>();
    }

    JsonObject prediction =
        inference["prediction"];

    if (
        !prediction.isNull())
    {
        predictionLabel =
            prediction["label"] |
            "Unknown";

        predictionClassID =
            prediction["class_id"] |
            -1;

        predictionConfidence =
            prediction["confidence"] |
            0.0f;

        predictionInferenceTimeMs =
            prediction["inference_time_ms"] |
            0.0f;
    }

    /*
      Unknown discovery
    */

    JsonObject unknownDiscovery =
        inference["unknown_discovery"];

    if (
        !unknownDiscovery.isNull())
    {
        JsonObject decision =
            unknownDiscovery["decision"];

        if (
            !decision.isNull())
        {
            predictionIsUnknown =
                decision["is_unknown"] |
                false;
        }
    }

    /*
      Edge runtime decision
    */

    JsonObject edgeRuntime =
        inference["edge_runtime"];

    if (
        !edgeRuntime.isNull())
    {
        JsonObject decision =
            edgeRuntime["decision"];

        if (
            !decision.isNull())
        {
            predictionRiskLevel =
                decision["risk_level"] |
                "UNKNOWN";

            predictionRecommendedAction =
                decision["recommended_action"] |
                "NONE";

            predictionRequiresAttention =
                decision["requires_attention"] |
                false;
        }
    }

    /*
      Local Emergency Alert Notification
    */
    JsonObject emergencyAlert =
        inference["emergency_alert"];

    bool localAlertActive = false;
    String alertThreat = "";
    String alertId = "";

    if (!emergencyAlert.isNull())
    {
        localAlertActive = emergencyAlert["triggered"] | false;
        if (localAlertActive)
        {
            alertThreat = emergencyAlert["threat_type"] | "THREAT";
            alertId = emergencyAlert["alert_id"] | "N/A";
        }
    }

    /*
      Print result
    */

    Serial.println();

    Serial.println(
        "============================================================");

    Serial.println(
        "                 AI INFERENCE RESULT");

    Serial.println(
        "============================================================");

    Serial.print(
        "Prediction          : ");

    Serial.println(
        predictionLabel);

    Serial.print(
        "Class ID            : ");

    Serial.println(
        predictionClassID);

    Serial.print(
        "Confidence          : ");

    Serial.print(
        predictionConfidence * 100.0f,
        2);

    Serial.println(
        " %");

    Serial.print(
        "Inference Time      : ");

    Serial.print(
        predictionInferenceTimeMs,
        2);

    Serial.println(
        " ms");

    Serial.print(
        "Unknown Discovery   : ");

    Serial.println(
        predictionIsUnknown
            ? "YES"
            : "NO");

    Serial.print(
        "Risk Level          : ");

    Serial.println(
        predictionRiskLevel);

    Serial.print(
        "Recommended Action  : ");

    Serial.println(
        predictionRecommendedAction);

    Serial.print(
        "Requires Attention  : ");

    Serial.println(
        predictionRequiresAttention
            ? "YES"
            : "NO");

    if (localAlertActive)
    {
        Serial.println(
            "---------------- EMERGENCY ALERT TRIGGERED -----------------");
        Serial.print(
            "Alert Threat        : ");
        Serial.println(
            alertThreat);
        Serial.print(
            "Alert ID            : ");
        Serial.println(
            alertId);
        Serial.println(
            "Action              : Activating local strobe/alarm indicator...");
        
        // Fast triple-pulse visual strobe indicator on RED LED
        for (int i = 0; i < 3; i++)
        {
            digitalWrite(RED_LED, HIGH);
            delay(120);
            digitalWrite(RED_LED, LOW);
            delay(80);
        }
    }

    Serial.println(
        "============================================================");
}

// ============================================================
// SEND AUDIO TO FASTAPI
// ============================================================

bool sendAudioToBackend()
{
    if (
        WiFi.status() != WL_CONNECTED)
    {
        Serial.println(
            "Audio inference aborted: WiFi disconnected.");

        audioBackendOK = false;

        return false;
    }

    if (
        audioBuffer == nullptr)
    {
        Serial.println(
            "Audio inference aborted: audio buffer unavailable.");

        audioBackendOK = false;

        return false;
    }

    /*
      FastAPI endpoint expects:

        device_id   -> query parameter
        timestamp   -> query parameter
        sample_rate -> query parameter
        audio       -> raw application/octet-stream body

      Therefore the required metadata is placed in the URL.
    */

    String timestamp =
        String(
            getTimestamp(),
            3);

    String url =
        getBaseURL() +
        String(AUDIO_API_PATH) +
        "?device_id=" +
        DEVICE_ID +
        "&timestamp=" +
        timestamp +
        "&sample_rate=" +
        String(AUDIO_SAMPLE_RATE);

    Serial.println();

    Serial.println(
        "============================================================");

    Serial.println(
        "                 AUDIO AI INFERENCE");

    Serial.println(
        "============================================================");

    Serial.print(
        "Audio URL: ");

    Serial.println(
        url);

    HTTPClient http;

    http.setTimeout(45000);
    http.setReuse(false);

    Serial.print(
        "Free heap before audio upload: ");

    Serial.print(
        ESP.getFreeHeap());

    Serial.println(
        " bytes");

    WiFiClientSecure audioClient;
    bool beginResult = false;
    if (url.startsWith("https://"))
    {
        audioClient.setInsecure();
        audioClient.setTimeout(45);
        beginResult = http.begin(audioClient, url);
    }
    else
    {
        beginResult = http.begin(url);
    }

    if (!beginResult)
    {
        Serial.println(
            "ERROR: HTTPClient.begin() failed.");

        http.end();

        audioBackendOK = false;

        return false;
    }

    /*
      Send raw PCM16.

      Backend expects:

        format      = signed 16-bit little-endian PCM
        sample rate = 16000 Hz
        channels    = 1
        duration    = 5 seconds

      AUDIO_BUFFER_BYTES =
        80,000 samples x 2 bytes
        = 160,000 bytes
    */

    http.addHeader(
        "Content-Type",
        "application/octet-stream");

    http.addHeader(
        "Accept",
        "application/json");

    /*
      These headers are informational only.
      The FastAPI endpoint does not use them for
      device_id, timestamp, or sample_rate.
    */

    http.addHeader(
        "X-Channels",
        "1");

    http.addHeader(
        "X-Bit-Depth",
        "16");

    http.addHeader(
        "X-Device-Token",
        DEVICE_API_KEY);

    http.addHeader(
        "X-API-Key",
        DEVICE_API_KEY);

    Serial.print(
        "Device ID: ");

    Serial.println(
        DEVICE_ID);

    Serial.print(
        "Timestamp: ");

    Serial.println(
        timestamp);

    Serial.print(
        "Sample rate: ");

    Serial.println(
        AUDIO_SAMPLE_RATE);

    Serial.print(
        "Sending PCM bytes: ");

    Serial.println(
        AUDIO_BUFFER_BYTES);

    int responseCode =
        http.POST(
            (
                uint8_t *)audioBuffer,
            AUDIO_BUFFER_BYTES);

    Serial.print(
        "Audio HTTP Response: ");

    Serial.println(
        responseCode);

    bool success =
        responseCode >= 200 &&
        responseCode < 300;

    if (
        responseCode > 0)
    {
        String response =
            http.getString();

        Serial.println();

        Serial.println(
            "AI Backend Response:");

        Serial.println(
            response);

        if (success)
        {
            parseInferenceResponse(
                response);
        }
        else
        {
            Serial.println();
            Serial.println(
                "Audio backend returned an HTTP error.");

            if (responseCode == 422)
            {
                Serial.println(
                    "HTTP 422: FastAPI rejected the request.");

                Serial.println(
                    "Check device_id, timestamp, sample_rate, and raw PCM body.");
            }
            else if (responseCode == 400)
            {
                Serial.println(
                    "HTTP 400: Backend rejected the audio payload.");
            }
            else if (responseCode >= 500)
            {
                Serial.println(
                    "HTTP 5xx: Backend inference/server error.");
            }
        }
    }
    else
    {
        Serial.print(
            "Audio HTTP Error: ");

        Serial.println(
            http.errorToString(
                responseCode));
    }

    audioBackendOK =
        success;

    http.end();

    Serial.println(
        "============================================================");

    return success;
}

// ============================================================
// COMPLETE AUDIO INFERENCE
// ============================================================

bool performAudioInference()
{
    if (!microphoneOK)
    {
        Serial.println(
            "Cannot perform AI inference: INMP441 unavailable.");

        return false;
    }

    /*
      Allocate the 5-second PCM buffer.
      80,000 samples x 2 bytes = 160,000 bytes
    */
    if (audioBuffer == nullptr)
    {
        if (psramFound())
        {
            audioBuffer =
                (int16_t *)
                    ps_malloc(
                        AUDIO_BUFFER_BYTES);

            if (audioBuffer != nullptr)
            {
                Serial.println(
                    "Allocated 160 KB audio buffer in PSRAM.");
            }
        }

        if (audioBuffer == nullptr)
        {
            audioBuffer =
                (int16_t *)
                    malloc(
                        AUDIO_BUFFER_BYTES);

            if (audioBuffer != nullptr)
            {
                Serial.println(
                    "Allocated 160 KB audio buffer in SRAM.");
            }
        }
    }

    if (audioBuffer == nullptr)
    {
        Serial.println(
            "ERROR: Unable to allocate 160 KB audio buffer (out of heap).");

        return false;
    }

    bool captured =
        captureAudio();

    if (!captured)
    {
        return false;
    }

    /*
      Save a local copy for debugging.

      You can remove this call later if
      you do not want every test recording
      written to the SD card.
    */

    saveAudioToSD();

    /*
      Send to Python backend.
    */

    bool sent =
        sendAudioToBackend();

    return sent;
}

// ============================================================
// LED STATUS
// ============================================================

void updateLEDs(
    bool backendSuccess)
{
    if (
        backendSuccess &&
        wifiOK)
    {
        digitalWrite(
            GREEN_LED,
            HIGH);

        digitalWrite(
            RED_LED,
            LOW);

        return;
    }

    digitalWrite(
        GREEN_LED,
        LOW);

    digitalWrite(
        RED_LED,
        HIGH);
}

// ============================================================
// SERIAL TELEMETRY
// ============================================================

void printTelemetry()
{
    bool overallHardware =
        microphoneOK &&
        bh1750OK &&
        max17048OK &&
        dhtOK &&
        sdOK &&
        wifiOK;

    Serial.println();

    Serial.println(
        "============================================================");

    Serial.println(
        "             AURAFOREST EDGE NODE STATUS");

    Serial.println(
        "============================================================");

    Serial.print(
        "Device             : ");

    Serial.println(
        DEVICE_ID);

    Serial.println();

    Serial.println(
        "---------------- SENSOR VALUES ----------------");

    Serial.print(
        "Temperature        : ");

    if (dhtOK)
    {
        Serial.print(
            temperatureC,
            2);

        Serial.println(
            " C");
    }
    else
    {
        Serial.println(
            "NOT_WORKING");
    }

    Serial.print(
        "Humidity           : ");

    if (dhtOK)
    {
        Serial.print(
            humidity,
            2);

        Serial.println(
            " %");
    }
    else
    {
        Serial.println(
            "NOT_WORKING");
    }

    Serial.print(
        "Light              : ");

    if (bh1750OK)
    {
        Serial.print(
            lightLux,
            2);

        Serial.println(
            " lux");
    }
    else
    {
        Serial.println(
            "NOT_WORKING");
    }

    Serial.print(
        "Battery            : ");

    if (max17048OK)
    {
        Serial.print(
            batteryPercent,
            2);

        Serial.println(
            " %");
    }
    else
    {
        Serial.println(
            "NOT_WORKING");
    }

    Serial.print(
        "Battery Voltage    : ");

    if (max17048OK)
    {
        Serial.print(
            batteryVoltage,
            3);

        Serial.println(
            " V");
    }
    else
    {
        Serial.println(
            "NOT_WORKING");
    }

    Serial.print(
        "Vibration          : ");

    Serial.println(
        vibrationDetected
            ? "YES"
            : "NO");

    Serial.print(
        "Microphone Level   : ");

    Serial.println(
        microphoneLevel);

    Serial.print(
        "MQ-2 Smoke/Gas     : ");

    Serial.print(
        mq2Raw);

    Serial.println(
        " ADC");

    Serial.print(
        "MQ-135 Gas/VOC     : ");

    Serial.print(
        mq135Raw);

    Serial.println(
        " ADC");

    Serial.println();

    Serial.println(
        "---------------- GPS ----------------");

    if (gpsFix)
    {
        Serial.println(
            "GPS                : WORKING / FIX");

        Serial.print(
            "Latitude           : ");

        Serial.println(
            latitude,
            6);

        Serial.print(
            "Longitude          : ");

        Serial.println(
            longitude,
            6);

        Serial.print(
            "Altitude           : ");

        Serial.print(
            altitude,
            2);

        Serial.println(
            " m");

        Serial.print(
            "Satellites         : ");

        Serial.println(
            gpsSatellites);
    }
    else
    {
        Serial.println(
            "GPS                : NOT_WORKING / NO_FIX");

        Serial.println(
            "Location           : Mysore, Karnataka");

        Serial.println(
            "Location Source    : DEMO_FALLBACK");
    }

    Serial.println();

    Serial.println(
        "---------------- HARDWARE HEALTH ----------------");

    Serial.print(
        "INMP441            : ");

    Serial.println(
        microphoneOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "BH1750             : ");

    Serial.println(
        bh1750OK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "MAX17048           : ");

    Serial.println(
        max17048OK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "DHT11              : ");

    Serial.println(
        dhtOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "MQ-2               : ");

    Serial.println(
        mq2OK
            ? "READABLE"
            : "NOT_WORKING");

    Serial.print(
        "MQ-135             : ");

    Serial.println(
        mq135OK
            ? "READABLE"
            : "NOT_WORKING");

    Serial.print(
        "SW-420             : ");

    Serial.println(
        "WORKING");

    Serial.print(
        "NEO-6M GPS         : ");

    Serial.println(
        gpsFix
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "MicroSD            : ");

    Serial.println(
        sdOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "WiFi               : ");

    Serial.println(
        wifiOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "Telemetry Backend  : ");

    Serial.println(
        telemetryBackendOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "Audio Backend      : ");

    Serial.println(
        audioBackendOK
            ? "WORKING"
            : "NOT_WORKING");

    Serial.print(
        "Overall Hardware   : ");

    Serial.println(
        overallHardware
            ? "WORKING"
            : "NOT_WORKING");

    Serial.println(
        "============================================================");
}

// ============================================================
// SERIAL COMMANDS
// ============================================================

void processSerialCommands()
{
    if (!Serial.available())
    {
        return;
    }

    String input = Serial.readStringUntil('\n');
    input.trim();
    if (input.length() == 0)
    {
        return;
    }

    // Allow setting target PC backend IP directly from Serial Monitor without reflashing!
    // Example: "IP=192.168.43.150"
    if (input.startsWith("IP=") || input.startsWith("ip=") || input.startsWith("SET_IP="))
    {
        int eqIdx = input.indexOf('=');
        String newIP = input.substring(eqIdx + 1);
        newIP.trim();
        if (newIP.length() > 6)
        {
            activeServerIP = newIP;
            saveWiFiPreferences(activeWiFiSSID, activeWiFiPassword, activeServerIP, activeServerPort);
            Serial.println();
            Serial.println("============================================================");
            Serial.print("  [SUCCESS] PC Server IP updated to: ");
            Serial.println(activeServerIP);
            Serial.println("  Saved to NVS flash permanently.");
            Serial.println("  Testing live connection to backend now...");
            Serial.println("============================================================");
            bool ok = testBackendConnection();
            telemetryBackendOK = ok;
            updateLEDs(ok);
        }
        return;
    }

    char command = input.charAt(0);

    if (
        command == 'a' ||
        command == 'A')
    {
        Serial.println();

        Serial.println(
            "Manual audio AI inference requested.");

        performAudioInference();

        return;
    }

    if (
        command == 's' ||
        command == 'S')
    {
        printTelemetry();

        return;
    }

    if (
        command == 't' ||
        command == 'T')
    {
        Serial.println("\nTesting backend connection on demand...");
        bool ok = testBackendConnection();
        telemetryBackendOK = ok;
        updateLEDs(ok);
        return;
    }

    if (
        command == 'f' ||
        command == 'F')
    {
        Serial.println("\nStarting universal auto-discovery scan on local network...");
        bool found = autoDiscoverBackend();
        telemetryBackendOK = found;
        updateLEDs(found);
        return;
    }

    if (
        command == 'i' ||
        command == 'I')
    {
        Serial.println();
        Serial.println("================ NETWORK STATUS ================");
        Serial.print("Wi-Fi SSID       : "); Serial.println(activeWiFiSSID);
        Serial.print("ESP32 Local IP   : "); Serial.println(WiFi.localIP());
        Serial.print("Hotspot Gateway  : "); Serial.println(WiFi.gatewayIP());
        Serial.print("Subnet Mask      : "); Serial.println(WiFi.subnetMask());
        Serial.print("Target Server IP : "); Serial.println(activeServerIP);
        Serial.print("Target Port      : "); Serial.println(activeServerPort);
        Serial.print("Target URL       : "); Serial.println(getBaseURL());
        Serial.print("Telemetry Backend: "); Serial.println(telemetryBackendOK ? "ONLINE (200 OK)" : "OFFLINE / UNREACHABLE");
        Serial.println("================================================");
        return;
    }

    if (
        command == 'r' ||
        command == 'R')
    {
        Serial.println(
            "Restarting ESP32...");

        delay(500);

        ESP.restart();
    }

    if (
        command == 'w' ||
        command == 'W')
    {
        Serial.println(
            "Starting Web Configuration Portal...");

        startWiFiPortal();

        return;
    }
}

// ============================================================
// SETUP
// ============================================================

void setup()
{
    Serial.begin(115200);

    delay(1500);

    Serial.println();

    Serial.println(
        "================================================");

    Serial.println(
        " AURAFOREST ADAPTIVE EDGE AI");

    Serial.println(
        " ESP32-S3 EDGE NODE");

    // Pre-allocate 5-second 160 KB audio buffer immediately before heap fragments
    if (psramFound())
    {
        audioBuffer = (int16_t *)ps_malloc(AUDIO_BUFFER_BYTES);
    }
    if (audioBuffer == nullptr)
    {
        audioBuffer = (int16_t *)heap_caps_malloc(AUDIO_BUFFER_BYTES, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
    }
    if (audioBuffer == nullptr)
    {
        audioBuffer = (int16_t *)malloc(AUDIO_BUFFER_BYTES);
    }

    if (audioBuffer != nullptr)
    {
        Serial.print("Audio buffer allocated successfully: ");
        Serial.print(AUDIO_BUFFER_BYTES / 1024);
        Serial.println(" KB (5-second 16kHz PCM)");
    }
    else
    {
        Serial.println("WARNING: Audio buffer heap allocation deferred.");
    }

    // ----------------------------------------------------------
    // GPIO / ADC
    // ----------------------------------------------------------

    analogReadResolution(12);

    analogSetPinAttenuation(
        MQ2_PIN,
        ADC_11db);

    analogSetPinAttenuation(
        MQ135_PIN,
        ADC_11db);

    pinMode(
        MQ2_PIN,
        INPUT);

    pinMode(
        MQ135_PIN,
        INPUT);

    pinMode(
        VIBRATION_PIN,
        INPUT);

    pinMode(
        GREEN_LED,
        OUTPUT);

    pinMode(
        RED_LED,
        OUTPUT);

    digitalWrite(
        GREEN_LED,
        LOW);

    digitalWrite(
        RED_LED,
        LOW);

    // ----------------------------------------------------------
    // I2C
    // ----------------------------------------------------------

    Wire.begin(
        PIN_SDA,
        PIN_SCL);

    Wire.setTimeOut(50);

    // ----------------------------------------------------------
    // DHT11
    // ----------------------------------------------------------

    dht.begin();

    delay(1000);

    // ----------------------------------------------------------
    // MAX17048
    // ----------------------------------------------------------

    max17048OK =
        initMAX17048();

    // ----------------------------------------------------------
    // BH1750
    // ----------------------------------------------------------

    bh1750OK =
        initBH1750();

    // ----------------------------------------------------------
    // GPS
    // ----------------------------------------------------------

    GPSSerial.begin(
        9600,
        SERIAL_8N1,
        GPS_RX,
        GPS_TX);

    // ----------------------------------------------------------
    // MICROPHONE
    // ----------------------------------------------------------

    microphoneOK =
        initMicrophone();

    // (audioBuffer already allocated at boot)

    // ----------------------------------------------------------
    // MICROSD
    // ----------------------------------------------------------

    sdOK =
        initSD();

    // ----------------------------------------------------------
    // WIFI
    // ----------------------------------------------------------

    connectWiFi();

    Serial.println();

    Serial.println(
        "Hardware initialization complete.");

    // ----------------------------------------------------------
    // INITIAL SENSOR READINGS
    // ----------------------------------------------------------

    readDHT();

    lightLux =
        readBH1750();

    readBattery();

    readVibration();

    microphoneLevel =
        readMicrophone();

    readGasSensors();

    readGPS();

    // ----------------------------------------------------------
    // INITIAL STATUS
    // ----------------------------------------------------------

    printTelemetry();

    // ----------------------------------------------------------
    // BACKEND CONNECTION TEST
    // ----------------------------------------------------------

    if (wifiOK)
    {
        bool backendAvailable =
            testBackendConnection();

        telemetryBackendOK =
            backendAvailable;

        updateLEDs(
            backendAvailable);
    }

    // ----------------------------------------------------------
    // SERIAL COMMAND HELP
    // ----------------------------------------------------------

    Serial.println();

    Serial.println(
        "============================================================");

    Serial.println(
        "COMMANDS");

    Serial.println(
        "  A           = Manual 5s audio + AI inference");

    Serial.println(
        "  S           = Print telemetry");

    Serial.println(
        "  T           = Test backend connection");

    Serial.println(
        "  F           = Universal Auto-Discover backend on any local network");

    Serial.println(
        "  I           = Show network status and IPs");

    Serial.println(
        "  IP=x.x.x.x  = Set PC backend IP directly (e.g. IP=192.168.43.150)");

    Serial.println(
        "  W           = Open Wi-Fi / Hotspot Web Setup Portal (http://192.168.4.1)");

    Serial.println(
        "  R           = Restart ESP32");

    Serial.println(
        "============================================================");
}

// ============================================================
// LOOP
// ============================================================

void loop()
{
    if (wifiPortalActive)
    {
        dnsServer.processNextRequest();
        configServer.handleClient();
    }

    uint32_t now =
        millis();

    // ----------------------------------------------------------
    // SERIAL COMMANDS
    // ----------------------------------------------------------

    processSerialCommands();

    // ----------------------------------------------------------
    // GPS MUST BE SERVICED CONTINUOUSLY
    // ----------------------------------------------------------

    readGPS();

    // ----------------------------------------------------------
    // WIFI MAINTENANCE
    // ----------------------------------------------------------

    maintainWiFi();

    // ----------------------------------------------------------
    // AUTOMATIC CONTINUOUS AUDIO AI DETECTION
    // ----------------------------------------------------------
    //
    // Automatically performs:
    //   1. Capture 5 seconds of microphone audio
    //   2. Send raw PCM16 audio to FastAPI
    //   3. Receive and parse AI inference
    //   4. Start the next detection cycle
    //
    // The A serial command remains available for manual testing.

    if (
        automaticAudioDetection &&
        microphoneOK &&
        WiFi.status() == WL_CONNECTED &&
        millis() >= nextAudioInference)
    {
        nextAudioInference =
            millis() + AUDIO_INFERENCE_INTERVAL;

        Serial.println();
        Serial.println(
            "############################################################");

        Serial.println(
            "        AUTOMATIC AUDIO AI DETECTION");

        Serial.println(
            "############################################################");

        Serial.println(
            "Starting continuous 5-second audio capture...");

        bool inferenceSuccess =
            performAudioInference();

        if (inferenceSuccess)
        {
            Serial.println();
            Serial.println(
                "Automatic audio inference completed successfully.");

            Serial.print(
                "Detected event: ");

            Serial.println(
                predictionLabel);

            Serial.print(
                "Confidence: ");

            Serial.print(
                predictionConfidence * 100.0f,
                2);

            Serial.println(
                " %");
        }
        else
        {
            Serial.println();
            Serial.println(
                "Automatic audio inference failed.");

            Serial.println(
                "Retrying automatically...");
        }

        Serial.println(
            "############################################################");
    }

    // ----------------------------------------------------------
    // SENSOR READINGS
    // ----------------------------------------------------------

    if (
        now - lastSensorRead >=
        SENSOR_INTERVAL)
    {
        lastSensorRead =
            now;

        readDHT();

        lightLux =
            readBH1750();

        readBattery();

        readVibration();

        readGasSensors();

        microphoneLevel =
            readMicrophone();

        readGPS();

        printTelemetry();
    }

    // ----------------------------------------------------------
    // TELEMETRY TRANSMISSION
    // ----------------------------------------------------------

    if (
        now - lastPost >=
        POST_INTERVAL)
    {
        lastPost =
            now;

        String json =
            createPayload();

        Serial.println();

        Serial.println(
            "--------------- JSON PAYLOAD ---------------");

        Serial.println(
            json);

        Serial.println(
            "---------------------------------------------");

        bool backendSuccess =
            sendToBackend(
                json);

        // --------------------------------------------------------
        // MICROSD FALLBACK
        // --------------------------------------------------------

        if (!backendSuccess)
        {
            saveToSD(json);
        }

        // --------------------------------------------------------
        // LED
        // --------------------------------------------------------

        updateLEDs(
            backendSuccess);
    }

    delay(10);
}