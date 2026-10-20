"""Kampányoldal: tényadatok, nyitott kérdések, szabálykártyák."""
from datetime import date

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.channels import service as channel_service
from app.modules.checklist import service as checklist_service
from app.modules.references import service as ref_service
from app.modules.factsheet import queries as fact_queries
from app.modules.factsheet import service as fact_service
from app.modules.issues import queries as issue_queries
from app.modules.issues.resolver import check_delivery_readiness
from app.modules.rules import queries as rule_queries
from app.modules.rules.models import APPROVED
from app.modules.tenants import service as tenants

from .deps import back, get_db, render, ui_user

router = APIRouter()


def _campaign(db: Session, user: User, campaign_id: int, edit: bool = False):
    campaign = tenants.get_campaign(db, campaign_id)
    if not campaign or not access.can_access(db, user, campaign.client_id, campaign_id):
        raise HTTPException(404)
    if edit and user.role not in EDIT_ROLES:
        raise HTTPException(403)
    return campaign


def _parse_date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


@router.get("/campaigns/{campaign_id}")
def campaign_page(campaign_id: int, request: Request, user: User = Depends(ui_user),
                  db: Session = Depends(get_db)):
    campaign = _campaign(db, user, campaign_id)
    client = tenants.get_client(db, campaign.client_id)
    ctx = request.app.state.ctx
    assets_raw = asset_service.list_assets(db, campaign_id)
    assets_with_runs = [(a, audit_service.latest_run_for_asset(db, a.id)) for a in assets_raw]
    refs = ref_service.list_references(db, "campaign", campaign_id) + ref_service.list_references(db, "client", client.id)
    channels = channel_service.list_channels(db, campaign_id)
    deliverables = channel_service.list_deliverables(db, campaign_id)
    deliverables_by_channel = {}
    for d in deliverables:
        deliverables_by_channel.setdefault(d.channel_id, []).append(d)
    asset_by_id = {a.id: a for a in assets_raw}
    latest_run_by_asset = {a.id: run for a, run in assets_with_runs}

    channel_by_id = {c.id: c for c in channels}

    return render(
        request, "campaign.html", user, campaign=campaign, client=client,
        facts=fact_queries.confirmed_facts(db, campaign_id),
        questions=fact_queries.open_questions(db, campaign_id),
        proposals=fact_queries.proposals(db, campaign_id),
        drafts=(rule_queries.drafts(db, "campaign", campaign_id)
                + rule_queries.drafts(db, "client", client.id)),
        approved=rule_queries.active_rules(db, client.id, campaign_id),
        categories=ctx.categories.items(),
        open_issues=issue_queries.open_issues(db, campaign_id),
        closed_issues=issue_queries.closed_issues(db, campaign_id),
        checklist=checklist_service.list_items(db, campaign_id),
        assets=assets_with_runs,
        references=refs,
        channels=channels,
        channel_by_id=channel_by_id,
        deliverables=deliverables,
        deliverables_by_channel=deliverables_by_channel,
        asset_by_id=asset_by_id,
        latest_run_by_asset=latest_run_by_asset,
        delivery=check_delivery_readiness(db, campaign_id),
    )


@router.post("/campaigns/{campaign_id}/facts")
def add_fact(campaign_id: int, key: str = Form(...), value: str = Form(""), source: str = Form(""),
             source_date: str = Form(""), user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    if value.strip():
        fact_service.set_fact(db, campaign_id, key, value.strip(), source, _parse_date(source_date), user.id)
    else:
        try:
            fact_service.open_question(db, campaign_id, key, source, user.id)
        except ValueError:
            pass
    return back(f"/campaigns/{campaign_id}")


@router.post("/campaigns/{campaign_id}/facts/{fact_id}/{action}")
def resolve_proposal(campaign_id: int, fact_id: int, action: str, user: User = Depends(ui_user),
                     db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    if action == "accept":
        fact_service.accept_proposal(db, fact_id, user.id)
    elif action == "reject":
        fact_service.reject_proposal(db, fact_id)
    return back(f"/campaigns/{campaign_id}")


@router.post("/campaigns/{campaign_id}/channels")
def create_channel(campaign_id: int, name: str = Form(...), code: str = Form("other"),
                   description: str = Form(""), user: User = Depends(ui_user),
                   db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    try:
        channel_service.create_channel(db, campaign_id, name, code, description)
    except ValueError:
        pass
    return back(f"/campaigns/{campaign_id}#channels")


@router.post("/campaigns/{campaign_id}/channels/{channel_id}/delete")
def delete_channel(campaign_id: int, channel_id: int, user: User = Depends(ui_user),
                   db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    channel_service.delete_channel(db, channel_id)
    return back(f"/campaigns/{campaign_id}#channels")


@router.post("/campaigns/{campaign_id}/channels/{channel_id}/deliverables")
def create_deliverable(campaign_id: int, channel_id: int, name: str = Form(...),
                       specs: str = Form(""), expected_copy: str = Form(""),
                       post_copy: str = Form(""), file_pattern: str = Form(""),
                       user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    try:
        channel_service.create_deliverable(
            db, channel_id, campaign_id, name, specs, expected_copy, post_copy, file_pattern
        )
    except ValueError:
        pass
    return back(f"/campaigns/{campaign_id}#channels")


__all__ = ["router", "APPROVED"]
