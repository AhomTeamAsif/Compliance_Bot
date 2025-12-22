import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from models.activity_log_model import ActivityLogModel
from models.user_model import UserModel
from views.activity_log_views import ActivityLogsPaginationView
from utils.verification_helper import is_super_admin
from utils.database import db


class ActivityLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== VIEW ALL ACTIVITY LOGS ====================
    @app_commands.command(name="activity_logs", description="View all activity logs with pagination (SUPER ADMIN)")
    async def activity_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check if super admin
        if not await is_super_admin(interaction.user.id):
            await interaction.followup.send(
                "❌ Only SUPER ADMIN can view activity logs!",
                ephemeral=True
            )
            return
        
        try:
            # Get total count
            total_count = await ActivityLogModel.get_activity_logs_count()
            
            if total_count == 0:
                await interaction.followup.send(
                    "📋 No activity logs found!",
                    ephemeral=True
                )
                return
            
            # Fetch first page
            logs = await ActivityLogModel.get_activity_logs(limit=15, offset=0)
            
            # Create pagination view
            view = ActivityLogsPaginationView(total_count=total_count, per_page=15)
            
            # Create embed for first page
            embed = discord.Embed(
                title=f"📊 Activity Logs - All Users",
                description=f"**Total Logs:** {total_count} | **Page:** 1/{view.total_pages}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for log in logs:
                user_mention = f"<@{log['user_discord_id']}>" if log['user_discord_id'] else "Unknown"
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(log['user_role_id'], "NORMAL")
                
                field_value = (
                    f"**User:** {user_mention} ({log['user_name'] or 'N/A'})\n"
                    f"**Department:** {log['user_department'] or 'N/A'}\n"
                    f"**Role:** {role_name}\n"
                    f"**Command:** `/{log['slash_command_used']}`\n"
                    f"**Executed At:** <t:{int(log['created_at'].timestamp())}:f>"
                )
                
                embed.add_field(
                    name=f"Log ID: {log['id']} | User ID: {log['user_id']}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"Showing logs 1-{min(15, total_count)} of {total_count}")
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to fetch activity logs: {str(e)}",
                ephemeral=True
            )

    # ==================== VIEW ACTIVITY LOGS BY USER ====================
    @app_commands.command(name="activity_logs_user", description="View activity logs for a specific user (SUPER ADMIN)")
    @app_commands.describe(user="The user to view activity logs for")
    async def activity_logs_user(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        
        # Check if super admin
        if not await is_super_admin(interaction.user.id):
            await interaction.followup.send(
                "❌ Only SUPER ADMIN can view activity logs!",
                ephemeral=True
            )
            return
        
        try:
            # Get user_id from discord_id
            user_data = await UserModel.get_user_by_discord_id(user.id, include_deleted=True)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ **{user.mention}** is not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get total count for this user
            total_count = await ActivityLogModel.get_activity_logs_count_by_user(user_data['user_id'])
            
            if total_count == 0:
                await interaction.followup.send(
                    f"📋 No activity logs found for **{user.mention}**!",
                    ephemeral=True
                )
                return
            
            # Fetch first page
            logs = await ActivityLogModel.get_activity_logs_by_user(
                user_id=user_data['user_id'],
                limit=15,
                offset=0
            )
            
            # Create pagination view
            view = ActivityLogsPaginationView(
                total_count=total_count,
                per_page=15,
                user_id=user_data['user_id']
            )
            
            # Create embed for first page
            embed = discord.Embed(
                title=f"📊 Activity Logs - {user_data['name']}",
                description=f"**Total Logs:** {total_count} | **Page:** 1/{view.total_pages}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            for log in logs:
                user_mention = f"<@{log['user_discord_id']}>" if log['user_discord_id'] else "Unknown"
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(log['user_role_id'], "NORMAL")
                
                field_value = (
                    f"**User:** {user_mention} ({log['user_name'] or 'N/A'})\n"
                    f"**Department:** {log['user_department'] or 'N/A'}\n"
                    f"**Role:** {role_name}\n"
                    f"**Command:** `/{log['slash_command_used']}`\n"
                    f"**Executed At:** <t:{int(log['created_at'].timestamp())}:f>"
                )
                
                embed.add_field(
                    name=f"Log ID: {log['id']} | User ID: {log['user_id']}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"Showing logs 1-{min(15, total_count)} of {total_count}")
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to fetch activity logs: {str(e)}",
                ephemeral=True
            )

    # ==================== DELETE ACTIVITY LOGS BY USER ====================
    @app_commands.command(name="activity_logs_delete", description="Delete all activity logs for a user (SUPER ADMIN)")
    @app_commands.describe(user="The user whose activity logs to delete")
    async def activity_logs_delete(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        
        # Check if super admin
        if not await is_super_admin(interaction.user.id):
            await interaction.followup.send(
                "❌ Only SUPER ADMIN can delete activity logs!",
                ephemeral=True
            )
            return
        
        try:
            # Get user_id from discord_id
            user_data = await UserModel.get_user_by_discord_id(user.id, include_deleted=True)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ **{user.mention}** is not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get count before deletion
            count = await ActivityLogModel.get_activity_logs_count_by_user(user_data['user_id'])
            
            if count == 0:
                await interaction.followup.send(
                    f"📋 No activity logs found for **{user.mention}**!",
                    ephemeral=True
                )
                return
            
            # Delete logs
            success = await ActivityLogModel.delete_activity_logs_by_user(user_data['user_id'])
            
            if success:
                embed = discord.Embed(
                    title="✅ Activity Logs Deleted",
                    description=f"Successfully deleted **{count}** activity log(s) for **{user.mention}**",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 User", value=f"{user.mention} ({user_data['name']})", inline=True)
                embed.add_field(name="🗑️ Logs Deleted", value=str(count), inline=True)
                embed.set_thumbnail(url=user.display_avatar.url)
                embed.set_footer(text=f"Deleted by {interaction.user.name}")
                
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(
                    f"❌ Failed to delete activity logs for **{user.mention}**!",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to delete activity logs: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ActivityLogs(bot))