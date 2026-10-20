"""Alkalmazás-beállítások. Minden érték környezeti változóból (AUDIT_ előtag) vagy .env-ből felülírható."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUDIT_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///data/audit.db"
    secret_key: str = "change-me"
    # Betöltendő modulok sorrendben. Új képesség = új modul felvétele ide, a mag érintetlen marad.
    modules: list[str] = [
        "accounts", "tenants", "factsheet", "rules", "issues",
        "notifications", "checklist", "references", "assets", "audits", "ui"
    ]
    extractor: str = "null"  # a szabály-kinyerő regisztrált kulcsa
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    admin_email: str = "admin@example.local"
    admin_password: str = "admin"

