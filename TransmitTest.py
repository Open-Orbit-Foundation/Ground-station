import time
import serial
from datetime import datetime

# ---------------- USER SETTINGS ----------------
SERIAL_PORT  = "/dev/tty.usbserial-0001"      # e.g. /dev/ttyS0 (Pi) or /dev/ttyUSB0
BAUD_RATE    = 9600             # 9600 is default for E22 UART modules
FREQ_MHZ     = 915              # 410–493 or 850–930 range
MY_ADDR      = 0                # this node’s address (0–65535)
DEST_ADDR    = 20               # destination node address
TX_POWER     = 10               # transmit power in dBm {10, 13, 17, 22}
MESSAGE      = "Hello from the ground station!"  # payload text
APPEND_CRLF  = False            # set True to add \r\n
SEND_HZ      = 0.2              # send frequency (Hz)
LISTEN       = False            # True = also print incoming messages
# ------------------------------------------------

class sx126x:
    def __init__(self, port, freq, addr, power):
        self.ser = serial.Serial(port, BAUD_RATE, timeout=0, write_timeout=2.0)
        self.addr = addr & 0xFFFF
        self.freq = freq
        self.power = power  # store for reference
        self.start_freq = 850 if freq >= 850 else 410
        self.offset_freq = int(freq - self.start_freq)

        # (Optional future step)
        # Here you could add a UART config command to actually set the power
        # Example: self.ser.write(b'\xC0\x00...') etc., per module datasheet

    def send(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def receive(self):
        if self.ser.in_waiting > 0:
            time.sleep(0.2)
            r = self.ser.read(self.ser.in_waiting)
            if len(r) >= 4:
                src_addr = (r[0]<<8) + r[1]
                freq = self.start_freq + r[2]
                msg = r[3:]
                print(f"RX from {src_addr} @ {freq} MHz: {msg.decode('utf-8', 'replace')}")

    def close(self):
        self.ser.close()

def build_frame(dest_addr, dest_freq_mhz, payload_bytes, node):
    base = 850 if dest_freq_mhz >= 850 else 410
    off  = int(dest_freq_mhz - base) & 0xFF
    d_hi, d_lo = (dest_addr>>8)&0xFF, dest_addr&0xFF
    my_hi, my_lo = (node.addr>>8)&0xFF, node.addr&0xFF
    my_off = node.offset_freq & 0xFF
    return bytes([d_hi,d_lo,off,my_hi,my_lo,my_off]) + payload_bytes

# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    node = sx126x(SERIAL_PORT, FREQ_MHZ, MY_ADDR, TX_POWER)
    payload = MESSAGE.encode('utf-8')
    if APPEND_CRLF:
        payload += b"\r\n"
    frame = build_frame(DEST_ADDR, FREQ_MHZ, payload, node)

    period = 1.0 / SEND_HZ
    count = 0
    print(f"Starting transmitter on {SERIAL_PORT} @ {BAUD_RATE} baud")
    print(f"RF: {FREQ_MHZ} MHz | TX Power: {TX_POWER} dBm | Addr: {MY_ADDR} → {DEST_ADDR}")
    print(f"Sending every {period:.2f}s")
    print("-"*60)
    try:
        t0 = time.perf_counter()
        while True:
            target = t0 + count * period
            if time.perf_counter() < target:
                time.sleep(0.01)
                if LISTEN:
                    node.receive()
                continue
            node.send(frame)
            count += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent #{count}")
            if LISTEN:
                node.receive()
    except KeyboardInterrupt:
        print("\nStopping transmitter…")
    finally:
        node.close()
        print("Serial port closed.")
