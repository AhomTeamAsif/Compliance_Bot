from utils.database import db
from datetime import datetime

class UserModel:
    """Database operations for users table"""
    
    @staticmethod
    async def user_registration(discord_id: int, name: str, department: str = None, 
                               position: str = None, trackabi_id: str = None, 
                               desklog_id: str = None, role_id: int = None, 
                               pending_leaves: int = None, contract_started_at: datetime = None,
                               permission_ids: list = None,granted_by:int= None):
        """Register a new user with all details and permissions"""
        async with db.pool.acquire() as conn:
            async with conn.transaction():
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
                
                # Insert permissions if provided
                if permission_ids:
                    for perm_id in permission_ids:
                        await conn.execute('''
                            INSERT INTO user_permissions (user_id, permission_id, granted_by)
                            VALUES ($1, $2, $3)
                            ON CONFLICT (user_id, permission_id) DO NOTHING
                        ''', user_id, perm_id, granted_by)
                
                return user_id
    
    @staticmethod
    async def user_removal(discord_id: int, deleted_by_user_id: int, reason: str = None,
                        seniors_informed: bool = False, admins_informed: bool = False, 
                        is_with_us: bool = False):
        """Soft delete a user and log the deletion"""
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                # Get user_id before soft delete
                user = await conn.fetchrow(
                    'SELECT user_id FROM users WHERE discord_id = $1 AND is_deleted = FALSE', 
                    discord_id
                )
                
                if not user:
                    return False
                
                # Soft delete user
                await conn.execute('''
                    UPDATE users 
                    SET is_deleted = TRUE, updated_at = TIMEZONE('utc', CURRENT_TIMESTAMP)
                    WHERE discord_id = $1
                ''', discord_id)
                
                # Log deletion with additional data
                await conn.execute('''
                    INSERT INTO user_delete_logs (deleted_user_id, deleted_by_user_id, reason, 
                                                seniors_informed, admins_informed, is_with_us)
                    VALUES ($1, $2, $3, $4, $5, $6)
                ''', user['user_id'], deleted_by_user_id, reason, seniors_informed, 
                    admins_informed, is_with_us)
                
                return True
    
    @staticmethod
    async def user_info_update(discord_id: int, permission_ids: list = None, granted_by:int = None, **kwargs):
        """Update user information and permissions"""
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                set_clauses = []
                values = []
                param_count = 1
                
                for key, value in kwargs.items():
                    if value is not None and key in ['name', 'department', 'position', 'trackabi_id', 'desklog_id', 'role_id', 'pending_leaves']:
                        set_clauses.append(f"{key} = ${param_count}")
                        values.append(value)
                        param_count += 1
                
                if set_clauses:
                    values.append(discord_id)
                    query = f'''
                        UPDATE users 
                        SET {', '.join(set_clauses)}, updated_at = TIMEZONE('utc', CURRENT_TIMESTAMP)
                        WHERE discord_id = ${param_count}
                    '''
                    await conn.execute(query, *values)
                
                # Update permissions if provided
                if permission_ids is not None:
                    user = await conn.fetchrow(
                        'SELECT user_id FROM users WHERE discord_id = $1', discord_id
                    )
                    
                    if user:
                        # Remove existing permissions
                        await conn.execute(
                            'DELETE FROM user_permissions WHERE user_id = $1', 
                            user['user_id']
                        )
                        
                        # Insert new permissions
                        for perm_id in permission_ids:
                            await conn.execute('''
                                INSERT INTO user_permissions (user_id, permission_id, granted_by)
                                VALUES ($1, $2, $3)
                            ''', user['user_id'], perm_id, granted_by)
                
                return True
    
    @staticmethod
    async def get_user_by_discord_id(discord_id: int, include_deleted: bool = False):
        """Get user by Discord ID"""
        async with db.pool.acquire() as conn:
            if include_deleted:
                user = await conn.fetchrow(
                    'SELECT * FROM users WHERE discord_id = $1', discord_id
                )
            else:
                user = await conn.fetchrow(
                    'SELECT * FROM users WHERE discord_id = $1 AND is_deleted = FALSE', discord_id
                )
            return user
    
    @staticmethod
    async def user_exists(discord_id: int, include_deleted: bool = False):
        """Check if user exists"""
        async with db.pool.acquire() as conn:
            if include_deleted:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM users WHERE discord_id = $1)', discord_id
                )
            else:
                result = await conn.fetchval(
                    'SELECT EXISTS(SELECT 1 FROM users WHERE discord_id = $1 AND is_deleted = FALSE)', discord_id
                )
            return result
    
    @staticmethod
    async def get_all_users(include_deleted: bool = False):
        """Get all users"""
        async with db.pool.acquire() as conn:
            if include_deleted:
                users = await conn.fetch('SELECT * FROM users ORDER BY created_at DESC')
            else:
                users = await conn.fetch(
                    'SELECT * FROM users WHERE is_deleted = FALSE ORDER BY created_at DESC'
                )
            return users
    
    @staticmethod
    async def get_users_by_department(department: str, include_deleted: bool = False):
        """Get users by department"""
        async with db.pool.acquire() as conn:
            if include_deleted:
                users = await conn.fetch(
                    'SELECT * FROM users WHERE department = $1', department
                )
            else:
                users = await conn.fetch(
                    'SELECT * FROM users WHERE department = $1 AND is_deleted = FALSE', department
                )
            return users
    
    @staticmethod
    async def get_users_by_role(role_id: int, include_deleted: bool = False):
        """Get users by role"""
        async with db.pool.acquire() as conn:
            if include_deleted:
                users = await conn.fetch(
                    'SELECT * FROM users WHERE role_id = $1', role_id
                )
            else:
                users = await conn.fetch(
                    'SELECT * FROM users WHERE role_id = $1 AND is_deleted = FALSE', role_id
                )
            return users


    @staticmethod
    async def restore_user(discord_id: int):
        """Restore a soft-deleted user"""
        async with db.pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE users 
                SET is_deleted = FALSE, updated_at = TIMEZONE('utc', CURRENT_TIMESTAMP)
                WHERE discord_id = $1 AND is_deleted = TRUE
            ''', discord_id)
            
            return result != "UPDATE 0"