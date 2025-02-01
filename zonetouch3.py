import socket
import logging
import math
import time
LOGGER = logging.getLogger("ZoneTouch3")

class Zonetouch3:

    def __init__(self, address: str, port: int, zone: str) -> None:
        self._address = address
        self._port = port
        self._zone = zone
        self._state = False
        self._percentage = 0

    def crc16_modbus (self, hex_data: str) -> str:
        poly = 0xA001
        crc = 0xFFFF

        data = bytes.fromhex(hex_data)
        for b in data:
            crc ^= b
            for i in range(8):
                if crc & 0x0001:
                   crc = (crc >> 1) ^ poly
                else:
                    crc >>=1
        return format(crc, "04x")

    def hex_string(self, hex_data: list) -> str:
        return ''.join([str(item) for item in hex_data])

    def hex_to_int(self, hex_data: str) -> int:
        return int(hex_data, 16)

    def int_to_hex(self, num: int) -> str:
        # Ensure the number is whole
        if not isinstance(num, int) or num < 0:
            raise ValueError("The number must be a whole, non-negative integer.")

        return hex(num)[2:]

    def hex_to_ascii(self, hex_data: str) -> str:
        byte_string = bytearray.fromhex(hex_data).decode('utf-8')
        return byte_string.strip('\x00')

    def extract_data(self, hex_data: str, offset: int, length: int) -> str:
        bytepairs = [hex_data[i:i+2] for i in range(0, len(hex_data), 2)]

        data = self.hex_string(bytepairs[offset:(offset + length)])

        return data

    def send_data(self, server_ip: str, server_port: int, hex_data: str) -> str:
        dbytes = bytes.fromhex(hex_data)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._address, self._port))
        s.sendall(dbytes)
        response_bytes = s.recv(1024)
        response_hex = response_bytes.hex().upper()

        return response_hex
    
    def request_all_information(self) -> str:
        REQUEST_ALL_HEX = ['55', '55', '55', '55', '55', 'aa', '90', 'b0', '01', '1f', '00', '02', 'ff', 'f0', 'cb', '8c']
        REQUEST_ALL_STRING = self.hex_string(REQUEST_ALL_HEX)
        REQUEST_ALL_RESP = self.send_data(self._address, self._port, REQUEST_ALL_STRING)

        return REQUEST_ALL_RESP
    
    def return_system_id(self, zt3_data: str) -> str:
        SYSTEM_ID = self.hex_to_ascii(self.extract_data(zt3_data, 12, 8))
        return SYSTEM_ID
    
    def return_system_name(self, zt3_data: str) -> str:
        SYSTEM_NAME = self.hex_to_ascii(self.extract_data(zt3_data, 20, 16))
        return SYSTEM_NAME
    
    def return_system_installer(self, zt3_data: str) -> str:
        SYSTEM_INSTALLER = self.hex_to_ascii(self.extract_data(zt3_data, 46, 10))
        return SYSTEM_INSTALLER
    
    def return_installer_number(self, zt3_data: str) -> str:
        INSTALLER_NUMBER = self.hex_to_ascii(self.extract_data(zt3_data, 56, 12))
        return INSTALLER_NUMBER
    
    def return_console_temp(self, zt3_data: str) -> str:
        CONSOLE_TEMP = self.hex_to_int(self.extract_data(zt3_data, 68, 2))
        REAL_TEMP_DEC = (CONSOLE_TEMP - 500) / 10
        REAL_TEMP = math.ceil(REAL_TEMP_DEC)
        return str(REAL_TEMP)
    
    def return_firmware_version(self, zt3_data: str) -> str:
        FIRMWARE_VERSION = self.hex_to_ascii(self.extract_data(zt3_data, 79, 7))
        return FIRMWARE_VERSION
    
    def return_console_version(self, zt3_data: str) -> str:
        CONSOLE_VERSION = self.hex_to_ascii(self.extract_data(zt3_data, 95, 7))
        return CONSOLE_VERSION
    
    def return_zone_name(self, zt3_data: str, zone: str) -> str:
        ZONE_NAME = self.hex_to_ascii(self.extract_data(zt3_data, 133 + (int(zone) * 22), 12))
        
        return ZONE_NAME
        
    def return_zone_state(self, zt3_data: str, zone: str):
        GROUP_DATA = self.extract_data(zt3_data, 123 + (int(zone) * 22), 1)

        GROUP_POWER_AND_ID_HEX = self.extract_data(GROUP_DATA, 0, 1)
        GROUP_POWER_AND_ID_BIN = bin(int(GROUP_POWER_AND_ID_HEX, 16))[2:].zfill(8)
        GROUP_POWER_BIN = GROUP_POWER_AND_ID_BIN[:2]

        match GROUP_POWER_BIN:
            case '00':
                self._state = False #off
            case '01':
                self._state = True #On
            case '11':
                self._state = True #Turbo
            case _:
                self._state = False #Unknown

        return self._state
    
    def return_zone_percentage(self, zt3_data: str, zone: str):
        percentage =  self.hex_to_int(self.extract_data(zt3_data, 124 + (int(zone) * 22), 1))

        return percentage
    
    def get_zonetouch_temp(self) -> int:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_RAW_TEMP = self.hex_to_int(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 68, 2))
        REAL_TEMP = math.ceil((CONSOLE_RAW_TEMP - 500) / 10)

        return REAL_TEMP

    def update_zone_state(self, state: str, percentage: int) -> None:
        UPDATE_ZONE_STATE_HEX = ['55', '55', '55', 'aa', '80', 'b0', '0f', 'c0', '00', '0c', '20', '00', '00', '00', '00', '04', '00', '01', '00', '02', '00', '00', '00', '00']
    
        UPDATE_ZONE_STATE_HEX[18] = '0' + str(self.int_to_hex(self._zone))
        UPDATE_ZONE_STATE_HEX[19] = state
        UPDATE_ZONE_STATE_HEX[20] = str(self.int_to_hex(percentage))

        checksum = self.crc16_modbus(self.hex_string(UPDATE_ZONE_STATE_HEX[4:22]))
        UPDATE_ZONE_STATE_HEX[22] = checksum[0:2]
        UPDATE_ZONE_STATE_HEX[23] = checksum[2:4]

        UPDATE_ZONE_STATE_STR = self.hex_string(UPDATE_ZONE_STATE_HEX)
        UPDATE_ZONE_STATE = self.send_data(self._address, self._port, UPDATE_ZONE_STATE_STR)