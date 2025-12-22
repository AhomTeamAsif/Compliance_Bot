from utils.database import db
from datetime import datetime

class ActivityLogModel:
    """Database operations for activity_logs table"""
    
    @staticmethod
    async def log_activity(user_id: int, slash_command_used: str):
        """Insert a new activity log"""
        async with db.pool.acquire() as conn:
            log_id = await conn.fetchval('''
                INSERT INTO activity_logs (user_id, slash_command_used)
                VALUES ($1, $2)
                RETURNING id
            ''', user_id, slash_command_used)
            return log_id
    
    @staticmethod
    async def delete_activity_log(log_id: int):
        """Delete an activity log by ID"""
        async with db.pool.acquire() as conn:
            result = await conn.execute('''
                DELETE FROM activity_logs
                WHERE id = $1
            ''', log_id)
            return result != "DELETE 0"
    
    @staticmethod
    async def delete_activity_logs_by_user(user_id: int):
        """Delete all activity logs for a specific user"""
        async with db.pool.acquire() as conn:
            result = await conn.execute('''
                DELETE FROM activity_logs
                WHERE user_id = $1
            ''', user_id)
            return result != "DELETE 0"
    
    @staticmethod
    async def get_activity_logs_count():
        """Get total count of activity logs"""
        async with db.pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM activity_logs')
            return count
    
    @staticmethod
    async def get_activity_logs(limit: int = 15, offset: int = 0):
        """Get activity logs with user information (paginated)"""
        async with db.pool.acquire() as conn:
            logs = await conn.fetch('''
                SELECT 
                    al.id,
                    al.user_id,
                    al.slash_command_used,
                    al.created_at,
                    u.name as user_name,
                    u.discord_id as user_discord_id,
                    u.department as user_department,
                    u.role_id as user_role_id
                FROM activity_logs al
                LEFT JOIN users u ON al.user_id = u.user_id
                ORDER BY al.created_at DESC
                LIMIT $1 OFFSET $2
            ''', limit, offset)
            return logs
    
    @staticmethod
    async def get_activity_logs_by_user(user_id: int, limit: int = 15, offset: int = 0):
        """Get activity logs for a specific user (paginated)"""
        async with db.pool.acquire() as conn:
            logs = await conn.fetch('''
                SELECT 
                    al.id,
                    al.user_id,
                    al.slash_command_used,
                    al.created_at,
                    u.name as user_name,
                    u.discord_id as user_discord_id,
                    u.department as user_department,
                    u.role_id as user_role_id
                FROM activity_logs al
                LEFT JOIN users u ON al.user_id = u.user_id
                WHERE al.user_id = $1
                ORDER BY al.created_at DESC
                LIMIT $2 OFFSET $3
            ''', user_id, limit, offset)
            return logs
    
    @staticmethod
    async def get_activity_logs_count_by_user(user_id: int):
        """Get total count of activity logs for a specific user"""
        async with db.pool.acquire() as conn:
            count = await conn.fetchval(
                'SELECT COUNT(*) FROM activity_logs WHERE user_id = $1', 
                user_id
            )
            return count
    
    # @staticmethod
    # async def get_recent_activity(user_id: int, limit: int = 10):
    #     """Get recent activity for a user (no pagination)"""
    #     async with db.pool.acquire() as conn:
    #         logs = await conn.fetch('''
    #             SELECT 
    #                 id,
    #                 slash_command_used,
    #                 created_at
    #             FROM activity_logs
    #             WHERE user_id = $1
    #             ORDER BY created_at DESC
    #             LIMIT $2
    #         ''', user_id, limit)
    #         return logs

