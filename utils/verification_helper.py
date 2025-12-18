from utils.database import db

# #TEST
# async def check_user_permission(discord_id: int, permission_name: str):
#     return True

async def check_user_permission(discord_id: int, permission_name: str):
    """Check if user has admin/super role first, then check specific permission"""
    async with db.pool.acquire() as conn:
        # First check if user is ADMIN or SUPER
        user_role = await conn.fetchval('''
            SELECT role_id FROM users 
            WHERE discord_id = $1 AND is_deleted = FALSE
        ''', discord_id)
        
        # If not ADMIN (2) or SUPER (1), deny
        if user_role not in [1, 2]:
            return False
        
        # If SUPER (has administer permission), allow everything
        has_administer = await conn.fetchval('''
            SELECT EXISTS(
                SELECT 1 FROM users u
                JOIN user_permissions up ON u.user_id = up.user_id
                JOIN permissions p ON up.permission_id = p.permission_id
                WHERE u.discord_id = $1 AND p.permission_name = 'administer'
            )
        ''', discord_id)

        
        if has_administer:
            return True
        
        # For ADMIN, check specific permission
        has_permission = await conn.fetchval('''
            SELECT EXISTS(
                SELECT 1 FROM users u
                JOIN user_permissions up ON u.user_id = up.user_id
                JOIN permissions p ON up.permission_id = p.permission_id
                WHERE u.discord_id = $1 AND p.permission_name = $2
            )
        ''', discord_id, permission_name)
        
        return has_permission


async def get_all_permissions():
    """Get all permissions except 'administer'"""
    async with db.pool.acquire() as conn:
        permissions = await conn.fetch(
            "SELECT permission_id, permission_name, description FROM permissions WHERE permission_name != 'administer' ORDER BY permission_name"
        )
        return permissions


async def get_user_permissions(user_id: int):
    """Get user's permission IDs"""
    async with db.pool.acquire() as conn:
        perms = await conn.fetch(
            "SELECT permission_id FROM user_permissions WHERE user_id = $1", user_id
        )
        return [p['permission_id'] for p in perms]

async def check_role_hierarchy(actor_discord_id: int, target_discord_id: int):
    """
    Check if actor has permission to modify target based on role hierarchy
    Returns: (can_modify: bool, message: str)
    """
    async with db.pool.acquire() as conn:
        # Get actor's role
        actor_role = await conn.fetchval('''
            SELECT role_id FROM users 
            WHERE discord_id = $1 AND is_deleted = FALSE
        ''', actor_discord_id)
        
        # Get target's role
        target_role = await conn.fetchval('''
            SELECT role_id FROM users 
            WHERE discord_id = $1 AND is_deleted = FALSE
        ''', target_discord_id)
        
        if actor_role is None:
            return False, "You are not registered in the system!"
        
        if target_role is None:
            return False, "Target user is not registered in the system!"
        
        # Role hierarchy: 1 (SUPER) > 2 (ADMIN) > 3 (NORMAL)
        # Lower number = higher privilege
        if actor_role > target_role:
            role_names = {1: "SUPER ADMIN", 2: "ADMIN", 3: "NORMAL"}
            return False, f"You cannot modify {role_names.get(target_role, 'this')} users!"
        
        return True, "Authorization successful"

async def is_super_admin(discord_id: int):
    """Check if user is SUPER ADMIN (role_id = 1)"""
    async with db.pool.acquire() as conn:
        role_id = await conn.fetchval('''
            SELECT role_id FROM users 
            WHERE discord_id = $1 AND is_deleted = FALSE
        ''', discord_id)
        return role_id == 1


async def is_admin(discord_id: int):
    """Check if user is ADMIN (role_id = 2)"""
    async with db.pool.acquire() as conn:
        role_id = await conn.fetchval('''
            SELECT role_id FROM users 
            WHERE discord_id = $1 AND is_deleted = FALSE
        ''', discord_id)
        return role_id == 2