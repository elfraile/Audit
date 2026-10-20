from app.core.modules import ModuleContext

from . import models  # noqa: F401  (a táblák regisztrálása)
from .router import router
from .service import ensure_admin


def setup(ctx: ModuleContext) -> None:
    ctx.app.include_router(router)
    ctx.startup_hooks.append(
        lambda db: ensure_admin(db, ctx.settings.admin_email, ctx.settings.admin_password)
    )
