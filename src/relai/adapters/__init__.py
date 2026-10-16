"""Adapters that turn external agent systems into relai Agents."""

from relai.adapters.openai_compat import OpenAICompatAgent, http_transport

__all__ = ["OpenAICompatAgent", "http_transport"]
