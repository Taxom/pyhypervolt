from pyhypervolt.auth import calculate_auth_response


def test_known_auth_vectors():
    mac = "10:20:30:40:50:60"
    vectors = {
        bytes.fromhex("01 CA 6E 71"): bytes.fromhex("01 58 59 D2"),
        bytes.fromhex("01 52 DD FA"): bytes.fromhex("01 20 97 82"),
        bytes.fromhex("01 44 4A 59"): bytes.fromhex("01 1C 05 40"),
        bytes.fromhex("01 83 D7 1F"): bytes.fromhex("01 14 46 FC"),
    }
    for challenge, expected in vectors.items():
        assert calculate_auth_response(mac, challenge) == expected
