from utils.database import db
from datetime import datetime

class ScreenShareModel:
    """Database operations for screen_share_sessions table"""
    
    @staticmethod
    async def start_session(user_id: int, reason: str = None):
        """Start a new screen share session"""
        async with db.pool.acquire() as conn:
            session_id = await conn.fetchval('''
                INSERT INTO screen_share_sessions 
                (user_id, screen_share_on_time, screen_share_on_reason, is_screen_shared)
                VALUES ($1, $2, $3, TRUE)
                RETURNING session_id
            ''', user_id, datetime.now(), reason)
            return session_id
    
    @staticmethod
    async def end_session(user_id: int, reason: str = None):
        """End the active screen share session for a user"""
        async with db.pool.acquire() as conn:
            # Get the active session
            session = await conn.fetchrow('''
                SELECT session_id, screen_share_on_time 
                FROM screen_share_sessions
                WHERE user_id = $1 
                AND screen_share_off_time IS NULL
                ORDER BY screen_share_on_time DESC
                LIMIT 1
            ''', user_id)
            
            if not session:
                return None
            
            # Calculate duration
            off_time = datetime.now()
            duration = int((off_time - session['screen_share_on_time']).total_seconds() / 60)
            
            # Update the session
            await conn.execute('''
                UPDATE screen_share_sessions
                SET screen_share_off_time = $1,
                    screen_share_off_reason = $2,
                    duration_minutes = $3,
                    is_screen_shared = FALSE
                WHERE session_id = $4
            ''', off_time, reason, duration, session['session_id'])
            
            return session['session_id']
    
    @staticmethod
    async def get_active_session(user_id: int):
        """Get user's active screen share session"""
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow('''
                SELECT * FROM screen_share_sessions
                WHERE user_id = $1 
                AND screen_share_off_time IS NULL
                ORDER BY screen_share_on_time DESC
                LIMIT 1
            ''', user_id)
            return session
    
    @staticmethod
    async def get_all_active_sessions():
        """Get all active screen share sessions"""
        async with db.pool.acquire() as conn:
            sessions = await conn.fetch('''
                SELECT s.*, u.name, u.discord_id
                FROM screen_share_sessions s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.screen_share_off_time IS NULL
                ORDER BY s.screen_share_on_time DESC
            ''')
            return sessions
    
    @staticmethod
    async def update_screen_frozen(session_id: int, is_frozen: bool, frozen_duration: int = 0):
        """Update screen frozen status"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE screen_share_sessions
                SET is_screen_frozen = $1,
                    screen_frozen_duration_minutes = screen_frozen_duration_minutes + $2
                WHERE session_id = $3
            ''', is_frozen, frozen_duration, session_id)
    
    @staticmethod
    async def update_not_shared_duration(session_id: int, duration: int):
        """Update not shared duration"""
        async with db.pool.acquire() as conn:
            await conn.execute('''
                UPDATE screen_share_sessions
                SET not_shared_duration_minutes = not_shared_duration_minutes + $1
                WHERE session_id = $2
            ''', duration, session_id)
    
    @staticmethod
    async def get_user_history(user_id: int, limit: int = 10):
        """Get user's screen share history"""
        async with db.pool.acquire() as conn:
            sessions = await conn.fetch('''
                SELECT * FROM screen_share_sessions
                WHERE user_id = $1
                ORDER BY screen_share_on_time DESC
                LIMIT $2
            ''', user_id, limit)
            return sessions
    
    @staticmethod
    async def get_session_by_id(session_id: int):
        """Get session by ID"""
        async with db.pool.acquire() as conn:
            session = await conn.fetchrow('''
                SELECT * FROM screen_share_sessions
                WHERE session_id = $1
            ''', session_id)
            return session