from __future__ import annotations

# Functional lookup table recovered while documenting the Hypervolt 2 BLE
# interoperability protocol. See docs/protocol.md for provenance.
LOOKUP: tuple[int, ...] = (
    1, 128, 64, 32, 16, 8, 132, 66, 33, 144, 72, 164, 82, 41, 20, 10,
    133, 194, 97, 176, 88, 172, 214, 107, 53, 154, 205, 102, 51, 153, 76, 166,
    83, 169, 84, 42, 149, 202, 229, 242, 121, 60, 158, 207, 103, 179, 217, 108,
    182, 91, 45, 22, 11, 5, 130, 65, 160, 80, 40, 148, 74, 165, 210, 105,
    52, 26, 141, 70, 35, 145, 200, 228, 114, 57, 28, 142, 199, 227, 241, 248,
    252, 254, 255, 127, 63, 31, 15, 7, 131, 193, 224, 112, 56, 156, 206, 231,
    243, 249, 124, 190, 223, 111, 55, 155, 77, 38, 19, 137, 68, 34, 17, 136,
    196, 98, 49, 152, 204, 230, 115, 185, 92, 174, 215, 235, 117, 186, 221, 110,
    183, 219, 109, 54, 27, 13, 6, 3, 129, 192, 96, 48, 24, 140, 198, 99,
    177, 216, 236, 246, 123, 61, 30, 143, 71, 163, 209, 232, 244, 122, 189, 94,
    175, 87, 171, 85, 170, 213, 234, 245, 250, 253, 126, 191, 95, 47, 23, 139,
    69, 162, 81, 168, 212, 106, 181, 218, 237, 118, 59, 29, 14, 135, 195, 225,
    240, 120, 188, 222, 239, 119, 187, 93, 46, 151, 203, 101, 178, 89, 44, 150,
    75, 37, 146, 73, 36, 18, 9, 4, 2, 1, 128, 64, 32, 16, 8, 132,
    66, 33, 144, 72, 164, 82, 41, 20, 10, 133, 194, 97, 176, 88, 172, 214,
    107, 53, 154, 205, 102, 51, 153, 76, 166, 83, 169, 84, 42, 149, 202, 229,
)


def _signed_byte(value: int) -> int:
    return value - 256 if value >= 128 else value


def calculate_auth_response(mac_address: str, challenge: bytes) -> bytes:
    """Calculate the four-byte response for a Hypervolt 2 challenge.

    Args:
        mac_address: Six-byte Bluetooth address, such as ``10:20:30:40:50:60``.
        challenge: Four bytes read once from characteristic 4570.

    Returns:
        Four-byte response to write back to characteristic 4570.
    """
    if len(challenge) != 4:
        raise ValueError(f"Expected a 4-byte challenge, got {len(challenge)}")

    try:
        mac = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    except ValueError as exc:
        raise ValueError(f"Invalid MAC address: {mac_address}") from exc
    if len(mac) != 6:
        raise ValueError(f"Invalid MAC address: {mac_address}")

    b0, b1, b2 = challenge[-3:][::-1]
    m0, m1, m2, m3, m4, m5 = mac

    index1 = (m4 ^ b2) & 0xFF
    index2 = (_signed_byte(m2) & _signed_byte(b1)) & 0xFF
    index3 = (b0 ^ m5) & 0xFF

    value1 = (
        (_signed_byte(m5) | _signed_byte(m1))
        ^ _signed_byte(LOOKUP[index1] & 0xFF)
    ) & 0xFF
    out1 = (value1 >> (b0 & 1)) & 0xFF

    value2 = ((LOOKUP[index2] & 0xFFFF) + m3) & 0xFFFF
    out2 = (b2 ^ value2) & 0xFF

    value3 = (_signed_byte(m0) ^ _signed_byte(LOOKUP[index3] & 0xFF)) & 0xFF
    out3 = (value3 << (b1 & 1)) & 0xFF

    return bytes((0x01, out1, out2, out3))
