"""
Startup configuration validation.

Logs warnings for misconfigured secrets and missing credentials.
Never logs secret values — only structural checks (presence, length, known-bad strings).
"""
import logging
import os

logger = logging.getLogger(__name__)

# Secrets that are known placeholders/defaults and must be replaced in production
_KNOWN_BAD_JWT_SECRETS = frozenset(
    {
        "change-me-in-production",
        "secret",
        "jwt-secret",
        "your-secret-key",
        "supersecret",
        "",
    }
)


def validate_startup_config() -> None:
    """
    Check critical env vars at startup and emit structured warnings.
    Does NOT raise — development startup is never blocked.
    """
    issues: list[str] = []

    # ── JWT secret ─────────────────────────────────────────────────────────────
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    if not jwt_secret:
        issues.append(
            "JWT_SECRET_KEY is not set — token signing will use an empty secret"
        )
    elif jwt_secret.lower() in _KNOWN_BAD_JWT_SECRETS:
        issues.append(
            "JWT_SECRET_KEY is a known weak placeholder. "
            "Generate a strong secret: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    elif len(jwt_secret) < 32:
        issues.append(
            f"JWT_SECRET_KEY is only {len(jwt_secret)} chars — "
            "use at least 32 random characters"
        )

    # ── AI credentials ─────────────────────────────────────────────────────────
    use_bedrock = os.getenv("CLAUDE_CODE_USE_BEDROCK", "false").lower() in (
        "1", "true", "yes",
    )
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    placeholder_keys = {"sk-ant-...", "your-key-here", ""}

    if not use_bedrock:
        if not api_key:
            issues.append(
                "ANTHROPIC_API_KEY is not set and CLAUDE_CODE_USE_BEDROCK is false "
                "— AI features will fail at runtime"
            )
        elif api_key in placeholder_keys:
            issues.append(
                "ANTHROPIC_API_KEY appears to be a placeholder "
                "— AI features will fail at runtime"
            )

        # Warn if the model ID looks like a Bedrock cross-region ARN
        model = os.getenv("ANTHROPIC_MODEL", "")
        if model.startswith("us.anthropic.") or model.startswith("eu.anthropic."):
            issues.append(
                f"ANTHROPIC_MODEL looks like a Bedrock cross-region ARN ('{model[:30]}…') "
                "but CLAUDE_CODE_USE_BEDROCK is not enabled — model calls may fail"
            )

    # ── CORS / debug flag ──────────────────────────────────────────────────────
    debug = os.getenv("DEBUG", "false").lower() in ("1", "true", "yes")
    if debug:
        issues.append(
            "DEBUG=true: CORS allows the 'null' origin (file:// requests). "
            "Do not run with DEBUG=true in production."
        )

    for msg in issues:
        logger.warning("CONFIG WARNING: %s", msg)

    if not issues:
        logger.info("Startup config OK")
