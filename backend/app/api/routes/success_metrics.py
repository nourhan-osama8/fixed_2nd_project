"""
api/routes/success_metrics.py
──────────────────────────────
REST endpoints that expose Contact-Centre success KPIs.

GET /api/v1/metrics/all          – full dashboard bundle
GET /api/v1/metrics/latency      – avg response latency only
GET /api/v1/metrics/satisfaction – satisfaction survey breakdown
GET /api/v1/metrics/ai-usage     – AI vs human call split
GET /api/v1/metrics/knowledge    – knowledge-base coverage score
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import require_admin
from app.models.user import User
from app.services.success_metrics_service import SuccessMetricsService
from app.core.constants import CallType

router = APIRouter(prefix="/metrics")


@router.get("/all", summary="All success KPIs in one response")
def get_all_metrics(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Returns the full set of contact-centre success metrics."""
    return SuccessMetricsService(db).get_all()


@router.get("/latency", summary="Average agent response latency")
def get_latency(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SuccessMetricsService(db)
    return {
        "avg_time_to_answer_sec": svc._avg_time_to_answer(),
        "avg_response_latency_sec": svc._avg_response_latency(),
    }


@router.get("/satisfaction", summary="Customer satisfaction survey results")
def get_satisfaction(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return SuccessMetricsService(db)._satisfaction_survey()


@router.get("/ai-usage", summary="AI vs human call usage rate")
def get_ai_usage(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SuccessMetricsService(db)
    return {
        "ai_usage_rate_pct": svc._ai_usage_rate(),
        "total_ai_calls": svc._count_calls_by_type(CallType.OUTBOUND_AI),
        "total_human_calls": svc._count_human_calls(),
    }


@router.get("/knowledge", summary="Knowledge-base coverage score")
def get_knowledge_coverage(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return {
        "knowledge_coverage_score": SuccessMetricsService(db)._knowledge_coverage(),
    }
