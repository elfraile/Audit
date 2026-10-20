from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.modules.accounts.models import User
from app.modules.accounts.roles import EDIT_ROLES
from app.modules.assets import service as asset_service
from app.modules.audits import service as audit_service
from app.modules.audits.models import AuditResult
from app.modules.issues import service as issue_service
from app.modules.tenants import service as tenant_service
from app.modules.tenants.guards import ensure_campaign_access

from .deps import back, get_db, render, ui_user

router = APIRouter()


@router.post("/campaigns/{campaign_id}/assets/{asset_id}/audit")
def trigger_audit(
    campaign_id: int, asset_id: int,
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)
    try:
        run = audit_service.run_audit(db, campaign_id, asset_id, user.id)
        return back(f"/audits/{run.id}")
    except ValueError:
        return back(f"/campaigns/{campaign_id}#assets")


@router.get("/audits/{run_id}")
def audit_report(
    run_id: int, request: Request,
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    run = audit_service.get_audit_run(db, run_id)
    if not run:
        raise HTTPException(404, "Audit futtatás nem található")
    ensure_campaign_access(db, user, run.campaign_id)
    asset = asset_service.get_asset(db, run.asset_id)
    campaign = tenant_service.get_campaign(db, run.campaign_id)
    results = audit_service.list_results(db, run_id)
    content = asset_service.get_content(db, run.asset_id)

    return render(
        request, "audit_report.html", user,
        run=run, asset=asset, campaign=campaign, results=results,
        content=content, categories=request.app.state.ctx.categories.items()
    )


@router.post("/audits/{run_id}/results/{result_id}/issue")
def create_issue_from_result(
    run_id: int, result_id: int,
    user: User = Depends(ui_user), db: Session = Depends(get_db)
):
    run = audit_service.get_audit_run(db, run_id)
    if not run:
        raise HTTPException(404)
    ensure_campaign_access(db, user, run.campaign_id)
    if user.role not in EDIT_ROLES:
        raise HTTPException(403)

    res = db.get(AuditResult, result_id)
    asset = asset_service.get_asset(db, run.asset_id)
    if res:
        desc = f"Audit hiba: {res.title} - {res.message}"
        issue_service.create_issue(
            db, run.campaign_id, description=desc,
            asset_ref=asset.name if asset else "",
            source=f"Audit #{run.id}", category=res.category, user_id=user.id
        )
    return back(f"/audits/{run_id}#results")
