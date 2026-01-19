"""Configuration management using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, computed_field
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
    OUTPUT_ROOT_DIR: str = Field(default=".", description="Root directory for all output files")
    OUTPUT_DIR: str = Field(default="output", description="Subdirectory within OUTPUT_ROOT_DIR for generated guides")
    CACHE_DIR: str = Field(default="cache", description="Subdirectory within OUTPUT_ROOT_DIR for cached pages")
    LOG_DIR: str = Field(default="logs", description="Subdirectory within OUTPUT_ROOT_DIR for log files")

    # Scraping settings
    RATE_LIMIT_SECONDS: float = Field(default=2.0, description="Delay between requests")
    BROWSER_HEADLESS: bool = Field(default=True, description="Run browser in headless mode")
    BROWSER_TIMEOUT: int = Field(default=60000, description="Browser timeout in milliseconds")
    SCRAPE_MAX_RETRIES: int = Field(default=3, description="Maximum retry attempts for failed scrapes")
    SCRAPE_RETRY_DELAY: float = Field(default=5.0, description="Initial delay between retries in seconds")
    SCRAPE_RETRY_BACKOFF: float = Field(default=2.0, description="Backoff multiplier for retry delays")

    # Logging settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format",
    )

    # Image settings
    IMAGE_DOWNLOAD_TIMEOUT: int = Field(default=30, description="Image download timeout in seconds")
    IMAGE_OUTPUT_DIR: str = Field(default="images", description="Subdirectory for images")
    IMAGE_SCALE: float = Field(default=1.0, description="Scale factor for images (1.0 = original size)")

    # Enhancement settings (Upscayl)
    UPSCAYL_PATH: str = Field(
        default="C:\\Program Files\\Upscayl\\resources\\bin\\upscayl-bin.exe",
        description="Path to Upscayl binary",
    )
    UPSCAYL_SCALE: int = Field(default=4, description="Upscale factor (2 or 4)")
    UPSCAYL_MODEL: str = Field(default="realesrgan-x4plus", description="Upscayl model name")
    ENHANCE_IMAGES: bool = Field(default=True, description="Enable image enhancement")

    # QR Code settings
    QRCODE_SCALE: float = Field(default=1.0, description="Scale factor for QR codes (1.0 = original size)")

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

    # Print/PDF settings
    PDF_PAGE_SIZE: str = Field(default="A4", description="PDF page size")
    PDF_PAGE_ORIENTATION: str = Field(default="portrait", description="PDF page orientation")
    PDF_MARGIN: str = Field(default="15mm 20mm", description="PDF page margins")
    PDF_CONSTRUCTION_PER_PAGE: int = Field(
        default=2, description="Number of construction diagrams per page"
    )

    # Computed properties for full paths
    @computed_field
    @property
    def output_path(self) -> Path:
        """Full path to output directory (OUTPUT_ROOT_DIR / OUTPUT_DIR)."""
        return Path(self.OUTPUT_ROOT_DIR) / self.OUTPUT_DIR

    @computed_field
    @property
    def cache_path(self) -> Path:
        """Full path to cache directory (OUTPUT_ROOT_DIR / CACHE_DIR)."""
        return Path(self.OUTPUT_ROOT_DIR) / self.CACHE_DIR

    @computed_field
    @property
    def log_path(self) -> Path:
        """Full path to log directory (OUTPUT_ROOT_DIR / LOG_DIR)."""
        return Path(self.OUTPUT_ROOT_DIR) / self.LOG_DIR


# Singleton pattern for settings
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
