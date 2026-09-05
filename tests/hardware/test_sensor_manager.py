from hardware import (
    BatterySensor,
    EnvironmentalSensor,
    GPSSensor,
    HardwareSensorManager,
    LightSensor,
    LocationTelemetry,
    VibrationSensor,
)


class FakeBattery(BatterySensor):

    def read_battery_percent(self):
        return 82.5

    def read_battery_voltage(self):
        return 3.91


class FakeEnvironment(EnvironmentalSensor):

    def read_temperature(self):
        return 28.4

    def read_humidity(self):
        return 67.2


class FakeLight(LightSensor):

    def read_light_level(self):
        return 145.0


class FakeVibration(VibrationSensor):

    def vibration_detected(self):
        return False


class FakeGPS(GPSSensor):

    def read_location(self):
        return LocationTelemetry(
            latitude=12.2958,
            longitude=76.6394,
            altitude=770.0,
            accuracy=4.5,
        )


def test_sensor_manager_reads_all_sensors():

    manager = HardwareSensorManager(

        battery_sensor=FakeBattery(),

        environmental_sensor=FakeEnvironment(),

        light_sensor=FakeLight(),

        vibration_sensor=FakeVibration(),

        gps_sensor=FakeGPS(),

    )

    telemetry = manager.read_all()

    assert (
        telemetry.location.latitude
        == 12.2958
    )

    assert (
        telemetry.location.longitude
        == 76.6394
    )

    assert (
        telemetry.device_status.battery_percent
        == 82.5
    )

    assert (
        telemetry.device_status.battery_voltage
        == 3.91
    )

    assert (
        telemetry.device_status.temperature
        == 28.4
    )

    assert (
        telemetry.device_status.humidity
        == 67.2
    )

    assert (
        telemetry.device_status.light_level
        == 145.0
    )

    assert (
        telemetry.device_status.vibration_detected
        is False
    )


def test_sensor_manager_supports_missing_sensors():

    manager = HardwareSensorManager()

    telemetry = manager.read_all()

    assert telemetry.location is None

    assert telemetry.device_status.battery_percent is None

    assert telemetry.device_status.temperature is None

    assert telemetry.device_status.light_level is None

    assert telemetry.device_status.vibration_detected is None