from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import bus
from app.modules.assets.models import Asset, AssetContent
from app.modules.factsheet.queries import confirmed_facts
from app.modules.references.models import Reference
from app.modules.rules.queries import active_rules
from app.modules.tenants.service import get_campaign

from .engine import check_fact, check_rule
from .models import FAILED, PASSED, WARNING, AuditResult, AuditRun


def run_audit(db: Session, campaign_id: int, asset_id: int, user_id: int | None = None) -> AuditRun:
    asset = db.get(Asset, asset_id)
    if not asset or asset.campaign_id != campaign_id:
        raise ValueError("Asset nem található")

    campaign = get_campaign(db, campaign_id)
    client_id = campaign.client_id if campaign else 0
    content = db.scalar(select(AssetContent).where(AssetContent.asset_id == asset_id, AssetContent.page_num == 0))
    full_text = content.plain_text if content else ""
    blocks = content.blocks if content else []

    run = AuditRun(campaign_id=campaign_id, asset_id=asset_id, created_by=user_id)
    db.add(run)
    db.flush()

    passed, failed, warning = 0, 0, 0

    # 1. Szabályok ellenőrzése
    ref_lookup = lambda rid: db.get(Reference, rid)
    for rule in active_rules(db, client_id, campaign_id):
        verdict, msg, evidence = check_rule(
            rule.text, rule.check or {}, full_text, blocks,
            asset_preview_path=asset.preview_path or "", ref_resolver=ref_lookup
        )
        res = AuditResult(
            audit_run_id=run.id, rule_id=rule.id, check_type="rule",
            title=rule.text[:250], category=rule.category, severity=rule.severity,
            verdict=verdict, message=msg, evidence=evidence
        )
        db.add(res)
        if verdict == PASSED: passed += 1
        elif verdict == FAILED: failed += 1
        else: warning += 1

    # 2. Kampány-adatlap (tényadatok) ellenőrzése
    for fact in confirmed_facts(db, campaign_id):
        fact_eval = check_fact(fact.key, fact.value, full_text, blocks)
        if fact_eval:
            verdict, msg, evidence = fact_eval
            res = AuditResult(
                audit_run_id=run.id, rule_id=None, check_type="factsheet",
                title=f"Kampány adat: {fact.key}", category="consistency", severity="warning",
                verdict=verdict, message=msg, evidence=evidence
            )
            db.add(res)
            if verdict == PASSED: passed += 1
            elif verdict == FAILED: failed += 1
            else: warning += 1

    run.passed_count, run.failed_count, run.warning_count = passed, failed, warning
    run.status = FAILED if failed > 0 else (WARNING if warning > 0 else PASSED)
    db.commit()

    bus.publish("audit.completed", db=db, run=run, asset=asset, actor_id=user_id)
    return run


def get_audit_run(db: Session, run_id: int) -> AuditRun | None:
    return db.get(AuditRun, run_id)


def list_results(db: Session, run_id: int) -> list[AuditResult]:
    return list(db.scalars(select(AuditResult).where(AuditResult.audit_run_id == run_id).order_by(AuditResult.id)))


def latest_run_for_asset(db: Session, asset_id: int) -> AuditRun | None:
    return db.scalar(select(AuditRun).where(AuditRun.asset_id == asset_id).order_by(AuditRun.id.desc()))
