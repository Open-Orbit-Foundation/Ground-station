import time
import serial
import serial.tools.list_ports
from datetime import datetime

SERIAL_PORT  = "/dev/cu.usbserial-0001"
BAUD_RATE    = 9600

print("Available serial ports:")
for p in serial.tools.list_ports.comports():
    print(f"  {p.device}  |  {p.description}")
print("-" * 60)