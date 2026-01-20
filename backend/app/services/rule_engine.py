"""Rule Engine service for evaluating and executing seeding rules."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Rule, Torrent, ActionLog, Tracker, Settings
from app.models.settings import DEFAULT_SETTINGS
from app.services.qbittorrent import QBittorrentService, TorrentInfo


@dataclass
class RuleMatch:
    """Result of matching a torrent against rules."""

    rule: Rule
    torrent: Torrent
    should_act: bool
    reason: str


@dataclass
class ActionResult:
    """Result of executing an action."""

    success: bool
    action: str
    reason: str
    dry_run: bool


@dataclass
class ScanResult:
    """Result of a complete scan."""

    dry_run: bool
    started_at: datetime
    completed_at: datetime
    torrents_scanned: int
    actions_taken: int
    deleted: int
    paused: int
    tagged: int
    protected_skipped: int
    items: List[dict]


class RuleEngine:
    """Engine for evaluating and executing seeding rules."""

    def __init__(self, db: AsyncSession, qbt_service: QBittorrentService):
        """Initialize rule engine."""
        self.db = db
        self.qbt = qbt_service

    async def _get_setting(self, key: str):
        """Get a setting value."""
        result = await self.db.execute(select(Settings).where(Settings.key == key))
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
        return DEFAULT_SETTINGS.get(key)

    async def _get_protected_tags(self) -> List[str]:
        """Get list of protected tags."""
        return await self._get_setting("protected_tags") or []

    async def _get_protected_categories(self) -> List[str]:
        """Get list of protected categories."""
        return await self._get_setting("protected_categories") or []

    def _matches_conditions(self, torrent: Torrent, conditions: dict) -> bool:
        """Check if torrent matches rule conditions."""
        # Check tracker
        tracker_ids = conditions.get("tracker_ids", [])
        if tracker_ids and torrent.tracker_id not in tracker_ids:
            return False

        # Check category
        categories = conditions.get("categories", [])
        if categories and torrent.category not in categories:
            return False

        # Check tags (any match)
        required_tags = conditions.get("tags", [])
        if required_tags:
            torrent_tags = torrent.tags or []
            if not any(tag in torrent_tags for tag in required_tags):
                return False

        # Check size
        size_gb = torrent.size_bytes / (1024 ** 3)
        min_size = conditions.get("min_size_gb")
        max_size = conditions.get("max_size_gb")

        if min_size is not None and size_gb < min_size:
            return False
        if max_size is not None and size_gb > max_size:
            return False

        return True

    def _meets_criteria(self, torrent: Torrent, criteria: dict) -> Tuple[bool, str]:
        """Check if torrent meets deletion criteria."""
        operator = criteria.get("operator", "AND")
        met_conditions = []
        reasons = []

        # Check minimum seed time
        min_seed_time = criteria.get("min_seed_time_minutes")
        if min_seed_time is not None:
            seed_time_minutes = torrent.seed_time_seconds / 60
            meets_seed_time = seed_time_minutes >= min_seed_time
            met_conditions.append(meets_seed_time)
            if meets_seed_time:
                reasons.append(f"seed_time ({seed_time_minutes:.0f}min) >= {min_seed_time}min")
            else:
                reasons.append(f"seed_time ({seed_time_minutes:.0f}min) < {min_seed_time}min")

        # Check minimum ratio
        min_ratio = criteria.get("min_ratio")
        if min_ratio is not None:
            meets_ratio = torrent.ratio >= min_ratio
            met_conditions.append(meets_ratio)
            if meets_ratio:
                reasons.append(f"ratio ({torrent.ratio:.2f}) >= {min_ratio}")
            else:
                reasons.append(f"ratio ({torrent.ratio:.2f}) < {min_ratio}")

        # Check maximum seed time
        max_seed_time = criteria.get("max_seed_time_minutes")
        if max_seed_time is not None:
            seed_time_minutes = torrent.seed_time_seconds / 60
            meets_max_seed = seed_time_minutes >= max_seed_time
            met_conditions.append(meets_max_seed)
            if meets_max_seed:
                reasons.append(f"max_seed_time ({seed_time_minutes:.0f}min) >= {max_seed_time}min")
            else:
                reasons.append(f"max_seed_time ({seed_time_minutes:.0f}min) < {max_seed_time}min")

        if not met_conditions:
            return False, "No criteria defined"

        # Apply operator
        if operator == "AND":
            should_act = all(met_conditions)
        else:  # OR
            should_act = any(met_conditions)

        reason = f" {operator} ".join(reasons)
        return should_act, reason

    def _check_exceptions(self, torrent: Torrent, exceptions: dict) -> Tuple[bool, str]:
        """Check if torrent should be protected by exceptions."""
        # Check seeders threshold
        keep_if_seeders_below = exceptions.get("keep_if_seeders_below")
        if keep_if_seeders_below is not None:
            if torrent.num_seeds < keep_if_seeders_below:
                return True, f"Keeping: only {torrent.num_seeds} seeders (threshold: {keep_if_seeders_below})"

        # Check last activity
        keep_if_last_activity_days = exceptions.get("keep_if_last_activity_days")
        if keep_if_last_activity_days is not None:
            days_since_activity = (datetime.utcnow() - torrent.last_activity).days
            if days_since_activity <= keep_if_last_activity_days:
                return True, f"Keeping: last activity {days_since_activity} days ago (threshold: {keep_if_last_activity_days})"

        return False, ""

    async def evaluate_torrent(self, torrent: Torrent, rules: List[Rule]) -> Optional[RuleMatch]:
        """Evaluate a torrent against all rules and return the first match."""
        # Check if torrent is protected
        if torrent.protected:
            return RuleMatch(
                rule=None,
                torrent=torrent,
                should_act=False,
                reason="Torrent is protected",
            )

        # Check protected tags
        protected_tags = await self._get_protected_tags()
        torrent_tags = torrent.tags or []
        for tag in protected_tags:
            if tag in torrent_tags:
                return RuleMatch(
                    rule=None,
                    torrent=torrent,
                    should_act=False,
                    reason=f"Has protected tag: {tag}",
                )

        # Check protected categories
        protected_categories = await self._get_protected_categories()
        if torrent.category in protected_categories:
            return RuleMatch(
                rule=None,
                torrent=torrent,
                should_act=False,
                reason=f"In protected category: {torrent.category}",
            )

        # Evaluate against rules (sorted by priority)
        sorted_rules = sorted([r for r in rules if r.enabled], key=lambda r: r.priority)

        for rule in sorted_rules:
            # Check if torrent matches conditions
            if not self._matches_conditions(torrent, rule.conditions):
                continue

            # Check if criteria are met
            should_act, criteria_reason = self._meets_criteria(torrent, rule.criteria)
            if not should_act:
                continue

            # Check exceptions
            has_exception, exception_reason = self._check_exceptions(torrent, rule.exceptions)
            if has_exception:
                return RuleMatch(
                    rule=rule,
                    torrent=torrent,
                    should_act=False,
                    reason=exception_reason,
                )

            # All checks passed
            return RuleMatch(
                rule=rule,
                torrent=torrent,
                should_act=True,
                reason=f"Rule '{rule.name}': {criteria_reason}",
            )

        return None

    async def execute_action(
        self, torrent: Torrent, rule: Rule, dry_run: bool = False
    ) -> ActionResult:
        """Execute the action defined by the rule."""
        action = rule.action
        action_params = rule.action_params or {}

        if dry_run:
            return ActionResult(
                success=True,
                action=action,
                reason=f"[DRY-RUN] Would {action} torrent",
                dry_run=True,
            )

        try:
            if action == "delete":
                success = await self.qbt.delete_torrent(torrent.hash, delete_files=True)
                return ActionResult(
                    success=success,
                    action="deleted",
                    reason="Deleted torrent and files",
                    dry_run=False,
                )

            elif action == "delete_torrent_only":
                success = await self.qbt.delete_torrent(torrent.hash, delete_files=False)
                return ActionResult(
                    success=success,
                    action="deleted",
                    reason="Deleted torrent (kept files)",
                    dry_run=False,
                )

            elif action == "pause":
                success = await self.qbt.pause_torrent(torrent.hash)
                return ActionResult(
                    success=success,
                    action="paused",
                    reason="Paused torrent",
                    dry_run=False,
                )

            elif action == "tag":
                tag = action_params.get("tag", "completed")
                success = await self.qbt.add_tag(torrent.hash, tag)
                return ActionResult(
                    success=success,
                    action="tagged",
                    reason=f"Added tag '{tag}'",
                    dry_run=False,
                )

            else:
                return ActionResult(
                    success=False,
                    action=action,
                    reason=f"Unknown action: {action}",
                    dry_run=False,
                )

        except Exception as e:
            logger.error(f"Failed to execute action {action} on {torrent.hash}: {e}")
            return ActionResult(
                success=False,
                action=action,
                reason=str(e),
                dry_run=False,
            )

    async def _log_action(
        self,
        torrent: Torrent,
        rule: Optional[Rule],
        action: str,
        reason: str,
        dry_run: bool,
    ) -> None:
        """Log an action to the database."""
        log = ActionLog(
            torrent_hash=torrent.hash,
            torrent_name=torrent.name,
            tracker_id=torrent.tracker_id,
            rule_id=rule.id if rule else None,
            action=action,
            reason=reason,
            dry_run=dry_run,
        )
        self.db.add(log)
        await self.db.commit()

    async def run_scan(self, dry_run: bool = False) -> ScanResult:
        """Run a complete scan of all torrents."""
        started_at = datetime.utcnow()
        items = []
        deleted = 0
        paused = 0
        tagged = 0
        protected_skipped = 0

        # Get global dry_run setting
        global_dry_run = await self._get_setting("dry_run_mode")
        if global_dry_run:
            dry_run = True

        logger.info(f"Starting scan (dry_run={dry_run})")

        # Get all rules
        result = await self.db.execute(select(Rule).where(Rule.enabled == True))
        rules = result.scalars().all()

        if not rules:
            logger.warning("No enabled rules found")

        # Get all torrents from cache
        result = await self.db.execute(select(Torrent))
        torrents = result.scalars().all()

        logger.info(f"Evaluating {len(torrents)} torrents against {len(rules)} rules")

        for torrent in torrents:
            # Only process completed torrents
            if torrent.state not in ["uploading", "stalledUP", "pausedUP", "queuedUP", "forcedUP"]:
                continue

            match = await self.evaluate_torrent(torrent, rules)

            if match is None:
                continue

            if not match.should_act:
                protected_skipped += 1
                continue

            # Execute action
            action_result = await self.execute_action(torrent, match.rule, dry_run)

            if action_result.success:
                # Log the action
                await self._log_action(
                    torrent,
                    match.rule,
                    action_result.action,
                    match.reason,
                    dry_run,
                )

                # Get tracker name
                tracker_name = None
                if torrent.tracker_id:
                    result = await self.db.execute(
                        select(Tracker).where(Tracker.id == torrent.tracker_id)
                    )
                    tracker = result.scalar_one_or_none()
                    if tracker:
                        tracker_name = tracker.name

                items.append({
                    "torrent_hash": torrent.hash,
                    "torrent_name": torrent.name,
                    "tracker_name": tracker_name,
                    "rule_name": match.rule.name,
                    "action": action_result.action,
                    "reason": match.reason,
                })

                if action_result.action == "deleted":
                    deleted += 1
                    if not dry_run:
                        # Remove from cache
                        await self.db.delete(torrent)
                        await self.db.commit()
                elif action_result.action == "paused":
                    paused += 1
                elif action_result.action == "tagged":
                    tagged += 1

        completed_at = datetime.utcnow()
        duration = (completed_at - started_at).total_seconds()

        logger.info(
            f"Scan completed in {duration:.2f}s: "
            f"{len(items)} actions, {deleted} deleted, {paused} paused, "
            f"{tagged} tagged, {protected_skipped} protected"
        )

        return ScanResult(
            dry_run=dry_run,
            started_at=started_at,
            completed_at=completed_at,
            torrents_scanned=len(torrents),
            actions_taken=len(items),
            deleted=deleted,
            paused=paused,
            tagged=tagged,
            protected_skipped=protected_skipped,
            items=items,
        )

    async def test_rule(self, rule: Rule) -> dict:
        """Test a rule against all torrents without executing actions."""
        result = await self.db.execute(select(Torrent))
        torrents = result.scalars().all()

        matched_torrents = []
        would_be_deleted = 0
        would_be_paused = 0
        would_be_tagged = 0
        protected_count = 0

        for torrent in torrents:
            # Only process completed torrents
            if torrent.state not in ["uploading", "stalledUP", "pausedUP", "queuedUP", "forcedUP"]:
                continue

            match = await self.evaluate_torrent(torrent, [rule])

            if match is None:
                continue

            # Get tracker name
            tracker_name = None
            if torrent.tracker_id:
                result = await self.db.execute(
                    select(Tracker).where(Tracker.id == torrent.tracker_id)
                )
                tracker = result.scalar_one_or_none()
                if tracker:
                    tracker_name = tracker.name

            matched_torrents.append({
                "hash": torrent.hash,
                "name": torrent.name,
                "tracker_name": tracker_name,
                "category": torrent.category,
                "ratio": torrent.ratio,
                "seed_time_minutes": torrent.seed_time_seconds / 60,
                "would_act": match.should_act,
                "reason": match.reason,
            })

            if not match.should_act:
                protected_count += 1
            elif rule.action == "delete" or rule.action == "delete_torrent_only":
                would_be_deleted += 1
            elif rule.action == "pause":
                would_be_paused += 1
            elif rule.action == "tag":
                would_be_tagged += 1

        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "matched_torrents": matched_torrents,
            "total_matched": len(matched_torrents),
            "would_be_deleted": would_be_deleted,
            "would_be_paused": would_be_paused,
            "would_be_tagged": would_be_tagged,
            "protected_count": protected_count,
        }
