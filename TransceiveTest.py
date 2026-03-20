import time
import serial
import threading
from datetime import datetime

# ---------------- USER SETTINGS ----------------
SERIAL_PORT  = "/dev/cu.usbserial-0001"   # macOS usually prefers /dev/cu.*
BAUD_RATE    = 9600
FREQ_MHZ     = 915
MY_ADDR      = 0
DEST_ADDR    = 20
TX_POWER     = 10
MESSAGE      = "Hello from the ground station!"
APPEND_CRLF  = False
SEND_HZ      = 0.05
LISTEN       = True
RX_POLL_DT   = 0.05                       # seconds between receive polls
# ------------------------------------------------


class SX126x:
    def __init__(self, port, baud_rate, freq, addr, power):
        self.ser = serial.Serial(
            port=port,
            baudrate=baud_rate,
            timeout=0,            # nonblocking
            write_timeout=2.0
        )
        self.addr = addr & 0xFFFF
        self.freq = freq
        self.power = power
        self.start_freq = 850 if freq >= 850 else 410
        self.offset_freq = int(freq - self.start_freq)

        self._stop_event = threading.Event()
        self._rx_thread = None
        self._lock = threading.Lock()

    def send(self, data: bytes):
        with self._lock:
            self.ser.write(data)
            self.ser.flush()

    def receive_once(self):
        """
        Read whatever is currently available and parse one packet blob.
        Assumes received format:
            [src_hi, src_lo, freq_offset, payload...]
        """
        with self._lock:
            n = self.ser.in_waiting
            if n <= 0:
                return

            # Small pause can help let the UART buffer finish filling
            time.sleep(0.05)
            n = self.ser.in_waiting
            r = self.ser.read(n)

        if len(r) < 3:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] RX short/raw: {r!r}")
            return

        src_addr = (r[0] << 8) + r[1]
        freq = self.start_freq + r[2]
        msg = r[3:].decode("utf-8", errors="replace")

        print(f"[{datetime.now().strftime('%H:%M:%S')}] RX from {src_addr} @ {freq} MHz: {msg}")

    def _rx_loop(self):
        while not self._stop_event.is_set():
            try:
                self.receive_once()
            except serial.SerialException as e:
                print(f"\n[RX ERROR] Serial exception: {e}")
                self._stop_event.set()
                break
            except Exception as e:
                print(f"\n[RX ERROR] {e}")
            time.sleep(RX_POLL_DT)

    def start_receiver(self):
        if self._rx_thread is None or not self._rx_thread.is_alive():
            self._stop_event.clear()
            self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self._rx_thread.start()

    def stop_receiver(self):
        self._stop_event.set()
        if self._rx_thread is not None:
            self._rx_thread.join(timeout=1.0)

    def close(self):
        self.stop_receiver()
        with self._lock:
            if self.ser.is_open:
                self.ser.close()


def build_frame(dest_addr, dest_freq_mhz, payload_bytes, node):
    """
    TX frame format:
        [dest_hi, dest_lo, dest_freq_offset, my_hi, my_lo, my_freq_offset, payload...]
    """
    base = 850 if dest_freq_mhz >= 850 else 410
    off = int(dest_freq_mhz - base) & 0xFF

    d_hi = (dest_addr >> 8) & 0xFF
    d_lo = dest_addr & 0xFF
    my_hi = (node.addr >> 8) & 0xFF
    my_lo = node.addr & 0xFF
    my_off = node.offset_freq & 0xFF

    return bytes([d_hi, d_lo, off, my_hi, my_lo, my_off]) + payload_bytes


if __name__ == "__main__":
    node = SX126x(SERIAL_PORT, BAUD_RATE, FREQ_MHZ, MY_ADDR, TX_POWER)

    payload = MESSAGE.encode("utf-8")
    if APPEND_CRLF:
        payload += b"\r\n"

    frame = build_frame(DEST_ADDR, FREQ_MHZ, payload, node)

    period = 1.0 / SEND_HZ
    count = 0

    print(f"Starting transceiver on {SERIAL_PORT} @ {BAUD_RATE} baud")
    print(f"RF: {FREQ_MHZ} MHz | TX Power: {TX_POWER} dBm | Addr: {MY_ADDR} -> {DEST_ADDR}")
    print(f"Sending every {period:.2f} s")
    print(f"Parallel receive: {'ON' if LISTEN else 'OFF'}")
    print("-" * 60)

    try:
        if LISTEN:
            node.start_receiver()

        t0 = time.perf_counter()

        while True:
            target = t0 + count * period
            now = time.perf_counter()

            if now < target:
                time.sleep(min(0.01, target - now))
                continue

            node.send(frame)
            count += 1
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sent #{count}")

    except KeyboardInterrupt:
        print("\nStopping transceiver...")

    finally:
        node.close()
        print("Serial port closed.")