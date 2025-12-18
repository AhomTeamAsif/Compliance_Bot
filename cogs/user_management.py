import discord
from discord import app_commands
from discord.ext import commands
from models.user_model import UserModel
from views.user_management_views import (
    RegisterUserSelectView, UpdateUserSelectView, DeleteUserSelectView,
    RestoreUserSelectView, ActiveAllUsersModal
)
from utils.verification_helper import check_user_permission, is_super_admin, is_admin
from utils.database import db

class UserManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== REGISTER USER ====================
    @app_commands.command(name="user_register", description="Register a new user in the system")
    async def register_user(self, interaction: discord.Interaction):
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
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== UPDATE USER ====================
    @app_commands.command(name="user_update", description="Update user information")
    async def update_user(self, interaction: discord.Interaction):
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
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== DELETE USER ====================
    @app_commands.command(name="user_delete", description="Delete a user from the system")
    async def delete_user(self, interaction: discord.Interaction):
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
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== RESTORE USER ====================
    @app_commands.command(name="user_restore", description="Restore a deleted user (SUPER ADMIN ONLY)")
    async def restore_user(self, interaction: discord.Interaction):
        # Check if super admin (has administer permission)
        has_permission = await check_user_permission(interaction.user.id, 'administer')
        
        if not has_permission:
            await interaction.response.send_message(
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
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
                
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user_data['role_id'], "NORMAL")
                status = "🔴 Deleted" if user_data['is_deleted'] else "🟢 Active"
                
                embed = discord.Embed(
                    title=f"👤 User Information: {user_data['name']}",
                    color=discord.Color.red() if user_data['is_deleted'] else discord.Color.blue(),
                    timestamp=user_data['created_at']
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
                embed.add_field(name="🗓️ Contract Start", value=user_data['contract_started_at'].strftime('%Y-%m-%d') if user_data['contract_started_at'] else "N/A", inline=True)
                
                # Permissions and Granted By
                if perms:
                    perm_text = "\n".join([f"• {p['permission_name']}" for p in perms])
                    granted_text = "\n".join([f"• {p['granted_by_name'] or 'System'}" for p in perms])
                    
                    embed.add_field(name="🔑 Permissions", value=perm_text, inline=True)
                    embed.add_field(name="👤 Granted By", value=granted_text, inline=True)
                else:
                    embed.add_field(name="🔑 Permissions", value="None", inline=False)
                
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text="User registered at")
                
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
            
            role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(user_data['role_id'], "NORMAL")
            
            embed = discord.Embed(
                title=f"👤 User Information: {user_data['name']}",
                color=discord.Color.blue(),
                timestamp=user_data['created_at']
            )
            
            embed.add_field(name="🆔 User ID", value=f"`{user_data['user_id']}`", inline=True)
            embed.add_field(name="👤 Discord", value=user.mention, inline=True)
            embed.add_field(name="🏢 Department", value=user_data['department'] or "N/A", inline=True)
            embed.add_field(name="💼 Position", value=user_data['position'] or "N/A", inline=True)
            embed.add_field(name="👑 Role", value=role_name, inline=True)
            embed.add_field(name="📊 Trackabi ID", value=f"`{user_data['trackabi_id']}`" if user_data['trackabi_id'] else "N/A", inline=True)
            embed.add_field(name="🖥️ Desklog ID", value=f"`{user_data['desklog_id']}`" if user_data['desklog_id'] else "N/A", inline=True)
            embed.add_field(name="🏖️ Pending Leaves", value=f"{user_data['pending_leaves']} days", inline=True)
            embed.add_field(name="🗓️ Contract Start", value=user_data['contract_started_at'].strftime('%Y-%m-%d') if user_data['contract_started_at'] else "N/A", inline=True)
            
            # Permissions and Granted By
            if perms:
                perm_text = "\n".join([f"• {p['permission_name']}" for p in perms])
                granted_text = "\n".join([f"• {p['granted_by_name'] or 'System'}" for p in perms])
                
                embed.add_field(name="🔑 Permissions", value=perm_text, inline=True)
                embed.add_field(name="👤 Granted By", value=granted_text, inline=True)
            else:
                embed.add_field(name="🔑 Permissions", value="None", inline=False)
            
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text="User registered at")
            
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
        is_super = await check_user_permission(interaction.user.id, 'administer')
        
        # Check if super admin
        if await is_super_admin(interaction.user.id):
            # Show modal to ask active/all
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
            # Regular admin - only show active users
            users = await UserModel.get_all_users(include_deleted=False)
            
            if not users:
                await interaction.response.send_message("❌ No users found in the system!", ephemeral=True)
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
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserManagement(bot))