from utils.database import db
from datetime import datetime
from typing import Optional, List, Dict, Any

class TimeTrackingModel:
    """Database operations for time_tracking table"""
    
    @staticmethod
    async def create_time_tracking(
        user_id: int,
        starting_time: datetime,
        present_date: datetime.date,
        clock_in_time: datetime,
        reason: str,
        screen_share_verified: bool = False
    ) -> int:
        """Create a new time tracking record for the day"""
        async with db.pool.acquire() as conn:
            tracking_id = await conn.fetchval('''
                INSERT INTO time_tracking (
                    user_id, starting_time, present_date, 
                    clock_in, clockin_reason, time_logged_in, break_duration, screen_share_verified
                )
                VALUES ($1, $2, $3, $4, $5, 0, 0,$6)
                RETURNING id
            ''', user_id, starting_time, present_date, [clock_in_time], [reason],screen_share_verified)
            return tracking_id
    
    @staticmethod
    async def get_today_tracking(user_id: int, present_date: datetime.date) -> Optional[Dict[str, Any]]:
        """Get today's time tracking record for a user"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT id, clock_in, clock_out, starting_time, end_of_the_day, 
                       break_duration, time_logged_in, break_counter, screen_share_verified
                FROM time_tracking
                WHERE user_id = $1 AND present_date = $2
                ORDER BY created_at DESC
                LIMIT 1
            ''', user_id, present_date)
            return dict(row) if row else None

    @staticmethod
    async def update_screen_share_verified(tracking_id: int, verified: bool = True):
        """Update screen share verification status"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE time_tracking
                SET screen_share_verified = $1
                WHERE id = $2
            ''', verified, tracking_id)
    
    @staticmethod
    async def add_clock_in(tracking_id: int, clock_in_time: datetime, reason: str, break_duration: int = None):
        """Add a new clock-in time to existing record"""
        async with db.pool.acquire() as conn:
            if break_duration is not None:
                await conn.execute('''
                    UPDATE time_tracking
                    SET clock_in = array_append(clock_in, $1),
                        clockin_reason = array_append(COALESCE(clockin_reason, ARRAY[]::TEXT[]), $2),
                        break_duration = $3
                    WHERE id = $4
                ''', clock_in_time, reason, break_duration, tracking_id)
            else:
                await conn.execute('''
                    UPDATE time_tracking
                    SET clock_in = array_append(clock_in, $1),
                        clockin_reason = array_append(COALESCE(clockin_reason, ARRAY[]::TEXT[]), $2)
                    WHERE id = $3
                ''', clock_in_time, reason, tracking_id)
    
    @staticmethod
    async def add_clock_out(tracking_id: int, clock_out_time: datetime, reason: str, time_logged: int):
        """Add a new clock-out time to existing record"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE time_tracking
                SET clock_out = array_append(COALESCE(clock_out, ARRAY[]::TIMESTAMP[]), $1),
                    clockout_reason = array_append(COALESCE(clockout_reason, ARRAY[]::TEXT[]), $2),
                    time_logged_in = $3
                WHERE id = $4
            ''', clock_out_time, reason, time_logged, tracking_id)
    
    @staticmethod
    async def increment_break_counter(tracking_id: int):
        """Increment break counter when clocking out (not end of day)"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE time_tracking
                SET break_counter = COALESCE(break_counter, 0) + 1
                WHERE id = $1
            ''', tracking_id)
    
    @staticmethod
    async def end_day(tracking_id: int, end_time: datetime):
        """Mark the end of the workday"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE time_tracking
                SET end_of_the_day = $1
                WHERE id = $2
            ''', end_time, tracking_id)
    
    @staticmethod
    async def get_all_clocked_in_today(present_date: datetime.date) -> List[Dict[str, Any]]:
        """Get all users currently clocked in (not clocked out yet)"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT u.name, u.discord_id, tt.starting_time, 
                       tt.clock_in[ARRAY_LENGTH(tt.clock_in, 1)] as last_clock_in,
                       tt.time_logged_in, tt.break_counter, tt.screen_share_verified
                FROM time_tracking tt
                JOIN users u ON tt.user_id = u.user_id
                WHERE tt.present_date = $1
                    AND tt.end_of_the_day IS NULL
                    AND ARRAY_LENGTH(tt.clock_in, 1) > COALESCE(ARRAY_LENGTH(tt.clock_out, 1), 0)
                ORDER BY tt.starting_time
            ''', present_date)
            return [dict(row) for row in rows]

    @staticmethod
    async def get_user_time_logs(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        """Get user's time tracking history"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT * FROM time_tracking
                WHERE user_id = $1
                ORDER BY present_date DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]
    
    @staticmethod
    async def get_tracking_by_id(tracking_id: int) -> Optional[Dict[str, Any]]:
        """Get time tracking by ID"""
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow('''
                SELECT * FROM time_tracking
                WHERE id = $1
            ''', tracking_id)
            return dict(row) if row else None






        