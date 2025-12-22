from utils.database import db
from datetime import datetime
import json

class UserModel:
    """Database operations for users table"""
    
    @staticmethod
    async def user_registration(discord_id: int, name: str, department: str = None, 
                               position: str = None, trackabi_id: str = None, 
                               desklog_id: str = None, role_id: int = None, 
                               pending_leaves: int = None, contract_started_at: datetime = None,
                               permission_ids: list = None,granted_by:int= None,registered_by: int = None):
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
                                      desklog_id, role_id, pending_leaves, contract_started_at, registered_by)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING user_id
                ''', discord_id, name, department, position, trackabi_id, desklog_id, 
                     role_id, pending_leaves, contract_started_at, registered_by)
                
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
    async def user_info_update(discord_id: int, updated_by_user_id: int, permission_ids: list = None, granted_by: int = None, **kwargs):
        """Update user information and permissions with logging"""
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                # Get current user data for comparison
                user = await conn.fetchrow('SELECT * FROM users WHERE discord_id = $1', discord_id)
                
                if not user:
                    return False
                
                # Track changes
                fields_updated = []
                old_values = {}
                new_values = {}
                
                # Build update query and track changes
                set_clauses = []
                values = []
                param_count = 1
                
                for key, value in kwargs.items():
                    if value is not None and key in ['name', 'department', 'position', 'trackabi_id', 'desklog_id', 'role_id', 'pending_leaves']:
                        # Check if value actually changed
                        if user[key] != value:
                            fields_updated.append(key)
                            old_values[key] = user[key]
                            new_values[key] = value
                            
                            set_clauses.append(f"{key} = ${param_count}")
                            values.append(value)
                            param_count += 1
                
                # Update basic info if there are changes
                if set_clauses:
                    values.append(discord_id)
                    query = f'''
                        UPDATE users 
                        SET {', '.join(set_clauses)}, updated_at = TIMEZONE('utc', CURRENT_TIMESTAMP)
                        WHERE discord_id = ${param_count}
                    '''
                    await conn.execute(query, *values)
                
                # Handle permission updates
                permissions_added = []
                permissions_removed = []
                
                if permission_ids is not None:
                    # Get current permissions
                    current_perms = await conn.fetch(
                        'SELECT permission_id FROM user_permissions WHERE user_id = $1',
                        user['user_id']
                    )
                    current_perm_ids = set(p['permission_id'] for p in current_perms)
                    new_perm_ids = set(permission_ids)
                    
                    # Calculate differences
                    permissions_added = list(new_perm_ids - current_perm_ids)
                    permissions_removed = list(current_perm_ids - new_perm_ids)
                    
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
                
                # Log the update if there were any changes
                if fields_updated or permissions_added or permissions_removed:
                    # Determine update type
                    update_type = 'info_update'
                    if permissions_added or permissions_removed:
                        update_type = 'permission_update' if not fields_updated else 'full_update'
                    
                    # Generate change summary
                    summary_parts = []
                    if fields_updated:
                        summary_parts.append(f"Updated: {', '.join(fields_updated)}")
                    if permissions_added:
                        summary_parts.append(f"Added {len(permissions_added)} permission(s)")
                    if permissions_removed:
                        summary_parts.append(f"Removed {len(permissions_removed)} permission(s)")
                    change_summary = "; ".join(summary_parts)
                    
                    # Insert update log
                    await conn.execute('''
                        INSERT INTO user_update_logs 
                        (updated_user_id, updated_by_user_id, fields_updated, old_values, new_values,
                        permissions_added, permissions_removed, update_type, change_summary)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ''', user['user_id'], updated_by_user_id, fields_updated, 
                        json.dumps(old_values), json.dumps(new_values),
                        permissions_added, permissions_removed, update_type, change_summary)
                
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

    @staticmethod
    async def get_delete_logs_count():
        """Get total count of delete logs"""
        async with db.pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM user_delete_logs')
            return count

    @staticmethod
    async def get_delete_logs(limit: int = 15, offset: int = 0):
        """Get user deletion logs with user information (paginated)"""
        async with db.pool.acquire() as conn:
            logs = await conn.fetch('''
                SELECT 
                    udl.id,
                    udl.deleted_user_id,
                    du.name as deleted_user_name,
                    du.discord_id as deleted_user_discord_id,
                    du.department as deleted_user_department,
                    udl.deleted_by_user_id,
                    dbu.name as deleted_by_name,
                    dbu.discord_id as deleted_by_discord_id,
                    udl.reason,
                    udl.seniors_informed,
                    udl.admins_informed,
                    udl.is_with_us,
                    udl.deleted_at
                FROM user_delete_logs udl
                LEFT JOIN users du ON udl.deleted_user_id = du.user_id
                LEFT JOIN users dbu ON udl.deleted_by_user_id = dbu.user_id
                ORDER BY udl.deleted_at DESC
                LIMIT $1 OFFSET $2
            ''', limit, offset)
            return logs

    @staticmethod


    @staticmethod
    async def get_update_logs_count():
        """Get total count of update logs"""
        async with db.pool.acquire() as conn:
            count = await conn.fetchval('SELECT COUNT(*) FROM user_update_logs')
            return count

    @staticmethod
    async def get_update_logs(limit: int = 15, offset: int = 0):
        """Get user update logs with user information (paginated)"""
        async with db.pool.acquire() as conn:
            logs = await conn.fetch('''
                SELECT 
                    uul.id,
                    uul.updated_user_id,
                    uu.name as updated_user_name,
                    uu.discord_id as updated_user_discord_id,
                    uu.department as updated_user_department,
                    uul.updated_by_user_id,
                    ubu.name as updated_by_name,
                    ubu.discord_id as updated_by_discord_id,
                    uul.fields_updated,
                    uul.old_values,
                    uul.new_values,
                    uul.permissions_added,
                    uul.permissions_removed,
                    uul.update_type,
                    uul.change_summary,
                    uul.updated_at
                FROM user_update_logs uul
                LEFT JOIN users uu ON uul.updated_user_id = uu.user_id
                LEFT JOIN users ubu ON uul.updated_by_user_id = ubu.user_id
                ORDER BY uul.updated_at DESC
                LIMIT $1 OFFSET $2
            ''', limit, offset)
            return logs

    @staticmethod
    async def get_update_logs_by_user(user_id: int, limit: int = 15, offset: int = 0):
        """Get update logs for a specific user (paginated)"""
        async with db.pool.acquire() as conn:
            logs = await conn.fetch('''
                SELECT 
                    uul.id,
                    uul.updated_user_id,
                    uu.name as updated_user_name,
                    uu.discord_id as updated_user_discord_id,
                    uu.department as updated_user_department,
                    uul.updated_by_user_id,
                    ubu.name as updated_by_name,
                    ubu.discord_id as updated_by_discord_id,
                    uul.fields_updated,
                    uul.old_values,
                    uul.new_values,
                    uul.permissions_added,
                    uul.permissions_removed,
                    uul.update_type,
                    uul.change_summary,
                    uul.updated_at
                FROM user_update_logs uul
                LEFT JOIN users uu ON uul.updated_user_id = uu.user_id
                LEFT JOIN users ubu ON uul.updated_by_user_id = ubu.user_id
                WHERE uul.updated_user_id = $1
                ORDER BY uul.updated_at DESC
                LIMIT $2 OFFSET $3
            ''', user_id, limit, offset)
            return logs

    @staticmethod
    async def get_update_logs_count_by_user(user_id: int):
        """Get total count of update logs for a specific user"""
        async with db.pool.acquire() as conn:
            count = await conn.fetchval(
                'SELECT COUNT(*) FROM user_update_logs WHERE updated_user_id = $1',
                user_id
            )
            return count