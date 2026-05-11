"""
SOC360 Risk Assessment Service
Service for managing risk assessments.
"""
from datetime import datetime
from typing import List, Optional

from app.extensions import db
from app.models.monitoring.report import RiskAssessment


class RiskAssessmentService:
    """Service for managing risk assessments."""

    @staticmethod
    def create_assessment(
        user_id: int,
        asset_id: int,
        vulnerability_id: int,
        risk_score: float,
        recommendation_id: Optional[int] = None
    ) -> RiskAssessment:
        """Create a new risk assessment."""
        assessment = RiskAssessment(
            created_by=user_id,
            asset_id=asset_id,
            vulnerability_id=vulnerability_id,
            recommendation_id=recommendation_id,
            risk_score=risk_score,
            created_at=datetime.utcnow()
        )
        db.session.add(assessment)
        db.session.commit()
        return assessment

    @staticmethod
    def list_assessments_for_asset(asset_id: int) -> List[RiskAssessment]:
        """Return all risk assessments for a specific asset."""
        return RiskAssessment.query.filter_by(asset_id=asset_id).all()

    @staticmethod
    def list_assessments_for_user(user_id: int) -> List[RiskAssessment]:
        """Return all risk assessments created by a specific user."""
        return RiskAssessment.query.filter_by(created_by=user_id).all()

    @staticmethod
    def get_assessment(assessment_id: int) -> RiskAssessment:
        """Get a risk assessment by ID."""
        assessment = db.session.get(RiskAssessment, assessment_id)
        if not assessment:
            raise ValueError(f"Risk assessment {assessment_id} not found.")
        return assessment

    @staticmethod
    def update_assessment(assessment_id: int, **kwargs) -> RiskAssessment:
        """Update fields of a risk assessment."""
        assessment = RiskAssessmentService.get_assessment(assessment_id)
        for key, value in kwargs.items():
            if hasattr(assessment, key):
                setattr(assessment, key, value)
        db.session.commit()
        return assessment

    @staticmethod
    def delete_assessment(assessment_id: int) -> None:
        """Delete a risk assessment."""
        assessment = RiskAssessmentService.get_assessment(assessment_id)
        db.session.delete(assessment)
        db.session.commit()