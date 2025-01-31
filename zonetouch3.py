import socket
import logging
import math

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

    def extract_bits(self, hex_data: str):
        HEX_DATA_INT = self.hex_to_int(hex_data)


    def send_data(self, server_ip: str, server_port: int, hex_data: str) -> str:
        dbytes = bytes.fromhex(hex_data)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._address, self._port))
        s.sendall(dbytes)
        response_bytes = s.recv(1024)
        response_hex = response_bytes.hex().upper()

        return response_hex

    def get_zone_percentage(self) -> str:
        # Example Response
        # 55 55 55 AA B0 80 01 C0 0030 21 00 | 00 00 00 08 00 05 | 40649C6401F40000 | 41649C6401F40000 | 02649C0001F40000| 03649C0001F40000 | 44649C6401F40000 5350
        REQUEST_ZONE_STATE_HEX = ['55', '55', '55', 'aa', '80', 'b0', '01', 'c0', '00', '08', '21', '00', '00', '00', '00', '00', '00', '00', 'a4', '31']
        REQUEST_ZONE_STATE_STR = self.hex_string(REQUEST_ZONE_STATE_HEX)
        REQUEST_ZONE_STATE = self.send_data(self._address, self._port, REQUEST_ZONE_STATE_STR)
        LOGGER.debug(f"Response from the Zonetouch for percentage: {REQUEST_ZONE_STATE}")

        GROUP_DATA = self.extract_data(REQUEST_ZONE_STATE, 18 + (int(self._zone)*8), 8)
        LOGGER.debug(f"The extracted data for percentage: {GROUP_DATA}")

        GROUP_OPEN_PERCENTAGE_HEX = self.extract_data(GROUP_DATA, 1, 1)
        LOGGER.debug(f"The extracted hex for percentage: {GROUP_OPEN_PERCENTAGE_HEX}")

        GROUP_OPEN_PERCENTAGE_BIN = bin(int(GROUP_OPEN_PERCENTAGE_HEX, 16))[2:].zfill(8)
        LOGGER.debug(f"The extracted binary for percentage: {GROUP_OPEN_PERCENTAGE_BIN}")

        GROUP_OPEN_PERCENTAGE_BTS71 = GROUP_OPEN_PERCENTAGE_BIN[1:]
        LOGGER.debug(f"The extracted bits 7-1 for percentage: {GROUP_OPEN_PERCENTAGE_BTS71}")

        GROUP_OPEN_PERCENTAGE_INT = int(GROUP_OPEN_PERCENTAGE_BTS71, 2)
        LOGGER.debug(f"The extracted open percentage as int: {GROUP_OPEN_PERCENTAGE_INT}")

        self._percentage = GROUP_OPEN_PERCENTAGE_INT

        return self._percentage

    def get_zone_state(self) -> str:
        # Example Response
        # 55 55 55 AA B0 80 01 C0 0030 21 00 | 00 00 00 08 00 05 | 40649C6401F40000 | 41649C6401F40000 | 02649C0001F40000| 03649C0001F40000 | 44649C6401F40000 5350
        REQUEST_ZONE_STATE_HEX = ['55', '55', '55', 'aa', '80', 'b0', '01', 'c0', '00', '08', '21', '00', '00', '00', '00', '00', '00', '00', 'a4', '31']
        REQUEST_ZONE_STATE_STR = self.hex_string(REQUEST_ZONE_STATE_HEX)
        REQUEST_ZONE_STATE = self.send_data(self._address, self._port, REQUEST_ZONE_STATE_STR)

        GROUP_DATA = self.extract_data(REQUEST_ZONE_STATE, 18 + (int(self._zone)*8), 8)
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

    def get_zone_name(self) -> str:
        REQUEST_ALL_GROUPS_HEX = ['55', '55', '55', 'AA', '90', 'b0', '01', '1f', '00', '02', 'ff', '13', '42', 'cd']
        REQUEST_ALL_GROUPS_STR = self.hex_string(REQUEST_ALL_GROUPS_HEX)
        REQUEST_ALL_GROUPS_RESP = self.send_data(self._address, self._port, REQUEST_ALL_GROUPS_STR)

        DATA_LENGTH = self.hex_to_int(self.extract_data(REQUEST_ALL_GROUPS_RESP, 13, 2))

        GROUP_NAME = self.hex_to_ascii(self.extract_data(REQUEST_ALL_GROUPS_RESP, 13 + 1 + (self._zone * 13), 12))

        return GROUP_NAME
    
    def get_zonetouch_temp(self) -> int:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_RAW_TEMP = self.hex_to_int(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 68, 2))
        REAL_TEMP = math.ceil((CONSOLE_RAW_TEMP - 500) / 10)

        return REAL_TEMP

    def get_zonetouch_system_id(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_SYSTEM_ID = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 12, 8))

        return CONSOLE_SYSTEM_ID
    
    def get_zonetouch_system_name(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_SYSTEM_NAME = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 20, 16))
        
        return CONSOLE_SYSTEM_NAME

    def get_zonetouch_system_installer(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_INSTALLER_NAME = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 46, 10))
        
        return CONSOLE_INSTALLER_NAME
    
    def get_zonetouch_system_installer_number(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_INSTALLER_NUMBER = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 56, 12))
        
        return CONSOLE_INSTALLER_NUMBER
    
    def get_zonetouch_system_firmware(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_FIRMWARE = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 79, 7))
       
        return CONSOLE_FIRMWARE
    
    def get_zonetouch_console_version(self) -> str:
        REQUEST_ALL_INFO_HEX = ['55','55','55','aa','90','b0','01','1f','00','02','ff','f0','cb','8c']
        REQUEST_ALL_INFO_STR = self.hex_string(REQUEST_ALL_INFO_HEX)
        REQUEST_ALL_INFO_STR_RESP = self.send_data(self._address, self._port, REQUEST_ALL_INFO_STR)

        CONSOLE_VERSION = self.hex_to_ascii(self.extract_data(REQUEST_ALL_INFO_STR_RESP, 95, 7))

        return CONSOLE_VERSION

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

zt3 = Zonetouch3('192.168.15.7', 7030, '3')
print(zt3.get_zone_percentage())