from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from app.models.call import Call
from app.core.constants import CallOutcome, CallType


class CallRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, call_id: UUID) -> Optional[Call]:
        return (
            self.db.query(Call)
            .options(joinedload(Call.customer), joinedload(Call.case), joinedload(Call.agent))
            .filter(Call.id == call_id)
            .first()
        )

    def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        customer_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> List[Call]:
        query = self.db.query(Call).options(
            joinedload(Call.customer), joinedload(Call.case), joinedload(Call.agent)
        )
        if customer_id:
            query = query.filter(Call.customer_id == customer_id)
        if case_id:
            query = query.filter(Call.case_id == case_id)
        if agent_id:
            query = query.filter(Call.agent_id == agent_id)
        return query.order_by(Call.started_at.desc()).offset(skip).limit(limit).all()

    def get_pending_outbound_ai_call(self, case_id: UUID) -> Optional[Call]:
        """Returns active/pending OUTBOUND_AI call for this case to prevent duplicate call records."""
        return (
            self.db.query(Call)
            .options(joinedload(Call.customer), joinedload(Call.case))
            .filter(
                Call.case_id == case_id,
                Call.call_type == CallType.OUTBOUND_AI,
                Call.outcome == CallOutcome.PENDING,
            )
            .order_by(Call.started_at.desc())
            .first()
        )

    def count(
        self,
        customer_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        agent_id: Optional[UUID] = None,
    ) -> int:
        query = self.db.query(Call)
        if customer_id:
            query = query.filter(Call.customer_id == customer_id)
        if case_id:
            query = query.filter(Call.case_id == case_id)
        if agent_id:
            query = query.filter(Call.agent_id == agent_id)
        return query.count()

    def create(self, call: Call) -> Call:
        self.db.add(call)
        self.db.commit()
        self.db.refresh(call)
        return self.get_by_id(call.id)

    def update(self, call: Call) -> Call:
        self.db.commit()
        self.db.refresh(call)
        return call
