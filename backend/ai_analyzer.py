import json
import os
from typing import Any

from openai import OpenAI


class AIAnalysisError(Exception):
    """Raised when AI analysis fails or returns invalid payload."""


def _build_prompt(provider: str, resources: list[dict[str, Any]]) -> str:
    sample = resources[:200]
    return (
        "Analyze this cloud inventory for cost optimization opportunities. "
        "Return ONLY valid JSON with keys: summary, issues, estimated_savings. "
        "Each issue must include resource_name, issue_type, severity, explanation, fix_command. "
        "Allowed issue_type: over-provisioned, unused, misconfigured, wrong-tier. "
        "Allowed severity: high, medium, low. "
        f"Cloud provider: {provider}. "
        "Resource data:\n"
        + json.dumps(sample, ensure_ascii=True)
    )


def _normalize_issue(issue: dict[str, Any]) -> dict[str, str]:
    issue_type = str(issue.get("issue_type", "misconfigured")).strip().lower()
    if issue_type not in {"over-provisioned", "unused", "misconfigured", "wrong-tier"}:
        issue_type = "misconfigured"

    severity = str(issue.get("severity", "low")).strip().lower()
    if severity not in {"high", "medium", "low"}:
        severity = "low"

    return {
        "resource_name": str(issue.get("resource_name", "unknown-resource")),
        "issue_type": issue_type,
        "severity": severity,
        "explanation": str(issue.get("explanation", "No explanation provided.")),
        "fix_command": str(issue.get("fix_command", "No command provided.")),
    }


def _normalize_response(payload: dict[str, Any]) -> dict[str, Any]:
    issues_raw = payload.get("issues")
    issues: list[dict[str, str]] = []
    if isinstance(issues_raw, list):
        for issue in issues_raw:
            if isinstance(issue, dict):
                issues.append(_normalize_issue(issue))

    return {
        "summary": str(payload.get("summary", "No summary provided.")),
        "issues": issues,
        "estimated_savings": str(payload.get("estimated_savings", "$0/month")),
    }


def analyze_resources(provider: str, resources: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIAnalysisError("OPENAI_API_KEY is missing in environment variables.")

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(provider=provider, resources=resources)

    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a cloud FinOps assistant. "
                        "Return strictly valid JSON and keep recommendations practical."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise AIAnalysisError(f"OpenAI API request failed: {exc}") from exc

    choices = completion.choices or []
    if not choices or not choices[0].message or not choices[0].message.content:
        raise AIAnalysisError("OpenAI returned an empty analysis response.")

    content = choices[0].message.content
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AIAnalysisError("OpenAI response was not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise AIAnalysisError("OpenAI response JSON must be an object.")

    return _normalize_response(payload)
