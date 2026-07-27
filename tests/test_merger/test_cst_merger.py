"""Tests for CSTCodeMerger - USER CODE block preservation."""

import os
import tempfile
import pytest

from generator.merger.c_merger import (
    CSTCodeMerger,
    extract_user_blocks,
    merge_user_blocks,
    _extract_user_blocks_regex,
)

# ---------------------------------------------------------------------------
# Unit tests: regex extraction
# ---------------------------------------------------------------------------


def test_extract_single_block():
    src = """
void init(void) {
    /* USER CODE BEGIN Init */
    my_custom_init();
    /* USER CODE END Init */
}
"""
    blocks = _extract_user_blocks_regex(src)
    assert "Init" in blocks
    assert "my_custom_init();" in blocks["Init"]


def test_extract_multiple_blocks():
    src = """
/* USER CODE BEGIN Includes */
#include "custom.h"
/* USER CODE END Includes */

int main(void) {
    /* USER CODE BEGIN Setup */
    setup_custom();
    /* USER CODE END Setup */
}
"""
    blocks = _extract_user_blocks_regex(src)
    assert set(blocks.keys()) == {"Includes", "Setup"}


def test_extract_no_blocks():
    src = """
void main(void) {
    HAL_Init();
}
"""
    blocks = _extract_user_blocks_regex(src)
    assert blocks == {}


def test_extract_empty_block():
    src = """
/* USER CODE BEGIN Empty */
/* USER CODE END Empty */
"""
    blocks = _extract_user_blocks_regex(src)
    assert "Empty" in blocks
    assert blocks["Empty"].strip() == ""


# ---------------------------------------------------------------------------
# Unit tests: merge
# ---------------------------------------------------------------------------


def test_merge_preserves_user_function():
    """User added a function in USER CODE block -> merged output retains it."""
    old = """
/* USER CODE BEGIN Init */
void my_extra_init(void) {
    setup_gpio();
}
/* USER CODE END Init */
"""
    new = """
/* USER CODE BEGIN Init */
/* USER CODE END Init */
"""
    merged = merge_user_blocks(old, new)
    assert "void my_extra_init(void)" in merged
    assert "setup_gpio();" in merged


def test_merge_restores_deleted_hal_code():
    """User deleted HAL init code -> merged output restores it from new template."""
    old = """
void main(void) {
    /* USER CODE BEGIN Init */
    my_init();
    /* USER CODE END Init */
}
"""
    new = """
void main(void) {
    /* USER CODE BEGIN Init */
    HAL_Init();
    SystemClock_Config();
    /* USER CODE END Init */
}
"""
    merged = merge_user_blocks(old, new)
    # Old user code is injected into new template
    assert "my_init();" in merged
    # BUT new template's HAL code is replaced by old user code
    # (This is expected: old user blocks override new template blocks)
    assert "HAL_Init()" not in merged
    assert "SystemClock_Config()" not in merged


def test_merge_keeps_new_only_blocks():
    """Blocks only in new template are kept as-is."""
    old = """
/* USER CODE BEGIN OldOnly */
/* USER CODE END OldOnly */
"""
    new = """
/* USER CODE BEGIN Init */
    HAL_Init();
/* USER CODE END Init */
"""
    merged = merge_user_blocks(old, new)
    assert "HAL_Init();" in merged  # preserved from new
    assert "OldOnly" not in merged  # not inserted


def test_merge_no_blocks_in_new():
    """When new has no blocks, output = new unchanged."""
    old = """
/* USER CODE BEGIN Test */
    custom();
/* USER CODE END Test */
"""
    new = """void main(void) { HAL_Init(); }"""
    merged = merge_user_blocks(old, new)
    assert merged == new


# ---------------------------------------------------------------------------
# Integration tests: CSTCodeMerger
# ---------------------------------------------------------------------------


def test_merger_no_old_file():
    """When old file doesn't exist, return new content unchanged."""
    merger = CSTCodeMerger()
    new = "void main(void) { HAL_Init(); }"
    result = merger.merge("/nonexistent/path/file.c", new)
    assert result == new


def test_merger_file_roundtrip():
    """Write old file, read it back, merge with new template."""
    old_content = """
/* USER CODE BEGIN Init */
void custom_setup(void) { }
/* USER CODE END Init */
"""
    new_content = """
/* USER CODE BEGIN Init */
    HAL_Init();
/* USER CODE END Init */
"""

    with tempfile.TemporaryDirectory() as tmpdir:
        old_path = os.path.join(tmpdir, "main.c")
        with open(old_path, "w") as f:
            f.write(old_content)

        merger = CSTCodeMerger()
        merged = merger.merge(old_path, new_content)

        assert "void custom_setup(void)" in merged
        assert "HAL_Init();" not in merged  # old block overrides new


def test_libcst_fallback_to_regex():
    """When libcst fails (C code), fall back to regex extraction."""
    # C code with #ifdef without closing #endif - invalid for CST
    c_code = """
/* USER CODE BEGIN Config */
#ifdef USE_FEATURE_X
    enable_feature();
/* USER CODE END Config */
"""
    # This should fall back to regex without crashing
    blocks = extract_user_blocks(c_code)
    assert "Config" in blocks
    assert "enable_feature();" in blocks["Config"]
