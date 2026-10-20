"""Alkalmazás-összeállítás: a mag + a konfigurált modulok."""
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import Settings
from app.core.db import Base, make_session_factory
from app.core.modules import ModuleContext, load_modules


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Audit")
    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    engine, session_factory = make_session_factory(settings.database_url)
    app.state.session_factory = session_factory
    ctx = ModuleContext(app=app, settings=settings)
    app.state.ctx = ctx

    load_modules(ctx)  # a modellek itt regisztrálódnak a Base-be
    Base.metadata.create_all(engine)
    with session_factory() as db:
        for hook in ctx.startup_hooks:
            hook(db)
    return app
