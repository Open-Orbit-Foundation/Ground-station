# hab_main.py
# High-Altitude Balloon Main Script

# === General Purpose ===
import os
import sys
import csv
import time
import threading
from datetime import datetime
import logging
from typing import Optional
import json

# === Raspberry Pi Hardware ===
import board
import busio
import RPi.GPIO as GPIO

# === Serial / GPS ===
import serial
import devices.sx126x as sx126x

# === Sensor Modules ===
from devices.bno08x_sensor import BNO08xSensor #Accelerometer, Gyroscope, Magnometer
from devices.mcp9600_sensor import MCP9600Sensor #Thermocouple
from devices.bosch_pressure_sensor import BoschPressureSensor #Pressure 
from adafruit_ina260 import INA260 #Power Sensor

# === Camera ===
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder


# === Set Up Console Logger ==
# Options:
#   - logging.DEBUG: Log more detailed system debug info (variable states, etc.)
#   - logging.INFO: Log info about system status (processes starting, inits failing, etc.)
#   - logging.WARNING: Only log warnings about system issues
#
# A given logging level will also log all levels below it
LOGGING_LEVEL = logging.INFO
logger = logging.getLogger(__name__)


#region Sensors

def init_sensors(debug=False):
    """
    Initializes all system sensors.
    
    Args:
        debug (bool): Flag for printing debug information.

    Returns:
        dict: Dictionary of sensors. Sensors that failed to initialize have a value of None.
    
    """
    logger.info("[Init] Starting sensor initialization...")
    sensors = {}

    # === Shared I2C Bus ===
    logger.info("[Init] Attempting to initialze I2C board...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
       
        while not i2c.try_lock():
            time.sleep(0.01)
        i2c.unlock()
        logger.info("[Init] I2C bus ready.")
    except Exception as e:
        logger.info(f"[Init] Failed to initialize I2C bus: {e}")
        return {} # break return none sensors, we are cooked


    # === BNO08x IMU (on I2C bus) ===
    MAX_IMU_INIT_ATTEMPTS = 5
    imu_init_attempt = 0
    logger.info(f"[BNO08x] Attempting to initialize IMU...")

    while imu_init_attempt < MAX_IMU_INIT_ATTEMPTS:
        logger.debug(f"[BNO08x] Attempt {imu_init_attempt + 1}...")
        sensors["bno"] = BNO08xSensor(i2c)
        time.sleep(0.1)
        if sensors["bno"] is None:
            imu_init_attempt += 1
            continue
        else:
            break
    if sensors["bno"] is None:
        logger.info("[BNO08x] All attempts failed. Continuing without IMU.")


    # === MCP9600 Thermocouple 1 ===
    sensors["mcp_1"] = MCP9600Sensor(i2c,0x67)
    time.sleep(0.5)

    # === MCP9600 Thermocouple 2 ===
    sensors["mcp_2"] = MCP9600Sensor(i2c,0x65)
    time.sleep(0.5)

    # === Bosch Pressure Sensor (SSCDANN015PA2A3) ===
    try:
        bosch_address = 0x28
        sensors["bosch"] = BoschPressureSensor(i2c, bosch_address) # default address=0x28, p_min=-15, p_max=15
        time.sleep(0.5)
        logger.info("[Bosch] SSCDANN015PA2A3 initialized successfully.")
    except Exception as e:
        logger.info("[Bosch] SSCDANN015PA2A3 failed to initialize.")

    # === Adafruit INA260 Current and Poewr Sensor ===
    try:
        sensors["ina260"] = INA260(i2c) # default address=0x40
        time.sleep(0.5)
        logger.info("[INA260] INA260 initialized successfully.")
    except Exception as e:
        logger.info(f"[INA260] INA260 failed to initialize.")

    logger.info("[Init] Sensor initialization complete.")
    return sensors

def sensor_logger(sensors, log_dir):
    CSV_DURATION = 600  # seconds = 10 minutes
    os.makedirs(log_dir, exist_ok=True)

    def timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def write_header(writer):
        writer.writerow([
            "timestamp",
            "mcp_1_temp[C]", "mcp_2_temp[C]",
            "bosch_pressure[Psi]", "bosch_temp[C]",
            "accel_x[m/s2]", "accel_y[m/s2]", "accel_z[m/s2]",
            "gyro_x[deg/s]", "gyro_y[deg/s]", "gyro_z[deg/s]",
            "mag_x[muT]", "mag_y[muT]", "mag_z[muT]",
            "quat_i", "quat_j", "quat_k", "quat_real",
            "current[mA]", "voltage[V]", "power[mW]"
        ])

    fname = os.path.join(log_dir, f"sensors_{timestamp()}.csv")
    logger.info(f"[Logging]: Creating log file {fname}...")
    f = open(fname, "w", newline="")
    writer = csv.writer(f)
    write_header(writer)

    start_time = time.time()
    next_split = start_time + CSV_DURATION

    while True:
        now = time.time()

        # Rotate file if needed
        if now >= next_split:
            f.close()
            fname = os.path.join(log_dir, f"sensors_{timestamp()}.csv")
            logger.info(f"[Logging]: Moving to new log file {fname}...")
            f = open(fname, "w", newline="")
            writer = csv.writer(f)
            write_header(writer)
            next_split = now + CSV_DURATION

        row = [datetime.now().isoformat()]

        # === MCP9600 ===
        try:
            row.append(sensors["mcp_1"].read_temperature())
            row.append(sensors["mcp_2"].read_temperature())
        except:
            row.append(None)

        # === Bosch Sensor ===
        try:
            pressure, temp = sensors["bosch"].read_data()
            row.append(pressure)
            row.append(temp)
        except:
            row += [None, None]

        # === BNO08x IMU ===
        try:
            imu = sensors["bno"]
            row += list(imu.read_accel())
            row += list(imu.read_gyro())
            row += list(imu.read_mag())
            row += list(imu.read_quat())
        except:
            row += [None] * (3 + 3 + 3 + 4)

        # === INA260 ===
        try:
            row.append(sensors["ina260"].current)
            row.append(sensors["ina260"].voltage)
            row.append(sensors["ina260"].power)
        except:
            row.append(None)
            row.append(None)
            row.append(None)

        writer.writerow(row)
        f.flush()
        logger.debug("[Logging] Log cycle completed.")
        time.sleep(1)

#endregion Sensors

#region GPS

#==========================================================================


#!/usr/bin/env python3
# gps_to_lora.py
#
# Reads NMEA sentences from a hardware UART (e.g., /dev/ttyAMA1 or AMA2)
# and transmits them over an SX126x LoRa HAT on /dev/ttyAMA0.
#
# Notes:
# - Disable the Linux serial console on BOTH ports you use (raspi-config).
# - Wiring:
#     GPS TX -> Pi RX pin of the UART you've enabled (e.g., UART2 RX on GPIO5)
#     GPS GND -> Pi GND
# - LoRa HAT jumpers: remove M0/M1 jumpers per your board docs (as in your code).
#
# Controls:
# - Ctrl+C to quit.
# - Everything else is automatic: every valid NMEA line gets forwarded.


# ------------------- CONFIG -------------------

# GPS side (change to "/dev/ttyAMA2" if that's your UART):
GPS_PORT = "/dev/ttyAMA1"          # e.g. AMA1 or AMA2 depending on overlay
GPS_BAUD = 9600
GPS_TIMEOUT_S = 1.0                 # readline timeout

# LoRa side:
LORA_PORT = "/dev/ttyAMA0"          # your HAT UART
LORA_FREQ_MHZ = 915                 # 410–493 or 850–930 MHz supported by your HAT
LORA_ADDR = 1                       # this node address
LORA_POWER_DBM = 22                 # {10, 13, 17, 22}
LORA_AIR_SPEED = 2400               # per your working config
LORA_RSSI_PRINT = True
LORA_RELAY = False

# Forwarding:
FORWARD_ONLY_VALID_NMEA = True      # only send lines that pass checksum
FILTER_TALKERS = None               # e.g. set to {"GNRMC","GNGGA"} to only forward these
TX_MAX_RATE_HZ = 1                 # safety limiter in case input floods
# ---------------------------------------------

# TODO: restructure this into inheritance (OOP in python ;-;)
class Packet:
    class GPS_Packet:
        class GGA_Packet:
            def __init__(self):
                self.time = None
                self.lat = None
                self.ns_ind = None
                self.long = None
                self.ew_ind = None
                self.pos_fix = None
                self.sats = None
                self.hdop = None
                self.msl = None
                self.msl_units = None
                self.geo_sep = None
                self.geo_sep_units = None
                self.aodc = None
                self.checksum = None
            
            def __str__(self):
                return ",".join(str(x) if x is not None else "" for x in [
                    self.time, self.lat, self.long, self.pos_fix, self.msl
                ])

        class GSA_Packet:
            def __init__(self):
                self.mode_1 = None
                self.mode_2 = None
                self.num_sats = None
                self.sats = None # list
                self.pdop = None
                self.hdop = None
                self.vdop = None
                self.checksum = None
            
            def __str__(self):
                sats_str = ";".join(map(str, self.sats)) if self.sats else ""
                return ",".join(str(x) if x is not None else "" for x in [
                    self.mode_1, self.mode_2, self.num_sats, sats_str,
                    self.pdop, self.hdop, self.vdop, self.checksum
                ])

        class GSV_Packet:
            def __init__(self):
                self.num_msg = None
                self.msg_1 = None
                self.num_sats = None
                self.sats = None # list of list kms
                self.checksum = None

            def __str__(self):
                sats_str = ";".join(",".join(map(str, sat)) for sat in self.sats) if self.sats else ""
                return ",".join(str(x) if x is not None else "" for x in [
                    self.num_msg, self.msg_1, self.num_sats, sats_str, self.checksum
                ])

        class RMC_Packet:
            def __init__(self):
                self.time = None
                self.status = None
                self.lat = None
                self.ns_ind = None
                self.long = None
                self.ew_ind = None
                self.gnd_spd = None
                self.gnd_course = None
                self.date = None
                self.mag_var = None
                self.mode = None
                self.checksum = None
            
            def __str__(self):
                return ",".join(str(x) if x is not None else "" for x in [
                    self.time, self.status, self.lat, self.long, self.gnd_spd, self.gnd_course
                ])

        class VTG_Packet:
            def __init__(self):
                self.course_1 = None
                self.ref_1 = None
                self.course_2 = None
                self.ref_2 = None
                self.speed_1 = None
                self.units_1 = None
                self.speed_2 = None
                self.units_2 = None
                self.mode = None
                self.checksum = None

            def __str__(self):
                return ",".join(str(x) if x is not None else "" for x in [
                    self.course_1, self.ref_1, self.course_2, self.ref_2,
                    self.speed_1, self.units_1, self.speed_2, self.units_2,
                    self.mode, self.checksum
                ])
        
        
        def __init__(self):
            self.gga = self.GGA_Packet()
            self.gsa = self.GSA_Packet()
            self.gsv = self.GSV_Packet()
            self.rmc = self.RMC_Packet()
            self.vtg = self.VTG_Packet()
        
        def __str__(self):
            return "GPGGA," + str(self.gga) + ";GPRMC," + str(self.rmc)

    def __init__(self):
        self.gps = self.GPS_Packet()

    def __str__(self):
        return str(self.gps)

class ClassEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)

def nmea_is_valid(line: str) -> bool:
    """
    Validate NMEA sentence checksum: $...*HH
    """
    if len(line) < 9:  # minimal $x*HH
        return False
    if line[0] != '$':
        return False
    star = line.rfind('*')
    if star == -1 or star > len(line) - 3:
        return False
    try:
        sent_sum = int(line[star+1:star+3], 16)
    except ValueError:
        return False
    calc = 0
    for ch in line[1:star]:
        calc ^= ord(ch)
    return calc == sent_sum

def nmea_talker(line: str) -> Optional[str]:
    """
    Return the 5-char talker+type, e.g., 'GPRMC','GNGGA', or None if malformed.
    $XXYYY, where talker=XX, type=YYY
    """
    if not line.startswith('$'):
        return None
    star = line.find('*')
    comma = line.find(',')
    end = star if star != -1 else len(line)
    head = line[1:end]
    if len(head) < 5:
        return None
    return head[:5]

def calc_checksum(message: str):
    checksum = 0
    for char in message:checksum ^= ord(char)
    return hex(checksum)[2:].upper()

def pass_to_gps(ser: serial.Serial, message: str):
    try:
        ser.write(f"${message}*{calc_checksum(message)}<CR><LF>\r\n".encode('utf-8'))
    except Exception as e:
        logger.warning(f"Message Failed to Send to GPS: {e}")

def wait_for_response(ser: serial.Serial, expected: str, timeout: float = 3.0):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            line = ser.readline().decode("utf-8", errors="replace").strip()
            if expected in line:
                return line
        except Exception as e:
            logger.warning(f"Error reading from GPS: {e}")
            break
    return None

def set_gps(ser: serial.Serial, query: str, set: str, ret: str, arg: str, intent: str):
    logger.info(f"Attempting to {intent}...")
    pass_to_gps(ser, query)
    response = wait_for_response(ser, ret)
    if response is None:
        logger.warning("No response received for query.")
        return
    if f"{ret},{arg}" in response:
        return
    pass_to_gps(ser, f"{set},{arg}")
    time.sleep(0.2)
    pass_to_gps(ser, query)
    if wait_for_response(ser, f"{ret},{arg}"):
        return
    else:
        logger.warning(f"Failed to {intent}")
        
def gps_reader(port: str, baud: int, timeout: float, packet: Packet, stop_evt: threading.Event):
    try:
        ser = serial.Serial(
            port,
            baud,
            timeout=timeout,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
        )
        logger.info(f"[GPS] Opened {port} @ {baud}.")
        # clean buffers
        try:
            ser.reset_input_buffer()
            ser.reset_output_buffer()
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"[GPS] Failed to open {port}: {e}")
        stop_evt.set()
        return

#This is where we set GPS settings (send packets over UART to chip; see datasheet) ===serial.write(sentence.encode('utf-8'))===
#Need to set differential GPD (DGPS) toimprove location accuracy (currently set to A=automatic a.k.a. not DGPS)
#Query all settings prior to set and after to confirm, throw exceptions ===readout===
    #PMTK251 --> Set_NMEA_Port_Baud_Rate xx ===this HAS to be before DGPS, gets reset with cold start===
    #PMTK301 --> API_Set_DGPS_Mode xx
    #PMTK313 --> API_Set_SBAS_Enabled xx
    #PMTK314 --> API_Set_NMEA_Out
    #PMTK319 --> API_Set_SBAS_Mode xx
    #PMTK104 --> Full_Cold_Start ===optional before EVERYTHING===
    #PMTK607 --> Query EPO (ephemeris) data to check time coverage --> determine if download is needed
    #PMTK127 --> Clear EPO data (manual; all)
    #PMTK330 --> Set Datum (verify WGS84) xx


    try:
        logger.info("==========Configuring GPS (PA1616S)==========") #sometimes requires a rerun if it does not finish cold restart

        # Reset to factory settings, not necessary every time
        # set_gps(ser, "PMTK104", "PMTK104", "PMTK010", "001", "Cold Restart")
        # print("Cold Restart Completed")
        # time.sleep(1)

        pass_to_gps(ser, f"PMTK220,{1000}")

        pass_to_gps(ser, f"PMTK251,{baud}")
        logger.info(f"NMEA baud set to: {baud}")

        set_gps(ser, "PMTK401", "PMTK301", "PMTK501", "2", "set DGPS to WAAS")
        logger.info("DGPS set to: WAAS")

        set_gps(ser, "PMTK413", "PMTK313", "PMTK513", "1", "enable SBAS")
        logger.info("SBAS: enabled")

        set_gps(ser, "PMTK419", "PMTK319", "PMTK519", "1", "set SBAS to Integrity Mode")
        logger.info("SBAS set to: Integrity Mode")

        set_gps(ser, "PMTK430", "PMTK330", "PMTK530", "0", "set Datum to WGS84")
        logger.info("Datum set to: WGS84")

#=======================finish settings====================================

    except Exception as e:
        logger.warning(f"[GPS] Reader error: {e}")



    try:
        while not stop_evt.is_set():
            raw = ser.readline()  # up to \n or timeout
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            # filter?
            talker = nmea_talker(line)
            if FORWARD_ONLY_VALID_NMEA and not nmea_is_valid(line):
                continue
            if FILTER_TALKERS:
                if (talker is None) or (talker not in FILTER_TALKERS):
                    continue

            #print(line)
            #print("============================")
            line_data = line.split(',')
            
            #out_q.put(line)  # push whole NMEA sentence (without trailing \n)
            #print(line)
            #print(line_data)
            #print(talker)
            match talker:
                case 'GPGGA':
                    packet.gps.gga.time = line_data[1]
                    packet.gps.gga.lat = line_data[2]
                    packet.gps.gga.ns_ind = line_data[3]
                    packet.gps.gga.long = line_data[4]
                    packet.gps.gga.ew_ind = line_data[5]
                    packet.gps.gga.pos_fix = line_data[6]
                    packet.gps.gga.sats = line_data[7]
                    packet.gps.gga.hdop = line_data[8]
                    packet.gps.gga.msl = line_data[9]
                    packet.gps.gga.msl_units = line_data[10]
                    packet.gps.gga.geo_sep = line_data[11]
                    packet.gps.gga.geo_sep_units = line_data[12]
                    packet.gps.gga.aodc = line_data[13]
                    packet.gps.gga.checksum = line_data[14]
                case 'GPGSA':
                    #print(len(line_data))
                    packet.gps.gsa.mode_1 = line_data[1]
                    packet.gps.gsa.mode_2 = line_data[2]
                    packet.gps.gsa.num_sats = line_data[3]
                    packet.gps.gsa.sats = line_data[4:-4] # TODO: confirm this is a static length, using -4 index makes it variable
                    packet.gps.gsa.pdop = line_data[-4]
                    packet.gps.gsa.hdop = line_data[-3]
                    packet.gps.gsa.vdop = line_data[-2]
                    packet.gps.gsa.checksum = line_data[-1]
                case 'GPGSV':
                    packet.gps.gsv.num_msg = line_data[1]
                    packet.gps.gsv.msg_1 = line_data[2]
                    if len(line_data) > 4:
                        packet.gps.gsv.num_sats = line_data[3]
                        packet.gps.gsv.sats = line_data[4:-2]
                    #     packet.gps.gsv.sats = []
                    #     for i in range(4):
                    #         if(len(line_data) >= 4 + 4*i):
                    #             packet.gps.gsv.sats.append(line_data[4*i:(4*i)+4])
                            # packet.gps.gsv.sats = [line_data[4:8], line_data[8:12], line_data[12:16], line_data[16:20]]
                    
                    packet.gps.gsv.checksum = line_data[-1]
                case 'GPRMC':
                    packet.gps.rmc.time = line_data[1]
                    packet.gps.rmc.status = line_data[2]
                    packet.gps.rmc.lat = line_data[3]
                    packet.gps.rmc.ns_ind = line_data[4]
                    packet.gps.rmc.long = line_data[5]
                    packet.gps.rmc.ew_ind = line_data[6]
                    packet.gps.rmc.gnd_spd = line_data[7]
                    packet.gps.rmc.gnd_course = line_data[8]
                    packet.gps.rmc.date = line_data[9]
                    packet.gps.rmc.mag_var = line_data[10]
                    packet.gps.rmc.mode = line_data[11]
                    packet.gps.rmc.checksum = line_data[12]
                case 'GPVTG':
                    packet.gps.vtg.course_1 = line_data[1]
                    packet.gps.vtg.ref_1 = line_data[2]
                    packet.gps.vtg.course_2 = line_data[3]
                    packet.gps.vtg.ref_2 = line_data[4]
                    packet.gps.vtg.speed_1 = line_data[5]
                    packet.gps.vtg.units_1 = line_data[6]
                    packet.gps.vtg.speed_2 = line_data[7]
                    packet.gps.vtg.units_2 = line_data[8]
                    packet.gps.vtg.mode = line_data[9]
                    packet.gps.vtg.checksum = line_data[10]
                case _:
                    raise AssertionError # hacky change this, only done since we know it won't be thrown by something else   

    except AssertionError as e:
        logger.warning(f"[GPS] Unexpected header error: {e}")

    except Exception as e:
        logger.warning(f"[GPS] Reader error: {e}")
    finally:
        try:
            ser.close()
        except Exception:
            logger.warning("[GPS] Erorr occured when closing the serial port.")
        logger.info("[GPS] Port closed.")

#endregion GPS

#region Radio

def build_lora_frame(node, payload: bytes, dst_addr: int = 0xFFFF) -> bytes:
    """
    Match your earlier header format:
      [dst_hi][dst_lo][dst_offset][src_hi][src_lo][src_offset] + payload
    """
    return bytes([ (dst_addr >> 8) & 0xFF ]) + \
           bytes([  dst_addr        & 0xFF ]) + \
           bytes([ node.offset_freq ]) + \
           bytes([ (node.addr >> 8) & 0xFF ]) + \
           bytes([  node.addr       & 0xFF ]) + \
           bytes([ node.offset_freq ]) + \
           payload

def lora_sender(node, packet: Packet, stop_evt: threading.Event): #in_q: queue.Queue
    logger.info("[LoRa] Sender up; forwarding NMEA to air.")
    last_tx = 0.0
    min_dt = 1.0 / max(1.0, float(TX_MAX_RATE_HZ))
    try:
        while not stop_evt.is_set():
            line = str(packet)

            now = time.time()
            if now - last_tx < min_dt:
                # simple rate limit to avoid saturation
                time.sleep(min_dt - (now - last_tx))
            last_tx = time.time()

            payload = (line).encode("utf-8", errors="replace")
            logger.debug(payload)
            frame = build_lora_frame(node, payload, dst_addr=0xFFFF)  # broadcast
            logger.debug(frame)

            try:
                node.send(frame)
                # Light receiver polling to print RSSI (per your rssi=True)
                node.receive()
            except Exception as e:
                logger.warning(f"[LoRa] Send error: {e}")
    except Exception as e:
        logger.warning(f"[LoRa] Sender thread error: {e}")



 #===================================================================

#endregion Radio

#region Camera

def timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def camera_thread(save_dir):
    VIDEO_DURATION = 600
    os.makedirs(save_dir, exist_ok=True)

    cam = Picamera2()
    cam.configure(cam.create_video_configuration(main={"size": (640, 480)}))
    cam.start()
    time.sleep(2)

    encoder = H264Encoder()

    while True:
        try:
            fname = os.path.join(save_dir, f"video_{timestamp()}.h264")
            logger.info(f"[Camera] Recording to {fname}")
            cam.start_recording(encoder, output=fname)
            time.sleep(VIDEO_DURATION)
            cam.stop_recording()
        except Exception as e:
            logger.warning(f"[Camera] Error: {e}")
            time.sleep(5)

#endregion Camera

def shutdown_monitor(timeout_sec=10800):
    DISABLE_PIN = 21  # BCM numbering (GPIO21 = pin 40)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(DISABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    logger.info(f"[Shutdown] Timer armed for {timeout_sec} seconds.")
    remaining = timeout_sec
    last_check = time.time()

    while True:
        now = time.time()
        dt = now - last_check
        last_check = now

        if GPIO.input(DISABLE_PIN):  # Pulled HIGH (inactive)
            remaining -= dt
            if remaining <= 0:
                logger.critical("[Shutdown] Timer expired. Initiating shutdown.")
                os.system("sudo shutdown -h now")
                break
        else:  # Jumper pulled LOW
            remaining = timeout_sec  # Reset the countdown

        time.sleep(1)


def main():
    # Init logging
    if LOGGING_LEVEL == logging.DEBUG:
        logging_format = '%(asctime)s - [%(filename)s] - %(levelname)s: %(message)s'
    else:
        logging_format = '%(asctime)s - %(levelname)s: %(message)s'
    log_formatter = logging.Formatter(logging_format)

    log_folder = 'status_logs'
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, timestamp())

    log_file_handler = logging.FileHandler(log_file, 'a')
    log_file_handler.setLevel(LOGGING_LEVEL)

    log_stream_handler = logging.StreamHandler()
    log_stream_handler.setLevel(LOGGING_LEVEL)

    logging.basicConfig(
        handlers=[log_file_handler, log_stream_handler],
        level=logging.DEBUG, # overall minimum severity to log
        format=logging_format
    )


    # Init LoRa node (matches your working parameters)
    try:
        logger.info("[LoRa] Initializing SX126x…")
        node = sx126x.sx126x(
            serial_num=LORA_PORT,
            freq=LORA_FREQ_MHZ,
            addr=LORA_ADDR,
            power=LORA_POWER_DBM,
            rssi=LORA_RSSI_PRINT,
            air_speed=LORA_AIR_SPEED,
            relay=LORA_RELAY
        )
        # Read/print settings just like your script
        node.get_settings()
    except Exception as e:
        logger.warning(f"[LoRa] Failed to init SX126x on {LORA_PORT}: {e}")
        sys.exit(1)

    # Queue + threads
    #q_lines: queue.Queue[str] = queue.Queue(maxsize=256)
    packet = Packet()
    stop_evt = threading.Event()

    launch_datetime = timestamp()
    video_dir = os.path.join("flight_video", launch_datetime)
    log_dir = os.path.join("flight_logs", launch_datetime) 

    sensors = init_sensors()
    t_sense = threading.Thread(target=sensor_logger, args=(sensors, log_dir), daemon=True)
    t_gps = threading.Thread(target=gps_reader, args=(GPS_PORT, GPS_BAUD, GPS_TIMEOUT_S, packet, stop_evt), daemon=True) ################
    t_tx  = threading.Thread(target=lora_sender, args=(node, packet, stop_evt), daemon=True)
    t_cam = threading.Thread(target=camera_thread, args=(video_dir,), daemon=True)
    t_shutdown = threading.Thread(target=shutdown_monitor, daemon=True)
    #sens_thread = threading.Thread(target=I2C_HAART_2_out.main, args=(), daemon=True) #TESTING PURPOSES

    t_sense.start()
    t_gps.start()
    t_tx.start()
    t_cam.start()
    t_shutdown.start()
    #sens_thread.start()

    logger.info("\n[Run] Forwarding GPS → LoRa. Press Ctrl+C to stop.\n")
    try:
        while True:
            # keep LoRa receive service alive even if no GPS lines (RSSI prints, etc.)
            node.receive()
            time.sleep(0.1)
    except KeyboardInterrupt:
        logger.warning("\n[Run] Stopping…")
    finally:
        stop_evt.set()
        t_gps.join(timeout=2.0)
        t_tx.join(timeout=2.0)
        #sens_thread.join(timeout=2.0)
        logger.info("[Run] Done.")

if __name__ == "__main__":
    main()
 

