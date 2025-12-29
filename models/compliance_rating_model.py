from utils.database import db
from datetime import date
from typing import Dict, Any, List, Optional

class ComplianceRatingModel:
    """Database operations for compliance_ratings table"""
    
    @staticmethod
    async def create_rating(
        user_id: int,
        rated_by_user_id: int,
        rating_date: date,
        compliance_rule_breaks: int,
        task_submission_rating: int,
        task_submission_feedback: str,
        overall_performance_rating: int,
        overall_performance_feedback: str
    ) -> int:
        """Create a new compliance rating"""
        async with db.pool.acquire() as conn:
            rating_id = await conn.fetchval('''
                INSERT INTO compliance_ratings (
                    user_id, rated_by_user_id, rating_date,
                    compliance_rule_breaks, task_submission_rating, task_submission_feedback,
                    overall_performance_rating, overall_performance_feedback
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING rating_id
            ''', user_id, rated_by_user_id, rating_date, compliance_rule_breaks,
                task_submission_rating, task_submission_feedback,
                overall_performance_rating, overall_performance_feedback)
            return rating_id
    
    @staticmethod
    async def get_user_ratings(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all ratings for a specific user"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    er.rating_id,
                    er.rating_date,
                    er.compliance_rule_breaks,
                    er.task_submission_rating,
                    er.task_submission_feedback,
                    er.overall_performance_rating,
                    er.overall_performance_feedback,
                    er.created_at,
                    u.name as rated_by_name
                FROM compliance_ratings er
                JOIN users u ON er.rated_by_user_id = u.user_id
                WHERE er.user_id = $1
                ORDER BY er.rating_date DESC, er.created_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]
    
    @staticmethod
    async def get_rating_by_date(user_id: int, rating_date: date) -> Optional[Dict[str, Any]]:
        """Get rating for a user on a specific date"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT 
                    er.rating_id,
                    er.rating_date,
                    er.compliance_rule_breaks,
                    er.task_submission_rating,
                    er.task_submission_feedback,
                    er.overall_performance_rating,
                    er.overall_performance_feedback,
                    er.created_at,
                    u.name as rated_by_name
                FROM compliance_ratings er
                JOIN users u ON er.rated_by_user_id = u.user_id
                WHERE er.user_id = $1 AND er.rating_date = $2
            ''', user_id, rating_date)
            return dict(row) if row else None
    
    @staticmethod
    async def get_all_ratings_by_date(rating_date: date) -> List[Dict[str, Any]]:
        """Get all ratings for a specific date"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    er.rating_id,
                    er.user_id,
                    u.name as user_name,
                    er.rating_date,
                    er.compliance_rule_breaks,
                    er.task_submission_rating,
                    er.task_submission_feedback,
                    er.overall_performance_rating,
                    er.overall_performance_feedback,
                    er.created_at,
                    rater.name as rated_by_name
                FROM compliance_ratings er
                JOIN users u ON er.user_id = u.user_id
                JOIN users rater ON er.rated_by_user_id = rater.user_id
                WHERE er.rating_date = $1
                ORDER BY u.name
            ''', rating_date)
            return [dict(row) for row in rows]

