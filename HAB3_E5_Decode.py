import serial
import time
import re
import struct

PORT = "/dev/tty.usbserial-10"
BAUD = 9600
TIMEOUT = 0.2

CONFIG = {
    "frequency_mhz": 915.125,
    "spreading_factor": "SF11",
    "bandwidth_khz": 125,
    "rx_bandwidth_khz": 8,
    "bitrate_or_offset": 15,
    "power_dbm": 14,
    "crc": "ON",
    "iq_inverted": "OFF",
    "network_mode": "OFF",
}

# -----------------------------
# Packet type IDs
# Update these to match telemetry.h exactly.
# -----------------------------
LORA_PKT_NAV = 0xA1
LORA_PKT_SENSORS = 0xA2
LORA_PKT_CAN_RELAY = 0xA3

# -----------------------------
# Health flags
# Update these if your bit positions differ.
# -----------------------------

TELEMETRY_HEALTH_BMP280   = 1 << 0
TELEMETRY_HEALTH_TMP117   = 1 << 1
TELEMETRY_HEALTH_HWELL    = 1 << 2
TELEMETRY_HEALTH_BNO086   = 1 << 3
TELEMETRY_HEALTH_MAXM10S  = 1 << 4
TELEMETRY_HEALTH_CAN      = 1 << 5
TELEMETRY_HEALTH_GPS_FIX  = 1 << 6
TELEMETRY_HEALTH_IMU_DATA = 1 << 7

# -----------------------------
# Struct layouts from packed C structs
# little-endian, packed
# -----------------------------
# struct __packed lora_pkt_nav {
#   uint8_t  type;
#   uint8_t  health_flags;
#   uint32_t timestamp_ms;
#   unit32_t utc timestamp hhmmss
#   uint8_t  fix_quality;
#   int32_t  lat_deg_e7;
#   int32_t  lon_deg_e7;
#   int32_t  alt_mm;
#   int32_t speed_knots_x100;
#   int32_t course_deg_x100;
# };
NAV_FMT = "<BBIIBiiiii"
NAV_LEN = struct.calcsize(NAV_FMT)

# struct __packed lora_pkt_sensors {
#   uint8_t  type;
#   uint8_t  health_flags;
#   uint32_t timestamp_ms;
#   int32_t  bmp_temp_c_x100;
#   uint32_t bmp_press_pa_x256;
#   int32_t  tmp_temp_c_x1000;
#   int32_t  hwell_press_pa;
#   int32_t  hwell_temp_c_x100;
# };
SENS_FMT = "<BBIiIiii"
SENS_LEN = struct.calcsize(SENS_FMT)

# Earlier CAN relay packet shape, inferred from your C:
# struct lora_pkt_can_relay {
#   uint8_t  type;
#   uint8_t  dlc;
#   uint32_t timestamp_ms;
#   uint32_t can_counter;
#   uint32_t can_id;
#   uint8_t  data[8];
# };
CAN_FMT = "<BBIII8s"
CAN_LEN = struct.calcsize(CAN_FMT)

rx_re = re.compile(r'\+TEST:\s*RX\s*"([0-9A-Fa-f]+)"')


def clean_lines(text):
    return [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]


def send_command(ser, cmd, delay=0.5):
    print(f"\n>>> {cmd}")
    ser.write((cmd + "\r\n").encode("ascii"))
    ser.flush()
    time.sleep(delay)

    resp = ser.read_all().decode(errors="replace")
    lines = clean_lines(resp)

    if lines:
        for line in lines:
            print("   ", line)
    else:
        print("    [no response]")

    return lines


def build_rfcfg_command(cfg):
    return (
        "AT+TEST=RFCFG,"
        f"{cfg['frequency_mhz']},"
        f"{cfg['spreading_factor']},"
        f"{cfg['bandwidth_khz']},"
        f"{cfg['rx_bandwidth_khz']},"
        f"{cfg['bitrate_or_offset']},"
        f"{cfg['power_dbm']},"
        f"{cfg['crc']},"
        f"{cfg['iq_inverted']},"
        f"{cfg['network_mode']}"
    )


def health_flags_to_names(flags: int):
    names = []
    if flags & TELEMETRY_HEALTH_BMP280:
        names.append("BMP280")
    if flags & TELEMETRY_HEALTH_TMP117:
        names.append("TMP117")
    if flags & TELEMETRY_HEALTH_HWELL:
        names.append("HWELL")
    if flags & TELEMETRY_HEALTH_BNO086:
        names.append("BNO086")
    if flags & TELEMETRY_HEALTH_MAXM10S:
        names.append("MAXM10S")
    if flags & TELEMETRY_HEALTH_CAN:
        names.append("CAN")
    if flags & TELEMETRY_HEALTH_GPS_FIX:
        names.append("GPS_FIX")
    if flags & TELEMETRY_HEALTH_IMU_DATA:
        names.append("IMU_DATA")
    return names


def format_latlon_e7(value_e7: int) -> float:
    return value_e7 / 1e7


def format_alt_mm(value_mm: int) -> float:
    return value_mm / 1000.0


def decode_nav_packet(payload: bytes):
    if len(payload) < NAV_LEN:
        raise ValueError(f"NAV packet too short: got {len(payload)} bytes, need {NAV_LEN}")

    pkt_type, health,  timestamp_ms,utc, fix_quality,lat_e7, lon_e7, alt_mm, speed,course  = struct.unpack(
        NAV_FMT, payload[:NAV_LEN]
    )

    return {
        "packet_name": "NAV",
        "type": pkt_type,
        "health_flags": health,
        "health_names": health_flags_to_names(health),
        "timestamp_ms": timestamp_ms,
        "lat_deg_e7": lat_e7,
        "lon_deg_e7": lon_e7,
        "alt_mm": alt_mm,
        "lat_deg": format_latlon_e7(lat_e7),
        "lon_deg": format_latlon_e7(lon_e7),
        "alt_m": format_alt_mm(alt_mm),
        "speed": speed,
        "course": course/100,
        "fix_quality": fix_quality,
    }


def decode_sensor_packet(payload: bytes):
    if len(payload) < SENS_LEN:
        raise ValueError(f"SENSOR packet too short: got {len(payload)} bytes, need {SENS_LEN}")

    (
        pkt_type,
        health,
        timestamp_ms,
        bmp_temp_c_x100,
        bmp_press_pa_x256,
        tmp_temp_c_x1000,
        hwell_press_pa,
        hwell_temp_c_x100,
    ) = struct.unpack(SENS_FMT, payload[:SENS_LEN])

    return {
        "packet_name": "SENSORS",
        "type": pkt_type,
        "health_flags": health,
        "health_names": health_flags_to_names(health),
        "timestamp_ms": timestamp_ms,
        "bmp_temp_c_x100": bmp_temp_c_x100,
        "bmp_temp_c": bmp_temp_c_x100 / 100.0,
        "bmp_press_pa_x256": bmp_press_pa_x256,
        "bmp_press_pa": bmp_press_pa_x256 / 256.0,
        "tmp_temp_c_x1000": tmp_temp_c_x1000,
        "tmp_temp_c": tmp_temp_c_x1000 / 1000.0,
        "hwell_press_pa": hwell_press_pa,
        "hwell_temp_c_x100": hwell_temp_c_x100,
        "hwell_temp_c": hwell_temp_c_x100 / 100.0,
    }


def decode_can_relay_packet(payload: bytes):
    if len(payload) < CAN_LEN:
        raise ValueError(f"CAN relay packet too short: got {len(payload)} bytes, need {CAN_LEN}")

    pkt_type, dlc, timestamp_ms, can_counter, can_id, data_bytes = struct.unpack(CAN_FMT, payload[:CAN_LEN])
    data_list = list(data_bytes[:dlc])

    return {
        "packet_name": "CAN_RELAY",
        "type": pkt_type,
        "dlc": dlc,
        "timestamp_ms": timestamp_ms,
        "can_counter": can_counter,
        "can_id": can_id,
        "data_bytes_full": list(data_bytes),
        "data_bytes_used": data_list,
    }


def decode_packet(payload: bytes):
    if len(payload) < 1:
        raise ValueError("Empty payload")

    pkt_type = payload[0]

    if pkt_type == LORA_PKT_NAV:
        return decode_nav_packet(payload)
    elif pkt_type == LORA_PKT_SENSORS:
        return decode_sensor_packet(payload)
    elif pkt_type == LORA_PKT_CAN_RELAY:
        return decode_can_relay_packet(payload)
    else:
        return {
            "packet_name": "UNKNOWN",
            "type": pkt_type,
            "raw_hex": payload.hex().upper(),
            "length": len(payload),
        }


def pretty_print_packet(pkt: dict):
    print("\n" + "=" * 72)
    print(f"Decoded Packet: {pkt['packet_name']} (type=0x{pkt['type']:02X})")

    if pkt["packet_name"] == "NAV":
        print(f"  timestamp_ms : {pkt['timestamp_ms']}")
        print(f"  health_flags : 0x{pkt['health_flags']:02X} -> {pkt['health_names']}")
        print(f"  lat          : {pkt['lat_deg']:.7f} deg")
        print(f"  lon          : {pkt['lon_deg']:.7f} deg")
        print(f"  alt          : {pkt['alt_m']:.3f} m")
        print(f"  speed        : {pkt['speed']:.3f}")
        print(f"  course       : {pkt['course']:.3f}")
        print(f"  fix_quality  : {pkt['fix_quality']}")

    elif pkt["packet_name"] == "SENSORS":
        print(f"  timestamp_ms : {pkt['timestamp_ms']}")
        print(f"  health_flags : 0x{pkt['health_flags']:02X} -> {pkt['health_names']}")
        print(f"  BMP temp     : {pkt['bmp_temp_c']:.2f} C")
        print(f"  BMP press    : {pkt['bmp_press_pa']:.2f} Pa")
        print(f"  TMP117 temp  : {pkt['tmp_temp_c']:.3f} C")
        print(f"  HWELL press  : {pkt['hwell_press_pa']} Pa")
        print(f"  HWELL temp   : {pkt['hwell_temp_c']:.2f} C")

    elif pkt["packet_name"] == "CAN_RELAY":
        print(f"  timestamp_ms : {pkt['timestamp_ms']}")
        print(f"  can_counter  : {pkt['can_counter']}")
        print(f"  can_id       : 0x{pkt['can_id']:03X}")
        print(f"  dlc          : {pkt['dlc']}")
        print(f"  data         : {' '.join(f'{b:02X}' for b in pkt['data_bytes_used'])}")

    else:
        print(f"  raw length   : {pkt['length']}")
        print(f"  raw hex      : {pkt['raw_hex']}")

    print("=" * 72)


def configure_receiver(ser):
    send_command(ser, "AT")
    send_command(ser, "AT+VER")
    send_command(ser, "AT+MODE=TEST")
    send_command(ser, build_rfcfg_command(CONFIG))
    send_command(ser, "AT+TEST=RXLRPKT", delay=0.8)


def main():
    with serial.Serial(PORT, BAUD, timeout=TIMEOUT) as ser:
        time.sleep(1.5)

        configure_receiver(ser)

        print("\nListening for LoRa packets... Ctrl+C to stop.\n")

        buffer = ""

        try:
            while True:
                chunk = ser.read_all().decode(errors="replace")
                if chunk:
                    buffer += chunk

                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()
                        if not line:
                            continue

                        print(line)

                        m = rx_re.search(line)
                        if not m:
                            continue

                        hex_payload = m.group(1)

                        try:
                            payload = bytes.fromhex(hex_payload)
                        except ValueError:
                            print("  [decode error] RX payload was not valid hex")
                            continue

                        try:
                            decoded = decode_packet(payload)
                            pretty_print_packet(decoded)
                        except Exception as e:
                            print(f"  [packet decode error] {e}")
                            print(f"  raw hex: {hex_payload}")

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\nStopping receiver.")


if __name__ == "__main__":
    main()