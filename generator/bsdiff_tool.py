#!/usr/bin/env python3
"""
BSDIFF Patch Generator for Hardware2Code FOTA
Generates a binary diff patch between two firmware versions.

Output format: BSDIFF40 (raw, no bzip2 compression for embedded compatibility)
Header:  "BSDIFF40" (8 bytes)
         ctrl_len   (8 bytes, little-endian)
         data_len   (8 bytes, little-endian)
         new_size   (8 bytes, little-endian)
Body:    [control block (raw)] [diff block (raw)] [extra block (raw)]

Each control triple: add_len(8B) | copy_len(8B) | seek_len(8B)  = 24 bytes per entry

Usage: python bsdiff_tool.py old.bin new.bin -o patch.bin [--raw]
"""

import argparse
import struct
import sys
from pathlib import Path


def suffix_array(data: bytes) -> list:
    """
    Build a suffix array for the byte string data.
    Simple implementation using Python's sorted() — acceptable for firmware
    sizes up to ~256KB.
    """
    n = len(data)
    # Build indices sorted by suffix
    sa = list(range(n))
    sa.sort(key=lambda i: data[i:])
    return sa


def bsearch_sa(data: bytes, sa: list, pattern: bytes) -> int:
    """
    Binary search the suffix array for the longest prefix match of `pattern`.
    Returns the index in data where the best match starts, or -1 if none.
    """
    lo, hi = 0, len(sa) - 1
    best_len = 0
    best_pos = -1

    while lo <= hi:
        mid = (lo + hi) // 2
        suffix = data[sa[mid]:]

        # Compare pattern with suffix
        match_len = 0
        min_len = min(len(pattern), len(suffix))
        while match_len < min_len and pattern[match_len] == suffix[match_len]:
            match_len += 1

        if match_len > best_len:
            best_len = match_len
            best_pos = sa[mid]

        if match_len == min_len:
            # Pattern is prefix of suffix or vice versa
            if len(suffix) <= len(pattern):
                lo = mid + 1
            else:
                hi = mid - 1
        elif suffix[match_len] < pattern[match_len]:
            lo = mid + 1
        else:
            hi = mid - 1

    return best_pos if best_len >= 8 else -1


def bsdiff(old_data: bytes, new_data: bytes) -> tuple:
    """
    Generate BSDIFF40 diff between old_data and new_data.
    Returns (ctrl_block, diff_block, extra_block) as bytes.
    """
    old_len = len(old_data)
    new_len = len(new_data)

    # Build suffix array for old data
    sa = suffix_array(old_data)

    # Control triples: (add_len, copy_len, seek_len)
    ctrl_entries = []
    diff_parts = []
    extra_parts = []

    scan = 0      # position in new_data
    last_scan = 0  # last position where we changed from writing extra
    last_pos = 0   # last matching position in old_data

    while scan < new_len:
        # Find the best match in old_data for remaining new_data
        remaining = new_data[scan:scan + min(256, new_len - scan)]
        old_score = 0
        score_pos = 0

        # Search for matching position in old data
        pos = bsearch_sa(old_data, sa, remaining)
        if pos >= 0:
            # Extend match forward
            s = 0
            while scan + s < new_len and pos + s < old_len and new_data[scan + s] == old_data[pos + s]:
                s += 1
            # Extend match backward
            t = 0
            while scan > t and pos > t and new_data[scan - t - 1] == old_data[pos - t - 1]:
                t += 1

            old_score = s + t

        if old_score > 8:
            # Good match found — extend score backward
            score_pos = pos - (old_score - (scan - (scan - 0)))
            # Correct: score_len = old_score, score_pos = pos
            score_len = old_score
            score_pos = pos
        else:
            old_score = 0

        if old_score > 8:
            # Found a good match — emit add for the bytes before match, then copy for match
            add_len = scan - last_scan

            if add_len > 0:
                extra_parts.append(new_data[last_scan:scan])
                add_len = scan - last_scan

            copy_len = old_score
            seek_len = score_pos - last_pos

            ctrl_entries.append((add_len, copy_len, seek_len))
            diff_parts.append(b'')  # no diff bytes for copy

            scan += old_score
            last_scan = scan
            last_pos = score_pos + old_score
        else:
            scan += 1

    # Remaining bytes at the end are extra
    if last_scan < new_len:
        extra_parts.append(new_data[last_scan:])

    ctrl_entries.append((new_len - last_scan, 0, 0))
    extra_parts.append(new_data[last_scan:])

    # Build control block: 24 bytes per entry (3 × int64 LE)
    ctrl_block = b''
    for add_len, copy_len, seek_len in ctrl_entries:
        ctrl_block += struct.pack('<QQQ', add_len, copy_len, seek_len)

    # Build diff block (empty — no diff bytes in raw format)
    diff_block = b''.join(diff_parts)

    # Build extra block
    extra_block = b''.join(extra_parts)

    return ctrl_block, diff_block, extra_block, new_len


def main():
    parser = argparse.ArgumentParser(
        description='BSDIFF patch generator for Hardware2Code FOTA')
    parser.add_argument('old_file', help='Old firmware binary')
    parser.add_argument('new_file', help='New firmware binary')
    parser.add_argument('-o', '--output', required=True, help='Output patch file')
    parser.add_argument('--raw', action='store_true',
                        help='Raw format (no compression, default for embedded)')
    args = parser.parse_args()

    # Read input files
    try:
        old_data = Path(args.old_file).read_bytes()
        new_data = Path(args.new_file).read_bytes()
    except FileNotFoundError as e:
        print(f"ERROR: File not found: {e}")
        sys.exit(1)
    except (PermissionError, OSError, MemoryError) as e:
        print(f"ERROR: Failed to read input files: {e}")
        sys.exit(1)

    print(f"Old firmware: {len(old_data)} bytes")
    print(f"New firmware: {len(new_data)} bytes")

    # Generate diff
    ctrl_block, diff_block, extra_block, new_size = bsdiff(old_data, new_data)

    # Assemble BSDIFF40 file
    header = b'BSDIFF40'
    header += struct.pack('<QQQ', len(ctrl_block), len(diff_block), new_size)

    patch_data = header + ctrl_block + diff_block + extra_block

    # Write output
    output_path = Path(args.output)
    output_path.write_bytes(patch_data)

    total_size = len(patch_data)
    ratio = (total_size / len(new_data)) * 100 if len(new_data) > 0 else 0
    print(f"Patch file: {total_size} bytes ({ratio:.1f}% of new firmware)")
    print(f"  Control block: {len(ctrl_block)} bytes")
    print(f"  Diff block:    {len(diff_block)} bytes")
    print(f"  Extra block:   {len(extra_block)} bytes")
    print(f"Written to: {output_path}")


if __name__ == '__main__':
    main()
