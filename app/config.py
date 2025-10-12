# app/config.py
# Global configuration file: loads environment variables and .env
# Using pydantic-settings to automatically map env vars to Python attributes

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------
    # Server configuration
    # -------------------------
    HOST: str = "0.0.0.0"
    # IP address to bind (0.0.0.0 = all interfaces)

    PORT: int = 8000
    # Port number to listen on

    RELOAD: bool = False
    # Enable auto-reload (useful in development, disable in production)

    # -------------------------
    # Global control options
    # -------------------------
    KEEP_CSV: bool = False
    # True  = keep temp CSV files (for debugging)
    # False = delete temp CSV after job completion (recommended in production)

    MAX_PARALLEL: int = 0
    #  >0   = explicit number of concurrent jobs (e.g. 4)
    #  0    = auto (defaults to CPU count - 1)

    GLABELS_TIMEOUT: int = 600
    # Max timeout per job in seconds (default 600 = 10 minutes)

    RETENTION_HOURS: int = 24
    # Hours to keep job states in memory before cleanup (avoids memory bloat)

    AUTO_CLEANUP_PDF: bool = True
    # Whether to automatically cleanup PDF files when jobs expire

    LOG_LEVEL: str = "INFO"
    # Logging level: DEBUG / INFO / WARNING / ERROR
    # Default INFO, recommended INFO or higher in production

    # Directory for log files. Can be relative or absolute. Default: logs
    LOG_DIR: str = "logs"

    # -------------------------
    # Internal settings
    # -------------------------
    # Load .env file from project root
    model_config = SettingsConfigDict(env_file=".env")


# Singleton instance
settings = Settings()
