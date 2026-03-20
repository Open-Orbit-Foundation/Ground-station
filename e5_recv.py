import serial
import time
import re

PORT = "/dev/tty.usbserial-10"
BAUD = 9600
TIMEOUT = 0.2

# ---------------------------
# User-editable labeled config
# ---------------------------
CONFIG = {
    "frequency_mhz": 915.125,
    "spreading_factor": "SF7",
    "bandwidth_khz": 125,
    "rx_bandwidth_khz": 8,
    "bitrate_or_offset": 15,
    "power_dbm": 22,
    "crc": "ON",
    "iq_inverted": "OFF",
    "network_mode": "OFF",
}

SETUP_COMMANDS = [
    "AT",
    "AT+VER",
    "AT+MODE=TEST",
]

START_RX_COMMAND = "AT+TEST=RXLRPKT"

# More forgiving hex grab:
# Looks for quoted hex first, but not only in one exact line structure
QUOTED_HEX_RE = re.compile(r'"([0-9A-Fa-f]+)"')

# Also allow unquoted HEX after RX-ish text
RX_HEX_RE = re.compile(r'RX[^0-9A-Fa-f]*([0-9A-Fa-f]{8,})', re.IGNORECASE)

# Pull out RSSI / SNR loosely if present
RSSI_RE = re.compile(r'RSSI\s*[:=]\s*(-?\d+)', re.IGNORECASE)
SNR_RE = re.compile(r'SNR\s*[:=]\s*(-?\d+)', re.IGNORECASE)
LEN_RE = re.compile(r'LEN\s*[:=]\s*(\d+)', re.IGNORECASE)


def print_section(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72)


def clean_lines(text):
    """Split incoming serial text into stripped non-empty lines."""
    return [line.strip() for line in text.replace("\r", "").split("\n") if line.strip()]


def decode_hex_payload(hex_payload):
    """Decode hex payload to UTF-8 text if possible."""
    try:
        raw = bytes.fromhex(hex_payload)
        text = raw.decode("utf-8", errors="replace")
        return raw, text
    except Exception as e:
        return None, f"[decode error: {e}]"


def build_rfcfg_command(cfg):
    """
    Build:
    AT+TEST=RFCFG,freq,sf,bw,rx_bw,bitrate_or_offset,power,crc,iq,network
    """
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


def send_command(ser, cmd, delay=0.6, show_response=True):
    """Send AT command and optionally print cleaned response."""
    print(f"\n>>> {cmd}")
    ser.write((cmd + "\r\n").encode())
    ser.flush()
    time.sleep(delay)

    data = ser.read_all()
    text = data.decode(errors="replace")
    lines = clean_lines(text)

    if show_response:
        if lines:
            for line in lines:
                print(f"    {line}")
        else:
            print("    [no response]")

    return lines


def extract_hex_payload(line):
    """
    Try a few patterns to find hex payload in a flexible way.
    Returns hex string or None.
    """
    m = QUOTED_HEX_RE.search(line)
    if m:
        candidate = m.group(1)
        if len(candidate) % 2 == 0:
            return candidate

    m = RX_HEX_RE.search(line)
    if m:
        candidate = m.group(1)
        if len(candidate) % 2 == 0:
            return candidate

    return None


def extract_meta(line):
    """Loosely parse LEN/RSSI/SNR if present."""
    meta = {}

    m = LEN_RE.search(line)
    if m:
        meta["len"] = int(m.group(1))

    m = RSSI_RE.search(line)
    if m:
        meta["rssi"] = int(m.group(1))

    m = SNR_RE.search(line)
    if m:
        meta["snr"] = int(m.group(1))

    return meta


def process_line(line):
    """Print line, extract metadata, and decode payload if found."""
    print(line)

    meta = extract_meta(line)
    if meta:
        pretty = ", ".join(f"{k}={v}" for k, v in meta.items())
        print(f"    meta: {pretty}")

    hex_payload = extract_hex_payload(line)
    if hex_payload:
        raw, decoded = decode_hex_payload(hex_payload)
        print(f"    hex: {hex_payload}")
        print(f"    decoded: {decoded}")


def show_config(cfg):
    print_section("Current RFCFG labels")
    for key, value in cfg.items():
        print(f"{key:20s}: {value}")


def run_setup(ser, cfg):
    print_section("SX126x AT Setup")
    show_config(cfg)

    for cmd in SETUP_COMMANDS:
        send_command(ser, cmd)

    rfcfg = build_rfcfg_command(cfg)
    send_command(ser, rfcfg)

    send_command(ser, START_RX_COMMAND)


def listen_forever(ser):
    print_section("Listening for packets (Ctrl+C to stop)")
    buffer = ""

    try:
        while True:
            chunk = ser.read_all().decode(errors="replace")
            if chunk:
                print(f"\n[RAW CHUNK] {repr(chunk)}")
                buffer += chunk

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    process_line(line)

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nStopping listener...")


def main():
    with serial.Serial(PORT, BAUD, timeout=TIMEOUT) as ser:
        time.sleep(1.5)
        run_setup(ser, CONFIG)
        listen_forever(ser)


if __name__ == "__main__":
    main()