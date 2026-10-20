from app.core.events import bus
from app.core.modules import ModuleContext

from . import listeners, models  # noqa: F401
from .extraction.null import NullExtractor
from .extraction.openrouter import OpenRouterExtractor
from .router import router
from .taxonomy import register_defaults


def setup(ctx: ModuleContext) -> None:
    register_defaults(ctx.categories)
    ctx.extractors.register("null", lambda settings: NullExtractor())
    ctx.extractors.register(
        "openrouter",
        lambda s: OpenRouterExtractor(s.openrouter_api_key, s.openrouter_model),
    )
    ctx.app.include_router(router)
    if "issues" in ctx.settings.modules:  # csak akkor figyel, ha az issues modul be van töltve
        listeners.subscribe(bus)
