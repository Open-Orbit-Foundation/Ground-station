#!/usr/bin/env python3
"""
Ground Station Control Interface
Receives and displays demodulated signals from E22900t22s LoRa module
"""

import serial
import sys
import time
import argparse
import socket

# Configuration for E22900t22s module
SERIAL_PORT = 'COM5'  # Adjust for your system (COM port on Windows, /dev/ttyUSB0 or /dev/serial0 on Linux)
BAUD_RATE = 9600      # Default baud rate for E22 modules
TIMEOUT = 1           # Serial read timeout in seconds

def configure_e22_channel(ser, chan):
    """Configure E22-900T22S channel (persistent). Requires module in CONFIG mode (M0=1, M1=1)."""
    # Read current params
    ser.reset_input_buffer()
    ser.write(bytes([0xC1, 0x00, 0x09]))
    ser.flush()
    params = ser.read(9)
    if len(params) != 9:
        raise RuntimeError("Failed to read E22 parameters (ensure M0=1, M1=1)")
    params = bytearray(params)
    # CHAN is index 6 for E22/E220 (base 850 MHz + CHAN)
    params[6] = chan & 0xFF
    # Write back persistently
    ser.write(bytes([0xC0, 0x00, 0x09]) + params)
    ser.flush()
    # Brief check: re-read
    time.sleep(0.1)
    ser.write(bytes([0xC1, 0x00, 0x09]))
    ser.flush()
    verify = ser.read(9)
    if len(verify) != 9 or verify[6] != (chan & 0xFF):
        raise RuntimeError("Verify failed setting channel; check wiring and mode")


def read_hat_channel(ser):
    """Read channel using LoRa-HAT control map (Begin=0x05, Len=0x01)."""
    ser.reset_input_buffer()
    # Read: C1 05 01
    ser.write(bytes([0xC1, 0x05, 0x01]))
    ser.flush()
    resp = ser.read(4)
    if len(resp) != 4 or resp[0] != 0xC1 or resp[1] != 0x05 or resp[2] != 0x01:
        raise RuntimeError("HAT read channel failed: bad response header")
    return resp[3]


def write_hat_channel(ser, chan, persistent=True):
    """Set channel using LoRa-HAT control map. persistent=True uses C0; else C2."""
    head = 0xC0 if persistent else 0xC2
    # Command: [head, 0x05, 0x01, chan]
    ser.reset_input_buffer()
    ser.write(bytes([head, 0x05, 0x01, (chan & 0xFF)]))
    ser.flush()
    # Expect echo: C1 05 01 <chan>
    ack = ser.read(4)
    if len(ack) != 4 or ack[0] != 0xC1 or ack[1] != 0x05 or ack[2] != 0x01 or ack[3] != (chan & 0xFF):
        raise RuntimeError("HAT write channel failed: no/invalid ACK (check M0/M1 and wiring)")
    # Verify via readback
    verify = read_hat_channel(ser)
    if verify != (chan & 0xFF):
        raise RuntimeError("HAT verify failed setting channel; check wiring and mode")


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--set-chan', type=int, help='Set RF channel (MHz = 850 + CHAN). Example: 915MHz -> 65')
    parser.add_argument('--set-915', action='store_true', help='Shortcut to set channel for 915 MHz (CHAN=65)')
    parser.add_argument('--hat', action='store_true', help='Use LoRa-HAT register map (C0/C1/C2 @ Begin=0x05,Len=0x01)')
    parser.add_argument('--udp', action='store_true', help='Print decoded payloads from UDP instead of serial (RTL-SDR demod)')
    parser.add_argument('--udp-host', default='0.0.0.0', help='UDP bind host (default 0.0.0.0)')
    parser.add_argument('--udp-port', type=int, default=16886, help='UDP bind port (default 16886)')
    args, _ = parser.parse_known_args()
    
    try:
        # Validate pyserial import (avoid conflict with the wrong 'serial' package)
        if not hasattr(serial, 'Serial'):
            raise ImportError("PySerial not available (wrong 'serial' package installed)")
        
        ser = None

        if args.udp:
            # UDP mode: print decoded payloads arriving via UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((args.udp_host, args.udp_port))
            sock.settimeout(0.2)
            print(f"Listening UDP on {args.udp_host}:{args.udp_port}...")
        else:
            # Open serial connection
            ser = serial.Serial(
                port=SERIAL_PORT,
                baudrate=BAUD_RATE,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=TIMEOUT
            )

        # Optional: configure RF channel
        if args.set_915 or args.set_chan is not None:
            target_chan = 65 if args.set_915 else int(args.set_chan)
            print(f"Setting RF channel to {target_chan} (≈ {850 + target_chan} MHz)...")
            try:
                if args.hat:
                    write_hat_channel(ser, target_chan, persistent=True)
                else:
                    configure_e22_channel(ser, target_chan)
                print("RF channel set successfully. Return module to normal mode (M0=0,M1=0). Exiting.")
                return
            except Exception as cfg_e:
                print(f"[ERROR] Channel set failed: {cfg_e}")
                print("Ensure M0=1 and M1=1 (CONFIG mode) and try again.")
                return

        # Minimal receiver: print only decoded payloads
        while True:
            if args.udp:
                try:
                    payload, _ = sock.recvfrom(65535)
                except socket.timeout:
                    time.sleep(0.05)
                    continue
                try:
                    decoded = payload.decode('utf-8', errors='ignore').strip()
                    if decoded:
                        print(decoded)
                except Exception:
                    pass
            else:
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    try:
                        decoded = data.decode('utf-8', errors='ignore').strip()
                        if decoded:
                            print(decoded)
                    except Exception:
                        pass
                time.sleep(0.1)  # Small delay to prevent CPU overload

    
    except KeyboardInterrupt:
        print("\n\nShutting down ground station...")
        try:
            if 'ser' in locals() and ser:
                ser.close()
            if 'sock' in locals() and sock:
                sock.close()
        except Exception:
            pass
        sys.exit(0)
    
    except Exception as e:
        msg = str(e)
        # Common pitfall: wrong 'serial' package installed instead of 'pyserial'
        if 'PySerial not available' in msg or 'object has no attribute' in msg:
            print("[ERROR] PySerial not available or wrong module loaded.")
            print("Fix:")
            print("  1) pip uninstall serial")
            print("  2) pip install pyserial")
            print("  3) Ensure no local file named 'serial.py' shadows PySerial")
        else:
            print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
