from utils.database import db
from datetime import datetime

class UserModel:
    """Database operations for users table"""
    
    @staticmethod
    async def user_registration(discord_id: int, name: str, department: str = None, 
                               position: str = None, trackabi_id: str = None, 
                               desklog_id: str = None, role_id: int = None,pending_leaves: int = None,contract_started_at: datetime = None):
        """Register a new user with all details"""
        async with db.pool.acquire() as conn:
            # Check if user already exists
            existing = await conn.fetchrow(
                'SELECT user_id FROM users WHERE discord_id = $1', discord_id
            )
            
            if existing:
                raise ValueError("User already registered")
            
            user_id = await conn.fetchval('''
                INSERT INTO users (discord_id, name, department, position, trackabi_id, 
                                  desklog_id, role_id, pending_leaves, contract_started_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING user_id
            ''', discord_id, name, department, position, trackabi_id, desklog_id, 
                 role_id, pending_leaves, contract_started_at)  
            
            return user_id
    
    @staticmethod
    async def user_removal(discord_id: int):
        """Remove a user from database"""
        async with db.pool.acquire() as conn:
            result = await conn.execute(
                'DELETE FROM users WHERE discord_id = $1', discord_id
            )
            
            if result == "DELETE 0":
                return False
            return True
    
    @staticmethod
    async def user_info_update(discord_id: int, **kwargs):
        """Update user information"""
        async with db.pool.acquire() as conn:
            # Build dynamic UPDATE query
            set_clauses = []
            values = []
            param_count = 1
            
            for key, value in kwargs.items():
                if value is not None and key in ['name', 'department', 'position', 'trackabi_id', 'desklog_id', 'role_id']:
                    set_clauses.append(f"{key} = ${param_count}")
                    values.append(value)
                    param_count += 1
            
            if not set_clauses:
                return False
            
            values.append(discord_id)
            query = f'''
                UPDATE users 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ${param_count}
            '''
            
            result = await conn.execute(query, *values)
            return result != "UPDATE 0"
    
    @staticmethod
    async def get_user_by_discord_id(discord_id: int):
        """Get user by Discord ID"""
        async with db.pool.acquire() as conn:
            user = await conn.fetchrow(
                'SELECT * FROM users WHERE discord_id = $1', discord_id
            )
            return user
    
    @staticmethod
    async def user_exists(discord_id: int):
        """Check if user exists"""
        async with db.pool.acquire() as conn:
            result = await conn.fetchval(
                'SELECT EXISTS(SELECT 1 FROM users WHERE discord_id = $1)', discord_id
            )
            return result
    
    @staticmethod
    async def get_all_users():
        """Get all users"""
        async with db.pool.acquire() as conn:
            users = await conn.fetch('SELECT * FROM users ORDER BY created_at DESC')
            return users
    
    @staticmethod
    async def get_users_by_department(department: str):
        """Get users by department"""
        async with db.pool.acquire() as conn:
            users = await conn.fetch(
                'SELECT * FROM users WHERE department = $1', department
            )
            return users
    
    @staticmethod
    async def get_users_by_role(role_id: int):
        """Get users by role"""
        async with db.pool.acquire() as conn:
            users = await conn.fetch(
                'SELECT * FROM users WHERE role_id = $1', role_id
            )
            return users