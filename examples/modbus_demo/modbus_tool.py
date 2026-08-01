#!/usr/bin/env python3
"""
modbus_tool.py - Modbus RTU master tool for the hw2c modbus_demo

Talks to the board's Modbus slave over a USB-TTL adapter (e.g. CP210x on
COM4) directly wired to USART1 (PA9=TX, PA10=RX) at 9600 baud - NOT RS485.

Supported function codes (same set as the firmware slave):
  FC03  read holding registers
  FC06  write single register
  FC16  write multiple registers

Usage:
  python modbus_tool.py read <addr> [count]
  python modbus_tool.py write <addr> <value>
  python modbus_tool.py write_multi <addr> <v0> <v1> ...
  python modbus_tool.py monitor [interval_s]     # poll temperature every N s

Options:
  --port COM4   serial port (default COM4)
  --baud 9600   baud rate (default 9600, matches firmware USART1)
  --slave 1     Modbus slave address (default 1)
  --timeout 0.2 response timeout in seconds (default 0.2)
"""

from __future__ import print_function

import argparse
import sys
import time

import serial


# ---------------------------------------------------------------------------
# CRC-16/MODBUS (polynomial 0x8005, reflected 0xA001) - must match firmware
# ---------------------------------------------------------------------------
def crc16_modbus(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_frame(slave, func, payload):
    frame = bytearray([slave & 0xFF, func & 0xFF])
    frame.extend(payload)
    crc = crc16_modbus(frame)
    frame.append(crc & 0xFF)       # CRC low byte first
    frame.append((crc >> 8) & 0xFF)
    return bytes(frame)


def _u16(v):
    return [(v >> 8) & 0xFF, v & 0xFF]


def _u16s(vals):
    out = []
    for v in vals:
        out.extend(_u16(v))
    return out


# ---------------------------------------------------------------------------
# Serial helpers
# ---------------------------------------------------------------------------
def read_exact(ser, timeout, n):
    """Read exactly n bytes; raise RuntimeError on timeout."""
    buf = bytearray()
    deadline = time.time() + timeout
    while len(buf) < n and time.time() < deadline:
        chunk = ser.read(n - len(buf))
        if chunk:
            buf.extend(chunk)
    if len(buf) < n:
        raise RuntimeError("response timeout: got %d/%d bytes" % (len(buf), n))
    return bytes(buf)


def read_response(ser, timeout, req_func):
    """Read one complete Modbus response frame and validate its CRC.

    Returns the body (without CRC).  Raises RuntimeError on timeout or a
    CRC mismatch.  Response layout depends on the request function code:
      FC03 : slave+func+byte_count+data+crc          (variable length)
      FC06 : slave+func+addr(2)+value(2)+crc          (fixed 8 bytes)
      FC16 : slave+func+addr(2)+count(2)+crc          (fixed 8 bytes)
      exc  : slave+func|0x80+excode+crc               (fixed 5 bytes)
    """
    head = read_exact(ser, timeout, 3)          # slave, func, x
    func = head[1]
    if func & 0x80:
        tail = read_exact(ser, timeout, 2)      # exception frame: excode + crc
        body = head
        crc_raw = tail
    elif req_func == 0x03:
        byte_count = head[2]
        tail = read_exact(ser, timeout, byte_count + 2)
        body = head + tail[:byte_count]
        crc_raw = tail[byte_count:]
    else:  # FC06 / FC16: fixed echo frame
        tail = read_exact(ser, timeout, 5)
        body = head + tail[:3]
        crc_raw = tail[3:]
    calc = crc16_modbus(body)
    if calc != (crc_raw[0] | (crc_raw[1] << 8)):
        raise RuntimeError(
            "CRC mismatch: calc=0x%04X frame=0x%02X%02X" % (calc, crc_raw[0], crc_raw[1])
        )
    return body


def expect_ok(ser, slave, func, timeout):
    """FC06/FC16 responses echo the request: slave + func + same payload."""
    body = read_response(ser, timeout, func)
    if len(body) != 6:
        raise RuntimeError("unexpected response length %d" % len(body))
    if body[0] != slave:
        raise RuntimeError("wrong slave id in response: %d" % body[0])
    if body[1] != func:
        raise RuntimeError("unexpected function code in response: 0x%02X" % body[1])


def check_exception(ser, slave, timeout):
    """FC03 read path: first byte after slave is either func or func|0x80."""
    body = read_response(ser, timeout, 0x03)
    if body[0] != slave:
        raise RuntimeError("wrong slave id in response: %d" % body[0])
    if body[1] & 0x80:
        code = body[2]
        names = {1: "illegal function", 2: "illegal data address", 3: "illegal data value"}
        raise RuntimeError("Modbus exception 0x%02X: %s" % (code, names.get(code, "unknown")))
    if body[1] != 0x03:
        raise RuntimeError("unexpected function code: 0x%02X" % body[1])
    return body


# ---------------------------------------------------------------------------
# Function codes
# ---------------------------------------------------------------------------
def read_holding_regs(ser, slave, addr, count, timeout):
    ser.reset_input_buffer()
    frame = build_frame(slave, 0x03, _u16(addr) + _u16(count))
    ser.write(frame)
    body = check_exception(ser, slave, timeout)
    byte_count = body[2]
    if byte_count != count * 2:
        raise RuntimeError("unexpected byte count %d (expected %d)" % (byte_count, count * 2))
    data = body[3:]
    if len(data) < byte_count:
        raise RuntimeError("truncated register data")
    return [((data[i] << 8) | data[i + 1]) for i in range(0, byte_count, 2)]


def write_single_reg(ser, slave, addr, value, timeout):
    ser.reset_input_buffer()
    frame = build_frame(slave, 0x06, _u16(addr) + _u16(value))
    ser.write(frame)
    expect_ok(ser, slave, 0x06, timeout)


def write_multiple_regs(ser, slave, addr, values, timeout):
    ser.reset_input_buffer()
    n = len(values)
    payload = _u16(addr) + _u16(n) + [n * 2] + _u16s(values)
    frame = build_frame(slave, 0x10, payload)
    ser.write(frame)
    expect_ok(ser, slave, 0x10, timeout)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def cmd_read(args, ser):
    vals = read_holding_regs(ser, args.slave, args.addr, args.count, args.timeout)
    for i, v in enumerate(vals):
        print("  reg[%d] = %u (0x%04X)" % (args.addr + i, v, v))
    print("read %d register(s) OK" % len(vals))


def cmd_write(args, ser):
    write_single_reg(ser, args.slave, args.addr, args.value, args.timeout)
    print("wrote %d to reg[%d] OK" % (args.value, args.addr))


def cmd_write_multi(args, ser):
    write_multiple_regs(ser, args.slave, args.addr, args.values, args.timeout)
    print("wrote %d register(s) starting at reg[%d] OK" % (len(args.values), args.addr))


def cmd_monitor(args, ser):
    print("polling reg[%d] every %.1f s (Ctrl+C to stop)" % (args.addr, args.interval))
    try:
        while True:
            vals = read_holding_regs(ser, args.slave, args.addr, args.count, args.timeout)
            ts = time.strftime("%H:%M:%S")
            desc = ", ".join("reg[%d]=%d" % (args.addr + i, v) for i, v in enumerate(vals))
            print("[%s] %s" % (ts, desc), flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")


def main():
    parser = argparse.ArgumentParser(description="Modbus RTU master for hw2c modbus_demo")
    parser.add_argument("--port", default="COM4", help="serial port (default COM4)")
    parser.add_argument("--baud", type=int, default=9600, help="baud rate (default 9600)")
    parser.add_argument("--slave", type=int, default=1, help="Modbus slave address (default 1)")
    parser.add_argument("--timeout", type=float, default=0.2, help="response timeout s (default 0.2)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_read = sub.add_parser("read", help="read holding registers (FC03)")
    p_read.add_argument("addr", type=int)
    p_read.add_argument("count", type=int, nargs="?", default=1)
    p_read.set_defaults(func=cmd_read)

    p_write = sub.add_parser("write", help="write single register (FC06)")
    p_write.add_argument("addr", type=int)
    p_write.add_argument("value", type=int)
    p_write.set_defaults(func=cmd_write)

    p_multi = sub.add_parser("write_multi", help="write multiple registers (FC16)")
    p_multi.add_argument("addr", type=int)
    p_multi.add_argument("values", type=int, nargs="+")
    p_multi.set_defaults(func=cmd_write_multi)

    p_mon = sub.add_parser("monitor", help="poll registers periodically")
    p_mon.add_argument("addr", type=int, nargs="?", default=1)
    p_mon.add_argument("count", type=int, nargs="?", default=1)
    p_mon.add_argument("interval", type=float, nargs="?", default=1.0)
    p_mon.set_defaults(func=cmd_monitor)

    args = parser.parse_args()
    try:
        ser = serial.Serial(args.port, args.baud, timeout=args.timeout)
    except serial.SerialException as e:
        print("cannot open %s: %s" % (args.port, e), file=sys.stderr)
        return 1
    try:
        args.func(args, ser)
    except RuntimeError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    finally:
        ser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
