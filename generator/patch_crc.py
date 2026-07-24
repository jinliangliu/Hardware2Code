#!/usr/bin/env python3
"""
CRC32 固件后处理脚本（匹配 STM32G0 硬件 CRC）
算法: CRC-32/MPEG-2 (poly=0x4C11DB7, init=0xFFFFFFFF, 输入/输出位反转)

固件镜像布局（Slot 内）:
  offset 0x00 - 0xBF:  向量表 (48 entries × 4 bytes = 192 bytes)
  offset 0xC0 - 0xC3:  image_size (4 bytes, 小端序)
  offset 0xC4 - 0xC7:  CRC32 (4 bytes, 小端序)
  offset 0xC8 - 0xCB:  magic 0x4841436B "H2Ck" (4 bytes)
  offset 0xCC - 0xCF:  fw_version (4 bytes, --version 参数)
  offset 0xD0 - end:   实际代码 + 数据

image_size = 4 (fw_version) + code_size
CRC 计算范围: offset 0xCC (fw_version + code) 到 bin 末尾的所有数据。

用法:
    python patch_crc.py firmware.bin -o output.bin [--version 1]
    python patch_crc.py firmware.bin --in-place
"""

import argparse
import struct
import sys
from pathlib import Path

# 头部偏移量（紧接向量表之后，魔数用于搜索定位）
HEADER_MAGIC  = 0x4841436B    # "H2Ck"
HEADER_SIZE   = 12            # image_size(4) + CRC32(4) + magic(4)
HEADER_SEARCH_MAX = 0x200     # 在前 512 字节内搜索 magic（覆盖各种向量表大小）


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


def patch_firmware(input_path: str, output_path: str = None, version: int = 0):
    """
    在固件头部区域搜索 magic "H2Ck"，定位 Header，计算 CRC 并回填。
    Header 格式: [image_size(4B) | CRC32(4B) | magic(4B)]
    Payload 格式: [fw_version(4B)] [code...]
    CRC 覆盖范围: magic 之后的所有数据（含 fw_version）。
    image_size = len(payload) = 4 (fw_version) + len(code)
    """
    input_path = Path(input_path)
    if not input_path.exists():
        print(f"[ERROR] File not found: {input_path}")
        sys.exit(1)

    data = bytearray(input_path.read_bytes())

    if len(data) < 256:
        print(f"[ERROR] Firmware too small ({len(data)} bytes), min 256 bytes.")
        sys.exit(1)

    # 搜索 magic "H2Ck" 定位头部（magic 位于 Header 第 3 个 LONG，即偏移 magic_offset）
    magic_offset = None
    for off in range(0, min(HEADER_SEARCH_MAX, len(data) - 4), 4):
        if struct.unpack_from('<I', data, off)[0] == HEADER_MAGIC:
            magic_offset = off
            break

    if magic_offset is None:
        print(f"[ERROR] Header magic 0x{HEADER_MAGIC:08X} not found in first {HEADER_SEARCH_MAX} bytes.")
        print("        请检查链接脚本是否包含 .app_header 段。")
        sys.exit(1)

    header_offset = magic_offset - 8    # image_size 和 CRC32 在 magic 之前
    payload_offset = magic_offset + 4   # 代码数据在 magic 之后

    print(f"Header found at offset 0x{header_offset:X} (magic @ 0x{magic_offset:X})")

    # 插入版本号（在 magic 之后，原 payload 之前）
    version_bytes = struct.pack('<I', version & 0x00FFFFFF)  # 24-bit version

    # 原 payload（magic 之后的所有数据）
    original_payload = data[payload_offset:]

    # 新 payload = version(4B) + original code
    new_payload = version_bytes + original_payload

    # 替换 payload 部分
    data[payload_offset:] = new_payload

    # 计算 CRC（覆盖 magic 之后的所有数据，含 fw_version + code）
    crc_value = stm32_crc32(new_payload)

    # 回填 image_size + CRC32（小端序）
    image_size = len(new_payload)
    struct.pack_into('<II', data, header_offset, image_size, crc_value)

    dest = output_path or input_path
    Path(dest).write_bytes(data)

    print(f"Version: 0x{version:06X}")
    print(f"Image size: {image_size} bytes")
    print(f"CRC32: 0x{crc_value:08X}")
    print(f"Output: {dest}")


def main():
    parser = argparse.ArgumentParser(description="STM32G0 固件 CRC32 后处理")
    parser.add_argument("input", help="输入固件 .bin 文件")
    parser.add_argument("-o", "--output", help="输出文件路径（默认覆盖输入）")
    parser.add_argument("--in-place", action="store_true", help="原位修改（同没有 -o）")
    parser.add_argument("--version", type=lambda x: int(x, 0), default=0,
                        help="固件版本号（24-bit，如 1 或 0x01）")
    args = parser.parse_args()

    output = args.output if args.output else (args.input if args.in_place else None)
    if output is None:
        print("[ERROR] Specify -o <output> or --in-place to modify in place.")
        sys.exit(1)

    patch_firmware(args.input, output, args.version)


if __name__ == "__main__":
    main()
