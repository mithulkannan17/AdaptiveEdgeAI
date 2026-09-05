#include <Arduino.h>
#include <driver/i2s.h>

#define I2S_PORT I2S_NUM_0

#define I2S_BCLK 4
#define I2S_WS   5
#define I2S_DIN  6

#define SAMPLE_RATE 16000
#define SAMPLE_COUNT 256

void setup() {

    Serial.begin(115200);

    delay(1000);

    Serial.println();
    Serial.println("================================");
    Serial.println("INMP441 I2S TEST");
    Serial.println("================================");

    i2s_config_t i2s_config = {

        .mode =
            (i2s_mode_t)(
                I2S_MODE_MASTER |
                I2S_MODE_RX
            ),

        .sample_rate =
            SAMPLE_RATE,

        .bits_per_sample =
            I2S_BITS_PER_SAMPLE_32BIT,

        .channel_format =
            I2S_CHANNEL_FMT_ONLY_LEFT,

        .communication_format =
            I2S_COMM_FORMAT_I2S,

        .intr_alloc_flags =
            ESP_INTR_FLAG_LEVEL1,

        .dma_buf_count =
            8,

        .dma_buf_len =
            256,

        .use_apll =
            false,

        .tx_desc_auto_clear =
            false,

        .fixed_mclk =
            0
    };

    i2s_pin_config_t pin_config = {

        .bck_io_num =
            I2S_BCLK,

        .ws_io_num =
            I2S_WS,

        .data_out_num =
            I2S_PIN_NO_CHANGE,

        .data_in_num =
            I2S_DIN
    };

    esp_err_t result;

    result = i2s_driver_install(
        I2S_PORT,
        &i2s_config,
        0,
        nullptr
    );

    if (result != ESP_OK) {

        Serial.print(
            "I2S driver install failed: "
        );

        Serial.println(result);

        return;
    }

    result = i2s_set_pin(
        I2S_PORT,
        &pin_config
    );

    if (result != ESP_OK) {

        Serial.print(
            "I2S pin configuration failed: "
        );

        Serial.println(result);

        return;
    }

    i2s_zero_dma_buffer(
        I2S_PORT
    );

    Serial.println(
        "I2S microphone initialized."
    );

    Serial.println(
        "Reading samples..."
    );
}

void loop() {

    int32_t samples[SAMPLE_COUNT];

    size_t bytes_read = 0;

    esp_err_t result = i2s_read(
        I2S_PORT,
        samples,
        sizeof(samples),
        &bytes_read,
        portMAX_DELAY
    );

    if (result != ESP_OK) {

        Serial.print(
            "I2S read failed: "
        );

        Serial.println(result);

        delay(1000);

        return;
    }

    int sample_count =
        bytes_read / sizeof(int32_t);

    int64_t sum_abs = 0;

    int32_t minimum =
        INT32_MAX;

    int32_t maximum =
        INT32_MIN;

    for (
        int i = 0;
        i < sample_count;
        i++
    ) {

        // INMP441 data is 24-bit audio
        // contained inside a 32-bit frame.
        int32_t sample =
            samples[i] >> 8;

        if (sample < minimum) {
            minimum = sample;
        }

        if (sample > maximum) {
            maximum = sample;
        }

        sum_abs +=
            abs(sample);
    }

    float average_abs =
        sample_count > 0
            ? (float)sum_abs / sample_count
            : 0.0f;

    Serial.print(
        "Samples: "
    );

    Serial.print(
        sample_count
    );

    Serial.print(
        " | Min: "
    );

    Serial.print(
        minimum
    );

    Serial.print(
        " | Max: "
    );

    Serial.print(
        maximum
    );

    Serial.print(
        " | AvgAbs: "
    );

    Serial.println(
        average_abs
    );

    delay(100);
}