from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from movie_night_mediator.mvp_plus_3 import (
    DirectedNudge,
    DirectedNudgeResolution,
    DirectedNudgeStatus,
    PersonCandidateIntent,
)

OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"
OPENAI_INTENT_MODEL_ENV_VAR = "OPENAI_INTENT_MODEL"
DEFAULT_OPENAI_INTENT_MODEL = "gpt-4.1-mini"
OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


@dataclass(frozen=True)
class OpenAIDirectedNudgeProvider:
    api_key: str
    model: str = DEFAULT_OPENAI_INTENT_MODEL

    @classmethod
    def from_env(cls) -> OpenAIDirectedNudgeProvider | None:
        api_key = os.environ.get(OPENAI_API_KEY_ENV_VAR, "").strip()
        if not api_key:
            return None
        model = os.environ.get(OPENAI_INTENT_MODEL_ENV_VAR, "").strip()
        return cls(api_key=api_key, model=model or DEFAULT_OPENAI_INTENT_MODEL)

    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        prompt = {
            "task": "interpret_directed_nudge",
            "user_text": text,
            "supported_filters": [
                "people",
                "genres",
                "release_year_min",
                "release_year_max",
                "exclude_watched",
                "exclude_subtitled",
            ],
            "supported_soft_signals": [
                "comforting",
                "intense",
                "bleak",
                "beautiful",
                "offbeat",
                "sad",
                "slow-burn",
                "desert",
                "manhunt",
                "lawman",
                "killer",
                "tonight",
            ],
            "rules": [
                "Be conservative.",
                "Only mark resolution=exact when the request maps cleanly to supported filters or soft signals.",
                "Use resolution=guess only when the inference is plausible and useful, and make the summary say it is a guess.",
                "Use resolution=unsupported when the request cannot be translated directly into supported filters.",
                "Do not invent a genre, person, or decade unless strongly implied.",
                "Preserve specific concrete cues from the user text when they are useful, such as western, desert, sheriff, killer, manhunt, slow-burn, or anti-superhero language.",
                "Do not collapse a specific request into a broader genre if the specific cue can be preserved.",
                "For aesthetic requests like color, texture, cinematography, or vibe, prefer unsupported unless there is a clear conventional mapping.",
                "If clarification is needed, use status=clarification_required and ask one short question.",
                "Always return valid JSON only.",
            ],
            "response_schema": {
                "status": "confirmation_required|clarification_required",
                "resolution": "exact|guess|unsupported",
                "user_facing_summary": "string|null",
                "clarification_question": "string|null",
                "unsupported_reason": "string|null",
                "filters": {
                    "people": ["string"],
                    "genres": ["string"],
                    "release_year_min": "number",
                    "release_year_max": "number",
                    "exclude_watched": "boolean",
                    "exclude_subtitled": "boolean",
                },
                "soft_signals": ["string"],
                "excluded_signals": ["string"],
                "person_intents": [{"raw_name": "string"}],
                "confidence": "low|medium|high",
            },
        }

        response_payload = self._chat_completion_json(prompt)
        return _payload_to_directed_nudge(text, response_payload)

    def _chat_completion_json(self, prompt: dict[str, Any]) -> dict[str, Any]:
        body = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You translate movie steering requests into conservative structured constraints. "
                        "Return JSON only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=True),
                },
            ],
        }
        req = request.Request(
            OPENAI_CHAT_COMPLETIONS_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"LLM steer request failed: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise ValueError(f"LLM steer request failed: {exc.reason}") from exc

        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        if not isinstance(content, str) or not content.strip():
            raise ValueError("LLM steer request returned no content.")
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM steer request returned invalid JSON.")
        return parsed


def _payload_to_directed_nudge(raw_text: str, payload: dict[str, Any]) -> DirectedNudge:
    status = payload.get("status", "confirmation_required")
    resolution = payload.get("resolution", "unsupported")
    filters = payload.get("filters")
    filters = filters if isinstance(filters, dict) else {}
    soft_signals = payload.get("soft_signals")
    excluded_signals = payload.get("excluded_signals")
    person_intents_payload = payload.get("person_intents")

    person_intents: list[PersonCandidateIntent] = []
    if isinstance(person_intents_payload, list):
        for item in person_intents_payload:
            if not isinstance(item, dict):
                continue
            raw_name = item.get("raw_name")
            if not isinstance(raw_name, str) or not raw_name.strip():
                continue
            person_intents.append(
                PersonCandidateIntent(
                    raw_name=raw_name.strip(),
                    normalized_name=raw_name.strip().casefold(),
                )
            )

    return DirectedNudge(
        raw_text=raw_text,
        status=DirectedNudgeStatus(status),
        resolution=DirectedNudgeResolution(resolution),
        user_facing_summary=_optional_str(payload.get("user_facing_summary")),
        clarification_question=_optional_str(payload.get("clarification_question")),
        unsupported_reason=_optional_str(payload.get("unsupported_reason")),
        filters=filters,
        soft_signals=_string_list(soft_signals),
        excluded_signals=_string_list(excluded_signals),
        person_intents=tuple(person_intents),
        confidence=_optional_str(payload.get("confidence")) or "medium",
    )


def _string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip()
        for item in value
        if isinstance(item, str) and item.strip()
    )


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
