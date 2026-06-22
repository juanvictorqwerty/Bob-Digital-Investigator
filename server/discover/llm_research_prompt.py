"""
LLM prompt builder for research report compilation.
This module re-exports build_research_prompt from research_generator
for backward compatibility with existing imports.
"""
from .research_generator import build_research_prompt

# Re-export for compatibility
__all__ = ['build_research_prompt']