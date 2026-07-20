"""Ordered, deterministic rules for identifying common local secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass
from re import Pattern

from debugmate.privacy.models import SecretKind


@dataclass(frozen=True, slots=True)
class RedactionRule:
    """One immutable rule; list order is its conflict-resolution priority."""

    rule_id: str
    kind: SecretKind
    pattern: Pattern[str]
    confidence: float


def _compile(pattern: str, flags: int = 0) -> Pattern[str]:
    return re.compile(pattern, flags)


REDACTION_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        "PRIVATE_KEY",
        SecretKind.PRIVATE_KEY,
        _compile(
            r"-----BEGIN(?: [A-Z0-9]+)* PRIVATE KEY-----[\s\S]*?"
            r"-----END(?: [A-Z0-9]+)* PRIVATE KEY-----"
        ),
        1.0,
    ),
    RedactionRule(
        "PASSWORD_ASSIGNMENT",
        SecretKind.PASSWORD,
        _compile(
            r"\b(?:password|passwd|pwd|secret)\s*[:=]\s*"
            r"(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s,;]+)",
            re.IGNORECASE,
        ),
        1.0,
    ),
    RedactionRule(
        "BEARER_OR_API_TOKEN",
        SecretKind.TOKEN,
        _compile(
            r"\b(?:"
            r"(?:authorization\s*:\s*)?bearer\s+"
            r"(?:[A-Za-z0-9._~+/=-]{8,})"
            r"|(?:api[_-]?key|access[_-]?token|token)\s*[:=]\s*"
            r"(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[A-Za-z0-9._~+/=-]{8,})"
            r")",
            re.IGNORECASE,
        ),
        1.0,
    ),
    RedactionRule(
        "EMAIL",
        SecretKind.EMAIL,
        _compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        0.99,
    ),
    RedactionRule(
        "WINDOWS_USER_PATH",
        SecretKind.WINDOWS_PATH,
        _compile(
            r"[A-Z]:(?:\\+)(?:Users|Documents and Settings)(?:\\+)[^\s\"'<>|]+",
            re.IGNORECASE,
        ),
        0.99,
    ),
    RedactionRule(
        "UNIX_HOME_PATH",
        SecretKind.UNIX_PATH,
        _compile(r"/(?:home|Users)/[^\s\"'<>|]+"),
        0.99,
    ),
    RedactionRule(
        "PRIVATE_HOST_ASSIGNMENT",
        SecretKind.PRIVATE_HOST,
        _compile(
            r"\b(?:host|hostname)\s*[:=]\s*(?:"
            r"10(?:\.\d{1,3}){3}|"
            r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}|"
            r"192\.168(?:\.\d{1,3}){2}|"
            r"127(?:\.\d{1,3}){3}|"
            r"localhost|[A-Z0-9][A-Z0-9.-]*\.(?:local|internal)"
            r")\b",
            re.IGNORECASE,
        ),
        0.98,
    ),
    RedactionRule(
        "USERNAME_ASSIGNMENT",
        SecretKind.USERNAME,
        _compile(
            r"\b(?:user(?:name)?|login|student[_-]?id)\s*[:=]\s*"
            r"(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s,;]+)",
            re.IGNORECASE,
        ),
        0.95,
    ),
    RedactionRule(
        "HIGH_ENTROPY_TOKEN",
        SecretKind.HIGH_ENTROPY,
        _compile(
            r"(?<![A-Z0-9_-])(?=[A-Z0-9_-]{32,})(?=[A-Z0-9_-]*[A-Z])"
            r"(?=[A-Z0-9_-]*\d)[A-Z0-9_-]{32,}(?![A-Z0-9_-])",
            re.IGNORECASE,
        ),
        0.75,
    ),
)


FIELD_KIND_RULES: dict[str, tuple[SecretKind, str, float, int]] = {
    "password": (SecretKind.PASSWORD, "PASSWORD_FIELD", 1.0, 1),
    "passwd": (SecretKind.PASSWORD, "PASSWORD_FIELD", 1.0, 1),
    "pwd": (SecretKind.PASSWORD, "PASSWORD_FIELD", 1.0, 1),
    "secret": (SecretKind.PASSWORD, "PASSWORD_FIELD", 1.0, 1),
    "token": (SecretKind.TOKEN, "TOKEN_FIELD", 1.0, 2),
    "api_key": (SecretKind.TOKEN, "TOKEN_FIELD", 1.0, 2),
    "access_token": (SecretKind.TOKEN, "TOKEN_FIELD", 1.0, 2),
    "authorization": (SecretKind.TOKEN, "TOKEN_FIELD", 1.0, 2),
    "username": (SecretKind.USERNAME, "USERNAME_FIELD", 0.99, 7),
    "user": (SecretKind.USERNAME, "USERNAME_FIELD", 0.99, 7),
    "login": (SecretKind.USERNAME, "USERNAME_FIELD", 0.99, 7),
    "student_id": (SecretKind.USERNAME, "USERNAME_FIELD", 0.99, 7),
    "host": (SecretKind.PRIVATE_HOST, "PRIVATE_HOST_FIELD", 0.98, 6),
    "hostname": (SecretKind.PRIVATE_HOST, "PRIVATE_HOST_FIELD", 0.98, 6),
}


def field_kind_rule(field_name: str) -> tuple[SecretKind, str, float, int] | None:
    """Resolve exact or conventionally prefixed secret environment keys."""

    normalized = field_name.lower().replace("-", "_")
    exact = FIELD_KIND_RULES.get(normalized)
    if exact is not None:
        return exact
    for suffix, rule in (
        ("_password", FIELD_KIND_RULES["password"]),
        ("_passwd", FIELD_KIND_RULES["passwd"]),
        ("_pwd", FIELD_KIND_RULES["pwd"]),
        ("_secret", FIELD_KIND_RULES["secret"]),
        ("_api_key", FIELD_KIND_RULES["api_key"]),
        ("_access_token", FIELD_KIND_RULES["access_token"]),
        ("_token", FIELD_KIND_RULES["token"]),
        ("_authorization", FIELD_KIND_RULES["authorization"]),
        ("_username", FIELD_KIND_RULES["username"]),
        ("_user", FIELD_KIND_RULES["user"]),
        ("_login", FIELD_KIND_RULES["login"]),
        ("_student_id", FIELD_KIND_RULES["student_id"]),
        ("_hostname", FIELD_KIND_RULES["hostname"]),
        ("_host", FIELD_KIND_RULES["host"]),
    ):
        if normalized.endswith(suffix):
            return rule
    return None
