from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Process-level secrets and endpoints. Behavior config lives in the database."""

    supabase_url: str
    supabase_service_role_key: str
    odds_api_key: str
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    telegram_bot_token: str
    app_base_url: str = ""
    # OpenCode Go (OpenAI-compatible) for the optional LLM annotation layer
    opencode_api_key: str = ""
    opencode_base_url: str = "https://opencode.ai/zen/go/v1"
    llm_model: str = "opencode-go/deepseek-v4-flash"
    sentry_dsn: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()  # type: ignore[call-arg]
