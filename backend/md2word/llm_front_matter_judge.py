import json
import os
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, OpenAI


@dataclass
class FrontMatterJudgeResult:
    has_subtitle: bool
    subtitle_text: str
    subtitle_line: int | None
    confidence: float
    reason: str
    source: str = "llm"


class OpenAICompatibleFrontMatterJudge:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 20.0):
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )

    @classmethod
    def from_env(cls) -> "OpenAICompatibleFrontMatterJudge | None":
        api_key = os.getenv("MD2WORD_LLM_API_KEY", "").strip()
        model = os.getenv("MD2WORD_LLM_MODEL", "").strip()
        if not api_key or not model:
            return None

        base_url = os.getenv("MD2WORD_LLM_BASE_URL", "https://api.openai.com/v1").strip()
        timeout = float(os.getenv("MD2WORD_LLM_TIMEOUT", "20").strip())
        return cls(base_url=base_url, api_key=api_key, model=model, timeout=timeout)

    def judge(self, front_matter_lines: str, heading_outline: str, first_body_heading: str) -> FrontMatterJudgeResult | None:
        prompt = (
            "You are judging the front matter of a Markdown document before DOCX rendering.\n"
            "Task: decide whether the document has a subtitle under the main title.\n"
            "A subtitle is optional. Most documents do not have one.\n"
            "Do not confuse subtitle text with metadata such as document number, recipient, date, purpose, directory, or body text.\n"
            "Return JSON only with keys: has_subtitle, subtitle_text, subtitle_line, confidence, reason.\n\n"
            "Front matter lines:\n"
            f"{front_matter_lines}\n\n"
            "Heading outline:\n"
            f"{heading_outline}\n\n"
            "First body heading:\n"
            f"{first_body_heading}\n"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You output strict JSON only. No markdown fences."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except (APIConnectionError, APITimeoutError, APIError, ValueError):
            return None

        try:
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            line = result.get("subtitle_line")
            subtitle_line = int(line) if line not in (None, "") else None
            return FrontMatterJudgeResult(
                has_subtitle=bool(result.get("has_subtitle", False)),
                subtitle_text=str(result.get("subtitle_text", "")).strip(),
                subtitle_line=subtitle_line,
                confidence=float(result.get("confidence", 0.0)),
                reason=str(result.get("reason", "")).strip(),
            )
        except (IndexError, TypeError, ValueError, json.JSONDecodeError):
            return None
