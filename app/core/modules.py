"""Modulbetöltő. Minden modul `module.py`-ja egy `setup(ctx)` függvényt ad."""
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import FastAPI
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.registry import Registry


@dataclass
class ModuleContext:
    app: FastAPI
    settings: Settings
    # Név -> gyártó függvény (settings -> példány)
    extractors: Registry = field(default_factory=lambda: Registry("extractors"))
    # Szabálykategória kulcs -> megjelenített név
    categories: Registry = field(default_factory=lambda: Registry("categories"))
    startup_hooks: list[Callable[[Session], None]] = field(default_factory=list)
    # (db, user) -> dict: minden oldalsablonhoz hozzáadott extra adatok (pl. értesítés-számláló)
    ui_extras: list[Callable[[Session, object], dict]] = field(default_factory=list)


def load_modules(ctx: ModuleContext) -> None:
    for name in ctx.settings.modules:
        importlib.import_module(f"app.modules.{name}.module").setup(ctx)
