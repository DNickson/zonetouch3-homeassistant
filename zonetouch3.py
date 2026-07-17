"""Async TCP client for the Polyaire ZoneTouch 3 zone controller.

Implements the "ZoneTouch 3 Communication Protocol V1.0":

- Frame: 0x55 0x55 0x55 0xAA header, address (2), message id (1), type (1),
  data length (2, big-endian), data, CRC16-MODBUS (2, high byte first).
- Byte stuffing: after every three consecutive 0x55 bytes a 0x00 is inserted
  so the payload can never look like a frame header. Stuffed bytes are not
  counted in the data length. The spec says they are excluded from the CRC,
  but the worked example in the spec includes them, so both are accepted.
- Documented messages: group control (0x20), group status (0x21) and group
  names (0xFF 0x13).
- The extended message 0xFF 0xF0 is not documented; it is what the official
  app uses to fetch system information and the console temperature. The
  field offsets below were reverse engineered from captures.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import IntEnum
import logging
from typing import Callable

_LOGGER = logging.getLogger(__name__)

DEFAULT_PORT = 7030
DEFAULT_TIMEOUT = 5.0

HEADER = b"\x55\x55\x55\xaa"
ADDRESS_CONTROL = b"\x80\xb0"
ADDRESS_EXTENDED = b"\x90\xb0"
MESSAGE_ID = 0x01

TYPE_CONTROL = 0xC0
TYPE_EXTENDED = 0x1F

SUBTYPE_GROUP_CONTROL = 0x20
SUBTYPE_GROUP_STATUS = 0x21
EXTENDED_GROUP_NAMES = b"\xff\x13"
EXTENDED_SYSTEM_INFO = b"\xff\xf0"

# Group control byte 2: bits 8-6 select what happens to the open percentage.
SETTING_SET_PERCENTAGE = 0b100 << 5
# Group control byte 3: values outside 0-100 mean "keep current setting".
KEEP_PERCENTAGE = 0xFF

# Offsets into the 0xFF 0xF0 response data (reverse engineered).
_INFO_SYSTEM_ID = (2, 8)
_INFO_SYSTEM_NAME = (10, 16)
_INFO_INSTALLER = (36, 10)
_INFO_INSTALLER_PHONE = (46, 12)
_INFO_CONSOLE_TEMP = (58, 2)  # value is temperature * 10 + 500
_INFO_FIRMWARE_VERSION = (69, 7)
_INFO_CONSOLE_VERSION = (85, 7)

_MAX_DATA_LENGTH = 4096
_MAX_HEADER_SEARCH = 256
_MAX_FRAME_SKIP = 8


class ZoneTouch3Error(Exception):
    """Base error for ZoneTouch 3 communication."""


class ZoneTouch3ConnectionError(ZoneTouch3Error):
    """Could not connect to or exchange data with the device."""


class ZoneTouch3ProtocolError(ZoneTouch3Error):
    """The device sent data that could not be understood."""


class PowerCommand(IntEnum):
    """Power bits (byte 2, bits 3-1) of a group control message."""

    KEEP = 0b000
    NEXT = 0b001
    OFF = 0b010
    ON = 0b011
    TURBO = 0b101


class PowerState(IntEnum):
    """Power bits (byte 1, bits 8-7) of a group status message."""

    OFF = 0b00
    ON = 0b01
    TURBO = 0b11


@dataclass
class ZoneStatus:
    """State of a single zone (group) as reported by the device."""

    number: int
    power: PowerState
    percentage: int
    turbo_supported: bool
    spill_active: bool
    name: str = ""

    @property
    def is_on(self) -> bool:
        return self.power is not PowerState.OFF


@dataclass
class SystemInfo:
    """Static system information and the console temperature."""

    system_id: str = ""
    name: str = ""
    installer: str = ""
    installer_phone: str = ""
    firmware_version: str = ""
    console_version: str = ""
    temperature: float | None = None


@dataclass
class ZoneTouchState:
    """Complete state of a ZoneTouch 3 system."""

    system: SystemInfo = field(default_factory=SystemInfo)
    zones: dict[int, ZoneStatus] = field(default_factory=dict)


def _crc16(data: bytes) -> bytes:
    """CRC16-MODBUS, transmitted high byte first."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc.to_bytes(2, "big")


def _stuff(data: bytes) -> bytes:
    """Insert a 0x00 after every three consecutive 0x55 bytes."""
    out = bytearray()
    run = 0
    for byte in data:
        out.append(byte)
        run = run + 1 if byte == 0x55 else 0
        if run == 3:
            out.append(0x00)
            run = 0
    return bytes(out)


def build_message(address: bytes, msg_type: int, data: bytes) -> bytes:
    """Build a complete frame ready to send."""
    body = _stuff(
        address + bytes((MESSAGE_ID, msg_type)) + len(data).to_bytes(2, "big") + data
    )
    return HEADER + body + _crc16(body)


def _group_control_data(
    zone: int, power: PowerCommand, percentage: int | None
) -> bytes:
    """Build the data section of a group control (0x20) message."""
    setting = SETTING_SET_PERCENTAGE if percentage is not None else 0
    # The spec documents the repeat count before the repeat length, but real
    # firmware uses the opposite order (confirmed against a live system,
    # whose status messages are laid out the same way).
    return bytes(
        (
            SUBTYPE_GROUP_CONTROL, 0x00,  # sub type, keep 0
            0x00, 0x00,  # common data length
            0x00, 0x04,  # each repeat data length
            0x00, 0x01,  # repeat data count
            zone & 0x3F,
            setting | power,
            percentage if percentage is not None else KEEP_PERCENTAGE,
            0x00,
        )
    )


_STATUS_REQUEST = build_message(
    ADDRESS_CONTROL, TYPE_CONTROL, bytes((SUBTYPE_GROUP_STATUS, 0, 0, 0, 0, 0, 0, 0))
)
_NAMES_REQUEST = build_message(ADDRESS_EXTENDED, TYPE_EXTENDED, EXTENDED_GROUP_NAMES)
_INFO_REQUEST = build_message(ADDRESS_EXTENDED, TYPE_EXTENDED, EXTENDED_SYSTEM_INFO)


def _is_group_status(msg_type: int, data: bytes) -> bool:
    return msg_type == TYPE_CONTROL and data[:1] == bytes((SUBTYPE_GROUP_STATUS,))


def _is_group_names(msg_type: int, data: bytes) -> bool:
    return msg_type == TYPE_EXTENDED and data[:2] == EXTENDED_GROUP_NAMES


def _is_system_info(msg_type: int, data: bytes) -> bool:
    return msg_type == TYPE_EXTENDED and data[:2] == EXTENDED_SYSTEM_INFO


class _FrameReader:
    """Reads bytes from a stream, removing stuffed 0x00 bytes on the fly."""

    def __init__(self, reader: asyncio.StreamReader) -> None:
        self._reader = reader
        self._run = 0
        self.raw = bytearray()  # everything read, including stuffed bytes

    async def read(self, count: int) -> bytes:
        out = bytearray()
        while len(out) < count:
            byte = (await self._reader.readexactly(1))[0]
            self.raw.append(byte)
            if self._run == 3:
                self._run = 0
                if byte == 0x00:
                    continue  # stuffed byte, drop it
            self._run = self._run + 1 if byte == 0x55 else 0
            out.append(byte)
        return bytes(out)


async def _read_frame(reader: asyncio.StreamReader) -> tuple[bytes, int, bytes]:
    """Read one frame and return (address, message type, unstuffed data)."""
    window = bytearray()
    while bytes(window[-4:]) != HEADER:
        window.extend(await reader.readexactly(1))
        if len(window) > _MAX_HEADER_SEARCH:
            raise ZoneTouch3ProtocolError("Frame header not found in stream")

    frame = _FrameReader(reader)
    preamble = await frame.read(6)  # address(2) + id(1) + type(1) + length(2)
    address = preamble[:2]
    msg_type = preamble[3]
    length = int.from_bytes(preamble[4:6], "big")
    if length > _MAX_DATA_LENGTH:
        raise ZoneTouch3ProtocolError(f"Implausible data length {length}")

    data = await frame.read(length)
    raw_body = bytes(frame.raw)  # body as transmitted, before the CRC
    crc = await frame.read(2)

    # The spec text says the CRC excludes stuffed bytes, but the spec's own
    # example includes them. Accept either.
    if crc not in (_crc16(raw_body), _crc16(preamble + data)):
        raise ZoneTouch3ProtocolError(
            f"CRC mismatch on frame: {(HEADER + raw_body).hex()} crc={crc.hex()}"
        )
    return address, msg_type, data


def _parse_group_status(data: bytes) -> dict[int, ZoneStatus]:
    """Parse a group status (0x21) message into per-zone status.

    The spec puts the repeat count in bytes 5-6 and the per-group data
    length in bytes 7-8, but real firmware sends them the other way around
    (e.g. 0x0008/0x0005 for five zones of eight bytes). Both orderings fit
    the payload size, so the two fields are disambiguated by checking under
    which interpretation the zone numbers are valid and unique.
    """
    if len(data) < 8:
        raise ZoneTouch3ProtocolError("Group status message too short")
    common_length = int.from_bytes(data[2:4], "big")
    field_a = int.from_bytes(data[4:6], "big")
    field_b = int.from_bytes(data[6:8], "big")
    start = 8 + common_length
    total = len(data) - start

    def plausible(count: int, each: int) -> bool:
        if not (0 < count <= 16 and each >= 2 and count * each == total):
            return False
        numbers = [data[start + i * each] & 0x3F for i in range(count)]
        return len(set(numbers)) == count and all(n <= 15 for n in numbers)

    if total == 0:
        return {}
    if plausible(field_a, field_b):  # documented order: count, length
        count, each_length = field_a, field_b
    elif plausible(field_b, field_a):  # order seen from real firmware
        count, each_length = field_b, field_a
    else:
        raise ZoneTouch3ProtocolError(
            f"Cannot interpret group status message: {data.hex()}"
        )

    zones: dict[int, ZoneStatus] = {}
    offset = start
    for _ in range(count):
        group = data[offset : offset + each_length]
        power_bits = (group[0] >> 6) & 0b11
        try:
            power = PowerState(power_bits)
        except ValueError:
            power = PowerState.OFF
        number = group[0] & 0x3F
        zones[number] = ZoneStatus(
            number=number,
            power=power,
            percentage=group[1] & 0x7F,
            turbo_supported=bool(group[6] >> 7) if each_length >= 7 else False,
            spill_active=bool((group[6] >> 1) & 1) if each_length >= 7 else False,
        )
        offset += each_length
    return zones


def _decode_text(raw: bytes) -> str:
    return raw.split(b"\x00")[0].decode("utf-8", errors="replace").strip()


def _parse_group_names(data: bytes) -> dict[int, str]:
    """Parse a group names (0xFF 0x13) message into {zone number: name}."""
    if len(data) < 3:
        raise ZoneTouch3ProtocolError("Group names message too short")
    name_length = data[2]
    entry_length = 1 + name_length  # group number + name
    names: dict[int, str] = {}
    offset = 3
    while offset + entry_length <= len(data):
        names[data[offset]] = _decode_text(data[offset + 1 : offset + entry_length])
        offset += entry_length
    return names


def _parse_system_info(data: bytes) -> SystemInfo:
    """Parse the undocumented system information (0xFF 0xF0) message."""

    def text(offset: int, length: int) -> str:
        return _decode_text(data[offset : offset + length])

    raw_temp_offset, raw_temp_length = _INFO_CONSOLE_TEMP
    raw_temp = int.from_bytes(
        data[raw_temp_offset : raw_temp_offset + raw_temp_length], "big"
    )
    return SystemInfo(
        system_id=text(*_INFO_SYSTEM_ID),
        name=text(*_INFO_SYSTEM_NAME),
        installer=text(*_INFO_INSTALLER),
        installer_phone=text(*_INFO_INSTALLER_PHONE),
        firmware_version=text(*_INFO_FIRMWARE_VERSION),
        console_version=text(*_INFO_CONSOLE_VERSION),
        temperature=(raw_temp - 500) / 10 if raw_temp else None,
    )


class ZoneTouch3Client:
    """Client that opens a short-lived TCP connection per operation."""

    def __init__(
        self, host: str, port: int = DEFAULT_PORT, timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._lock = asyncio.Lock()

    async def async_get_state(self) -> ZoneTouchState:
        """Fetch zone status, zone names and system information."""
        async with self._lock:
            reader, writer = await self._open()
            try:
                zones = _parse_group_status(
                    await self._exchange(reader, writer, _STATUS_REQUEST, _is_group_status)
                )
                names = _parse_group_names(
                    await self._exchange(reader, writer, _NAMES_REQUEST, _is_group_names)
                )
                system = _parse_system_info(
                    await self._exchange(reader, writer, _INFO_REQUEST, _is_system_info)
                )
            finally:
                await self._close(writer)

        for number, name in names.items():
            if number in zones:
                zones[number].name = name
        return ZoneTouchState(system=system, zones=zones)

    async def async_set_zone(
        self,
        zone: int,
        power: PowerCommand = PowerCommand.KEEP,
        percentage: int | None = None,
    ) -> dict[int, ZoneStatus]:
        """Control one zone and return the group status the device replies with."""
        if not 0 <= zone <= 15:
            raise ValueError(f"Zone number must be 0-15, got {zone}")
        if percentage is not None and not 0 <= percentage <= 100:
            raise ValueError(f"Percentage must be 0-100, got {percentage}")

        request = build_message(
            ADDRESS_CONTROL, TYPE_CONTROL, _group_control_data(zone, power, percentage)
        )
        async with self._lock:
            reader, writer = await self._open()
            try:
                return _parse_group_status(
                    await self._exchange(reader, writer, request, _is_group_status)
                )
            finally:
                await self._close(writer)

    async def _open(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        try:
            return await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), self._timeout
            )
        except (OSError, TimeoutError) as err:
            raise ZoneTouch3ConnectionError(
                f"Could not connect to {self._host}:{self._port}: {err}"
            ) from err

    @staticmethod
    async def _close(writer: asyncio.StreamWriter) -> None:
        try:
            writer.close()
            await writer.wait_closed()
        except OSError:
            pass

    async def _exchange(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        request: bytes,
        matches: Callable[[int, bytes], bool],
    ) -> bytes:
        """Send a request and return the data of the first matching response.

        The device sends group status messages on its own whenever a zone
        changes (e.g. from the wall console), so unrelated frames may arrive
        before the response we are waiting for; those are skipped.
        """
        try:
            writer.write(request)
            await asyncio.wait_for(writer.drain(), self._timeout)
            skipped: list[str] = []
            for _ in range(_MAX_FRAME_SKIP):
                _, msg_type, data = await asyncio.wait_for(
                    _read_frame(reader), self._timeout
                )
                _LOGGER.debug(
                    "Received frame type 0x%02X data=%s", msg_type, data.hex()
                )
                if matches(msg_type, data):
                    return data
                skipped.append(f"type=0x{msg_type:02X} data={data.hex()}")
            raise ZoneTouch3ProtocolError(
                f"No matching response to {request.hex()}; "
                f"received: {'; '.join(skipped)}"
            )
        except (asyncio.IncompleteReadError, TimeoutError, OSError) as err:
            raise ZoneTouch3ConnectionError(
                f"Communication with {self._host}:{self._port} failed: {err}"
            ) from err
