"""
Shared factory for the Anthropic client.
Set CLAUDE_CODE_USE_BEDROCK=1 to route through AWS Bedrock.
"""
import os
import anthropic


def get_anthropic_client() -> anthropic.Anthropic | anthropic.AnthropicBedrock:
    use_bedrock = os.getenv("CLAUDE_CODE_USE_BEDROCK", "").lower() in ("1", "true", "yes")
    if use_bedrock:
        region = os.getenv("AWS_REGION", "us-east-1")
        return anthropic.AnthropicBedrock(aws_region=region)
    return anthropic.Anthropic()


def get_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
