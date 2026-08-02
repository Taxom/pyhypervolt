from pyhypervolt.models import ControlState, Telemetry


def test_control_packet():
    state = ControlState.parse(bytes.fromhex("02 03"))
    assert state.speed == 2
    assert state.load_level == 3


def test_telemetry_packet():
    packet = bytes.fromhex("00 00 00 00 00 00 00 00 0E 48 05 E5 1B 00")
    data = Telemetry.parse(packet)
    assert data.motor_load_raw == 0x0E48
    assert data.battery_voltage == 15.09
    assert data.temperature_c == 27
    assert data.flags == 0
