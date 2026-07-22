#!/usr/bin/env python3
"""
HIL Test Runner - listens to serial output from target and displays Unity test results.
Usage: python hil_runner.py [--port COMx] [--baud 115200]
"""
import serial
import serial.tools.list_ports
import argparse
import sys
import time

def find_stlink_port(baudrate):
    """Try to find a serial port associated with ST-Link or generic USB serial."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        # ST-Link VCP usually appears as "STLink Virtual COM Port" or similar
        if "STLink" in port.description or "STMicroelectronics" in port.description:
            print(f"Auto-detected ST-Link VCP: {port.device}")
            return serial.Serial(port.device, baudrate, timeout=5)
    # Fallback: try any USB serial
    for port in ports:
        if "USB" in port.description or "Serial" in port.description:
            print(f"Auto-detected USB serial: {port.device}")
            return serial.Serial(port.device, baudrate, timeout=5)
    return None

def main():
    parser = argparse.ArgumentParser(description="HIL Test Runner")
    parser.add_argument("--port", help="Serial port (e.g., COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default 115200)")
    args = parser.parse_args()

    if args.port:
        ser = serial.Serial(args.port, args.baud, timeout=5)
        print(f"Using specified port {args.port}")
    else:
        ser = find_stlink_port(args.baud)
        if not ser:
            print("No suitable serial port found. Please specify --port.")
            sys.exit(1)

    print("Listening for test results...")
    while True:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if line:
            print(line)
            if "FAIL" in line or "OK" in line:
                # Unity prints summary line with FAIL or OK
                # We could parse, but just exit after summary
                time.sleep(1)
                # read any remaining lines
                while ser.in_waiting:
                    extra = ser.readline().decode('utf-8', errors='ignore').strip()
                    if extra:
                        print(extra)
                break
    ser.close()

if __name__ == "__main__":
    main()