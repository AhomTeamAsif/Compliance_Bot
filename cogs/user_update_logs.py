import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import json
from models.user_model import UserModel
from views.user_update_log_views import UpdateLogsPaginationView
from utils.verification_helper import is_super_admin, is_admin
from utils.database import db


class UserUpdateLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== VIEW ALL UPDATE LOGS ====================
    @app_commands.command(name="user_update_logs", description="View all user update logs with pagination (ADMIN+)")
    async def user_update_logs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view update logs!",
                ephemeral=True
            )
            return
        
        try:
            # Get total count
            total_count = await UserModel.get_update_logs_count()
            
            if total_count == 0:
                await interaction.followup.send(
                    "📋 No update logs found!",
                    ephemeral=True
                )
                return
            
            # Fetch first page
            logs = await UserModel.get_update_logs(limit=15, offset=0)
            
            # Create pagination view
            view = UpdateLogsPaginationView(total_count=total_count, per_page=15)
            
            # Create embed for first page
            embed = discord.Embed(
                title=f"📝 Update Logs - All Users",
                description=f"**Total Logs:** {total_count} | **Page:** 1/{view.total_pages}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            for log in logs:
                updated_user_mention = f"<@{log['updated_user_discord_id']}>" if log['updated_user_discord_id'] else "Unknown"
                updated_by_mention = f"<@{log['updated_by_discord_id']}>" if log['updated_by_discord_id'] else "Unknown"
                
                # Parse JSON values
                old_values = json.loads(log['old_values']) if log['old_values'] else {}
                new_values = json.loads(log['new_values']) if log['new_values'] else {}
                
                # Build field changes text
                changes_text = []
                if log['fields_updated']:
                    for field in log['fields_updated']:
                        old_val = old_values.get(field, 'N/A')
                        new_val = new_values.get(field, 'N/A')
                        changes_text.append(f"**{field}:** `{old_val}` → `{new_val}`")
                
                # Build permission changes text
                perm_changes = []
                if log['permissions_added']:
                    perm_changes.append(f"✅ Added: {len(log['permissions_added'])} permission(s)")
                if log['permissions_removed']:
                    perm_changes.append(f"❌ Removed: {len(log['permissions_removed'])} permission(s)")
                
                field_value = (
                    f"**Updated User:** {updated_user_mention} ({log['updated_user_name'] or 'N/A'})\n"
                    f"**Updated By:** {updated_by_mention} ({log['updated_by_name'] or 'N/A'})\n"
                    f"**Department:** {log['updated_user_department'] or 'N/A'}\n"
                    f"**Update Type:** {log['update_type']}\n"
                )
                
                if changes_text:
                    field_value += f"**Changes:**\n" + "\n".join(changes_text) + "\n"
                
                if perm_changes:
                    field_value += "**Permissions:**\n" + "\n".join(perm_changes) + "\n"
                
                field_value += f"**Updated At:** <t:{int(log['updated_at'].timestamp())}:f>"
                
                embed.add_field(
                    name=f"Log ID: {log['id']} | User ID: {log['updated_user_id']}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"Showing logs 1-{min(15, total_count)} of {total_count}")
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to fetch update logs: {str(e)}",
                ephemeral=True
            )

    # ==================== VIEW UPDATE LOGS BY USER ====================
    @app_commands.command(name="user_update_logs_user", description="View update logs for a specific user (ADMIN+)")
    @app_commands.describe(user="The user to view update logs for")
    async def user_update_logs_user(self, interaction: discord.Interaction, user: discord.User):
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view update logs!",
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
            total_count = await UserModel.get_update_logs_count_by_user(user_data['user_id'])
            
            if total_count == 0:
                await interaction.followup.send(
                    f"📋 No update logs found for **{user.mention}**!",
                    ephemeral=True
                )
                return
            
            # Fetch first page
            logs = await UserModel.get_update_logs_by_user(
                user_id=user_data['user_id'],
                limit=15,
                offset=0
            )
            
            # Create pagination view
            view = UpdateLogsPaginationView(
                total_count=total_count,
                per_page=15,
                user_id=user_data['user_id']
            )
            
            # Create embed for first page
            embed = discord.Embed(
                title=f"📝 Update Logs - {user_data['name']}",
                description=f"**Total Logs:** {total_count} | **Page:** 1/{view.total_pages}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            for log in logs:
                updated_user_mention = f"<@{log['updated_user_discord_id']}>" if log['updated_user_discord_id'] else "Unknown"
                updated_by_mention = f"<@{log['updated_by_discord_id']}>" if log['updated_by_discord_id'] else "Unknown"
                
                # Parse JSON values
                old_values = json.loads(log['old_values']) if log['old_values'] else {}
                new_values = json.loads(log['new_values']) if log['new_values'] else {}
                
                # Build field changes text
                changes_text = []
                if log['fields_updated']:
                    for field in log['fields_updated']:
                        old_val = old_values.get(field, 'N/A')
                        new_val = new_values.get(field, 'N/A')
                        changes_text.append(f"**{field}:** `{old_val}` → `{new_val}`")
                
                # Build permission changes text
                perm_changes = []
                if log['permissions_added']:
                    perm_changes.append(f"✅ Added: {len(log['permissions_added'])} permission(s)")
                if log['permissions_removed']:
                    perm_changes.append(f"❌ Removed: {len(log['permissions_removed'])} permission(s)")
                
                field_value = (
                    f"**Updated User:** {updated_user_mention} ({log['updated_user_name'] or 'N/A'})\n"
                    f"**Updated By:** {updated_by_mention} ({log['updated_by_name'] or 'N/A'})\n"
                    f"**Department:** {log['updated_user_department'] or 'N/A'}\n"
                    f"**Update Type:** {log['update_type']}\n"
                )
                
                if changes_text:
                    field_value += f"**Changes:**\n" + "\n".join(changes_text) + "\n"
                
                if perm_changes:
                    field_value += "**Permissions:**\n" + "\n".join(perm_changes) + "\n"
                
                field_value += f"**Updated At:** <t:{int(log['updated_at'].timestamp())}:f>"
                
                embed.add_field(
                    name=f"Log ID: {log['id']} | User ID: {log['updated_user_id']}",
                    value=field_value,
                    inline=False
                )
            
            embed.set_footer(text=f"Showing logs 1-{min(15, total_count)} of {total_count}")
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Failed to fetch update logs: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(UserUpdateLogs(bot))