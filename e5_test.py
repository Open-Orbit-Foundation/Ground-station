import serial
import time

PORT = "/dev/tty.usbserial-11440"
BAUD = 9600
TIMEOUT = 0.5

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

USE_STRING_MODE = True   # 🔥 toggle this
USE_HEX_MODE = True     # optional parallel testing


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


def tx_string_packet(ser, text, delay=1.0):
    cmd = f'AT+TEST=TXLRSTR,"{text}"'
    return send_command(ser, cmd, delay)


def tx_hex_packet(ser, text, delay=1.0):
    payload = text.encode("utf-8")
    hex_payload = payload.hex().upper()
    cmd = f"AT+TEST=TXLRPKT,{hex_payload}"
    return send_command(ser, cmd, delay)


def generate_text(length):
    """Generate readable repeating text of exact length."""
    base = "THE_QUICK_BROWN_FOX_JUMPS_OVER_THE_LAZY_DOG_"
    text = (base * ((length // len(base)) + 1))[:length]
    return text


def main():
    while True:
        with serial.Serial(PORT, BAUD, timeout=TIMEOUT) as ser:
            time.sleep(1.5)

            send_command(ser, "AT")
            send_command(ser, "AT+VER")
            send_command(ser, "AT+MODE=TEST")
            send_command(ser, build_rfcfg_command(CONFIG))

            # progressively increase text size
            sizes = [10, 20, 30, 40, 50, 60, 80, 100, 120]

            for n in sizes:
                text = generate_text(n)

                print("\n" + "=" * 60)
                print(f"Sending TEXT length: {n}")
                print(f"Actual string: {text}")
                print("=" * 60)

                if USE_STRING_MODE:
                    print("\n--- STRING MODE ---")
                    tx_string_packet(ser, text, delay=1.2)

                if USE_HEX_MODE:
                    print("\n--- HEX MODE ---")
                    tx_hex_packet(ser, text, delay=1.2)


if __name__ == "__main__":
    main()