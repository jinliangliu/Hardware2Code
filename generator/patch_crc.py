#!/usr/bin/env python3
"""
CRC32 固件后处理脚本（匹配 STM32G0 硬件 CRC）
算法: CRC-32/MPEG-2 (poly=0x4C11DB7, init=0xFFFFFFFF, 输入/输出位反转)
读取固件 .bin，计算除末尾 4 字节外的 CRC32，回填到末尾 4 字节。

用法:
    python patch_crc.py firmware.bin
    python patch_crc.py firmware.bin --in-place   (原位修改)
    python patch_crc.py firmware.bin -o output.bin (输出到新文件)
"""

import argparse
import struct
import sys
from pathlib import Path


def stm32_crc32(data: bytes) -> int:
    """
    STM32 硬件 CRC32（与 STM32G0 CRC 外设一致）
    CRC-32/MPEG-2，输入/输出位反转
    """
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF


def patch_firmware(input_path: str, output_path: str = None):
    """
    计算固件 CRC 并回填到末尾 4 字节。
    固件区域 = 去除末尾 4 字节 CRC 占位符的全体数据。
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    data = input_path.read_bytes()

    if len(data) < 12:
        print(f"[ERROR] Firmware too small ({len(data)} bytes), must be at least 12 bytes.")
        sys.exit(1)

    # 去除末尾 8 字节（size + CRC 占位符），计算 CRC
    payload = data[:-8]
    crc_value = stm32_crc32(payload)

    # 回填 size + CRC（小端序）
    output_data = payload + struct.pack('<II', len(payload), crc_value)

    dest = output_path or input_path
    Path(dest).write_bytes(output_data)

    print(f"CRC32: 0x{crc_value:08X} (payload {len(payload)} bytes)")
    print(f"Output: {dest}")


def main():
    parser = argparse.ArgumentParser(description="STM32G0 固件 CRC32 后处理")
    parser.add_argument("input", help="输入固件 .bin 文件")
    parser.add_argument("-o", "--output", help="输出文件路径（默认覆盖输入）")
    parser.add_argument("--in-place", action="store_true", help="原位修改（同没有 -o）")
    args = parser.parse_args()

    output = args.output if args.output else (args.input if args.in_place else None)
    if output is None:
        print("[ERROR] Specify -o <output> or --in-place to modify in place.")
        sys.exit(1)

    patch_firmware(args.input, output)


if __name__ == "__main__":
    main()
