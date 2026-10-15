"""Tests for settings and environment configuration validation."""

import pytest
from pydantic import ValidationError
from backend.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.APP_NAME == "NER-LINK"
    assert settings.POSTGRES_PORT == 55432
    assert settings.REDIS_PORT == 56379
    assert "postgresql+psycopg://" in settings.database_url_sync
    assert "postgresql+asyncpg://" in settings.database_url_async
    assert "redis://" in settings.redis_url


def test_valid_corridor_bbox():
    settings = Settings(
        CORRIDOR_MIN_LAT=26.0,
        CORRIDOR_MIN_LON=91.0,
        CORRIDOR_MAX_LAT=27.5,
        CORRIDOR_MAX_LON=92.5,
    )
    bbox = settings.corridor_bbox
    assert bbox == (26.0, 91.0, 27.5, 92.5)


def test_invalid_latitude():
    with pytest.raises(ValidationError):
        Settings(CORRIDOR_MIN_LAT=95.0)

    with pytest.raises(ValidationError):
        Settings(CORRIDOR_MAX_LAT=-95.0)


def test_invalid_longitude():
    with pytest.raises(ValidationError):
        Settings(CORRIDOR_MIN_LON=-190.0)

    with pytest.raises(ValidationError):
        Settings(CORRIDOR_MAX_LON=190.0)


def test_inverted_bbox_raises_error():
    settings = Settings(
        CORRIDOR_MIN_LAT=28.0,
        CORRIDOR_MAX_LAT=26.0,
    )
    with pytest.raises(ValueError, match="strictly less than"):
        _ = settings.corridor_bbox


def test_cors_origins_parsing():
    # Comma-separated string
    s1 = Settings(CORS_ORIGINS="http://localhost:3000, https://routex.ai")
    assert s1.CORS_ORIGINS == ["http://localhost:3000", "https://routex.ai"]

    # JSON array string
    s2 = Settings(CORS_ORIGINS='["http://localhost:3000", "https://app.routex.ai"]')
    assert s2.CORS_ORIGINS == ["http://localhost:3000", "https://app.routex.ai"]

    # Python list
    s3 = Settings(CORS_ORIGINS=["http://localhost:3000", "https://app.routex.ai"])
    assert s3.CORS_ORIGINS == ["http://localhost:3000", "https://app.routex.ai"]


def test_production_cors_wildcard_rejected():
    with pytest.raises(ValidationError, match=r"Wildcard '\*' CORS_ORIGINS is prohibited"):
        Settings(
            APP_ENV="production",
            CORS_ORIGINS="*",
            JWT_SECRET_KEY="a" * 32,
            ALLOW_DEV_AUTH_HEADERS=False,
            POSTGRES_PASSWORD="a_very_strong_production_password_2026",
        )


def test_production_weak_postgres_password_rejected():
    with pytest.raises(ValidationError, match="strong, explicit POSTGRES_PASSWORD"):
        Settings(
            APP_ENV="production",
            POSTGRES_PASSWORD="nerlink_secure_password",
            JWT_SECRET_KEY="a" * 32,
            ALLOW_DEV_AUTH_HEADERS=False,
            CORS_ORIGINS="https://routex.ai",
        )


def test_production_dev_auth_headers_rejected():
    with pytest.raises(ValidationError, match="ALLOW_DEV_AUTH_HEADERS cannot be True"):
        Settings(
            APP_ENV="production",
            ALLOW_DEV_AUTH_HEADERS=True,
            JWT_SECRET_KEY="a" * 32,
            POSTGRES_PASSWORD="a_very_strong_production_password_2026",
            CORS_ORIGINS="https://routex.ai",
        )


def test_production_weak_jwt_secret_rejected():
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(
            APP_ENV="production",
            JWT_SECRET_KEY="too_short",
            ALLOW_DEV_AUTH_HEADERS=False,
            POSTGRES_PASSWORD="a_very_strong_production_password_2026",
            CORS_ORIGINS="https://routex.ai",
        )


def test_production_valid_configuration():
    valid = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="super_strong_production_random_secret_32_chars!",
        POSTGRES_PASSWORD="strong_random_db_password_never_default",
        ALLOW_DEV_AUTH_HEADERS=False,
        CORS_ORIGINS="https://routex.ai, https://app.routex.ai",
    )
    assert valid.APP_ENV == "production"
    assert valid.CORS_ORIGINS == ["https://routex.ai", "https://app.routex.ai"]
    assert valid.ALLOW_DEV_AUTH_HEADERS is False


def test_render_internal_database_url_without_port():
    from sqlalchemy.engine import make_url

    s = Settings(
        DATABASE_URL="postgres://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a/nerlink"
    )
    assert s.database_url_async.startswith("postgresql+asyncpg://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a/nerlink")
    assert s.database_url_sync.startswith("postgresql+psycopg://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a/nerlink")

    async_parsed = make_url(s.database_url_async)
    assert async_parsed.drivername == "postgresql+asyncpg"
    assert async_parsed.host == "dpg-cxxxxxxxx-a"
    assert async_parsed.port is None
    assert async_parsed.database == "nerlink"

    sync_parsed = make_url(s.database_url_sync)
    assert sync_parsed.drivername == "postgresql+psycopg"
    assert sync_parsed.port is None


def test_render_external_database_url_with_sslmode():
    from sqlalchemy.engine import make_url

    s = Settings(
        DATABASE_URL="postgres://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a.oregon-postgres.render.com:5432/nerlink?sslmode=require"
    )
    assert "ssl=require" in s.database_url_async
    assert "sslmode=require" in s.database_url_sync

    async_parsed = make_url(s.database_url_async)
    assert async_parsed.port == 5432
    assert async_parsed.query.get("ssl") == "require"

    sync_parsed = make_url(s.database_url_sync)
    assert sync_parsed.port == 5432
    assert sync_parsed.query.get("sslmode") == "require"


def test_malformed_empty_port_colon_cleaned():
    from sqlalchemy.engine import make_url

    # Trailing colon before slash
    s = Settings(
        DATABASE_URL="postgres://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a:/nerlink"
    )
    async_parsed = make_url(s.database_url_async)
    assert async_parsed.host == "dpg-cxxxxxxxx-a"
    assert async_parsed.port is None


def test_postgres_host_as_full_connection_string():
    from sqlalchemy.engine import make_url

    s = Settings(
        POSTGRES_HOST="postgres://nerlink_user:super_secret_db_password@dpg-cxxxxxxxx-a/nerlink"
    )
    async_parsed = make_url(s.database_url_async)
    assert async_parsed.host == "dpg-cxxxxxxxx-a"
    assert async_parsed.database == "nerlink"
    assert async_parsed.port is None


def test_postgres_host_with_port_or_trailing_colon():
    from sqlalchemy.engine import make_url

    # Embedded port in host
    s1 = Settings(POSTGRES_HOST="dpg-cxxxxxxxx-a.render.com:5432")
    async_parsed1 = make_url(s1.database_url_async)
    assert async_parsed1.host == "dpg-cxxxxxxxx-a.render.com"
    assert async_parsed1.port == 5432
    assert ":5432:5432" not in s1.database_url_async

    # Host with trailing colon
    s2 = Settings(POSTGRES_HOST="dpg-cxxxxxxxx-a:")
    async_parsed2 = make_url(s2.database_url_async)
    assert async_parsed2.host == "dpg-cxxxxxxxx-a"
    assert not async_parsed2.host.endswith(":")


def test_empty_port_strings_sanitized():
    s = Settings(POSTGRES_PORT="", REDIS_PORT="")
    assert s.POSTGRES_PORT == 5432
    assert s.REDIS_PORT == 6379


def test_redis_url_configurations():
    s1 = Settings(REDIS_URL="redis://red-cxxxxxxxx:6379")
    assert s1.redis_url == "redis://red-cxxxxxxxx:6379"

    s2 = Settings(REDIS_URL="rediss://default:redis_secure_pass@red-cxxxxxxxx:6379/1")
    assert s2.redis_url == "rediss://default:redis_secure_pass@red-cxxxxxxxx:6379/1"

    s3 = Settings(REDIS_HOST="red-cxxxxxxxx:6379")
    assert s3.redis_url == "redis://red-cxxxxxxxx:6379/0"


def test_production_database_url_password_validation():
    # Strong password in DATABASE_URL passes in production without setting POSTGRES_PASSWORD
    valid = Settings(
        APP_ENV="production",
        DATABASE_URL="postgres://nerlink_user:super_strong_production_pw_2026@dpg-cxxxxxxxx-a/nerlink",
        JWT_SECRET_KEY="a" * 32,
        ALLOW_DEV_AUTH_HEADERS=False,
        CORS_ORIGINS="https://routex.ai",
    )
    assert valid.APP_ENV == "production"

    # Weak default password in DATABASE_URL is rejected in production
    with pytest.raises(ValidationError, match="strong, explicit POSTGRES_PASSWORD"):
        Settings(
            APP_ENV="production",
            DATABASE_URL="postgres://nerlink_user:nerlink_secure_password@dpg-cxxxxxxxx-a/nerlink",
            JWT_SECRET_KEY="a" * 32,
            ALLOW_DEV_AUTH_HEADERS=False,
            CORS_ORIGINS="https://routex.ai",
        )


def test_mask_sensitive_data():
    from backend.database import mask_sensitive_data

    # Standard database URL with credentials
    raw_db_err = "Failed to connect to postgresql+asyncpg://admin_user:super_secret_db_pass_123@dpg-cxxxx:5432/db"
    masked = mask_sensitive_data(raw_db_err)
    assert "super_secret_db_pass_123" not in masked
    assert "postgresql+asyncpg://admin_user:***@dpg-cxxxx:5432/db" in masked

    # Redis URL with password
    raw_redis_err = "Redis error: redis://:super_redis_pass_456@red-cxxxx:6379/0"
    masked_redis = mask_sensitive_data(raw_redis_err)
    assert "super_redis_pass_456" not in masked_redis
    assert "redis://:***@red-cxxxx:6379/0" in masked_redis

    # Key-value password
    raw_kv = "password='cleartext_secret' failed"
    masked_kv = mask_sensitive_data(raw_kv)
    assert "cleartext_secret" not in masked_kv


def test_cors_origins_vercel_normalization():
    # Default contains vercel domain
    s_default = Settings()
    assert "https://route-x-two.vercel.app" in s_default.CORS_ORIGINS

    # String with trailing slash normalizes without trailing slash
    s_slash = Settings(CORS_ORIGINS="https://route-x-two.vercel.app/, http://localhost:3000/")
    assert s_slash.CORS_ORIGINS == ["https://route-x-two.vercel.app", "http://localhost:3000"]


def test_production_cross_origin_cookie_settings():
    # Development mode keeps Lax and False for local HTTP dev
    s_dev = Settings(APP_ENV="development")
    assert s_dev.REFRESH_COOKIE_SECURE is False
    assert s_dev.REFRESH_COOKIE_SAMESITE == "lax"

    # Production mode automatically upgrades to Secure=True and SameSite=none for cross-origin Vercel -> Render auth
    s_prod = Settings(
        APP_ENV="production",
        JWT_SECRET_KEY="super_secret_production_key_32_chars!",
        POSTGRES_PASSWORD="strong_password_12345",
        ALLOW_DEV_AUTH_HEADERS=False,
        CORS_ORIGINS="https://route-x-two.vercel.app",
    )
    assert s_prod.REFRESH_COOKIE_SECURE is True
    assert s_prod.REFRESH_COOKIE_SAMESITE == "none"



