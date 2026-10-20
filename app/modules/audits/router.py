from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.modules.accounts.deps import current_user, require_editor
from app.modules.accounts.models import User
from app.modules.assets.models import Asset
from app.modules.issues import service as issue_service
from app.modules.tenants.guards import ensure_campaign_access

from . import service
from .models import AuditResult

router = APIRouter(prefix="/api", tags=["audits"])


def _res_out(r: AuditResult) -> dict:
    return {
        "id": r.id, "rule_id": r.rule_id, "check_type": r.check_type,
        "title": r.title, "category": r.category, "severity": r.severity,
        "verdict": r.verdict, "message": r.message, "evidence": r.evidence
    }


@router.post("/campaigns/{campaign_id}/audits/{asset_id}")
def trigger_audit(
    campaign_id: int, asset_id: int,
    user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    ensure_campaign_access(db, user, campaign_id)
    try:
        run = service.run_audit(db, campaign_id, asset_id, user.id)
        return {
            "id": run.id, "status": run.status,
            "passed": run.passed_count, "failed": run.failed_count,
            "warning": run.warning_count
        }
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/audits/{run_id}")
def get_audit(run_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    run = service.get_audit_run(db, run_id)
    if not run:
        raise HTTPException(404, "Audit nem található")
    ensure_campaign_access(db, user, run.campaign_id)
    results = service.list_results(db, run_id)
    return {
        "id": run.id, "campaign_id": run.campaign_id, "asset_id": run.asset_id,
        "status": run.status, "passed": run.passed_count, "failed": run.failed_count,
        "warning": run.warning_count, "results": [_res_out(r) for r in results]
    }


@router.post("/audits/results/{result_id}/create-issue")
def create_issue_from_result(
    result_id: int, user: User = Depends(require_editor), db: Session = Depends(get_db)
):
    res = db.get(AuditResult, result_id)
    if not res:
        raise HTTPException(404, "Audit eredmény nem található")
    run = service.get_audit_run(db, res.audit_run_id)
    ensure_campaign_access(db, user, run.campaign_id)
    asset = db.get(Asset, run.asset_id)
    asset_name = asset.name if asset else f"Asset #{run.asset_id}"
    desc = f"Audit hiba: {res.title} - {res.message}"
    issue = issue_service.create_issue(
        db, run.campaign_id, description=desc, asset_ref=asset_name,
        source=f"Audit #{run.id}", category=res.category, user_id=user.id
    )
    return {"issue_id": issue.id}
