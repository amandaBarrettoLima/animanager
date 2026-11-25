"""Configurações da aplicação (12-factor: tudo sobrescrevível por variável de ambiente)."""
import os
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "database" / "animanager.db"))
    SEED_DEMO = os.environ.get("SEED_DEMO", "1") == "1"      # carrega dados de demonstração
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)          # expiração da sessão (US-02)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    JANELA_CORRECAO_HORAS = 24                                # após isso, correção exige justificativa
    STATIC_DIR = str(BASE_DIR / "static")


class TestConfig(Config):
    TESTING = True
    SEED_DEMO = True
