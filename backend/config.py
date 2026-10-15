"""Application settings and configuration management."""

from functools import lru_cache
import re
from typing import Annotated, Any
from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_ENV: str = "development"
    APP_NAME: str = "NER-LINK"
    APP_DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL / PostGIS
    POSTGRES_USER: str = "nerlink_user"
    POSTGRES_PASSWORD: str = "nerlink_secure_password"
    POSTGRES_DB: str = "nerlink"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 55432

    # Database URL override (e.g. Render, Railway, Supabase, Neon)
    DATABASE_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "INTERNAL_DATABASE_URL",
            "POSTGRES_URL",
            "DATABASE_URI",
        ),
    )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 56379
    REDIS_DB: int = 0

    # Redis URL override (e.g. Render Redis, Upstash)
    REDIS_URL: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "REDIS_URL",
            "INTERNAL_REDIS_URL",
            "REDIS_URI",
        ),
    )

    # Study Corridor Configuration (Configurable geographic scope)
    CORRIDOR_NAME: str = "Guwahati-Tawang"
    CORRIDOR_MIN_LAT: float = 26.10
    CORRIDOR_MIN_LON: float = 91.50
    CORRIDOR_MAX_LAT: float = 27.70
    CORRIDOR_MAX_LON: float = 92.80

    # OSM Ingestion
    OSM_NETWORK_TYPE: str = "drive"
    OSM_DATA_DIR: str = "data/osm"

    # Evidence Storage & Incident Management (Data Collection)
    MEDIA_DIR: str = "data/evidence"
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/tiff",
        "image/geotiff",
    ]
    INCIDENT_ROAD_MATCH_RADIUS_M: float = 150.0  # Search radius in meters
    REDIS_STREAM_INCIDENTS: str = "events:incidents"
    REDIS_STREAM_ROADS: str = "events:roads"
    REDIS_STREAM_EVIDENCE: str = "events:evidence"
    REDIS_STREAM_VEHICLES: str = "events:vehicles"
    REDIS_STREAM_TRIPS: str = "events:trips"
    REDIS_STREAM_ALERTS: str = "events:alerts"
    REDIS_STREAM_RISK: str = "events:risk"

    # Weather Ingestion (Open-Meteo)
    OPEN_METEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    WEATHER_REQUEST_TIMEOUT_SECONDS: float = 10.0
    WEATHER_REFRESH_INTERVAL_MINUTES: int = 60
    WEATHER_SAMPLE_GRID_STEP_DEG: float = 0.5
    WEATHER_FORECAST_DAYS: int = 3
    WEATHER_MAX_RETRIES: int = 3
    WEATHER_RETRY_BACKOFF_SECONDS: float = 0.5
    WEATHER_STALE_THRESHOLD_MINUTES: int = 120

    # GPS & Telemetry Ingestion
    GPS_SNAP_THRESHOLD_M: float = 100.0
    GPS_MAX_SPEED_KMH: float = 250.0
    GPS_BATCH_MAX_SIZE: int = 200

    # ML Processing Contract
    ML_CLAIM_TIMEOUT_MINUTES: int = 15
    ML_SERVICE_ROLE: str = "ml_service"
    ML_WORKER_ID: str = "worker-routex-01"
    ML_YOLO_WEIGHTS_PATH: str = "ml/models/best.pt"
    ML_XGBOOST_RISK_PATH: str = "ml/models/xgboost/landslide_risk_xgboost.json"
    ML_XGBOOST_DELAY_PATH: str = "ml/models/xgboost/travel_delay_xgboost.json"
    ML_RISK_HORIZON_MINUTES: int = 360
    ML_RISK_STALE_MINUTES: int = 120

    # Satellite Ingestion Adapter
    SATELLITE_PROVIDER: str = "copernicus_sentinel2"
    SATELLITE_MAX_CLOUD_COVER_PERCENT: float = 40.0

    # Authentication & JWT Security
    JWT_SECRET_KEY: str = "nerlink-super-secret-jwt-key-change-in-prod-1234567890"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOW_DEV_AUTH_HEADERS: bool = True

    # Refresh Cookie Settings
    REFRESH_COOKIE_NAME: str = "rx_refresh_token"
    REFRESH_COOKIE_SECURE: bool = False
    REFRESH_COOKIE_HTTPONLY: bool = True
    REFRESH_COOKIE_SAMESITE: str = "lax"
    REFRESH_COOKIE_PATH: str = "/api/v1/auth"

    # Login Rate Limiting (Redis-backed)
    RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
    RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 300
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # CORS Origins
    CORS_ORIGINS: list[str] | str = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://route-x-two.vercel.app",
    ]

    # Admin Provisioning Configuration (supports ADMIN_EMAIL / ADMIN_PASSWORD or ADMIN_BOOTSTRAP_*)
    ADMIN_BOOTSTRAP_EMAIL: str = Field(
        default="admin@routex.ai",
        validation_alias=AliasChoices("ADMIN_BOOTSTRAP_EMAIL", "ADMIN_EMAIL"),
    )
    ADMIN_BOOTSTRAP_NAME: str = Field(
        default="RouteX Administrator",
        validation_alias=AliasChoices("ADMIN_BOOTSTRAP_NAME", "ADMIN_NAME"),
    )
    ADMIN_BOOTSTRAP_PASSWORD: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ADMIN_BOOTSTRAP_PASSWORD", "ADMIN_PASSWORD"),
    )

    @property
    def ADMIN_EMAIL(self) -> str:
        return self.ADMIN_BOOTSTRAP_EMAIL

    @property
    def ADMIN_PASSWORD(self) -> str | None:
        return self.ADMIN_BOOTSTRAP_PASSWORD

    @property
    def ADMIN_NAME(self) -> str:
        return self.ADMIN_BOOTSTRAP_NAME

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    return [i.strip().rstrip("/") for i in json.loads(v_str) if i.strip()]
                except Exception:
                    pass
            return [i.strip().rstrip("/") for i in v_str.split(",") if i.strip()]
        elif isinstance(v, list):
            return [str(i).strip().rstrip("/") for i in v if str(i).strip()]
        return []

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, v: list[str], info) -> list[str]:
        app_env = info.data.get("APP_ENV", "development") if info.data else "development"
        if app_env == "production":
            if not v:
                raise ValueError("Production environment requires explicit CORS_ORIGINS.")
            if "*" in v:
                raise ValueError(
                    "Wildcard '*' CORS_ORIGINS is prohibited in production when credentials are enabled."
                )
        return v

    @field_validator("DATABASE_URL", "REDIS_URL", mode="before")
    @classmethod
    def normalize_empty_urls(cls, v: Any) -> str | None:
        if isinstance(v, str):
            v_str = v.strip()
            return v_str if v_str else None
        return v

    @field_validator("POSTGRES_PORT", mode="before")
    @classmethod
    def assemble_postgres_port(cls, v: Any) -> int:
        if v is None or v == "":
            return 5432
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return 5432
            return int(v_str)
        return int(v)

    @field_validator("REDIS_PORT", mode="before")
    @classmethod
    def assemble_redis_port(cls, v: Any) -> int:
        if v is None or v == "":
            return 6379
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return 6379
            return int(v_str)
        return int(v)

    @field_validator("POSTGRES_HOST", mode="before")
    @classmethod
    def assemble_postgres_host(cls, v: Any) -> str:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return "localhost"
            return v_str.rstrip(":")
        return str(v) if v else "localhost"

    @field_validator("REDIS_HOST", mode="before")
    @classmethod
    def assemble_redis_host(cls, v: Any) -> str:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return "localhost"
            return v_str.rstrip(":")
        return str(v) if v else "localhost"

    @model_validator(mode="after")
    def validate_production_postgres_password(self) -> "Settings":
        if self.APP_ENV == "production":
            active_pwd = self.POSTGRES_PASSWORD
            target_url = self.DATABASE_URL or (self.POSTGRES_HOST if "://" in self.POSTGRES_HOST else None)
            if target_url:
                try:
                    raw = target_url.strip()
                    if "://" in raw:
                        scheme, rest = raw.split("://", 1)
                        if scheme in ("postgres", "postgresql"):
                            scheme = "postgresql"
                        rest = re.sub(r":(?=/|$|\?)", "", rest)
                        raw = f"{scheme}://{rest}"
                    parsed = make_url(raw)
                    if parsed.password:
                        active_pwd = parsed.password
                except Exception:
                    pass

            if not active_pwd or "nerlink_secure_password" in active_pwd or len(active_pwd) < 8:
                raise ValueError(
                    "Production environment requires a strong, explicit POSTGRES_PASSWORD."
                )

            # In production, cross-origin cookies between Vercel and Render require Secure=True and SameSite=none
            if not self.REFRESH_COOKIE_SECURE:
                self.REFRESH_COOKIE_SECURE = True
            if self.REFRESH_COOKIE_SAMESITE.lower() == "lax":
                self.REFRESH_COOKIE_SAMESITE = "none"

        return self

    @field_validator("ALLOW_DEV_AUTH_HEADERS")
    @classmethod
    def validate_dev_auth_headers(cls, v: bool, info) -> bool:
        app_env = info.data.get("APP_ENV", "development") if info.data else "development"
        if app_env == "production" and v is True:
            raise ValueError(
                "ALLOW_DEV_AUTH_HEADERS cannot be True in production environment."
            )
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development") if info.data else "development"
        if app_env == "production" and (
            not v or "change-in-prod" in v or "nerlink_super_secret" in v or len(v) < 32
        ):
            raise ValueError(
                "Production environment requires a strong, explicit JWT_SECRET_KEY of at least 32 characters."
            )
        return v

    @field_validator("CORRIDOR_MIN_LAT", "CORRIDOR_MAX_LAT")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not (-90.0 <= v <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90, got {v}")
        return v

    @field_validator("CORRIDOR_MIN_LON", "CORRIDOR_MAX_LON")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not (-180.0 <= v <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180, got {v}")
        return v

    def _build_database_url(self, async_driver: bool) -> str:
        """Constructs a robust SQLAlchemy database URL for sync or async operations."""
        raw_url = self.DATABASE_URL
        host = self.POSTGRES_HOST
        if not raw_url and host and ("://" in host):
            raw_url = host

        if raw_url:
            raw = raw_url.strip()
            # Clean empty port if present (e.g., host:/ or host:?)
            if "://" in raw:
                scheme, rest = raw.split("://", 1)
                if scheme in ("postgres", "postgresql"):
                    scheme = "postgresql"
                rest = re.sub(r":(?=/|$|\?)", "", rest)
                raw = f"{scheme}://{rest}"

            parsed = make_url(raw)
            if async_driver:
                async_query = dict(parsed.query)
                if "sslmode" in async_query:
                    sm = async_query.pop("sslmode")
                    if sm in ("require", "verify-ca", "verify-full"):
                        async_query["ssl"] = "require"
                    elif sm in ("disable", "none", "false"):
                        async_query["ssl"] = "disable"
                res_url = parsed.set(drivername="postgresql+asyncpg", query=async_query)
            else:
                res_url = parsed.set(drivername="postgresql+psycopg")
            return res_url.render_as_string(hide_password=False)

        # Individual field resolution
        h = (host or "localhost").strip().rstrip(":")
        p = self.POSTGRES_PORT
        if ":" in h and not h.startswith("["):
            parts = h.rsplit(":", 1)
            if parts[1].isdigit():
                h = parts[0]
                p = int(parts[1])

        if p is None:
            p = 55432 if h in ("localhost", "127.0.0.1") and self.APP_ENV != "production" else 5432

        base_url = URL.create(
            drivername="postgresql+asyncpg" if async_driver else "postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=h,
            port=p,
            database=self.POSTGRES_DB,
        )
        return base_url.render_as_string(hide_password=False)

    @property
    def database_url_sync(self) -> str:
        """Synchronous connection URL using psycopg for Alembic and CLI scripts."""
        return self._build_database_url(async_driver=False)

    @property
    def database_url_async(self) -> str:
        """Asynchronous connection URL using asyncpg for FastAPI application."""
        return self._build_database_url(async_driver=True)

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        raw_url = self.REDIS_URL
        host = self.REDIS_HOST
        if not raw_url and host and ("://" in host):
            raw_url = host

        if raw_url:
            raw = raw_url.strip()
            if "://" in raw:
                scheme, rest = raw.split("://", 1)
                rest = re.sub(r":(?=/|$|\?)", "", rest)
                raw = f"{scheme}://{rest}"
            return raw

        h = (host or "localhost").strip().rstrip(":")
        p = self.REDIS_PORT
        if ":" in h and not h.startswith("["):
            parts = h.rsplit(":", 1)
            if parts[1].isdigit():
                h = parts[0]
                p = int(parts[1])

        if p is None:
            p = 56379 if h in ("localhost", "127.0.0.1") and self.APP_ENV != "production" else 6379

        return f"redis://{h}:{p}/{self.REDIS_DB}"

    @property
    def corridor_bbox(self) -> tuple[float, float, float, float]:
        """Returns (south, west, north, east) bounding box tuple."""
        if self.CORRIDOR_MIN_LAT >= self.CORRIDOR_MAX_LAT:
            raise ValueError("CORRIDOR_MIN_LAT must be strictly less than CORRIDOR_MAX_LAT")
        if self.CORRIDOR_MIN_LON >= self.CORRIDOR_MAX_LON:
            raise ValueError("CORRIDOR_MIN_LON must be strictly less than CORRIDOR_MAX_LON")
        return (
            self.CORRIDOR_MIN_LAT,
            self.CORRIDOR_MIN_LON,
            self.CORRIDOR_MAX_LAT,
            self.CORRIDOR_MAX_LON,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
