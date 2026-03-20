from time import sleep
import board
from digitalio import DigitalInOut
from adafruit_mcp2515 import MCP2515 as CAN

cs = DigitalInOut(board.CAN_CS)
cs.switch_to_output()

spi = board.SPI()

print("Creating CAN object...")
can = CAN(spi, cs, baudrate=500000, crystal_freq=16000000)

print("CAN initialized successfully")

while True:
    print("alive")
    sleep(1)