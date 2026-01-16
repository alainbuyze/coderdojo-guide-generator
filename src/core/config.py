"""Configuration management using Pydantic Settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment files."""

    model_config = SettingsConfigDict(
        env_file=(".env.app", ".env.keys", ".env.local"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    # Output settings
    OUTPUT_ROOT_DIR: str = Field(default="./output", description="Root directory for all output files")
    OUTPUT_DIR: str = Field(default="./output", description="Output directory for generated guides")
    CACHE_DIR: str = Field(default="./cache", description="Cache directory for downloaded pages")

    # Scraping settings
    RATE_LIMIT_SECONDS: float = Field(default=2.0, description="Delay between requests")
    BROWSER_HEADLESS: bool = Field(default=True, description="Run browser in headless mode")
    BROWSER_TIMEOUT: int = Field(default=30000, description="Browser timeout in milliseconds")

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )

    # Image settings
    IMAGE_DOWNLOAD_TIMEOUT: int = Field(default=30, description="Image download timeout in seconds")
    IMAGE_OUTPUT_DIR: str = Field(default="images", description="Subdirectory for images")

    # Enhancement settings (Upscayl)
    UPSCAYL_PATH: str = Field(
        default="C:\\Program Files\\Upscayl\\resources\\bin\\upscayl-bin.exe",
        description="Path to Upscayl binary",
    )
    UPSCAYL_SCALE: int = Field(default=4, description="Upscale factor (2 or 4)")
    UPSCAYL_MODEL: str = Field(default="realesrgan-x4plus", description="Upscayl model name")
    ENHANCE_IMAGES: bool = Field(default=True, description="Enable image enhancement")

    # Translation settings
    TRANSLATE_ENABLED: bool = Field(default=True, description="Enable Dutch translation")
    TRANSLATION_SOURCE: str = Field(default="en", description="Source language")
    TRANSLATION_TARGET: str = Field(default="nl", description="Target language (Dutch)")

    # MakeCode settings
    MAKECODE_LANGUAGE: str = Field(default="nl", description="Language for MakeCode screenshots")
    MAKECODE_TIMEOUT: int = Field(default=30000, description="MakeCode page load timeout in ms")
    MAKECODE_REPLACE_ENABLED: bool = Field(
        default=True, description="Enable MakeCode screenshot replacement"
    )


# Singleton pattern for settings
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
