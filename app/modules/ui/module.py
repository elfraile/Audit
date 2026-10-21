from app.core.modules import ModuleContext

from . import (routes_admin, routes_assets, routes_audits, routes_auth,
               routes_campaign, routes_channels, routes_checklist, routes_client, routes_home,
               routes_issues, routes_notifications, routes_references, routes_rules)
from .deps import LoginRequired, login_required_handler


def setup(ctx: ModuleContext) -> None:
    ctx.app.add_exception_handler(LoginRequired, login_required_handler)
    for module in (routes_auth, routes_home, routes_client, routes_campaign, routes_channels,
                   routes_assets, routes_audits, routes_references, routes_rules,
                   routes_issues, routes_checklist, routes_notifications, routes_admin):
        ctx.app.include_router(module.router)
