import discord
from discord import app_commands
from discord.ext import commands
from models.user_model import UserModel
from datetime import datetime
from views.user_management_views import (
    RegisterUserSelectView, UpdateUserSelectView, DeleteUserSelectView,
    RestoreUserSelectView, ActiveAllUsersModal,DeleteLogsPaginationView
)
from utils.verification_helper import check_user_permission, is_super_admin, is_admin
from utils.database import db

class UserManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== REGISTER USER ====================
    @app_commands.command(name="user_register", description="Register a new user in the system")
    async def register_user(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        # Check permission
        has_permission = await check_user_permission(interaction.user.id, 'user_register')
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to register users!",
                ephemeral=True
            )
            return
        
        view = RegisterUserSelectView()
        
        embed = discord.Embed(
            title="👤 User Registration - Step 1/6",
            description="**Select a user** to register in the system:",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ==================== UPDATE USER ====================
    @app_commands.command(name="user_update", description="Update user information")
    async def update_user(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        # Check permission
        has_permission = await check_user_permission(interaction.user.id, 'user_update')
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to update users!",
                ephemeral=True
            )
            return
        
        view = UpdateUserSelectView()
        
        embed = discord.Embed(
            title="✏️ User Update - Step 1/5",
            description="**Select a user** to update:",
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ==================== DELETE USER ====================
    @app_commands.command(name="user_delete", description="Delete a user from the system")
    async def delete_user(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        # Check permission
        has_permission = await check_user_permission(interaction.user.id, 'user_delete')
        
        if not has_permission:
            await interaction.response.send_message(
                "❌ You don't have permission to delete users!",
                ephemeral=True
            )
            return
        
        # Get deleter's user_id
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        if not user:
            await interaction.response.send_message(
                "❌ User is not registered in the system!",
                ephemeral=True
            )
            return
        
        view = DeleteUserSelectView(user['user_id'])
        
        embed = discord.Embed(
            title="🗑️ User Deletion - Step 1/5",
            description="**Select a user** to delete from the system:",
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ==================== RESTORE USER ====================
    @app_commands.command(name="user_restore", description="Restore a deleted user (SUPER ADMIN ONLY)")
    async def restore_user(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check if super admin 
        has_super_role = await is_super_admin(interaction.user.id)
        
        if not has_super_role:
            await interaction.followup.send( 
                "❌ Only SUPER ADMIN can restore users!",
                ephemeral=True
            )
            return
        
        view = RestoreUserSelectView()
        
        embed = discord.Embed(
            title="♻️ User Restoration",
            description="**Select a user** to restore:",
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ==================== USER INFO ====================
    @app_commands.command(name="user_info", description="Get detailed information about a user")
    @app_commands.describe(user="The user to get information about")
    async def user_info(self, interaction: discord.Interaction, user: discord.User):
        # Check if super admin (role_id = 1)
        if await is_super_admin(interaction.user.id):
            # Show modal to ask active/all
            async def info_callback(inter, discord_id, include_deleted):
                user_data = await UserModel.get_user_by_discord_id(discord_id, include_deleted=include_deleted)
                
                if not user_data:
                    await inter.response.send_message(
                        f"❌ **{user.mention}** is not in the system!",
                        ephemeral=True
                    )
                    return
                
                # Get user permissions with granted_by info
                async with db.pool.acquire() as conn:
                    perms = await conn.fetch('''
                        SELECT p.permission_name, up.granted_by, u.name as granted_by_name
                        FROM user_permissions up
                        JOIN permissions p ON up.permission_id = p.permission_id
                        LEFT JOIN users u ON up.granted_by = u.user_id
                        WHERE up.user_id = $1
                    ''', user_data['user_id'])
                    
                    # Get registered_by info
                    registered_by_info = None
                    if user_data['registered_by']:
                        registered_by_info = await conn.fetchrow('''
                            SELECT name, discord_id FROM users WHERE user_id = $1
                        ''', user_data['registered_by'])
                    
                    # Get deleted_by info if user is deleted
                    deleted_by_info = None
                    if user_data['is_deleted']:
                        deleted_by_info = await conn.fetchrow('''
                            SELECT dbu.name, dbu.discord_id, udl.deleted_at
                            FROM user_delete_logs udl
                            LEFT JOIN users dbu ON udl.deleted_by_user_id = dbu.user_id
                            WHERE udl.deleted_user_id = $1
                            ORDER BY udl.deleted_at DESC
                            LIMIT 1
                        ''', user_data['user_id'])
                
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user_data['role_id'], "NORMAL")
                status = "🔴 Deleted" if user_data['is_deleted'] else "🟢 Active"
                
                embed = discord.Embed(
                    title=f"👤 User Information: {user_data['name']}",
                    color=discord.Color.red() if user_data['is_deleted'] else discord.Color.blue()
                )
                
                embed.add_field(name="Status", value=status, inline=True)
                embed.add_field(name="🆔 User ID", value=f"`{user_data['user_id']}`", inline=True)
                embed.add_field(name="👤 Discord", value=user.mention, inline=True)
                embed.add_field(name="🏢 Department", value=user_data['department'] or "N/A", inline=True)
                embed.add_field(name="💼 Position", value=user_data['position'] or "N/A", inline=True)
                embed.add_field(name="👑 Role", value=role_name, inline=True)
                embed.add_field(name="📊 Trackabi ID", value=f"`{user_data['trackabi_id']}`" if user_data['trackabi_id'] else "N/A", inline=True)
                embed.add_field(name="🖥️ Desklog ID", value=f"`{user_data['desklog_id']}`" if user_data['desklog_id'] else "N/A", inline=True)
                embed.add_field(name="🏖️ Pending Leaves", value=f"{user_data['pending_leaves']} days", inline=True)
                embed.add_field(name="🗓️ Contract Start", value=user_data['contract_started_at'].strftime('%d/%m/%Y') if user_data['contract_started_at'] else "N/A", inline=True)
                
                # Registered by info
                if registered_by_info:
                    registered_by_mention = f"<@{registered_by_info['discord_id']}>" if registered_by_info['discord_id'] else registered_by_info['name']
                    embed.add_field(name="📝 Registered By", value=registered_by_mention, inline=True)
                else:
                    embed.add_field(name="📝 Registered By", value="System", inline=True)
                
                # Registered at (created_at) - Exact UTC time
                embed.add_field(name="📅 Registered At", value=f"<t:{int(user_data['created_at'].timestamp())}:f>", inline=True)
                
                # Last updated - Exact UTC time
                embed.add_field(name="🔄 Last Updated", value=f"<t:{int(user_data['updated_at'].timestamp())}:f>", inline=True)
                
                # Deleted by info (only if user is deleted)
                if user_data['is_deleted'] and deleted_by_info:
                    deleted_by_mention = f"<@{deleted_by_info['discord_id']}>" if deleted_by_info['discord_id'] else (deleted_by_info['name'] or "Unknown")
                    deleted_at_timestamp = f"<t:{int(deleted_by_info['deleted_at'].timestamp())}:f>"
                    embed.add_field(name="🗑️ Deleted By", value=deleted_by_mention, inline=True)
                    embed.add_field(name="🗑️ Deleted At", value=deleted_at_timestamp, inline=True)
                
                # Permissions - Show single granted_by since we replace all permissions
                if perms:
                    perm_text = "\n".join([f"• {p['permission_name']}" for p in perms])
                    # Get the granted_by from first permission (all will be same since we replace)
                    granted_by_name = perms[0]['granted_by_name'] or 'System'
                    
                    embed.add_field(name="🔑 Permissions", value=perm_text, inline=True)
                    embed.add_field(name="👤 Granted By", value=granted_by_name, inline=True)
                else:
                    embed.add_field(name="🔑 Permissions", value="None", inline=False)
                
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text=f"All times shown in UTC • Requested by {inter.user.name}")
                
                await inter.response.send_message(embed=embed, ephemeral=True)
            
            modal = ActiveAllUsersModal(info_callback, user.id)
            await interaction.response.send_modal(modal)
        
        # Check if admin (role_id = 2)
        elif await is_admin(interaction.user.id):
            user_data = await UserModel.get_user_by_discord_id(user.id, include_deleted=False)
            
            if not user_data:
                await interaction.response.send_message(
                    f"❌ **{user.mention}** is not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get user permissions with granted_by info
            async with db.pool.acquire() as conn:
                perms = await conn.fetch('''
                    SELECT p.permission_name, up.granted_by, u.name as granted_by_name
                    FROM user_permissions up
                    JOIN permissions p ON up.permission_id = p.permission_id
                    LEFT JOIN users u ON up.granted_by = u.user_id
                    WHERE up.user_id = $1
                ''', user_data['user_id'])
                
                # Get registered_by info
                registered_by_info = None
                if user_data['registered_by']:
                    registered_by_info = await conn.fetchrow('''
                        SELECT name, discord_id FROM users WHERE user_id = $1
                    ''', user_data['registered_by'])
            
            role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user_data['role_id'], "NORMAL")
            
            embed = discord.Embed(
                title=f"👤 User Information: {user_data['name']}",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="🆔 User ID", value=f"`{user_data['user_id']}`", inline=True)
            embed.add_field(name="👤 Discord", value=user.mention, inline=True)
            embed.add_field(name="🏢 Department", value=user_data['department'] or "N/A", inline=True)
            embed.add_field(name="💼 Position", value=user_data['position'] or "N/A", inline=True)
            embed.add_field(name="👑 Role", value=role_name, inline=True)
            embed.add_field(name="📊 Trackabi ID", value=f"`{user_data['trackabi_id']}`" if user_data['trackabi_id'] else "N/A", inline=True)
            embed.add_field(name="🖥️ Desklog ID", value=f"`{user_data['desklog_id']}`" if user_data['desklog_id'] else "N/A", inline=True)
            embed.add_field(name="🏖️ Pending Leaves", value=f"{user_data['pending_leaves']} days", inline=True)
            embed.add_field(name="🗓️ Contract Start", value=user_data['contract_started_at'].strftime('%d/%m/%Y') if user_data['contract_started_at'] else "N/A", inline=True)
            
            # Registered by info
            if registered_by_info:
                registered_by_mention = f"<@{registered_by_info['discord_id']}>" if registered_by_info['discord_id'] else registered_by_info['name']
                embed.add_field(name="📝 Registered By", value=registered_by_mention, inline=True)
            else:
                embed.add_field(name="📝 Registered By", value="System", inline=True)
            
            # Registered at (created_at) - Exact UTC time
            embed.add_field(name="📅 Registered At", value=f"<t:{int(user_data['created_at'].timestamp())}:f>", inline=True)
            
            # Last updated - Exact UTC time
            embed.add_field(name="🔄 Last Updated", value=f"<t:{int(user_data['updated_at'].timestamp())}:f>", inline=True)
            
            # Permissions - Show single granted_by
            if perms:
                perm_text = "\n".join([f"• {p['permission_name']}" for p in perms])
                granted_by_name = perms[0]['granted_by_name'] or 'System'
                
                embed.add_field(name="🔑 Permissions", value=perm_text, inline=True)
                embed.add_field(name="👤 Granted By", value=granted_by_name, inline=True)
            else:
                embed.add_field(name="🔑 Permissions", value="None", inline=False)
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"All times shown in UTC • Requested by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            await interaction.response.send_message(
                "❌ You don't have permission to view user information!",
                ephemeral=True
            )


    # ==================== LIST ALL USERS ====================
    @app_commands.command(name="user_list", description="List all users in the system")
    async def user_list(self, interaction: discord.Interaction):
        # Check if super admin
        if await is_super_admin(interaction.user.id):
            # DON'T DEFER - Show modal immediately for super admin
            async def list_callback(inter, include_deleted):
                users = await UserModel.get_all_users(include_deleted=include_deleted)
                
                if not users:
                    await inter.response.send_message("❌ No users found in the system!", ephemeral=True)
                    return
                
                embed = discord.Embed(
                    title=f"📋 User List ({len(users)} users)",
                    description="All users in the system:",
                    color=discord.Color.blue()
                )
                
                for user in users[:25]:  # Discord embed field limit
                    role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user['role_id'], "NORMAL")
                    status = "🔴" if user['is_deleted'] else "🟢"
                    embed.add_field(
                        name=f"{status} {user['name']}",
                        value=f"ID: `{user['user_id']}` | Role: {role_name} | Dept: {user['department'] or 'N/A'}",
                        inline=False
                    )
                
                if len(users) > 25:
                    embed.set_footer(text=f"Showing 25 of {len(users)} users")
                
                await inter.response.send_message(embed=embed, ephemeral=True)
            
            modal = ActiveAllUsersModal(list_callback)
            await interaction.response.send_modal(modal)
        
        # Check if admin 
        elif await is_admin(interaction.user.id):
            # DEFER for regular admin (no modal needed)
            await interaction.response.defer(ephemeral=True)
            
            # Regular admin - only show active users
            users = await UserModel.get_all_users(include_deleted=False)
            
            if not users:
                await interaction.followup.send("❌ No users found in the system!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"📋 Active Users ({len(users)} users)",
                description="All active users in the system:",
                color=discord.Color.blue()
            )
            
            for user in users[:25]:  # Discord embed field limit
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user['role_id'], "NORMAL")
                embed.add_field(
                    name=f"🟢 {user['name']}",
                    value=f"ID: `{user['user_id']}` | Role: {role_name} | Dept: {user['department'] or 'N/A'}",
                    inline=False
                )
            
            if len(users) > 25:
                embed.set_footer(text=f"Showing 25 of {len(users)} users")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        else:
            await interaction.response.send_message(
                "❌ You don't have permission to list users!",
                ephemeral=True
            )

    # ==================== USER DELETE LOGS ====================
    @app_commands.command(name="user_delete_logs", description="View user deletion logs with pagination (ADMIN+)")
    async def user_delete_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check if super admin
        is_super = await is_super_admin(interaction.user.id)
        
        if not is_super:
            await interaction.followup.send(  # CHANGED HERE
                "❌ You don't have permission to view delete logs!",
                ephemeral=True
            )
            return
        
        try:
            # Get total count
            total_count = await UserModel.get_delete_logs_count()
            
            if total_count == 0:
                await interaction.followup.send(  # CHANGED HERE
                    "📋 No deletion logs found!",
                    ephemeral=True
                )
                return
            
            # Fetch first page
            logs = await UserModel.get_delete_logs(limit=15, offset=0)
            
            # Create pagination view
            view = DeleteLogsPaginationView(total_count=total_count, per_page=15)
            
            # Create embed for first page
            embed = discord.Embed(
                title=f"🗑️ User Deletion Logs",
                description=f"**Total Logs:** {total_count} | **Page:** 1/{view.total_pages}",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            for log in logs:
                deleted_user_mention = f"<@{log['deleted_user_discord_id']}>" if log['deleted_user_discord_id'] else "Unknown"
                deleted_by_mention = f"<@{log['deleted_by_discord_id']}>" if log['deleted_by_discord_id'] else "Unknown"
                
                field_value = (
                    f"**Deleted User:** {deleted_user_mention} ({log['deleted_user_name'] or 'N/A'})\n"
                    f"**Department:** {log['deleted_user_department'] or 'N/A'}\n"
                    f"**Deleted By:** {deleted_by_mention} ({log['deleted_by_name'] or 'N/A'})\n"
                    f"**Reason:** {log['reason'] or 'No reason provided'}\n"
                    f"**Seniors Informed:** {'✅ Yes' if log['seniors_informed'] else '❌ No'} | "
                    f"**Admins Informed:** {'✅ Yes' if log['admins_informed'] else '❌ No'} | "
                    f"**Is With Us:** {'✅ Yes' if log['is_with_us'] else '❌ No'}\n"
                    f"**Deleted At:** <t:{int(log['deleted_at'].timestamp())}:F>"
                )
                
                embed.add_field(
                    name=f"Log ID: {log['id']} | User ID: {log['deleted_user_id'] or 'N/A'}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"Showing logs 1-{min(15, total_count)} of {total_count}")
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send( 
                f"❌ Failed to fetch delete logs: {str(e)}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(UserManagement(bot))