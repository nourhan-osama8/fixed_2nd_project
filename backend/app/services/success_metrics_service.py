"""
success_metrics_service.py
──────────────────────────
Computes Contact-Centre success KPIs derived from the existing DB schema.

Metrics produced
────────────────
• avg_time_to_answer_sec  – average seconds between case creation and the first
                            completed call assigned to that case.
• avg_response_latency_sec – average call duration (proxy for how quickly the
                             agent / AI resolved the interaction).
• satisfaction_survey      – distribution of AIFollowup results (YES/NO/NO_ANSWER/UNKNOWN)
                             used as a customer-satisfaction signal.
• ai_usage_rate_pct        – share of total calls that were OUTBOUND_AI (bot-handled).
• knowledge_coverage_score – ratio of READY documents to total documents * 100.
• total_ai_calls           – absolute count of AI-handled calls.
• total_human_calls        – absolute count of human-handled calls.
• resolution_rate_pct      – percentage of resolved cases out of all cases.
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.call import Call
from app.models.case import Case
from app.models.ai_followup import AIFollowup
from app.models.document import Document
from app.core.constants import (
    CallType,
    CallOutcome,
    CaseStatus,
    DocumentStatus,
    FollowupResult,
)


class SuccessMetricsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all(self) -> dict:
        return {
            "avg_time_to_answer_sec": self._avg_time_to_answer(),
            "avg_response_latency_sec": self._avg_response_latency(),
            "satisfaction_survey": self._satisfaction_survey(),
            "ai_usage_rate_pct": self._ai_usage_rate(),
            "knowledge_coverage_score": self._knowledge_coverage(),
            "total_ai_calls": self._count_calls_by_type(CallType.OUTBOUND_AI),
            "total_human_calls": self._count_human_calls(),
            "resolution_rate_pct": self._resolution_rate(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _avg_time_to_answer(self) -> float | None:
        """
        Average gap (in seconds) between a case being created and the
        first call for that case starting.  This is the best proxy for
        'time-to-answer' given the current schema.
        """
        rows = (
            self.db.query(Case.created_at, func.min(Call.started_at))
            .join(Call, Call.case_id == Case.id)
            .filter(Call.started_at.isnot(None))
            .group_by(Case.id, Case.created_at)
            .all()
        )
        if not rows:
            return None
        deltas = []
        for case_created, first_call in rows:
            if first_call and case_created:
                # Make both timezone-aware or both naive before subtracting
                if hasattr(case_created, "tzinfo") and case_created.tzinfo and \
                   hasattr(first_call, "tzinfo") and first_call.tzinfo:
                    delta = (first_call - case_created).total_seconds()
                else:
                    # strip tzinfo if mixed
                    fc = first_call.replace(tzinfo=None) if first_call.tzinfo else first_call
                    cc = case_created.replace(tzinfo=None) if case_created.tzinfo else case_created
                    delta = (fc - cc).total_seconds()
                if delta >= 0:
                    deltas.append(delta)
        return round(sum(deltas) / len(deltas), 2) if deltas else None

    def _avg_response_latency(self) -> float | None:
        """Average call duration in seconds (resolved / completed calls only)."""
        result = (
            self.db.query(func.avg(Call.duration))
            .filter(Call.duration.isnot(None), Call.duration > 0)
            .scalar()
        )
        return round(float(result), 2) if result is not None else None

    def _satisfaction_survey(self) -> dict:
        """
        Distribution of AIFollowup results — used as satisfaction signal:
        YES  = issue resolved → happy customer
        NO   = issue persists → unhappy customer
        """
        rows = (
            self.db.query(AIFollowup.result, func.count(AIFollowup.id))
            .filter(AIFollowup.result.isnot(None))
            .group_by(AIFollowup.result)
            .all()
        )
        distribution = {r.value: 0 for r in FollowupResult}
        total = 0
        for result_val, cnt in rows:
            key = result_val.value if hasattr(result_val, "value") else str(result_val)
            distribution[key] = cnt
            total += cnt

        satisfaction_score = None
        if total > 0:
            yes_count = distribution.get(FollowupResult.YES.value, 0)
            satisfaction_score = round((yes_count / total) * 100, 1)

        return {
            "distribution": distribution,
            "total_surveys": total,
            "satisfaction_score_pct": satisfaction_score,
        }

    def _ai_usage_rate(self) -> float | None:
        total = self.db.query(func.count(Call.id)).scalar() or 0
        if total == 0:
            return None
        ai_calls = self.db.query(func.count(Call.id)).filter(
            Call.call_type == CallType.OUTBOUND_AI
        ).scalar() or 0
        return round((ai_calls / total) * 100, 1)

    def _knowledge_coverage(self) -> float | None:
        """Fraction of documents that are READY (fully indexed) × 100."""
        total = self.db.query(func.count(Document.id)).scalar() or 0
        if total == 0:
            return None
        ready = self.db.query(func.count(Document.id)).filter(
            Document.status == DocumentStatus.READY
        ).scalar() or 0
        return round((ready / total) * 100, 1)

    def _count_calls_by_type(self, call_type: CallType) -> int:
        return self.db.query(func.count(Call.id)).filter(
            Call.call_type == call_type
        ).scalar() or 0

    def _count_human_calls(self) -> int:
        return self.db.query(func.count(Call.id)).filter(
            Call.call_type.in_([CallType.INBOUND_HUMAN, CallType.OUTBOUND_HUMAN])
        ).scalar() or 0

    def _resolution_rate(self) -> float | None:
        total = self.db.query(func.count(Case.id)).scalar() or 0
        if total == 0:
            return None
        resolved = self.db.query(func.count(Case.id)).filter(
            Case.status == CaseStatus.RESOLVED
        ).scalar() or 0
        return round((resolved / total) * 100, 1)
