#!/usr/bin/env python3
"""
Hardware2Code Unit Test Runner
Compiles and runs all test executables using native gcc.
"""
import subprocess
import sys
import os
import glob
from pathlib import Path

# ---- Use absolute path to native GCC (no spaces) ----
# 根据操作系统选择 GCC 命令
if sys.platform.startswith("win"):
    GCC = "C:/mingw64/bin/gcc"      # Windows 绝对路径
else:
    GCC = "gcc"                     # Linux 环境下默认 gcc
CFLAGS = ["-Wall", "-Wextra", "-DTEST"]
INCLUDES = ["-I.", "-I../src", "-I../src/drivers", "-Iunity", "-I../config"]
UNITY_SRC = "unity/unity.c"
MOCK_SRC = "mock_hal.c"

def find_tests():
    """Return a list of test names (without .c extension) for all test_*.c files."""
    tests = []
    for f in glob.glob("test_*.c"):
        name = os.path.splitext(f)[0]
        tests.append(name)
    return sorted(tests)

def compile_test(name):
    src = name + ".c"
    exe = name + ".exe"
    cmd = [GCC] + CFLAGS + INCLUDES + [UNITY_SRC, MOCK_SRC, src, "-o", exe]
    print(f"Compiling {name}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Compilation failed for {name}:")
        print(result.stderr)
        return False
    return True

def run_test(name):
    exe = name + ".exe"
    print(f"Running {name}...")
    result = subprocess.run(["." + os.sep + exe], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"{name} FAILED")
        return False
    print(f"{name} PASSED")
    return True

def main():
    # 切换到 test/ 目录，确保找到测试文件
    os.chdir(Path(__file__).parent)
    tests = find_tests()
    if not tests:
        print("No test_*.c files found.")
        sys.exit(1)
    for test in tests:
        if not compile_test(test):
            sys.exit(1)
        if not run_test(test):
            sys.exit(1)
    print("All tests passed.")

if __name__ == "__main__":
    main()