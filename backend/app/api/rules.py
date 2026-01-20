"""Rules API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Rule, Connection
from app.schemas.rule import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleTestResult,
    RuleReorder,
)
from app.services.qbittorrent import QBittorrentService
from app.services.rule_engine import RuleEngine
from app.core.security import decrypt_password

router = APIRouter()


@router.get("", response_model=List[RuleResponse])
async def list_rules(db: AsyncSession = Depends(get_db)):
    """List all rules ordered by priority."""
    result = await db.execute(select(Rule).order_by(Rule.priority, Rule.name))
    rules = result.scalars().all()
    return rules


@router.post("", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(data: RuleCreate, db: AsyncSession = Depends(get_db)):
    """Create a new rule."""
    rule = Rule(
        name=data.name,
        priority=data.priority,
        enabled=data.enabled,
        conditions=data.conditions.model_dump(),
        criteria=data.criteria.model_dump(),
        exceptions=data.exceptions.model_dump(),
        action=data.action,
        action_params=data.action_params,
        notify=data.notify,
        notify_connections=data.notify_connections,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Get a rule by ID."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int, data: RuleUpdate, db: AsyncSession = Depends(get_db)
):
    """Update a rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = data.model_dump(exclude_unset=True)

    # Convert nested models to dicts
    if "conditions" in update_data and update_data["conditions"]:
        update_data["conditions"] = update_data["conditions"].model_dump() if hasattr(update_data["conditions"], "model_dump") else update_data["conditions"]
    if "criteria" in update_data and update_data["criteria"]:
        update_data["criteria"] = update_data["criteria"].model_dump() if hasattr(update_data["criteria"], "model_dump") else update_data["criteria"]
    if "exceptions" in update_data and update_data["exceptions"]:
        update_data["exceptions"] = update_data["exceptions"].model_dump() if hasattr(update_data["exceptions"], "model_dump") else update_data["exceptions"]

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(rule)
    await db.commit()


@router.put("/reorder", response_model=List[RuleResponse])
async def reorder_rules(data: RuleReorder, db: AsyncSession = Depends(get_db)):
    """Reorder rules by priority."""
    for index, rule_id in enumerate(data.rule_ids, start=1):
        result = await db.execute(select(Rule).where(Rule.id == rule_id))
        rule = result.scalar_one_or_none()
        if rule:
            rule.priority = index

    await db.commit()

    # Return updated list
    result = await db.execute(select(Rule).order_by(Rule.priority, Rule.name))
    return result.scalars().all()


async def _get_qbt_service(db: AsyncSession) -> QBittorrentService:
    """Get qBittorrent service instance."""
    result = await db.execute(
        select(Connection).where(
            Connection.type == "qbittorrent",
            Connection.enabled == True,
        )
    )
    connection = result.scalar_one_or_none()
    if not connection:
        raise HTTPException(status_code=400, detail="No qBittorrent connection configured")

    qbt = QBittorrentService(
        url=connection.url,
        username=connection.username or "",
        password=decrypt_password(connection.password) if connection.password else "",
    )
    if not await qbt.connect():
        raise HTTPException(status_code=400, detail="Failed to connect to qBittorrent")
    return qbt


@router.post("/{rule_id}/test", response_model=RuleTestResult)
async def test_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Test a rule against all torrents (dry-run)."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    qbt = await _get_qbt_service(db)
    try:
        engine = RuleEngine(db, qbt)
        test_result = await engine.test_rule(rule)
        return RuleTestResult(**test_result)
    finally:
        await qbt.disconnect()


@router.post("/{rule_id}/execute")
async def execute_rule(rule_id: int, dry_run: bool = True, db: AsyncSession = Depends(get_db)):
    """Execute a rule manually."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    qbt = await _get_qbt_service(db)
    try:
        engine = RuleEngine(db, qbt)

        # Temporarily enable this rule only
        original_enabled = rule.enabled
        original_other_rules = []

        # Disable all other rules temporarily
        result = await db.execute(select(Rule).where(Rule.id != rule_id))
        other_rules = result.scalars().all()
        for r in other_rules:
            original_other_rules.append((r.id, r.enabled))
            r.enabled = False

        rule.enabled = True
        await db.commit()

        try:
            scan_result = await engine.run_scan(dry_run=dry_run)
            return {
                "rule_id": rule_id,
                "rule_name": rule.name,
                "dry_run": dry_run,
                "actions_taken": scan_result.actions_taken,
                "deleted": scan_result.deleted,
                "paused": scan_result.paused,
                "tagged": scan_result.tagged,
                "items": scan_result.items,
            }
        finally:
            # Restore rule states
            rule.enabled = original_enabled
            for r_id, r_enabled in original_other_rules:
                result = await db.execute(select(Rule).where(Rule.id == r_id))
                r = result.scalar_one_or_none()
                if r:
                    r.enabled = r_enabled
            await db.commit()
    finally:
        await qbt.disconnect()
