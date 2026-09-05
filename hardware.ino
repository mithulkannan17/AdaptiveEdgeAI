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
#include <HTTPClient.h>

#include <ArduinoJson.h>
#include <DHT.h>
#include <TinyGPSPlus.h>

#include "driver/i2s.h"

// ============================================================
// DEVICE CONFIGURATION
// ============================================================

#define DEVICE_ID "edge_node_telemetry_001"

// ============================================================
// WIFI CONFIGURATION
// ============================================================

const char *WIFI_SSID = "HomeFiber";
const char *WIFI_PASSWORD = "kannan17";

// ============================================================
// BACKEND CONFIGURATION
// ============================================================

const char *SERVER_IP = "192.168.29.244";

const uint16_t SERVER_PORT = 8000;

const char *API_PATH =
    "/api/v1/edge/telemetry";

/*
  IMPORTANT:

  Change this ONLY if your FastAPI audio route
  has a different path.
*/
const char *AUDIO_API_PATH =
    "/api/v1/edge/audio";

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
        I2S_BITS_PER_SAMPLE_32BIT,

    .channel_format =
        I2S_CHANNEL_FMT_ONLY_LEFT,

    .communication_format =
        I2S_COMM_FORMAT_I2S,

    .intr_alloc_flags =
        ESP_INTR_FLAG_LEVEL1,

    .dma_buf_count = 4,

    .dma_buf_len = 256,

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

bool automaticAudioDetection = true;

// Small gap between completed inference cycles.
const uint32_t AUDIO_INFERENCE_INTERVAL = 1000;

uint32_t nextAudioInference = 0;

const uint32_t SENSOR_INTERVAL = 2000;

const uint32_t POST_INTERVAL = 5000;

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

    int32_t rawSamples[256];

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
              inside a 32-bit I2S word.

              Shift down to obtain a usable
              signed PCM16 representation.
            */

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

void connectWiFi()
{
    Serial.println();

    Serial.println(
        "Connecting to WiFi...");

    WiFi.mode(WIFI_STA);

    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD);

    uint32_t start =
        millis();

    while (
        WiFi.status() != WL_CONNECTED &&
        millis() - start < 15000)
    {
        delay(500);

        Serial.print(".");
    }

    Serial.println();

    if (
        WiFi.status() == WL_CONNECTED)
    {
        wifiOK = true;

        Serial.println(
            "WiFi connected.");

        Serial.print(
            "ESP32 IP: ");

        Serial.println(
            WiFi.localIP());

        Serial.print(
            "Gateway: ");

        Serial.println(
            WiFi.gatewayIP());
    }
    else
    {
        wifiOK = false;

        Serial.println(
            "WiFi connection failed.");
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
        WIFI_SSID,
        WIFI_PASSWORD);
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
// BACKEND CONNECTION TEST
// ============================================================

bool testBackendConnection()
{
    if (
        WiFi.status() != WL_CONNECTED)
    {
        return false;
    }

    String healthURL =
        "http://" +
        String(SERVER_IP) +
        ":" +
        String(SERVER_PORT) +
        "/health";

    Serial.println();

    Serial.println(
        "Testing backend connection...");

    Serial.println(
        healthURL);

    HTTPClient http;

    http.setTimeout(5000);

    bool beginResult =
        http.begin(
            healthURL);

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

    http.end();

    return (
        code >= 200 &&
        code < 300);
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
        "http://" +
        String(SERVER_IP) +
        ":" +
        String(SERVER_PORT) +
        String(API_PATH);

    HTTPClient http;

    http.setTimeout(5000);

    bool beginResult =
        http.begin(url);

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
        "http://" +
        String(SERVER_IP) +
        ":" +
        String(SERVER_PORT) +
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

    http.setTimeout(30000);

    bool beginResult =
        http.begin(url);

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

      80,000 samples x 2 bytes
      = 160,000 bytes
    */

    if (audioBuffer == nullptr)
    {
        audioBuffer =
            (int16_t *)
                malloc(
                    AUDIO_BUFFER_BYTES);
    }

    if (audioBuffer == nullptr)
    {
        Serial.println(
            "ERROR: Unable to allocate 160 KB audio buffer.");

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

    char command =
        Serial.read();

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
        command == 'r' ||
        command == 'R')
    {
        Serial.println(
            "Restarting ESP32...");

        delay(500);

        ESP.restart();
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

    Serial.println(
        "================================================");

    // ----------------------------------------------------------
    // GPIO
    // ----------------------------------------------------------

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
        "  A = Manual 5s audio + AI inference");

    Serial.println(
        "  S = Print telemetry");

    Serial.println(
        "  R = Restart ESP32");

    Serial.println(
        "============================================================");
}

// ============================================================
// LOOP
// ============================================================

void loop()
{
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