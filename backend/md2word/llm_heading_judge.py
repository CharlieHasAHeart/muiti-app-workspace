import json
import os
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI


@dataclass
class HeadingJudgeResult:
    has_document_title: bool
    heading_shift: int
    confidence: float
    reason: str
    remove_manual_toc: bool = False
    source: str = "llm"


class OpenAICompatibleHeadingJudge:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 20.0):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> "OpenAICompatibleHeadingJudge | None":
        api_key = os.getenv("MD2WORD_LLM_API_KEY", "").strip()
        model = os.getenv("MD2WORD_LLM_MODEL", "").strip()
        if not api_key or not model:
            return None

        base_url = os.getenv("MD2WORD_LLM_BASE_URL", "https://api.openai.com/v1").strip()
        timeout = float(os.getenv("MD2WORD_LLM_TIMEOUT", "20").strip())
        return cls(base_url=base_url, api_key=api_key, model=model, timeout=timeout)

    def judge(self, heading_outline: str, context_excerpt: str, manual_toc_summary: str = "none") -> HeadingJudgeResult | None:
        prompt = (
            "You are judging Markdown document structure before DOCX rendering.\n"
            "Tasks:\n"
            "1. Decide whether the first H1 is a document title instead of chapter 1.\n"
            "2. Decide whether a detected TOC block is a handwritten table of contents that should be removed because Word will generate a TOC automatically.\n"
            "If the first H1 is a document title, remaining headings should shift by -1 for rendering.\n"
            "Return JSON only with keys: has_document_title, heading_shift, remove_manual_toc, confidence, reason.\n"
            "heading_shift must be 0 or -1.\n\n"
            "Heading outline:\n"
            f"{heading_outline}\n\n"
            "Manual TOC candidate summary:\n"
            f"{manual_toc_summary}\n\n"
            "Context excerpt:\n"
            f"{context_excerpt}\n"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You output strict JSON only. No markdown fences.",
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except (APIConnectionError, APITimeoutError, APIError, ValueError):
            return None

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            shift = int(result.get("heading_shift", 0))
            if shift not in (0, -1):
                shift = 0
            return HeadingJudgeResult(
                has_document_title=bool(result.get("has_document_title", False)),
                heading_shift=shift,
                remove_manual_toc=bool(result.get("remove_manual_toc", False)),
                confidence=float(result.get("confidence", 0.0)),
                reason=str(result.get("reason", "")).strip(),
            )
        except (IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None
