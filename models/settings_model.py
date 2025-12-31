from utils.database import db
from datetime import datetime
from typing import Optional, Dict


class SettingsModel:
    @staticmethod
    async def get_sick_leave_settings() -> Dict[str, int]:
        async with db.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name, int_value FROM settings WHERE name IN ($1, $2, $3)",
                'sick_leave_anchor_hour', 'sick_leave_early_hours', 'sick_leave_late_hours'
            )
            data = {row['name']: row['int_value'] for row in rows}
            return {
                'anchor_hour': data.get('sick_leave_anchor_hour'),
                'early_hours': data.get('sick_leave_early_hours'),
                'late_hours': data.get('sick_leave_late_hours'),
            }

    @staticmethod
    async def update_sick_leave_settings(anchor_hour: int, early_hours: int, late_hours: int) -> bool:
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("""
                    INSERT INTO settings (name, int_value, updated_at)
                    VALUES ('sick_leave_anchor_hour', $1, TIMEZONE('utc', CURRENT_TIMESTAMP))
                    ON CONFLICT (name) DO UPDATE SET int_value = EXCLUDED.int_value, updated_at = EXCLUDED.updated_at
                """, anchor_hour)
                await conn.execute("""
                    INSERT INTO settings (name, int_value, updated_at)
                    VALUES ('sick_leave_early_hours', $1, TIMEZONE('utc', CURRENT_TIMESTAMP))
                    ON CONFLICT (name) DO UPDATE SET int_value = EXCLUDED.int_value, updated_at = EXCLUDED.updated_at
                """, early_hours)
                await conn.execute("""
                    INSERT INTO settings (name, int_value, updated_at)
                    VALUES ('sick_leave_late_hours', $1, TIMEZONE('utc', CURRENT_TIMESTAMP))
                    ON CONFLICT (name) DO UPDATE SET int_value = EXCLUDED.int_value, updated_at = EXCLUDED.updated_at
                """, late_hours)
                return True
