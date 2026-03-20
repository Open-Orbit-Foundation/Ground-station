import time
import serial
from datetime import datetime

SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD_RATE = 9600

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.1)

print(f"Listening on {SERIAL_PORT} @ {BAUD_RATE} baud...")
print("-" * 60)

try:
    while True:
        data = ser.read(ser.in_waiting or 1)
        if data:
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] RX raw: {data!r}")
            try:
                print(f"[{ts}] RX text: {data.decode('utf-8', errors='replace')}")
            except Exception:
                pass
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nStopping listener...")

finally:
    ser.close()
    print("Serial port closed.")