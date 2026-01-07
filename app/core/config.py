"""
Core configuration management using Pydantic Settings.
Handles environment variables, validation, and application settings.
"""

from typing import List, Optional
from pydantic import Field, field_validator, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All settings are validated at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # ============================================================================
    # APPLICATION SETTINGS
    # ============================================================================
    APP_NAME: str = Field(default="StudyZen API")
    APP_VERSION: str = Field(default="1.0.0")
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)
    API_V1_PREFIX: str = Field(default="/api/v1")

    # ============================================================================
    # SERVER SETTINGS
    # ============================================================================
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)
    WORKERS: int = Field(default=1)
    RELOAD: bool = Field(default=True)

    # ============================================================================
    # SECURITY & AUTHENTICATION
    # ============================================================================
    SECRET_KEY: str = Field(
        ...,  # Required field
        min_length=32,
        description="Secret key for JWT encoding (min 32 characters)"
    )
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7)

    # ============================================================================
    # CORS CONFIGURATION
    # ============================================================================
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:4200"
    )
    ALLOWED_METHODS: str = Field(default="GET,POST,PUT,DELETE,PATCH,OPTIONS")
    ALLOWED_HEADERS: str = Field(default="*")
    ALLOW_CREDENTIALS: bool = Field(default=True)

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def parse_allowed_origins(cls, v: str) -> List[str]:
        """Convert comma-separated origins to list."""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @field_validator("ALLOWED_METHODS")
    @classmethod
    def parse_allowed_methods(cls, v: str) -> List[str]:
        """Convert comma-separated methods to list."""
        return [method.strip() for method in v.split(",") if method.strip()]

    # ============================================================================
    # SUPABASE CONFIGURATION
    # ============================================================================
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(..., description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")
    SUPABASE_JWT_SECRET: str = Field(..., description="Supabase JWT secret")

    # ============================================================================
    # DATABASE CONFIGURATION
    # ============================================================================
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")
    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=10)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_RECYCLE: int = Field(default=3600)

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Ensure database URL starts with postgresql://"""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must start with postgresql://")
        return v

    # ============================================================================
    # REDIS CONFIGURATION
    # ============================================================================
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_DB: int = Field(default=0)
    REDIS_MAX_CONNECTIONS: int = Field(default=50)
    REDIS_SOCKET_TIMEOUT: int = Field(default=5)
    REDIS_SOCKET_CONNECT_TIMEOUT: int = Field(default=5)

    # ============================================================================
    # CACHE SETTINGS
    # ============================================================================
    CACHE_TTL: int = Field(default=300, description="Default cache TTL in seconds")
    CACHE_ENABLED: bool = Field(default=True)

    # ============================================================================
    # OPENAI GPT-4
    # ============================================================================
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_TOKENS: int = Field(default=4096)
    OPENAI_TEMPERATURE: float = Field(default=0.3)

    # ============================================================================
    # ANTHROPIC CLAUDE
    # ============================================================================
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic Claude API key")
    ANTHROPIC_MODEL: str = Field(default="claude-3-5-sonnet-20241022")
    ANTHROPIC_MAX_TOKENS: int = Field(default=8192)
    ANTHROPIC_TEMPERATURE: float = Field(default=0.7)

    # ============================================================================
    # GOOGLE GEMINI AI
    # ============================================================================
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-2.0-flash-exp")
    GEMINI_MAX_TOKENS: int = Field(default=8192)
    GEMINI_TEMPERATURE: float = Field(default=0.7)

    # ============================================================================
    # EMAIL SERVICE (RESEND)
    # ============================================================================
    RESEND_API_KEY: str = Field(..., description="Resend API key")
    FROM_EMAIL: str = Field(default="noreply@studyzen.com")
    FROM_NAME: str = Field(default="StudyZen")
    SUPPORT_EMAIL: str = Field(default="support@studyzen.com")

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    RATE_LIMIT_BURST: int = Field(default=10)
    RATE_LIMIT_STRATEGY: str = Field(default="fixed-window")

    # ============================================================================
    # FILE UPLOAD
    # ============================================================================
    MAX_UPLOAD_SIZE_MB: int = Field(default=10)
    ALLOWED_FILE_TYPES: str = Field(default="pdf,png,jpg,jpeg,webp,gif,svg")
    UPLOAD_FOLDER: str = Field(default="uploads")

    @field_validator("ALLOWED_FILE_TYPES")
    @classmethod
    def parse_allowed_file_types(cls, v: str) -> List[str]:
        """Convert comma-separated file types to list."""
        return [ft.strip().lower() for ft in v.split(",") if ft.strip()]

    # ============================================================================
    # SUPABASE STORAGE BUCKETS
    # ============================================================================
    STORAGE_BUCKET_PROFILE_IMAGES: str = Field(default="profile-images")
    STORAGE_BUCKET_STUDY_MATERIALS: str = Field(default="study-materials")
    STORAGE_BUCKET_USER_UPLOADS: str = Field(default="user-uploads")

    # ============================================================================
    # LOGGING
    # ============================================================================
    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(default="json")
    LOG_FILE: str = Field(default="logs/app.log")

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v_upper

    # ============================================================================
    # SENTRY ERROR TRACKING
    # ============================================================================
    SENTRY_DSN: Optional[str] = Field(default=None)
    SENTRY_ENVIRONMENT: str = Field(default="development")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=1.0)
    SENTRY_ENABLED: bool = Field(default=False)

    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    ENABLE_WEBSOCKETS: bool = Field(default=True)
    ENABLE_AI_TUTOR: bool = Field(default=True)
    ENABLE_RATE_LIMITING: bool = Field(default=True)
    ENABLE_CACHING: bool = Field(default=True)
    ENABLE_EMAIL: bool = Field(default=True)
    ENABLE_ANALYTICS: bool = Field(default=True)

    # ============================================================================
    # TESTING
    # ============================================================================
    TEST_DATABASE_URL: Optional[str] = Field(default=None)
    TEST_REDIS_URL: Optional[str] = Field(default=None)

    # ============================================================================
    # COMPUTED PROPERTIES
    # ============================================================================
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.ENVIRONMENT.lower() == "test"

    @property
    def max_upload_size_bytes(self) -> int:
        """Convert MAX_UPLOAD_SIZE_MB to bytes."""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def access_token_expire_seconds(self) -> int:
        """Convert ACCESS_TOKEN_EXPIRE_MINUTES to seconds."""
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        """Convert REFRESH_TOKEN_EXPIRE_DAYS to seconds."""
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
settings = Settings()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def get_settings() -> Settings:
    """
    Dependency function to get settings instance.
    Used in FastAPI dependency injection.
    """
    return settings


def print_settings_summary() -> None:
    """Print a summary of loaded settings (safe for logs)."""
    print("\n" + "=" * 80)
    print(f"📦 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 80)
    print(f"🌍 Environment: {settings.ENVIRONMENT}")
    print(f"🐛 Debug Mode: {settings.DEBUG}")
    print(f"🚀 Server: {settings.HOST}:{settings.PORT}")
    print(f"📊 Database: {'Connected' if settings.DATABASE_URL else 'Not configured'}")
    print(f"💾 Redis: {'Connected' if settings.REDIS_URL else 'Not configured'}")
    print(f"🤖 AI Tutor: {'Enabled' if settings.ENABLE_AI_TUTOR else 'Disabled'}")
    print(f"📧 Email: {'Enabled' if settings.ENABLE_EMAIL else 'Disabled'}")
    print(f"🔒 Rate Limiting: {'Enabled' if settings.ENABLE_RATE_LIMITING else 'Disabled'}")
    print(f"🔄 Caching: {'Enabled' if settings.ENABLE_CACHING else 'Disabled'}")
    print(f"📝 Log Level: {settings.LOG_LEVEL}")
    print("=" * 80 + "\n")