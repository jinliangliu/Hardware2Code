#!/usr/bin/env python3
"""
FOTA Patch Sender for Hardware2Code
Sends a BSDIFF patch file to the STM32G0 device via UART.

Protocol:
  START:  0xF0 0x0A [total_size:4B LE]
  CHUNK:  [seq:2B LE] [len:2B LE] [payload:N bytes] [crc16:2B LE]
  ACK:    0x06
  NAK:    0x15 [last_good_seq:2B LE]
  END:    0xF0 0x0E [final_crc32:4B LE]

Usage: python fota_sender.py COM4 patch.bin [--baud 115200]
"""

import argparse
import struct
import sys
import time
from pathlib import Path


CHUNK_SIZE = 1024
START_CMD = b'\xF0\x0A'
END_CMD = b'\xF0\x0E'
ACK_BYTE = b'\x06'
NAK_BYTE = b'\x15'
MAX_RETRIES = 3
ACK_TIMEOUT = 2.0  # seconds


# CRC-16/CCITT lookup table
_CRC16_TABLE = None


def _init_crc16_table():
    global _CRC16_TABLE
    if _CRC16_TABLE is not None:
        return
    _CRC16_TABLE = []
    for i in range(256):
        crc = i << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
        _CRC16_TABLE.append(crc)


def crc16(data: bytes) -> int:
    """Compute CRC-16/CCITT over bytes."""
    _init_crc16_table()
    crc = 0xFFFF
    for b in data:
        crc = ((crc << 8) ^ _CRC16_TABLE[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
    return crc


def crc32_mpeg2(data: bytes) -> int:
    """Compute CRC-32/MPEG-2 (matches STM32G0 hardware CRC)."""
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= (b & 0xFF)
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF


def send_fota(port: str, patch_path: str, baud: int = 115200):
    """Send FOTA patch file over serial port."""
    try:
        import serial
    except ImportError:
        print("ERROR: pyserial not installed. Run: pip install pyserial")
        sys.exit(1)

    patch_data = Path(patch_path).read_bytes()
    total_size = len(patch_data)
    print(f"Patch file: {total_size} bytes")

    # Open serial port
    try:
        ser = serial.Serial(port, baudrate=baud, timeout=ACK_TIMEOUT)
    except serial.SerialException as e:
        print(f"ERROR: Cannot open {port}: {e}")
        sys.exit(1)

    total_chunks = (total_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"Chunks: {total_chunks} × {CHUNK_SIZE} bytes")
    print(f"Serial: {port} @ {baud} baud")
    print()

    # Wait for device to be ready (send start command)
    print("Sending START command...")
    start_pkt = START_CMD + struct.pack('<I', total_size)
    ser.write(start_pkt)

    # Send chunks
    seq = 0
    offset = 0
    retry_count = 0

    while offset < total_size:
        chunk_end = min(offset + CHUNK_SIZE, total_size)
        chunk = patch_data[offset:chunk_end]

        # Build chunk packet
        pkt = struct.pack('<H', seq)
        pkt += struct.pack('<H', len(chunk))
        pkt += chunk
        pkt += struct.pack('<H', crc16(chunk))

        ser.write(pkt)
        print(f"  Chunk {seq:4d}  offset={offset:6d}  len={len(chunk):4d}  ... ", end='', flush=True)

        # Wait for ACK
        response = ser.read(3)  # ACK(1B) or NAK(1B) + seq(2B)
        if len(response) >= 1:
            if response[0] == ACK_BYTE[0]:
                print("ACK")
                seq += 1
                offset = chunk_end
                retry_count = 0
            elif response[0] == NAK_BYTE[0] and len(response) >= 3:
                last_good = struct.unpack('<H', response[1:3])[0]
                print(f"NAK (last_good={last_good})")
                retry_count += 1
                if retry_count > MAX_RETRIES:
                    print(f"ERROR: Exceeded max retries ({MAX_RETRIES})")
                    ser.close()
                    sys.exit(1)
                # Rewind to last good chunk
                seq = last_good + 1
                offset = seq * CHUNK_SIZE
                if offset >= total_size:
                    offset = max(0, total_size - CHUNK_SIZE)
            else:
                print(f"UNEXPECTED: {response.hex()}")
                retry_count += 1
        else:
            print("TIMEOUT")
            retry_count += 1
            if retry_count > MAX_RETRIES:
                print(f"ERROR: Exceeded max retries ({MAX_RETRIES})")
                ser.close()
                sys.exit(1)

        # Small delay between chunks to let device process
        time.sleep(0.01)

    # Send END command with CRC32 of full patch for final verification
    final_crc = crc32_mpeg2(patch_data)
    end_pkt = END_CMD + struct.pack('<I', final_crc)
    ser.write(end_pkt)
    print()
    print(f"END command sent. CRC32: 0x{final_crc:08X}")

    # Wait for final ACK
    response = ser.read(1)
    if response == ACK_BYTE:
        print("FOTA transfer complete — device ACK.")
    else:
        print(f"WARNING: No final ACK received. Device may still be applying patch.")

    ser.close()


def main():
    parser = argparse.ArgumentParser(
        description='Send FOTA patch to STM32G0 device via UART')
    parser.add_argument('port', help='Serial port (e.g., COM4, /dev/ttyUSB0)')
    parser.add_argument('patch', help='Patch file (.bin)')
    parser.add_argument('--baud', type=int, default=115200,
                        help='Baud rate (default: 115200)')
    parser.add_argument('--chunk-size', type=int, default=1024,
                        help='Chunk size in bytes (default: 1024)')
    args = parser.parse_args()

    global CHUNK_SIZE
    CHUNK_SIZE = args.chunk_size

    if not Path(args.patch).exists():
        print(f"ERROR: Patch file not found: {args.patch}")
        sys.exit(1)

    send_fota(args.port, args.patch, args.baud)


if __name__ == '__main__':
    main()
