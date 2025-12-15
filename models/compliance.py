from utils.database import db
from datetime import datetime
from typing import Optional, List, Dict, Any

class ComplianceModel:
    """Database operations for daily_compliance table"""
    
    @staticmethod
    async def create_compliance_record(
        user_id: int,
        desklog_usage: bool,
        desklog_reason: Optional[str],
        trackabi_usage: bool,
        trackabi_reason: Optional[str],
        discord_usage: bool,
        discord_reason: Optional[str],
        break_usage: bool,
        break_reason: Optional[str],
        google_drive_usage: bool,
        google_drive_reason: Optional[str],
        recorded_by_discord_id: int
    ) -> int:
        """Create a new compliance record and return compliance_id"""
        async with db.pool.acquire() as conn:
            compliance_id = await conn.fetchval('''
                INSERT INTO daily_compliance (
                    user_id, 
                    desklog_usage, desklog_reason,
                    trackabi_usage, trackabi_reason,
                    discord_usage, discord_reason,
                    break_usage, break_reason,
                    google_drive_usage, google_drive_reason,
                    recorded_by_discord_id
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING compliance_id
            ''', user_id, desklog_usage, desklog_reason, trackabi_usage, trackabi_reason,
                discord_usage, discord_reason, break_usage, break_reason,
                google_drive_usage, google_drive_reason, recorded_by_discord_id)
            return compliance_id
    
    @staticmethod
    async def get_user_compliance_history(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get compliance history for a specific user"""
        async with db.pool.acquire() as conn:
            rows = await conn.fetch('''
                SELECT 
                    compliance_id,
                    desklog_usage, desklog_reason,
                    trackabi_usage, trackabi_reason,
                    discord_usage, discord_reason,
                    break_usage, break_reason,
                    google_drive_usage, google_drive_reason,
                    recorded_at
                FROM daily_compliance
                WHERE user_id = $1
                ORDER BY recorded_at DESC
                LIMIT $2
            ''', user_id, limit)
            return [dict(row) for row in rows]