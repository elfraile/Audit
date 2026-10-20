from app.core.events import bus
from app.core.modules import ModuleContext

from . import listeners, models, service  # noqa: F401
from .router import router


def setup(ctx: ModuleContext) -> None:
    listeners.subscribe(bus)
    ctx.app.include_router(router)
    ctx.ui_extras.append(lambda db, user: {"unread": service.unread_count(db, user.id)})
