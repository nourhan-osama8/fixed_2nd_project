from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from app.models.ai_followup import AIFollowup
from app.core.constants import FollowupStatus


class FollowupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, followup_id: UUID) -> Optional[AIFollowup]:
        return (
            self.db.query(AIFollowup)
            .options(joinedload(AIFollowup.case), joinedload(AIFollowup.customer))
            .filter(AIFollowup.id == followup_id)
            .first()
        )

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        case_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
        status: Optional[FollowupStatus] = None,
    ) -> List[AIFollowup]:
        query = self.db.query(AIFollowup).options(
            joinedload(AIFollowup.case), joinedload(AIFollowup.customer)
        )
        if case_id:
            query = query.filter(AIFollowup.case_id == case_id)
        if customer_id:
            query = query.filter(AIFollowup.customer_id == customer_id)
        if status:
            query = query.filter(AIFollowup.status == status)
        return query.order_by(AIFollowup.scheduled_at.desc()).offset(skip).limit(limit).all()

    def get_active_by_case_id(self, case_id: UUID) -> Optional[AIFollowup]:
        """Returns in-progress or scheduled followup for a given case to prevent duplicates."""
        return (
            self.db.query(AIFollowup)
            .options(joinedload(AIFollowup.case), joinedload(AIFollowup.customer))
            .filter(
                AIFollowup.case_id == case_id,
                AIFollowup.status.in_([FollowupStatus.IN_PROGRESS, FollowupStatus.SCHEDULED]),
            )
            .order_by(AIFollowup.scheduled_at.asc())
            .first()
        )

    def count(
        self,
        case_id: Optional[UUID] = None,
        customer_id: Optional[UUID] = None,
        status: Optional[FollowupStatus] = None,
    ) -> int:
        query = self.db.query(AIFollowup)
        if case_id:
            query = query.filter(AIFollowup.case_id == case_id)
        if customer_id:
            query = query.filter(AIFollowup.customer_id == customer_id)
        if status:
            query = query.filter(AIFollowup.status == status)
        return query.count()

    def create(self, followup: AIFollowup) -> AIFollowup:
        self.db.add(followup)
        self.db.commit()
        self.db.refresh(followup)
        return self.get_by_id(followup.id)

    def update(self, followup: AIFollowup) -> AIFollowup:
        self.db.commit()
        self.db.refresh(followup)
        return followup
