from app.core.modules import ModuleContext
from . import models  # noqa: F401
from .router import router


def setup(ctx: ModuleContext) -> None:
    ctx.app.include_router(router)
