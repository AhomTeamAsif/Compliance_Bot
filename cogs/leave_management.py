"""Leave management commands for handling employee leave requests"""
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from models.user_model import UserModel
from models.leave_model import LeaveRequestModel
from views.leave_management_views import LeaveTypeSelectView, ReviewLeaveRequestsView, SickLeaveSettingsModal
from utils.verification_helper import check_user_permission, is_admin, is_super_admin
import pytz


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
                    "**📝 Unpaid Leave** - Unpaid leave request\n"
                    "**⚠️ Non-compliant** - Request 14 to 1 day before the off day\n"
                    "**🤒 Sick Leave** - Request 12 hours to 2 hours before the starting(10 AM) of the off day\n"
                    "**🚨 Emergency Leave** - Inform ASAP with valid reason\n"
                    "**⏰ Half-Day Leave** - Choose between unpaid/non-compliant\n"
                ),
                inline=False
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="sick_leave_settings",
        description="Update sick leave application window settings (Admin only)"
    )
    async def sick_leave_settings(self, interaction: discord.Interaction):
        try:
            if not await is_admin(interaction.user.id) and not await is_super_admin(interaction.user.id):
                await interaction.response.send_message("❌ Only admins can update settings.", ephemeral=True)
                return
            modal = SickLeaveSettingsModal()
            await interaction.response.send_modal(modal)
        except Exception as e:
            # If the interaction was already responded or modal fails, try followup
            try:
                await interaction.followup.send(f"❌ Error opening settings: {e}", ephemeral=True)
            except Exception:
                pass
    
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
                    "non_compliant": "⚠️ Non-compliant",
                    "paid_leave": "💰 Paid Leave",
                    "sick_leave": "🤒 Sick Leave",
                    "half_day": "⏰ Half-Day Leave",
                    "half_day_paid": "💰 Paid Half-Day",
                    "half_day_unpaid": "📝 Unpaid Half-Day",
                    "half_day_non_compliant": "⚠️ Non-compliant Half-Day",
                    "emergency_leave": "🚨 Emergency Leave",
                    "unpaid_leave": "📝 Unpaid Leave"
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
                
                field_value += f"**Requested:** {req['created_at'].strftime('%d/%m/%Y %H:%M')}"
                
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
                    f"**Contract Started:** {user['contract_started_at'].strftime('%d/%m/%Y')}"
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
                title="📋 Pending Leave Requests - Review Required",
                description=f"🔍 **Total Requests Awaiting Review:** `{len(pending_requests)}`\n\n"
                           f"Select one or multiple requests from the dropdown below to approve or reject them.",
                color=0xFFA500  # Orange color
            )

            # Add visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            for idx, req in enumerate(pending_requests, 1):
                leave_type_display = {
                    "non_compliant": "⚠️ Non-compliant",
                    "paid_leave": "💰 Paid Leave",
                    "sick_leave": "🤒 Sick Leave",
                    "half_day": "⏰ Half-Day Leave",
                    "half_day_paid": "💰 Paid Half-Day",
                    "half_day_unpaid": "📝 Unpaid Half-Day",
                    "half_day_non_compliant": "⚠️ Non-compliant Half-Day",
                    "emergency_leave": "🚨 Emergency Leave",
                    "unpaid_leave": "📝 Unpaid Leave"
                }.get(req['leave_type'], req['leave_type'])

                # Format dates nicely
                start_date_str = req['start_date'].strftime('%d/%m/%Y') if hasattr(req['start_date'], 'strftime') else str(req['start_date'])
                end_date_str = req['end_date'].strftime('%d/%m/%Y') if hasattr(req['end_date'], 'strftime') else str(req['end_date'])

                # Calculate duration
                if req['start_date'] == req['end_date']:
                    duration_str = "1 day"
                else:
                    days = (req['end_date'] - req['start_date']).days + 1
                    duration_str = f"{days} days"

                # Build field value with better formatting
                field_value = (
                    f"```yaml\n"
                    f"Employee: {req['name']}\n"
                    f"```\n"
                    f"**📅 Period:** {start_date_str} → {end_date_str} ({duration_str})\n"
                    f"**📋 Type:** {leave_type_display}\n"
                    f"**✏️ Reason:**\n> {req['reason']}\n"
                )

                # Add note for sick leave
                if req['leave_type'] == 'sick_leave':
                    field_value += f"**⚕️ Note:** *Employee should contact HR/CEO with medical documentation*\n"

                field_value += f"\n**⏰ Submitted:** `{req['created_at'].strftime('%d/%m/%Y at %H:%M')}`"

                # Add separator between requests (except for the last one)
                if idx < len(pending_requests):
                    field_value += "\n\n━━━━━━━━━━━━━━━━━━━━━━"

                embed.add_field(
                    name=f"🆔 Request #{req['leave_request_id']} - #{idx}",
                    value=field_value,
                    inline=False
                )
            
            view = ReviewLeaveRequestsView(pending_requests, interaction.user.id)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # ==================== ADMIN: VIEW USER LEAVE INFO ====================
    @app_commands.command(
        name="user_leave_info",
        description="[ADMIN] View a specific user's leave information and history"
    )
    @app_commands.describe(
        user="The user to view leave information for",
        limit="Number of recent requests to show (default: 10)"
    )
    async def user_leave_info(self, interaction: discord.Interaction, user: discord.Member, limit: int = 10):
        """Show a specific user's leave information for admin review"""

        await interaction.response.defer(ephemeral=True)

        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view user leave information!",
                ephemeral=True
            )
            return

        try:
            # Get user from database
            user_data = await UserModel.get_user_by_discord_id(user.id)

            if not user_data:
                await interaction.followup.send(
                    f"❌ User {user.mention} is not registered in the system!",
                    ephemeral=True
                )
                return

            # Get user's leave requests
            leave_requests = await LeaveRequestModel.get_user_leave_requests(
                user_data['user_id'],
                limit
            )

            # Create main embed with user info
            embed = discord.Embed(
                title=f"📋 Leave Information - {user_data['name']}",
                description=f"**Discord:** {user.mention}\n**Department:** {user_data['department'] or 'N/A'}\n**Position:** {user_data['position'] or 'N/A'}",
                color=discord.Color.blue()
            )

            # Add pending leaves balance
            pending_leaves = user_data['pending_leaves']
            if pending_leaves > 10:
                balance_color = "🟢"
            elif pending_leaves > 5:
                balance_color = "🟡"
            else:
                balance_color = "🔴"

            embed.add_field(
                name="💼 Leave Balance",
                value=(
                    f"{balance_color} **Pending Paid Leaves:** {pending_leaves} day(s)\n"
                    f"**Contract Started:** {user_data['contract_started_at'].strftime('%d/%m/%Y') if user_data['contract_started_at'] else 'N/A'}"
                ),
                inline=False
            )

            # Add leave history
            if not leave_requests:
                embed.add_field(
                    name="📜 Leave History",
                    value="No leave requests found.",
                    inline=False
                )
            else:
                # Count leave types
                leave_stats = {
                    'approved': 0,
                    'pending': 0,
                    'rejected': 0,
                    'paid_leave': 0,
                    'sick_leave': 0,
                    'non_compliant': 0,
                    'emergency_leave': 0
                }

                for req in leave_requests:
                    leave_stats[req['status']] += 1
                    if req['leave_type'] in leave_stats:
                        leave_stats[req['leave_type']] += 1

                embed.add_field(
                    name="📊 Leave Statistics (Last 10 Requests)",
                    value=(
                        f"**Status:**\n"
                        f"✅ Approved: {leave_stats['approved']}\n"
                        f"⏳ Pending: {leave_stats['pending']}\n"
                        f"❌ Rejected: {leave_stats['rejected']}\n\n"
                        f"**Types:**\n"
                        f"💰 Paid Leave: {leave_stats['paid_leave']}\n"
                        f"🤒 Sick Leave: {leave_stats['sick_leave']}\n"
                        f"⚠️ Non-compliant: {leave_stats['non_compliant']}\n"
                        f"🚨 Emergency: {leave_stats['emergency_leave']}"
                    ),
                    inline=False
                )

                embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

                # Show recent leave requests
                status_emoji = {
                    "pending": "⏳",
                    "approved": "✅",
                    "rejected": "❌"
                }

                for idx, req in enumerate(leave_requests[:5], 1):  # Show only top 5 in detail
                    leave_type_display = {
                        "non_compliant": "⚠️ Non-compliant",
                        "paid_leave": "💰 Paid Leave",
                        "sick_leave": "🤒 Sick Leave",
                        "half_day": "⏰ Half-Day Leave",
                        "half_day_paid": "💰 Paid Half-Day",
                        "half_day_unpaid": "📝 Unpaid Half-Day",
                        "half_day_non_compliant": "⚠️ Non-compliant Half-Day",
                        "emergency_leave": "🚨 Emergency Leave",
                        "unpaid_leave": "📝 Unpaid Leave"
                    }.get(req['leave_type'], req['leave_type'])

                    status = req['status']
                    emoji = status_emoji.get(status, "❓")

                    # Calculate duration
                    if req['duration_hours']:
                        duration_str = f"{req['duration_hours']} hour(s)"
                    else:
                        days = (req['end_date'] - req['start_date']).days + 1
                        duration_str = f"{days} day(s)"

                    field_value = (
                        f"**Type:** {leave_type_display}\n"
                        f"**Status:** {emoji} {status.capitalize()}\n"
                        f"**Period:** {req['start_date'].strftime('%d/%m/%Y')} → {req['end_date'].strftime('%d/%m/%Y')}\n"
                        f"**Duration:** {duration_str}\n"
                        f"**Reason:** {req['reason'][:100]}{'...' if len(req['reason']) > 100 else ''}\n"
                        f"**Requested:** {req['created_at'].strftime('%d/%m/%Y %H:%M')}"
                    )

                    embed.add_field(
                        name=f"Request #{req['leave_request_id']}",
                        value=field_value,
                        inline=False
                    )

                if len(leave_requests) > 5:
                    embed.add_field(
                        name="\u200b",
                        value=f"*... and {len(leave_requests) - 5} more requests (use limit parameter to see more)*",
                        inline=False
                    )

            embed.set_footer(text=f"Requested by {interaction.user.name}")
            embed.timestamp = datetime.now(pytz.UTC)

            await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    # ==================== ATTENDANCE DETAILS ====================
    @app_commands.command(
        name="attendance_details",
        description="View attendance details for a specific date (ADMIN+)"
    )
    @app_commands.describe(
        date="Date to check attendance (DD/MM/YYYY format)"
    )
    async def attendance_details(self, interaction: discord.Interaction, date: str):
        """Show who is present and absent on a specific date"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view attendance details!",
                ephemeral=True
            )
            return
        
        try:
            # Parse date
            try:
                date_obj = datetime.strptime(date, '%d/%m/%Y').date()
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid date format! Please use DD/MM/YYYY format.",
                    ephemeral=True
                )
                return
            
            # Get all active users
            all_users = await UserModel.get_all_users(include_deleted=False)
            
            # Get users on leave for this date
            users_on_leave = await LeaveRequestModel.get_users_on_leave_for_date(date_obj)
            on_leave_user_ids = {user['user_id'] for user in users_on_leave}
            
            # Separate present and absent
            absent_users = []
            present_users = []
            
            for user in all_users:
                user_dict = dict(user)
                if user_dict['user_id'] in on_leave_user_ids:
                    # Find the leave details for this user
                    leave_info = next((u for u in users_on_leave if u['user_id'] == user_dict['user_id']), None)
                    absent_users.append({
                        'user': user_dict,
                        'leave_info': leave_info
                    })
                else:
                    present_users.append(user_dict)
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 Attendance Details - {date_obj.strftime('%d/%m/%Y')}",
                description=f"**Total Employees:** {len(all_users)} | **Present:** {len(present_users)} | **Absent:** {len(absent_users)}",
                color=discord.Color.blue()
            )
            
            # Add absent users
            if absent_users:
                absent_list = []
                for item in absent_users[:20]:  # Limit to 20 to avoid embed limits
                    user = item['user']
                    leave = item['leave_info']
                    
                    leave_type_display = {
                        "non_compliant": "⚠️ Non-compliant",
                        "paid_leave": "💰 Paid Leave",
                        "sick_leave": "🤒 Sick Leave",
                        "half_day": "⏰ Half-Day Leave",
                        "emergency_leave": "🚨 Emergency Leave",
                        "unpaid_leave": "📝 Unpaid Leave"
                    }.get(leave['leave_type'], leave['leave_type'])
                    
                    status_emoji = "✅" if leave['status'] == 'approved' else "⏳"
                    
                    start_date_str = leave['start_date'].strftime('%d/%m/%Y') if hasattr(leave['start_date'], 'strftime') else str(leave['start_date'])
                    leave_dates = start_date_str
                    if leave['end_date'] and leave['end_date'] != leave['start_date']:
                        end_date_str = leave['end_date'].strftime('%d/%m/%Y') if hasattr(leave['end_date'], 'strftime') else str(leave['end_date'])
                        leave_dates += f" to {end_date_str}"
                    
                    absent_list.append(
                        f"**{user['name']}** ({user['department'] or 'N/A'})\n"
                        f"  {leave_type_display} {status_emoji} | {leave_dates}"
                    )
                
                if len(absent_users) > 20:
                    absent_list.append(f"\n*... and {len(absent_users) - 20} more*")
                
                embed.add_field(
                    name=f"❌ Absent ({len(absent_users)})",
                    value="\n".join(absent_list) if absent_list else "None",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"❌ Absent (0)",
                    value="No employees are on leave.",
                    inline=False
                )
            
            # Add present users
            if present_users:
                present_list = []
                for user in present_users[:20]:  # Limit to 20
                    present_list.append(f"**{user['name']}** ({user['department'] or 'N/A'})")
                
                if len(present_users) > 20:
                    present_list.append(f"\n*... and {len(present_users) - 20} more*")
                
                embed.add_field(
                    name=f"✅ Present ({len(present_users)})",
                    value="\n".join(present_list) if present_list else "None",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"✅ Present (0)",
                    value="No employees are present.",
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


   
async def setup(bot):
    await bot.add_cog(LeaveManagement(bot))
