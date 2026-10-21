"""Egyedi csatorna-munkatér (Single-channel Workspace) és slot-alapú műveletek."""
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from app.modules.accounts import access
from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.channels import service as channel_service
from app.modules.factsheet import queries as fact_queries
from app.modules.issues import queries as issue_queries
from app.modules.issues.resolver import check_delivery_readiness
from app.modules.rules import queries as rule_queries
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


@router.get("/campaigns/{campaign_id}/channels/{channel_id}")
def channel_workspace(campaign_id: int, channel_id: int, request: Request,
                      user: User = Depends(ui_user), db: Session = Depends(get_db)):
    campaign = _campaign(db, user, campaign_id)
    client = tenants.get_client(db, campaign.client_id)
    channel = channel_service.get_channel(db, channel_id)
    if not channel or channel.campaign_id != campaign_id:
        raise HTTPException(404, "Csatorna nem található")

    all_channels = channel_service.list_channels(db, campaign_id)
    channel_summaries = {
        c.id: channel_service.get_channel_summary(db, c.id, campaign_id)
        for c in all_channels
    }
    current_summary = channel_summaries.get(channel_id, {})

    deliverables = channel_service.list_deliverables(db, campaign_id, channel_id=channel_id)
    assets_raw = asset_service.list_assets(db, campaign_id)
    asset_by_id = {a.id: a for a in assets_raw}
    latest_run_by_asset = {
        d.asset_id: audit_service.latest_run_for_asset(db, d.asset_id)
        for d in deliverables if d.asset_id
    }

    # Szabályok bontása: erre a csatornára specifikus vs. örökölt (brandbook + kampány)
    all_rules = rule_queries.active_rules(db, client.id, campaign_id, channel_id=channel_id)
    channel_rules = [
        r for r in all_rules
        if r.scope_type == "channel" or (r.applies_to or {}).get("channel_id") == channel_id
    ]
    inherited_rules = [r for r in all_rules if r not in channel_rules]

    # Nyitott hibák ehhez a csatornához
    channel_asset_ids = {d.asset_id for d in deliverables if d.asset_id}
    open_campaign_issues = issue_queries.open_issues(db, campaign_id)
    channel_issues = [i for i in open_campaign_issues if i.asset_id in channel_asset_ids]

    # Tényadatok sáv (Factsheet Ribbon)
    facts = fact_queries.confirmed_facts(db, campaign_id)
    facts_dict = {f.key: f.value for f in facts}

    ctx = request.app.state.ctx

    return render(
        request, "channel_detail.html", user,
        campaign=campaign,
        client=client,
        channel=channel,
        channels=all_channels,
        channel_summaries=channel_summaries,
        current_summary=current_summary,
        deliverables=deliverables,
        asset_by_id=asset_by_id,
        latest_run_by_asset=latest_run_by_asset,
        channel_rules=channel_rules,
        inherited_rules=inherited_rules,
        channel_issues=channel_issues,
        facts=facts,
        facts_dict=facts_dict,
        categories=ctx.categories.items(),
        delivery=check_delivery_readiness(db, campaign_id),
        can_edit=(user.role in EDIT_ROLES),
    )


@router.post("/campaigns/{campaign_id}/channels/{channel_id}/deliverables")
def create_channel_deliverable(campaign_id: int, channel_id: int, name: str = Form(...),
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
    return back(f"/campaigns/{campaign_id}/channels/{channel_id}")


@router.post("/campaigns/{campaign_id}/channels/{channel_id}/deliverables/{deliverable_id}/delete")
def delete_channel_deliverable(campaign_id: int, channel_id: int, deliverable_id: int,
                               user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    channel_service.delete_deliverable(db, deliverable_id)
    return back(f"/campaigns/{campaign_id}/channels/{channel_id}")


@router.post("/campaigns/{campaign_id}/deliverables/{deliverable_id}/upload")
async def upload_deliverable_slot(campaign_id: int, deliverable_id: int,
                                  file: UploadFile = File(...),
                                  user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    deliv = channel_service.get_deliverable(db, deliverable_id)
    if not deliv or deliv.campaign_id != campaign_id:
        raise HTTPException(404, "Várt anyag nem található")

    content = await file.read()
    filename = file.filename or "slot_creative"
    channel_service.upload_to_deliverable(
        db, campaign_id, deliverable_id, filename, content, user_id=user.id
    )
    return back(f"/campaigns/{campaign_id}/channels/{deliv.channel_id}")


@router.post("/campaigns/{campaign_id}/deliverables/{deliverable_id}/unlink")
def unlink_deliverable_slot(campaign_id: int, deliverable_id: int,
                            user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    deliv = channel_service.get_deliverable(db, deliverable_id)
    if not deliv or deliv.campaign_id != campaign_id:
        raise HTTPException(404, "Várt anyag nem található")

    channel_service.unlink_deliverable_asset(db, campaign_id, deliverable_id)
    return back(f"/campaigns/{campaign_id}/channels/{deliv.channel_id}")


@router.post("/campaigns/{campaign_id}/deliverables/{deliverable_id}/audit")
def audit_deliverable_slot(campaign_id: int, deliverable_id: int,
                           user: User = Depends(ui_user), db: Session = Depends(get_db)):
    _campaign(db, user, campaign_id, edit=True)
    deliv = channel_service.get_deliverable(db, deliverable_id)
    if not deliv or deliv.campaign_id != campaign_id:
        raise HTTPException(404, "Várt anyag nem található")

    if deliv.asset_id:
        audit_service.run_audit(db, campaign_id, deliv.asset_id, user_id=user.id)
    return back(f"/campaigns/{campaign_id}/channels/{deliv.channel_id}")


__all__ = ["router"]
