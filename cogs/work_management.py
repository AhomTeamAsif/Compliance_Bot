import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime, date
from models.work_update_model import WorkUpdateModel
from models.late_reason_model import LateReasonModel
from models.user_model import UserModel
from utils.verification_helper import is_admin, is_super_admin
import pytz


class LateReasonApprovalView(ui.View):
    """View for approving/rejecting late reasons"""
    
    def __init__(self, late_reason_id: int, user_name: str):
        super().__init__(timeout=180)
        self.late_reason_id = late_reason_id
        self.user_name = user_name
    
    @ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        await LateReasonModel.update_admin_approval(self.late_reason_id, True)
        
        await interaction.response.edit_message(
            content=f"✅ **Late reason APPROVED** for {self.user_name}",
            view=None
        )
        self.stop()
    
    @ui.button(label="❌ Reject", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: ui.Button):
        await LateReasonModel.update_admin_approval(self.late_reason_id, False)
        
        await interaction.response.edit_message(
            content=f"❌ **Late reason REJECTED** for {self.user_name}",
            view=None
        )
        self.stop()


class WorkManagement(commands.Cog):
    """Commands for managing work updates and late reasons"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ==================== VIEW WORK UPDATES ====================
    @app_commands.command(
        name="work_updates",
        description="View all work updates for today (ADMIN+)"
    )
    async def work_updates(self, interaction: discord.Interaction):
        """View all work updates for today"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view work updates!",
                ephemeral=True
            )
            return
        
        try:
            today = datetime.now(pytz.utc).date()
            updates = await WorkUpdateModel.get_work_updates_by_date(today)
            
            if not updates:
                await interaction.followup.send(
                    "📋 No work updates found for today!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📋 Work Updates - {today.strftime('%d/%m/%Y')}",
                description=f"**Total Updates:** {len(updates)}",
                color=discord.Color.blue()
            )
            
            for update in updates[:10]:  # Limit to 10 to avoid embed limits
                tasks = update['start_of_the_day_plan'] if update['start_of_the_day_plan'] else []
                task_list = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)]) if tasks else "No tasks"
                
                desklog_status = "✅ ON" if update['desklog_on'] else "❌ OFF"
                trackabi_status = "✅ ON" if update['trackabi_on'] else "❌ OFF"
                
                user_mention = f"<@{update['discord_id']}>" if update['discord_id'] else update['name']
                
                embed.add_field(
                    name=f"👤 {update['name']}",
                    value=(
                        f"**Tasks:**\n{task_list}\n"
                        f"**Desklog:** {desklog_status}\n"
                        f"**Trackabi:** {trackabi_status}"
                    ),
                    inline=False
                )
            
            if len(updates) > 10:
                embed.set_footer(text=f"Showing 10 of {len(updates)} updates")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    # ==================== VIEW LATE USERS ====================
    @app_commands.command(
        name="late_users",
        description="View users who were late today (ADMIN+)"
    )
    async def late_users(self, interaction: discord.Interaction):
        """View all late users for today"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view late users!",
                ephemeral=True
            )
            return
        
        try:
            today = datetime.now(pytz.utc).date()
            late_users = await LateReasonModel.get_late_users_list(date_filter=today, limit=20)
            
            if not late_users:
                await interaction.followup.send(
                    "✅ No one was late today!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"⏰ Late Arrivals - {today.strftime('%d/%m/%Y')}",
                description=f"**Total Late Users:** {len(late_users)}",
                color=discord.Color.orange()
            )
            
            for late in late_users:
                approval_status = "✅ Approved" if late['admin_approval'] else "⏳ Pending"
                admin_informed = "✅ Yes" if late['is_admin_informed'] else "❌ No"
                meeting = "✅ Yes" if late['morning_meeting_attended'] else "❌ No"
                
                embed.add_field(
                    name=f"👤 {late['name']} - {late['late_mins']} min late",
                    value=(
                        f"**Reason:** {late['reason']}\n"
                        f"**Admin Informed:** {admin_informed}\n"
                        f"**Meeting Attended:** {meeting}\n"
                        f"**Status:** {approval_status}"
                    ),
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )
    
    # ==================== APPROVE/REJECT LATE REASON ====================
    @app_commands.command(
        name="late_approval",
        description="Approve or reject a late reason (ADMIN+)"
    )
    @app_commands.describe(user="The user whose late reason to review")
    async def late_approval(self, interaction: discord.Interaction, user: discord.User):
        """Approve or reject late reason for a user"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can approve late reasons!",
                ephemeral=True
            )
            return
        
        try:
            # Get user from database
            user_data = await UserModel.get_user_by_discord_id(user.id)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered!",
                    ephemeral=True
                )
                return
            
            # Get today's late reason
            today = datetime.now(pytz.utc).date()
            late_users = await LateReasonModel.get_late_users_list(date_filter=today, limit=50)
            
            # Find user's late reason
            user_late = None
            for late in late_users:
                if late['user_id'] == user_data['user_id']:
                    user_late = late
                    break
            
            if not user_late:
                await interaction.followup.send(
                    f"❌ No late reason found for {user.mention} today!",
                    ephemeral=True
                )
                return
            
            # Show approval view
            embed = discord.Embed(
                title=f"⏰ Late Reason Review - {user_data['name']}",
                description=f"**Late by:** {user_late['late_mins']} minutes",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="📝 Reason", value=user_late['reason'], inline=False)
            embed.add_field(name="👔 Admin Informed", value="✅ Yes" if user_late['is_admin_informed'] else "❌ No", inline=True)
            embed.add_field(name="📞 Meeting Attended", value="✅ Yes" if user_late['morning_meeting_attended'] else "❌ No", inline=True)
            
            current_status = "✅ Approved" if user_late['admin_approval'] else "⏳ Pending"
            embed.add_field(name="Current Status", value=current_status, inline=False)
            
            view = LateReasonApprovalView(user_late['id'], user_data['name'])
            
            await interaction.followup.send(
                embed=embed,
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(WorkManagement(bot))