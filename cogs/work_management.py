import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime, date
from models.work_update_model import WorkUpdateModel
from models.late_reason_model import LateReasonModel
from models.user_model import UserModel
from models.time_tracking_model import TimeTrackingModel
from utils.verification_helper import is_admin, is_super_admin
import pytz


class LateReasonApprovalView(ui.View):
    """View for approving/rejecting late reasons"""
    
    def __init__(self, late_reason_id: int, user_name: str, is_already_approved: bool = False):
        super().__init__(timeout=180)
        self.late_reason_id = late_reason_id
        self.user_name = user_name
        self.is_already_approved = is_already_approved  # Only True if already approved
    
    @ui.button(label="✅ Approve", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.is_already_approved:
            await interaction.response.send_message(
                f"⚠️ Late reason for {self.user_name} is already approved!",
                ephemeral=True
            )
            return
        
        success = await LateReasonModel.update_admin_approval(self.late_reason_id, True)
        
        if success:
            await interaction.response.edit_message(
                content=f"✅ **Late reason APPROVED** for {self.user_name}",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ Failed to update approval status for {self.user_name}",
                view=None
            )
        self.stop()
    
    @ui.button(label="❌ Reject", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: ui.Button):
        # Always allow reject, even if already rejected before
        success = await LateReasonModel.update_admin_approval(self.late_reason_id, False)
        
        if success:
            await interaction.response.edit_message(
                content=f"❌ **Late reason REJECTED** for {self.user_name}",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ Failed to update approval status for {self.user_name}",
                view=None
            )
        self.stop()


class WorkUpdateApprovalView(ui.View):
    """View for approving/rejecting work updates"""
    
    def __init__(self, work_update_id: int, user_name: str, is_already_approved: bool = False):
        super().__init__(timeout=180)
        self.work_update_id = work_update_id
        self.user_name = user_name
        self.is_already_approved = is_already_approved  # Only True if already approved
    
    @ui.button(label="✅ Approve Work Plan", style=discord.ButtonStyle.success)
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.is_already_approved:
            await interaction.response.send_message(
                f"⚠️ Work plan for {self.user_name} is already approved!",
                ephemeral=True
            )
            return
        
        success = await WorkUpdateModel.update_admin_approval(self.work_update_id, True)
        
        if success:
            await interaction.response.edit_message(
                content=f"✅ **Work plan APPROVED** for {self.user_name}",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ Failed to update approval status for {self.user_name}",
                view=None
            )
        self.stop()
    
    @ui.button(label="❌ Reject Work Plan", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: ui.Button):
        # Always allow reject, even if already rejected before
        success = await WorkUpdateModel.update_admin_approval(self.work_update_id, False)
        
        if success:
            await interaction.response.edit_message(
                content=f"❌ **Work plan REJECTED** for {self.user_name}",
                view=None
            )
        else:
            await interaction.response.edit_message(
                content=f"❌ Failed to update approval status for {self.user_name}",
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
                approval_status = "✅ Approved" if update.get('admin_approval') else "❌ Rejected" if update.get('admin_approval') is False else "⏳ Pending"
                
                user_mention = f"<@{update['discord_id']}>" if update['discord_id'] else update['name']
                
                embed.add_field(
                    name=f"👤 {update['name']} - {approval_status}",
                    value=(
                        f"**Tasks:**\n{task_list}\n"
                        f"**Desklog:** {desklog_status}\n"
                        f"**Trackabi:** {trackabi_status}\n"
                        f"**Update ID:** `{update['id']}`"
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
                approval_status = "✅ Approved" if late.get('admin_approval') else "❌ Rejected" if late.get('admin_approval') is False else "⏳ Pending"
                admin_informed = "✅ Yes" if late['is_admin_informed'] else "❌ No"
                meeting = "✅ Yes" if late['morning_meeting_attended'] else "❌ No"
                
                date_str = late.get('present_date', 'Unknown date')
                if isinstance(date_str, date):
                    date_str = date_str.strftime('%Y-%m-%d')
                
                embed.add_field(
                    name=f"👤 {late['name']} - {late['late_mins']} min late",
                    value=(
                        f"**Date:** {date_str}\n"
                        f"**Reason:** {late['reason']}\n"
                        f"**Admin Informed:** {admin_informed}\n"
                        f"**Meeting Attended:** {meeting}\n"
                        f"**Status:** {approval_status}\n"
                        f"**Late ID:** `{late['id']}`"
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
    @app_commands.describe(
        user="The user whose late reason to review",
        late_id="Specific late reason ID (optional)"
    )
    async def late_approval(self, interaction: discord.Interaction, user: discord.User, late_id: str = None):
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
            
            # Get late reason
            if late_id and late_id.isdigit():
                # Get by specific ID
                user_late = await LateReasonModel.get_late_reason_by_id(int(late_id))
                if not user_late or user_late['user_id'] != user_data['user_id']:
                    await interaction.followup.send(
                        f"❌ Late reason with ID `{late_id}` not found for {user.mention}!",
                        ephemeral=True
                    )
                    return
            else:
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
            
            # Fix: Safely get present_date with fallback
            present_date = user_late.get('present_date')
            if not present_date and 'time_tracking_id' in user_late:
                # Try to get date from time tracking
                tracking_data = await TimeTrackingModel.get_tracking_by_id(user_late['time_tracking_id'])
                if tracking_data:
                    present_date = tracking_data.get('present_date')
            
            # Convert date to string if it's a date object
            date_str = present_date
            if isinstance(present_date, date):
                date_str = present_date.strftime('%Y-%m-%d')
            elif not present_date:
                date_str = 'Unknown date'
            
            # Check if already approved (only show warning for approved, not rejected)
            if user_late.get('admin_approval') is True:  # Only check if True
                await interaction.followup.send(
                    f"⚠️ Late reason for {user.mention} is already **APPROVED**!\n"
                    f"**Late ID:** `{user_late['id']}`\n"
                    f"**Late by:** {user_late['late_mins']} minutes\n"
                    f"**Date:** {date_str}",
                    ephemeral=True
                )
                return
            
            # Show approval view
            embed = discord.Embed(
                title=f"⏰ Late Reason Review - {user_data['name']}",
                description=f"**Late ID:** `{user_late['id']}`",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="📅 Date", value=date_str, inline=True)
            embed.add_field(name="⏱️ Late by", value=f"{user_late['late_mins']} minutes", inline=True)
            embed.add_field(name="👤 User", value=user.mention, inline=True)
            embed.add_field(name="📝 Reason", value=user_late['reason'], inline=False)
            embed.add_field(name="👔 Admin Informed", value="✅ Yes" if user_late['is_admin_informed'] else "❌ No", inline=True)
            embed.add_field(name="📞 Meeting Attended", value="✅ Yes" if user_late['morning_meeting_attended'] else "❌ No", inline=True)
            
            # Pass whether it's already approved (only True if already approved)
            is_already_approved = user_late.get('admin_approval') is True
            view = LateReasonApprovalView(
                user_late['id'], 
                user_data['name'],
                is_already_approved=is_already_approved
            )
            
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
    
    # ==================== APPROVE/REJECT WORK UPDATE ====================
    @app_commands.command(
        name="work_approval",
        description="Approve or reject a work plan (ADMIN+)"
    )
    @app_commands.describe(
        user="The user whose work plan to review",
        update_id="Specific work update ID (optional)"
    )
    async def work_approval(self, interaction: discord.Interaction, user: discord.User, update_id: str = None):
        """Approve or reject work plan for a user"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can approve work plans!",
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
            
            # Get work update
            if update_id and update_id.isdigit():
                # Get by specific ID
                work_update = await WorkUpdateModel.get_work_update_by_id(int(update_id))
                if not work_update or work_update['user_id'] != user_data['user_id']:
                    await interaction.followup.send(
                        f"❌ Work update with ID `{update_id}` not found for {user.mention}!",
                        ephemeral=True
                    )
                    return
            else:
                # Get today's work update
                today = datetime.now(pytz.utc).date()
                work_update = await WorkUpdateModel.get_today_plan_by_user_id(user_data['user_id'], today)
                
                if not work_update:
                    await interaction.followup.send(
                        f"❌ No work plan found for {user.mention} today!",
                        ephemeral=True
                    )
                    return
            
            # Safely get present_date
            present_date = work_update.get('present_date', 'Unknown date')
            if isinstance(present_date, date):
                present_date = present_date.strftime('%Y-%m-%d')
            
            # Check if already approved (only show warning for approved, not rejected)
            if work_update.get('admin_approval') is True:  # Only check if True
                await interaction.followup.send(
                    f"⚠️ Work plan for {user.mention} is already **APPROVED**!\n"
                    f"**Update ID:** `{work_update['id']}`\n"
                    f"**Date:** {present_date}",
                    ephemeral=True
                )
                return
            
            # Show approval view
            embed = discord.Embed(
                title=f"📋 Work Plan Review - {user_data['name']}",
                description=f"**Update ID:** `{work_update['id']}`",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="📅 Date", value=present_date, inline=True)
            embed.add_field(name="👤 User", value=user.mention, inline=True)
            embed.add_field(name="⏰ Created", value=work_update['created_at'].strftime("%H:%M"), inline=True)
            
            # Tasks
            tasks = work_update['start_of_the_day_plan'] if work_update['start_of_the_day_plan'] else []
            task_list = "\n".join([f"{i+1}. {task}" for i, task in enumerate(tasks)]) if tasks else "No tasks provided"
            embed.add_field(name="📝 Tasks", value=task_list, inline=False)
            
            # Status
            desklog_status = "✅ ON" if work_update['desklog_on'] else "❌ OFF"
            trackabi_status = "✅ ON" if work_update['trackabi_on'] else "❌ OFF"
            embed.add_field(name="🖥️ Desklog", value=desklog_status, inline=True)
            embed.add_field(name="📊 Trackabi", value=trackabi_status, inline=True)
            
            # Pass whether it's already approved (only True if already approved)
            is_already_approved = work_update.get('admin_approval') is True
            view = WorkUpdateApprovalView(
                work_update['id'], 
                user_data['name'],
                is_already_approved=is_already_approved
            )
            
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