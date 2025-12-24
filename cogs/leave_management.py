"""Leave management commands for handling employee leave requests"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from models.user_model import UserModel
from models.leave_model import LeaveRequestModel
from views.leave_management_views import LeaveTypeSelectView
from utils.verification_helper import check_user_permission


class LeaveManagement(commands.Cog):
    """Leave management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ==================== LEAVE REQUEST ====================
    @app_commands.command(
        name="leave_request",
        description="Request a leave from work"
    )
    async def leave_request(self, interaction: discord.Interaction):
        """Start the leave request process"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is registered
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.followup.send(
                    "❌ You are not registered in the system! Please contact an admin.",
                    ephemeral=True
                )
                return
            
            # Show leave type selection
            view = LeaveTypeSelectView()
            
            embed = discord.Embed(
                title="🎫 Leave Request - Step 1/2",
                description="**Select a leave type** to continue:",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📋 Available Leave Types",
                value=(
                    "**💰 Paid Leave** - Must be requested 2+ weeks in advance\n"
                    "**🤒 Sick Leave** - Notify immediately and inform HR/CEO\n"
                    "**⏰ Half-Day Leave** - Up to 2 hours with prior approval\n"
                    "**🚨 Emergency Leave** - Inform ASAP with valid reason"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # ==================== VIEW MY LEAVES ====================
    @app_commands.command(
        name="my_leaves",
        description="View your leave request history"
    )
    @app_commands.describe(limit="Number of recent requests to show (default: 5)")
    async def my_leaves(self, interaction: discord.Interaction, limit: int = 5):
        """Show user's leave request history"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is registered
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.followup.send(
                    "❌ You are not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get user's leave requests
            leave_requests = await LeaveRequestModel.get_user_leave_requests(
                user['user_id'],
                limit
            )
            
            if not leave_requests:
                await interaction.followup.send(
                    "📋 You have no leave requests yet.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="📋 Your Leave Requests",
                description=f"Last {len(leave_requests)} request(s)",
                color=discord.Color.blue()
            )
            
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌"
            }
            
            for req in leave_requests:
                leave_type_display = {
                    "paid_leave": "💰 Paid Leave",
                    "sick_leave": "🤒 Sick Leave",
                    "half_day": "⏰ Half-Day Leave",
                    "emergency_leave": "🚨 Emergency Leave"
                }.get(req['leave_type'], req['leave_type'])
                
                status = req['status']
                emoji = status_emoji.get(status, "❓")
                
                field_value = (
                    f"**Type:** {leave_type_display}\n"
                    f"**Status:** {emoji} {status.capitalize()}\n"
                    f"**From:** {req['start_date']}\n"
                    f"**To:** {req['end_date']}\n"
                )
                
                if req['duration_hours']:
                    field_value += f"**Duration:** {req['duration_hours']} hour(s)\n"
                else:
                    field_value += f"**Duration:** {(req['end_date'] - req['start_date']).days + 1} day(s)\n"
                
                field_value += f"**Reason:** {req['reason']}\n"
                
                # Add reminder for sick leave to contact HR/CEO
                if req['leave_type'] == 'sick_leave':
                    field_value += f"**Note:** Remember to inform HR/CEO directly\n"
                
                field_value += f"**Requested:** {req['created_at'].strftime('%Y-%m-%d %H:%M')}"
                
                embed.add_field(
                    name=f"Request #{req['leave_request_id']}",
                    value=field_value,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # ==================== VIEW PENDING LEAVES ====================
    @app_commands.command(
        name="pending_leaves",
        description="View your remaining pending leaves"
    )
    async def pending_leaves(self, interaction: discord.Interaction):
        """Show user's remaining paid leaves"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is registered
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.followup.send(
                    "❌ You are not registered in the system!",
                    ephemeral=True
                )
                return
            
            pending_leaves = user['pending_leaves']
            
            # Color based on remaining leaves
            if pending_leaves > 10:
                color = discord.Color.green()
            elif pending_leaves > 5:
                color = discord.Color.gold()
            else:
                color = discord.Color.red()
            
            embed = discord.Embed(
                title="🖊️ Pending Leaves Balance",
                description=f"Remaining paid leave days: **{pending_leaves}**",
                color=color
            )
            
            embed.add_field(
                name="📊 Leave Summary",
                value=(
                    f"**Total Pending Days:** {pending_leaves}\n"
                    f"**Employee Name:** {user['name']}\n"
                    f"**Department:** {user['department']}\n"
                    f"**Contract Started:** {user['contract_started_at'].strftime('%Y-%m-%d')}"
                ),
                inline=False
            )
            
            if pending_leaves == 0:
                embed.add_field(
                    name="⚠️ Alert",
                    value="You have no pending leaves remaining. Contact HR for more information.",
                    inline=False
                )
            elif pending_leaves <= 3:
                embed.add_field(
                    name="⚠️ Low Balance",
                    value="Your leave balance is running low!",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # ==================== ADMIN: VIEW PENDING REQUESTS ====================
    @app_commands.command(
        name="review_leave_requests",
        description="[ADMIN] Review pending leave requests"
    )
    async def review_leave_requests(self, interaction: discord.Interaction):
        """Show all pending leave requests for admin review"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check permission
            has_permission = await check_user_permission(
                interaction.user.id,
                'user_update'
            )
            
            if not has_permission:
                await interaction.followup.send(
                    "❌ You don't have permission to review leave requests!",
                    ephemeral=True
                )
                return
            
            # Get pending requests
            pending_requests = await LeaveRequestModel.get_pending_leave_requests(limit=20)
            
            if not pending_requests:
                await interaction.followup.send(
                    "✅ No pending leave requests!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="📋 Pending Leave Requests",
                description=f"Total: {len(pending_requests)} request(s)",
                color=discord.Color.orange()
            )
            
            for idx, req in enumerate(pending_requests, 1):
                leave_type_display = {
                    "paid_leave": "💰 Paid Leave",
                    "sick_leave": "🤒 Sick Leave",
                    "half_day": "⏰ Half-Day Leave",
                    "emergency_leave": "🚨 Emergency Leave"
                }.get(req['leave_type'], req['leave_type'])
                
                field_value = (
                    f"**Employee:** {req['name']}\n"
                    f"**Type:** {leave_type_display}\n"
                    f"**From:** {req['start_date']}\n"
                    f"**To:** {req['end_date']}\n"
                    f"**Reason:** {req['reason']}\n"
                )
                
                # Add note for sick leave
                if req['leave_type'] == 'sick_leave':
                    field_value += f"**Note:** Employee should contact HR/CEO with medical docs (if available)\n"
                
                field_value += f"**Requested:** {req['created_at'].strftime('%Y-%m-%d %H:%M')}"
                
                embed.add_field(
                    name=f"#{idx}. Request ID: {req['leave_request_id']}",
                    value=field_value,
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(LeaveManagement(bot))