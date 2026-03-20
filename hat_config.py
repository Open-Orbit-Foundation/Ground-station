import serial
import time

SERIAL_PORT = "/dev/cu.usbserial-0001"
BAUD = 9600

def send_cmd(ser, data, pause=0.2):
    ser.reset_input_buffer()
    ser.write(bytes(data))
    ser.flush()
    time.sleep(pause)
    resp = ser.read_all()
    print(f"TX: {[hex(b) for b in data]}")
    print(f"RX: {[hex(b) for b in resp]}")
    return resp

with serial.Serial(SERIAL_PORT, BAUD, timeout=0.5) as ser:
    time.sleep(0.5)

    # read REG3
    send_cmd(ser, [0xC1, 0x06, 0x01])

    # set ADDH, ADDL, NETID = 0,0,0
    send_cmd(ser, [0xC0, 0x00, 0x03, 0x00, 0x00, 0x00])

    # set CH = 65 (915.125 MHz)
    send_cmd(ser, [0xC0, 0x05, 0x01, 0x41])

    # set REG3 = 0x00 (transparent, no RSSI byte, no relay, no LBT)
    send_cmd(ser, [0xC0, 0x06, 0x01, 0x00])

    # verify
    send_cmd(ser, [0xC1, 0x00, 0x07])