"""
context_builder.py
Backward-compatibility re-export. All logic has been moved to context/ package.
"""

from context.builder import build_context, load_model

__all__ = ['build_context', 'load_model']
