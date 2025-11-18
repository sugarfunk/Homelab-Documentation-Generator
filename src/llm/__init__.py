"""LLM integration for AI-powered documentation."""

from .multi_llm import MultiLLMClient, LLMProvider
from .prompts import (
    generate_service_explanation,
    generate_troubleshooting_guide,
    generate_plain_english_summary,
    generate_analogy,
    generate_procedure,
)

__all__ = [
    "MultiLLMClient",
    "LLMProvider",
    "generate_service_explanation",
    "generate_troubleshooting_guide",
    "generate_plain_english_summary",
    "generate_analogy",
    "generate_procedure",
]
