from abc import ABC, abstractmethod
import re
import httpx
from app.core.config import settings
from app.core.logging import logger


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate response from LLM."""
        pass


class MockLLMProvider(LLMProvider):
    """
    Offline/testing LLM provider that synthesizes grounded code explanations
    from the retrieved context chunks with valid file and line citations.
    """

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        logger.info("Using MockLLMProvider to generate grounded answer.")

        # Extract file paths and line ranges from the context if present
        file_matches = re.findall(
            r"\[File:\s*([^\s\]]+)\s*\|\s*Lines:\s*(\d+)–(\d+)\]", user_prompt
        )

        if not file_matches:
            return (
                "Based on the codebase analysis, I could not find relevant code "
                "or symbols matching your question in this repository."
            )

        citations_summary = []
        for file_path, start, end in file_matches[:3]:
            citations_summary.append(f"- **{file_path}** (Lines {start}–{end})")

        citations_text = "\n".join(citations_summary)
        first_file, first_start, first_end = file_matches[0]

        return (
            f"Based on the indexed codebase, the implementation is located in:\n\n"
            f"{citations_text}\n\n"
            f"### Implementation Summary\n"
            f"The primary logic is defined in `{first_file}` between lines {first_start} and {first_end}. "
            f"The functions and modules in these references handle the requested operation, coordinating "
            f"with the relevant components according to the architecture observed in the source code.\n\n"
            f"Refer to the source citations above for line-by-line inspection."
        )


class OpenAILikeProvider(LLMProvider):
    """Provider for OpenAI, Groq, Ollama, and OpenAI-compatible endpoints."""

    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        try:
            with httpx.Client(timeout=45.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    raise RuntimeError(
                        f"LLM API request failed with status {response.status_code}: {response.text}"
                    )
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"LLM provider error: {str(e)}") from e


def get_llm_provider() -> LLMProvider:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        api_key = settings.LLM_API_KEY
        if not api_key:
            logger.warning("Groq selected but LLM_API_KEY is empty. Falling back to MockLLMProvider.")
            return MockLLMProvider()
        base_url = settings.LLM_BASE_URL or "https://api.groq.com/openai/v1"
        return OpenAILikeProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.LLM_MODEL or "llama-3.3-70b-versatile",
        )

    elif provider == "openai":
        api_key = settings.LLM_API_KEY
        if not api_key:
            logger.warning("OpenAI selected but LLM_API_KEY is empty. Falling back to MockLLMProvider.")
            return MockLLMProvider()
        base_url = settings.LLM_BASE_URL or "https://api.openai.com/v1"
        return OpenAILikeProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.LLM_MODEL or "gpt-4o-mini",
        )

    elif provider == "ollama":
        base_url = settings.LLM_BASE_URL or "http://localhost:11434/v1"
        return OpenAILikeProvider(
            api_key="ollama",
            base_url=base_url,
            model=settings.LLM_MODEL or "llama3",
        )

    return MockLLMProvider()
