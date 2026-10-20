"""Automatikus lezáró (Auto-resolver) és leadási ellenőrző (Delivery Sign-Off).

Figyeli a lefutott auditokat ('audit.completed' esemény). Ha egy korábban hibás
kreatív anyag újra-auditálása sikeresen zárul vagy a vonatkozó szabály zöldre vált,
a rendszer a nyitott hibalista tételeket automatikusan 'done' státuszba lépteti
és naplózza a feloldást.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import bus
from app.modules.assets.models import Asset
from app.modules.audits.models import FAILED, PASSED, AuditResult, AuditRun
from app.modules.checklist import service as checklist_service

from . import service
from .models import DONE, OPEN, Issue


def resolve_issues_for_audit(db: Session, run: AuditRun, asset: Asset,
                             actor_id: int | None = None) -> list[Issue]:
    open_issues = list(db.scalars(
        select(Issue).where(Issue.campaign_id == run.campaign_id, Issue.status == OPEN)
    ))
    if not open_issues:
        return []

    results = list(db.scalars(
        select(AuditResult).where(AuditResult.audit_run_id == run.id)
    ))

    passed_rules = {r.rule_id for r in results if r.rule_id and r.verdict == PASSED}
    failed_rules = {r.rule_id for r in results if r.rule_id and r.verdict == FAILED}
    failed_titles = {r.title.lower() for r in results if r.verdict == FAILED}

    resolved: list[Issue] = []

    for issue in open_issues:
        matches_asset = False
        if issue.asset_id and issue.asset_id == asset.id:
            matches_asset = True
        elif issue.asset_ref:
            ref_low = issue.asset_ref.lower().strip()
            name_low = asset.name.lower().strip()
            if ref_low in name_low or name_low in ref_low:
                matches_asset = True

        if not matches_asset:
            continue

        should_resolve = False
        reason = ""

        # 1. Konkrét szabályhoz kötött tétel feloldása
        if issue.rule_id and issue.rule_id in passed_rules and issue.rule_id not in failed_rules:
            should_resolve = True
            reason = f"A vonatkozó szabály sikeresen lefutott a(z) '{asset.name}' anyagon (Audit #{run.id})."

        # 2. Teljes kreatív anyag zöldre váltása (0 hiba)
        elif run.status == PASSED:
            should_resolve = True
            reason = f"A(z) '{asset.name}' kreatív anyag hibátlan auditot zárt (Audit #{run.id})."

        # 3. Tartalmi illeszkedés a leírás és a sikeres szabályok között
        elif not any(ft in issue.description.lower() for ft in failed_titles):
            for r in results:
                if r.verdict == PASSED and r.title and len(r.title) > 4:
                    if r.title.lower() in issue.description.lower():
                        should_resolve = True
                        reason = f"A kapcsolódó ellenőrzés ('{r.title[:40]}...') sikeresen lefutott (Audit #{run.id})."
                        break

        if should_resolve:
            service.add_comment(db, issue.id, f"Automatikus feloldás: {reason}", actor_id)
            service.set_status(db, issue.id, DONE, user_id=actor_id)
            resolved.append(issue)

    return resolved


def check_delivery_readiness(db: Session, campaign_id: int) -> dict:
    """Megvizsgálja, hogy a kampány leadásra kész-e."""
    assets = list(db.scalars(select(Asset).where(Asset.campaign_id == campaign_id)))
    total_assets = len(assets)

    audited_count = 0
    failed_asset_names: list[str] = []

    for a in assets:
        last_run = db.scalar(
            select(AuditRun).where(AuditRun.asset_id == a.id).order_by(AuditRun.id.desc())
        )
        if last_run:
            audited_count += 1
            if last_run.status == FAILED:
                failed_asset_names.append(a.name)

    open_issues = list(db.scalars(
        select(Issue).where(Issue.campaign_id == campaign_id, Issue.status == OPEN)
    ))
    open_count = len(open_issues)

    checklist_items = checklist_service.list_items(db, campaign_id)
    pending_checklist = [i.label for i in checklist_items if not i.done]

    # Várt promóciós anyagok vizsgálata (ha vannak definiálva a kampányban)
    from app.modules.channels.models import Deliverable
    deliverables = list(db.scalars(select(Deliverable).where(Deliverable.campaign_id == campaign_id)))
    missing_deliverables = [d.name for d in deliverables if not d.asset_id]

    reasons: list[str] = []
    if total_assets == 0:
        reasons.append("Nincs még feltöltött kreatív anyag a kampányban.")
    elif audited_count < total_assets:
        reasons.append(f"{total_assets - audited_count} kreatív anyag még nem lett leauditálva.")

    if failed_asset_names:
        reasons.append(f"{len(failed_asset_names)} anyagon audit hiba található ({', '.join(failed_asset_names[:3])}).")

    if open_count > 0:
        reasons.append(f"{open_count} nyitott hibalista tétel vár még javításra.")

    if pending_checklist:
        reasons.append(f"{len(pending_checklist)} ellenőrzőlista tétel még nincs teljesítve.")

    if missing_deliverables:
        reasons.append(f"{len(missing_deliverables)} várt promóciós anyag még nem készült el ({', '.join(missing_deliverables[:3])}).")

    is_ready = (total_assets > 0 and audited_count == total_assets and
                len(failed_asset_names) == 0 and open_count == 0 and
                len(pending_checklist) == 0 and len(missing_deliverables) == 0)

    if is_ready:
        reasons.append("Minden kreatív anyag sikeresen auditálva, minden hibalista és ellenőrzőlista tétel teljesítve.")

    return {
        "ready": is_ready,
        "total_assets": total_assets,
        "audited_assets": audited_count,
        "failed_assets": len(failed_asset_names),
        "open_issues": open_count,
        "pending_checklist": len(pending_checklist),
        "missing_deliverables": len(missing_deliverables),
        "reasons": reasons
    }


def _on_audit_completed(db: Session, run: AuditRun, asset: Asset,
                        actor_id: int | None = None, **kwargs) -> None:
    resolve_issues_for_audit(db, run, asset, actor_id=actor_id)


def setup() -> None:
    bus.subscribe("audit.completed", _on_audit_completed)
