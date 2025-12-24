from utils.database import db
from datetime import datetime
from typing import List, Optional, Dict, Any

class WorkUpdateModel:
    """Database operations for work_updates table"""
    
    @staticmethod
    async def create_work_update(
        user_id: int,
        time_tracking_id: int,
        tasks: List[str],
        desklog_on: bool = False,
        trackabi_on: bool = False
    ) -> int:
        """Record daily work plan"""
        async with db.pool.acquire() as conn:
            update_id = await conn.fetchval('''
                INSERT INTO work_updates (
                    user_id, time_tracking_id, start_of_the_day_plan,
                    desklog_on, trackabi_on
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            ''', user_id, time_tracking_id, tasks, desklog_on, trackabi_on)
            return update_id
    
    @staticmethod
    async def get_today_plan(user_id: int, time_tracking_id: int) -> Optional[Dict[str, Any]]:
        """Get today's work plan for a user"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, start_of_the_day_plan, desklog_on, trackabi_on, created_at
                FROM work_updates
                WHERE user_id = $1 AND time_tracking_id = $2
                ORDER BY created_at DESC
                LIMIT 1
            ''', user_id, time_tracking_id)
            return dict(row) if row else None
    
    @staticmethod
    async def update_work_update(
        update_id: int,
        tasks: List[str] = None,
        desklog_on: bool = None,
        trackabi_on: bool = None,
        admin_approval: bool = None
    ) -> bool:
        """Update work plan"""
        async with db.pool.acquire() as conn:
            # Build dynamic update query
            updates = []
            params = []
            param_counter = 1
            
            if tasks is not None:
                updates.append(f"start_of_the_day_plan = ${param_counter}")
                params.append(tasks)
                param_counter += 1
            
            if desklog_on is not None:
                updates.append(f"desklog_on = ${param_counter}")
                params.append(desklog_on)
                param_counter += 1
            
            if trackabi_on is not None:
                updates.append(f"trackabi_on = ${param_counter}")
                params.append(trackabi_on)
                param_counter += 1
            
            if admin_approval is not None:
                updates.append(f"admin_approval = ${param_counter}")
                params.append(admin_approval)
                param_counter += 1
            
            if not updates:
                return False
            
            params.append(update_id)
            
            query = f'''
                UPDATE work_updates
                SET {', '.join(updates)}
                WHERE id = ${param_counter}
            '''
            
            await conn.execute(query, *params)
            return True
    
    @staticmethod
    async def get_work_updates_by_date(date: datetime.date) -> List[Dict[str, Any]]:
        """Get all work updates for a specific date"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT wu.*, u.name, u.discord_id, tt.present_date
                FROM work_updates wu
                JOIN time_tracking tt ON wu.time_tracking_id = tt.id
                JOIN users u ON wu.user_id = u.user_id
                WHERE tt.present_date = $1
                ORDER BY wu.created_at DESC
            ''', date)
            return [dict(row) for row in rows]
    
    @staticmethod
    async def get_user_work_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's work plan history"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT wu.*, tt.present_date
                FROM work_updates wu
                JOIN time_tracking tt ON wu.time_tracking_id = tt.id
                WHERE wu.user_id = $1
                ORDER BY tt.present_date DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]