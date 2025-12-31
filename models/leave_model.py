"""Leave request model for managing employee leave requests"""
from datetime import datetime
from utils.database import db


class LeaveRequestModel:
    """Model for managing leave requests"""
    
    @staticmethod
    async def create_leave_request(
        user_id: int,
        leave_type: str,
        start_date: str,
        end_date: str = None,
        duration_hours: int = None,
        reason: str = None,
        approval_required: bool = True,
        compensating_day: str = None,
        proof_provided: bool = False
    ) -> int:
        """Create a new leave request"""
        try:
            query = """
            INSERT INTO leave_requests (
                user_id, leave_type, start_date, end_date,
                duration_hours, reason, status, approval_required, 
                compensating_day, proof_provided, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            RETURNING leave_request_id
            """
            
            async with db.pool.acquire() as conn:
                leave_request_id = await conn.fetchval(
                    query,
                    user_id,
                    leave_type,
                    start_date,
                    end_date,
                    duration_hours,
                    reason,
                    'pending',
                    approval_required,
                    compensating_day,
                    proof_provided
                )
            
            return leave_request_id
        
        except Exception as e:
            print(f"❌ Error creating leave request: {e}")
            raise
    
    @staticmethod
    async def get_leave_request(leave_request_id: int):
        """Get a specific leave request"""
        try:
            query = """
            SELECT
                lr.leave_request_id,
                lr.user_id,
                u.name,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.duration_hours,
                lr.reason,
                lr.status,
                lr.approval_required,
                lr.compensating_day,
                lr.proof_provided,
                lr.created_at,
                lr.updated_at
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.user_id
            WHERE lr.leave_request_id = $1
            """
            
            async with db.pool.acquire() as conn:
                row = await conn.fetchrow(query, leave_request_id)
            
            if not row:
                return None
            
            return dict(row)
        
        except Exception as e:
            print(f"❌ Error fetching leave request: {e}")
            raise
    
    @staticmethod
    async def get_user_leave_requests(user_id: int, limit: int = 10):
        """Get all leave requests for a user"""
        try:
            query = """
            SELECT
                leave_request_id,
                leave_type,
                start_date,
                end_date,
                duration_hours,
                reason,
                status,
                created_at,
                updated_at
            FROM leave_requests
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """
            
            async with db.pool.acquire() as conn:
                rows = await conn.fetch(query, user_id, limit)
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"❌ Error fetching user leave requests: {e}")
            raise
    
    @staticmethod
    async def approve_leave_request(leave_request_id: int, approved_by_user_id: int) -> bool:
        """Approve a leave request"""
        try:
            query = """
            UPDATE leave_requests
            SET status = 'approved', approved_by = $1, updated_at = NOW()
            WHERE leave_request_id = $2
            """
            
            async with db.pool.acquire() as conn:
                result = await conn.execute(query, approved_by_user_id, leave_request_id)
            
            return result == 'UPDATE 1'
        
        except Exception as e:
            print(f"❌ Error approving leave request: {e}")
            raise
    
    @staticmethod
    async def reject_leave_request(leave_request_id: int, rejection_reason: str) -> bool:
        """Reject a leave request"""
        try:
            query = """
            UPDATE leave_requests
            SET status = 'rejected', rejection_reason = $1, updated_at = NOW()
            WHERE leave_request_id = $2
            """
            
            async with db.pool.acquire() as conn:
                result = await conn.execute(query, rejection_reason, leave_request_id)
            
            return result == 'UPDATE 1'
        
        except Exception as e:
            print(f"❌ Error rejecting leave request: {e}")
            raise
    
    @staticmethod
    async def get_pending_leave_requests(limit: int = 20):
        """Get all pending leave requests"""
        try:
            query = """
            SELECT
                lr.leave_request_id,
                lr.user_id,
                u.name,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.reason,
                lr.created_at
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.user_id
            WHERE lr.status = 'pending'
            ORDER BY lr.created_at ASC
            LIMIT $1
            """
            
            async with db.pool.acquire() as conn:
                rows = await conn.fetch(query, limit)
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"❌ Error fetching pending leave requests: {e}")
            raise
    
    @staticmethod
    async def check_pending_leaves(user_id: int) -> int:
        """Get number of pending leaves for a user"""
        try:
            query = """
            SELECT pending_leaves FROM users WHERE user_id = $1
            """
            
            async with db.pool.acquire() as conn:
                result = await conn.fetchval(query, user_id)
            
            return result or 0
        
        except Exception as e:
            print(f"❌ Error checking pending leaves: {e}")
            raise
    
    @staticmethod
    async def deduct_pending_leave(user_id: int, days: int = 1) -> bool:
        """Deduct a number of days from pending paid leaves (clamped at 0)"""
        try:
            query = """
            UPDATE users
            SET pending_leaves = CASE 
                WHEN pending_leaves > 0 THEN GREATEST(pending_leaves - $2, 0)
                ELSE 0
            END
            WHERE user_id = $1
            """
            
            async with db.pool.acquire() as conn:
                result = await conn.execute(query, user_id, days)
            
            return result == 'UPDATE 1'
        
        except Exception as e:
            print(f"❌ Error deducting pending leave: {e}")
            raise
    
    @staticmethod
    async def get_users_on_leave_for_date(check_date):
        """Get all users who are on leave (approved or pending) for a specific date"""
        try:
            query = """
            SELECT DISTINCT
                lr.user_id,
                u.name,
                u.department,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.status,
                lr.reason
            FROM leave_requests lr
            JOIN users u ON lr.user_id = u.user_id
            WHERE u.is_deleted = FALSE
                AND lr.status IN ('approved', 'pending')
                AND lr.start_date <= $1
                AND (lr.end_date >= $1 OR lr.end_date IS NULL)
            ORDER BY u.name
            """
            
            async with db.pool.acquire() as conn:
                rows = await conn.fetch(query, check_date)
            
            return [dict(row) for row in rows]
        
        except Exception as e:
            print(f"❌ Error fetching users on leave: {e}")
            raise
    
    @staticmethod
    async def get_non_compliant_count(user_id: int, start_date, end_date) -> int:
        """Get count of non-compliant leave requests for a user where the leave date falls within a date range"""
        try:
            query = """
            SELECT COUNT(*) 
            FROM leave_requests
            WHERE user_id = $1
                AND leave_type = 'non_compliant'
                AND status IN ('approved', 'pending')
                AND start_date >= $2
                AND start_date <= $3
            """
            
            async with db.pool.acquire() as conn:
                count = await conn.fetchval(query, user_id, start_date, end_date)
            
            return count or 0
        
        except Exception as e:
            print(f"❌ Error counting non-compliant leaves: {e}")
            return 0

    @staticmethod
    async def get_sick_leave_count(user_id: int, start_date, end_date) -> int:
        """Get count of sick leave requests for a user within a date range"""
        try:
            query = """
            SELECT COUNT(*)
            FROM leave_requests
            WHERE user_id = $1
                AND leave_type = 'sick_leave'
                AND status IN ('approved', 'pending')
                AND start_date >= $2
                AND start_date <= $3
            """
            async with db.pool.acquire() as conn:
                count = await conn.fetchval(query, user_id, start_date, end_date)
            return count or 0
        except Exception as e:
            print(f"❌ Error counting sick leaves: {e}")
            return 0
