"""Multi-LLM client supporting multiple providers."""

import asyncio
import logging
from enum import Enum
from typing import Optional, Dict, Any
import httpx


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    CLAUDE = "claude"
    OPENAI = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"


class MultiLLMClient:
    """Client for interacting with multiple LLM providers."""

    def __init__(self, config: Any):
        """Initialize multi-LLM client.

        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.default_provider = LLMProvider(config.llm.default_provider)
        self.privacy_provider = LLMProvider(config.llm.privacy_provider) if config.llm.privacy_mode else None

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        is_sensitive: bool = False,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """Generate text using specified LLM provider.

        Args:
            prompt: Input prompt
            provider: LLM provider to use (None = use default)
            is_sensitive: If True, use privacy provider for sensitive data
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Generated text or None on error
        """
        # Determine which provider to use
        if is_sensitive and self.privacy_provider:
            use_provider = self.privacy_provider
        elif provider:
            use_provider = provider
        else:
            use_provider = self.default_provider

        try:
            if use_provider == LLMProvider.CLAUDE:
                return await self._generate_claude(prompt, max_tokens, temperature)
            elif use_provider == LLMProvider.OPENAI:
                return await self._generate_openai(prompt, max_tokens, temperature)
            elif use_provider == LLMProvider.OLLAMA:
                return await self._generate_ollama(prompt, max_tokens, temperature)
            elif use_provider == LLMProvider.GEMINI:
                return await self._generate_gemini(prompt, max_tokens, temperature)
            else:
                self.logger.error(f"Unsupported provider: {use_provider}")
                return None

        except Exception as e:
            self.logger.error(f"LLM generation failed ({use_provider}): {str(e)}")
            return None

    async def _generate_claude(
        self,
        prompt: str,
        max_tokens: Optional[int],
        temperature: float
    ) -> Optional[str]:
        """Generate using Claude API.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Temperature

        Returns:
            Generated text
        """
        try:
            from anthropic import AsyncAnthropic

            provider_config = self.config.llm.providers.get("claude")
            if not provider_config or not provider_config.api_key:
                self.logger.error("Claude API key not configured")
                return None

            client = AsyncAnthropic(api_key=provider_config.api_key)

            message = await client.messages.create(
                model=provider_config.model,
                max_tokens=max_tokens or provider_config.max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if message.content and len(message.content) > 0:
                return message.content[0].text

            return None

        except Exception as e:
            self.logger.error(f"Claude API error: {str(e)}")
            return None

    async def _generate_openai(
        self,
        prompt: str,
        max_tokens: Optional[int],
        temperature: float
    ) -> Optional[str]:
        """Generate using OpenAI API.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Temperature

        Returns:
            Generated text
        """
        try:
            from openai import AsyncOpenAI

            provider_config = self.config.llm.providers.get("openai")
            if not provider_config or not provider_config.api_key:
                self.logger.error("OpenAI API key not configured")
                return None

            client = AsyncOpenAI(api_key=provider_config.api_key)

            response = await client.chat.completions.create(
                model=provider_config.model,
                max_tokens=max_tokens or provider_config.max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content

            return None

        except Exception as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            return None

    async def _generate_ollama(
        self,
        prompt: str,
        max_tokens: Optional[int],
        temperature: float
    ) -> Optional[str]:
        """Generate using Ollama local LLM.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Temperature

        Returns:
            Generated text
        """
        try:
            provider_config = self.config.llm.providers.get("ollama")
            if not provider_config:
                self.logger.error("Ollama not configured")
                return None

            base_url = provider_config.base_url or "http://localhost:11434"
            model = provider_config.model

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{base_url}/api/generate",
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens or 4096,
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "")

                self.logger.error(f"Ollama API returned status {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Ollama API error: {str(e)}")
            return None

    async def _generate_gemini(
        self,
        prompt: str,
        max_tokens: Optional[int],
        temperature: float
    ) -> Optional[str]:
        """Generate using Google Gemini API.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens
            temperature: Temperature

        Returns:
            Generated text
        """
        try:
            provider_config = self.config.llm.providers.get("gemini")
            if not provider_config or not provider_config.api_key:
                self.logger.error("Gemini API key not configured")
                return None

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{provider_config.model}:generateContent?key={provider_config.api_key}",
                    json={
                        "contents": [{
                            "parts": [{"text": prompt}]
                        }],
                        "generationConfig": {
                            "temperature": temperature,
                            "maxOutputTokens": max_tokens or provider_config.max_tokens,
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    if "candidates" in result and len(result["candidates"]) > 0:
                        candidate = result["candidates"][0]
                        if "content" in candidate and "parts" in candidate["content"]:
                            return candidate["content"]["parts"][0].get("text", "")

                self.logger.error(f"Gemini API returned status {response.status_code}")
                return None

        except Exception as e:
            self.logger.error(f"Gemini API error: {str(e)}")
            return None

    async def is_available(self, provider: LLMProvider) -> bool:
        """Check if a provider is available and configured.

        Args:
            provider: Provider to check

        Returns:
            bool: True if provider is available
        """
        provider_config = self.config.llm.providers.get(provider.value)

        if not provider_config:
            return False

        # Check for required API keys (except Ollama)
        if provider != LLMProvider.OLLAMA:
            return bool(provider_config.api_key)

        # For Ollama, check if service is reachable
        try:
            base_url = provider_config.base_url or "http://localhost:11434"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{base_url}/api/tags")
                return response.status_code == 200
        except:
            return False
