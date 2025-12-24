from utils.database import db
from datetime import datetime, date
from typing import List, Dict, Any

class LateReasonModel:
    """Database operations for late_reasons table"""
    
    @staticmethod
    async def create_late_reason(
        user_id: int,
        time_tracking_id: int,
        late_mins: int,
        reason: str,
        is_admin_informed: bool,
        morning_meeting_attended: bool = False
    ) -> int:
        """Record a late arrival reason"""
        async with db.pool.acquire() as conn:
            late_id = await conn.fetchval('''
                INSERT INTO late_reasons (
                    user_id, time_tracking_id, late_mins, 
                    reason, is_admin_informed, morning_meeting_attended
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            ''', user_id, time_tracking_id, late_mins, reason, is_admin_informed, morning_meeting_attended)
            return late_id
    
    @staticmethod
    async def get_user_late_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's late arrival history"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT lr.id, lr.late_mins, lr.reason, lr.is_admin_informed, 
                       lr.morning_meeting_attended, lr.recorded_at, tt.present_date
                FROM late_reasons lr
                JOIN time_tracking tt ON lr.time_tracking_id = tt.id
                WHERE lr.user_id = $1
                ORDER BY lr.recorded_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_late_users_list(date_filter: date = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get all users who were late on a specific date"""
        async with db.pool.acquire() as conn:
            if date_filter:
                rows = await conn.fetch('''
                    SELECT 
                        lr.id,
                        lr.user_id,
                        u.name,
                        lr.late_mins,
                        lr.reason,
                        lr.is_admin_informed,
                        lr.morning_meeting_attended,
                        lr.admin_approval,
                        lr.recorded_at,
                        lr.time_tracking_id
                    FROM late_reasons lr
                    JOIN users u ON lr.user_id = u.user_id
                    JOIN time_tracking tt ON lr.time_tracking_id = tt.id
                    WHERE tt.present_date = $1
                    ORDER BY lr.recorded_at DESC
                    LIMIT $2
                ''', date_filter, limit)
            else:
                rows = await conn.fetch('''
                    SELECT 
                        lr.id,
                        lr.user_id,
                        u.name,
                        lr.late_mins,
                        lr.reason,
                        lr.is_admin_informed,
                        lr.morning_meeting_attended,
                        lr.admin_approval,
                        lr.recorded_at,
                        lr.time_tracking_id
                    FROM late_reasons lr
                    JOIN users u ON lr.user_id = u.user_id
                    ORDER BY lr.recorded_at DESC
                    LIMIT $1
                ''', limit)
            return [dict(row) for row in rows]

    @staticmethod
    async def update_admin_approval(late_reason_id: int, admin_approval: bool):
        """Update admin approval status for a late reason"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE late_reasons
                SET admin_approval = $1
                WHERE id = $2
            ''', admin_approval, late_reason_id)
    
    @staticmethod
    async def get_late_reason_by_tracking_id(time_tracking_id: int) -> Dict[str, Any]:
        """Get late reason by time tracking ID"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM late_reasons
                WHERE time_tracking_id = $1
            ''', time_tracking_id)
            return dict(row) if row else None