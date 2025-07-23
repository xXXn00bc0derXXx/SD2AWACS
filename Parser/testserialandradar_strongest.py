import socket
import struct
import json
import serial
import threading
import time

# -------------------- CONFIG --------------------
RADAR_IP = "236.6.7.8"
RADAR_PORT = 6678
SERVER_IP = "104.248.6.221"
SERVER_PORT = 5005
SERIAL_PORT = "COM3"         # Replace as needed
BAUD_RATE = 4800
MAX_SERIAL_STEPS = 350
DISPLAY_EVERY_N_PACKETS = 100
# ------------------------------------------------

elevation_data = {"step": None, "angle": None}
stop_flag = False
ser = None

def step_to_angle(step, max_steps):
    step = max(0, min(step, max_steps))
    return (step / max_steps) * 60

def extract_uint16_le(data, offset):
    return data[offset] | (data[offset + 1] << 8)


def parse_radar_packet(data):
    if len(data) < 24 + 512:
        return {"error": "Packet too short"}

    header_len = data[8]
    status = data[9]
    scan_number = extract_uint16_le(data, 10)
    angle_raw = extract_uint16_le(data, 16)
    heading_raw = extract_uint16_le(data, 18)
    large_range = extract_uint16_le(data, 20)
    small_range = extract_uint16_le(data, 22)

    azimuth_degrees = angle_raw * 360 / 4096

    if large_range in (0x80, 0xFFFF):
        if small_range in (0xFFFF, 0x0000):
            range_meters = 0
        else:
            range_meters = small_range
    else:
        range_meters = (large_range * small_range) / 512

    bin_resolution_m = range_meters / 512
    strongest_index = max(range(512), key=lambda i: data[24 + i])
    strongest_strength = data[24 + strongest_index]
    strongest_range_nm = (strongest_index * bin_resolution_m) / 1852

    return {
        "header_length": header_len,
        "status": status,
        "scan_number": scan_number,
        "azimuth_raw": angle_raw,
        "azimuth_degrees": round(azimuth_degrees, 2),
        "heading_raw": heading_raw,
        "range_large": large_range,
        "range_small": small_range,
        "strongest_bin": strongest_index,
        "strongest_strength": strongest_strength,
        "strongest_range_nm": round(strongest_range_nm, 2),
        "doppler": None
    }

    if len(data) < 24:
        return {"error": "Packet too short"}

    header_len = data[8]
    status = data[9]
    scan_number = extract_uint16_le(data, 10)
    angle_raw = extract_uint16_le(data, 16)
    heading_raw = extract_uint16_le(data, 18)
    large_range = extract_uint16_le(data, 20)
    small_range = extract_uint16_le(data, 22)

    azimuth_degrees = angle_raw * 360 / 4096

    # Halo-specific range calculation
    if large_range == 0x80:
        if small_range == 0xFFFF:
            range_meters = 0
        else:
            range_meters = small_range / 4
    else:
        range_meters = (large_range * small_range) / 512

    # Clamp large ranges
    if range_meters > 68524:
        range_meters = 0

    range_nm = range_meters / 1852

    return {
        "header_length": header_len,
        "status": status,
        "scan_number": scan_number,
        "azimuth_raw": angle_raw,
        "azimuth_degrees": round(azimuth_degrees, 2),
        "heading_raw": heading_raw,
        "range_large": large_range,
        "range_small": small_range,
        "range_nm": round(range_nm, 2),
        "doppler": None
    }

def serial_reader():
    global stop_flag, elevation_data, ser
    max_observed_step = MAX_SERIAL_STEPS

    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[Serial] Listening on {SERIAL_PORT} at {BAUD_RATE} baud...")
            time.sleep(2)
            ser.write(b'1\n')  # Start signal

            while not stop_flag:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                try:
                    step = int(line)
                    if step > 1000:
                        step = 1
                    max_observed_step = max(max_observed_step, step)
                    angle = step_to_angle(step, max_observed_step)
                    elevation_data["step"] = step
                    elevation_data["angle"] = round(angle, 2)
                except ValueError:
                    continue
    except serial.SerialException as e:
        print(f"[Serial Error] {e}")

def input_listener():
    global stop_flag, ser
    while not stop_flag:
        cmd = input("Type '0' to stop: ").strip()
        #ser.write(b'0\n')
        if cmd == '0':
            stop_flag = True
            ser.write(b'0\n')
            print("Stopping...")

def start_combined_listener():
    # Start serial reading thread
    serial_thread = threading.Thread(target=serial_reader)
    serial_thread.daemon = True
    serial_thread.start()

    # Optional input stop thread
    input_thread = threading.Thread(target=input_listener)
    input_thread.daemon = True
    input_thread.start()

    # Setup radar UDP socket
    radar_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    radar_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    radar_sock.bind(('', RADAR_PORT))
    mreq = struct.pack("=4sl", socket.inet_aton(RADAR_IP), socket.INADDR_ANY)
    radar_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    # Setup outgoing socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print(f"[Radar] Listening on {RADAR_IP}:{RADAR_PORT}, forwarding to {SERVER_IP}:{SERVER_PORT}")

    packet_count = 0

    while not stop_flag:
        try:
            data, _ = radar_sock.recvfrom(65535)
            radar_data = parse_radar_packet(data)

            # Merge in elevation data
            radar_data["elevation_step"] = elevation_data.get("step")
            radar_data["elevation_angle"] = elevation_data.get("angle")

            server_message = json.dumps(radar_data)
            server_sock.sendto(server_message.encode(), (SERVER_IP, SERVER_PORT))

            packet_count += 1
            if packet_count % DISPLAY_EVERY_N_PACKETS == 0:
                print(server_message)

        except Exception as e:
            print(f"[Radar Error] {e}")

if __name__ == "__main__":
    start_combined_listener()
