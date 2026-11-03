from __future__ import annotations

import json
import re
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(secret|password|passwd|token|authorization|credential|private.?key|access.?key|api.?key|"
    r"connection.?string|database.?url|dsn|certificate|(?:^|_)auth(?:$|_))",
    re.IGNORECASE,
)
STRING_PATTERNS = (
    (re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"), "[REDACTED_AWS_ACCESS_KEY]"),
    (
        re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(r"(?i)(\b(?:password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*)[^\s,;]+"),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"(\b[A-Z0-9_.-]*(?:SECRET|TOKEN|PASSWORD|PASSWD|CREDENTIAL|PRIVATE_KEY|"
            r"ACCESS_KEY|API_KEY|AUTH|DATABASE_URL|DSN|CONNECTION_STRING)[A-Z0-9_.-]*\b"
            r"\s*[:=]\s*)[^\s,;]+"
        ),
        r"\1[REDACTED]",
    ),
    (
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?-----END "
            r"(?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.DOTALL,
        ),
        "[REDACTED_PRIVATE_KEY]",
    ),
)


def redact_text(value: str) -> str:
    result = value
    for pattern, replacement in STRING_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_string = str(key)
            if SENSITIVE_KEY.search(key_string):
                result[key_string] = "[REDACTED]"
            else:
                result[key_string] = redact(item)

        name = str(value.get("name", ""))
        if SENSITIVE_KEY.search(name) and "value" in value:
            result["value"] = "[REDACTED]"
        return result
    if isinstance(value, (list, tuple, set)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def json_safe(value: Any) -> Any:
    return json.loads(json.dumps(redact(value), default=str))
