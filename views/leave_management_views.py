"""Views for leave management UI components"""
import discord
from discord import ui
from datetime import datetime, timedelta
from models.user_model import UserModel
from models.leave_model import LeaveRequestModel


class LeaveTypeSelectView(discord.ui.View):
    """Select leave type"""
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_leave_type = None
    
    @discord.ui.select(
        placeholder="Select Leave Type",
        options=[
            discord.SelectOption(
                label="Paid Leave",
                value="paid_leave",
                emoji="💰",
                description="Must be requested at least 2 weeks in advance"
            ),
            discord.SelectOption(
                label="Sick Leave",
                value="sick_leave",
                emoji="🤒",
                description="Notify immediately and inform HR/CEO"
            ),
            discord.SelectOption(
                label="Half-Day Leave",
                value="half_day",
                emoji="⏰",
                description="Up to 2 hours permitted with prior approval"
            ),
            discord.SelectOption(
                label="Emergency Leave",
                value="emergency_leave",
                emoji="🚨",
                description="Inform ASAP with valid reason"
            ),
        ]
    )
    async def leave_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_leave_type = select.values[0]

        # Show appropriate modal based on leave type
        if self.selected_leave_type == "paid_leave":
            modal = PaidLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "sick_leave":
            # Directly show sick leave modal - no documentation question
            modal = SickLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "half_day":
            modal = HalfDayLeaveModal()
            await interaction.response.send_modal(modal)
        else:  # emergency_leave
            modal = EmergencyLeaveModal()
            await interaction.response.send_modal(modal)

        self.stop()


class PaidLeaveModal(discord.ui.Modal, title="Paid Leave Request"):
    """Modal for paid leave request"""
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="YYYY-MM-DD (must be 2+ weeks from today)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    end_date = discord.ui.TextInput(
        label="End Date",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    reason = discord.ui.TextInput(
        label="Reason for Leave",
        placeholder="Enter your reason...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate dates
            start = datetime.strptime(self.start_date.value, "%Y-%m-%d")
            end = datetime.strptime(self.end_date.value, "%Y-%m-%d")
            today = datetime.now()
            
            # Check if at least 2 weeks in advance
            days_advance = (start - today).days
            if days_advance < 14:
                await interaction.response.send_message(
                    f"❌ Paid leave must be requested at least 2 weeks in advance!\n"
                    f"Current date: {today.strftime('%Y-%m-%d')}\n"
                    f"Your requested date: {self.start_date.value}\n"
                    f"Days in advance: {days_advance} (minimum required: 14)",
                    ephemeral=True
                )
                return
            
            if end < start:
                await interaction.response.send_message(
                    "❌ End date must be after start date!",
                    ephemeral=True
                )
                return

            # Calculate requested duration
            duration = (end - start).days + 1
            if duration <= 0:
                await interaction.response.send_message(
                    "❌ Duration must be at least 1 day.",
                    ephemeral=True
                )
                return

            # Check user's remaining paid leaves
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.response.send_message(
                    "❌ You are not registered in the system! Please contact an admin.",
                    ephemeral=True
                )
                return

            pending_leaves = user.get('pending_leaves', 0)
            if pending_leaves is None:
                pending_leaves = 0

            if duration > pending_leaves:
                await interaction.response.send_message(
                    f"❌ You don't have enough paid leave balance.\n"
                    f"Requested: **{duration}** day(s)\n"
                    f"Available: **{pending_leaves}** day(s)",
                    ephemeral=True
                )
                return

            # Show confirmation
            view = ConfirmLeaveView("paid_leave", self.start_date.value, self.end_date.value, 
                                   None, self.reason.value, duration)
            
            embed = discord.Embed(
                title="📋 Paid Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="💰 Leave Type", value="Paid Leave", inline=True)
            embed.add_field(name="📅 Start Date", value=self.start_date.value, inline=True)
            embed.add_field(name="📅 End Date", value=self.end_date.value, inline=True)
            embed.add_field(name="📊 Duration", value=f"{duration} day(s)", inline=True)
            embed.add_field(name="✏️ Reason", value=self.reason.value, inline=False)
            embed.add_field(
                name="⚠️ Important",
                value="Your request requires manager approval. You'll be notified once reviewed.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class SickLeaveModal(discord.ui.Modal, title="Sick Leave Request"):
    """Modal for sick leave request - simplified without document upload"""

    def __init__(self):
        super().__init__()

    date = discord.ui.TextInput(
        label="Start Date",
        placeholder="YYYY-MM-DD (past 3 days, today, or tomorrow max)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )

    reason = discord.ui.TextInput(
        label="Reason/Illness Description",
        placeholder="Describe your illness or reason...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    end_date = discord.ui.TextInput(
        label="End Date (optional, max 7 days)",
        placeholder="YYYY-MM-DD (blank = single day only)",
        required=False,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate start date
            date_obj = datetime.strptime(self.date.value, "%Y-%m-%d")
            today = datetime.now()
            today_date = today.date()
            request_date = date_obj.date()
            
            # Calculate date range for past dates
            three_days_ago = (today - timedelta(days=3)).date()
            tomorrow = (today + timedelta(days=1)).date()
            
            # Validate start date
            if request_date < three_days_ago:
                await interaction.response.send_message(
                    f"❌ **Invalid Start Date!**\n"
                    f"Sick leave can be requested from the last 3 days onwards.\n"
                    f"**Earliest date allowed:** {three_days_ago}\n"
                    f"**Your requested date:** {self.date.value}",
                    ephemeral=True
                )
                return
            
            # For future dates, only allow today or tomorrow
            if request_date > tomorrow:
                await interaction.response.send_message(
                    f"❌ **Invalid Future Date!**\n"
                    f"Sick leave for future dates can only be requested for today or tomorrow.\n"
                    f"**Today:** {today_date}\n"
                    f"**Tomorrow:** {tomorrow}\n"
                    f"**Your requested date:** {self.date.value}\n"
                    f"For sick leave beyond tomorrow, please contact your manager directly.",
                    ephemeral=True
                )
                return
            
            # If future date, check 2-hour advance notice (before 10 AM)
            if request_date > today_date:
                # Calculate 10 AM on the requested date
                ten_am_on_request_date = datetime.combine(request_date, datetime.min.time().replace(hour=10))
                # Must request at least 2 hours before 10 AM
                deadline = ten_am_on_request_date - timedelta(hours=2)
                
                if today > deadline:
                    await interaction.response.send_message(
                        f"❌ **Too Late to Request!**\n"
                        f"For future sick leave, you must request at least 2 hours before 10:00 AM of the requested date.\n"
                        f"**Requested date:** {self.date.value}\n"
                        f"**Deadline:** {deadline.strftime('%Y-%m-%d %H:%M')}\n"
                        f"**Current time:** {today.strftime('%Y-%m-%d %H:%M')}\n"
                        f"Please contact your manager directly if this is an emergency.",
                        ephemeral=True
                    )
                    return
            
            # Handle end date (optional, for both past and future dates)
            end_date_str = self.end_date.value.strip() if self.end_date.value else None
            end_date = None
            duration_days = 1
            
            if end_date_str:
                # Multi-day sick leave
                try:
                    end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Invalid end date format! Please use YYYY-MM-DD",
                        ephemeral=True
                    )
                    return
                
                # Validate end date
                if end_date_obj < request_date:
                    await interaction.response.send_message(
                        f"❌ **Invalid End Date!**\n"
                        f"End date must be the same as or after the start date.\n"
                        f"**Start date:** {self.date.value}\n"
                        f"**End date:** {end_date_str}",
                        ephemeral=True
                    )
                    return
                
                # Check duration (max 7 days)
                duration_days = (end_date_obj - request_date).days + 1
                if duration_days > 7:
                    await interaction.response.send_message(
                        f"❌ **Duration Too Long!**\n"
                        f"Sick leave duration cannot exceed 7 days.\n"
                        f"**Your requested duration:** {duration_days} days\n"
                        f"**Maximum allowed:** 7 days\n"
                        f"Please reduce the end date.",
                        ephemeral=True
                    )
                    return
                
                end_date = end_date_obj
            else:
                # Single day sick leave (default)
                end_date = request_date
            
            # Show confirmation
            view = ConfirmLeaveView("sick_leave", self.date.value, end_date.strftime("%Y-%m-%d"),
                                   None, self.reason.value, duration_days)
            
            # Determine if past or future
            if request_date < today_date:
                date_type = f"📅 Past ({(today_date - request_date).days} day(s) ago)"
            elif request_date == today_date:
                date_type = "📅 Today"
            else:
                date_type = f"📅 Future (Tomorrow)"
            
            embed = discord.Embed(
                title="📋 Sick Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="🤒 Leave Type", value="Sick Leave", inline=True)
            embed.add_field(name="Date Type", value=date_type, inline=True)
            embed.add_field(name="📅 From", value=self.date.value, inline=True)
            embed.add_field(name="📅 To", value=end_date.strftime("%Y-%m-%d"), inline=True)
            embed.add_field(name="⏱️ Duration", value=f"{duration_days} day(s)", inline=True)
            embed.add_field(name="📝 Reason", value=self.reason.value, inline=False)
            embed.add_field(
                name="⚠️ Important - Please Inform HR/CEO",
                value=(
                    "**You must notify HR or CEO immediately about your sick leave.**\n\n"
                    "• If you have medical documentation (doctor's note, prescription, medical report), "
                    "please share it with HR or CEO.\n"
                    "• If you don't have documentation, still inform HR or CEO about your absence."
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        except ValueError as e:
            if "time data" in str(e):
                await interaction.response.send_message(
                    "❌ Invalid date format! Please use YYYY-MM-DD",
                    ephemeral=True
                )
            else:
                raise
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class HalfDayLeaveModal(discord.ui.Modal, title="Half-Day Leave Request"):
    """Modal for half-day leave request"""
    date = discord.ui.TextInput(
        label="Date of Half-Day Leave",
        placeholder="YYYY-MM-DD",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    duration = discord.ui.TextInput(
        label="Duration (in hours)",
        placeholder="Maximum 2 hours (e.g., 1, 1.5, 2)",
        required=True,
        max_length=4,
        style=discord.TextStyle.short
    )
    
    reason = discord.ui.TextInput(
        label="Reason for Half-Day Leave",
        placeholder="Enter your reason...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate date
            date_obj = datetime.strptime(self.date.value, "%Y-%m-%d")
            today = datetime.now()
            today_date = today.date()
            request_date = date_obj.date()
            
            # Validate that date is not in the past
            if request_date < today_date:
                await interaction.response.send_message(
                    f"❌ **Invalid Date!**\n"
                    f"Half-day leave can only be requested for today or future dates.\n"
                    f"**Today:** {today_date.strftime('%Y-%m-%d')}\n"
                    f"**Your requested date:** {self.date.value}\n"
                    f"Please select today or a future date.",
                    ephemeral=True
                )
                return
            
            # Validate duration
            try:
                hours = float(self.duration.value)
            except ValueError:
                await interaction.response.send_message(
                    "❌ Duration must be a valid number (e.g., 1, 1.5, 2)",
                    ephemeral=True
                )
                return
            
            if hours > 2:
                await interaction.response.send_message(
                    f"❌ Half-day leave cannot exceed 2 hours!\n"
                    f"You requested: {hours} hours",
                    ephemeral=True
                )
                return
            
            if hours <= 0:
                await interaction.response.send_message(
                    "❌ Duration must be greater than 0 hours!",
                    ephemeral=True
                )
                return
            
            # Validate advance notice for present day requests
            if request_date == today_date:
                # Calculate 7 PM today
                seven_pm_today = datetime.combine(today_date, datetime.min.time().replace(hour=19, minute=0))
                # Calculate deadline: X hours before 7 PM (where X = duration)
                deadline = seven_pm_today - timedelta(hours=hours)
                
                # Check if current time is before the deadline
                if today >= deadline:
                    hours_short = (today - deadline).total_seconds() / 3600
                    await interaction.response.send_message(
                        f"❌ **Too Late to Request!**\n"
                        f"For a {hours}-hour half-day leave today, you must request at least **{hours} hour(s) before 7:00 PM**.\n"
                        f"**Requested date:** {self.date.value} (Today)\n"
                        f"**Duration:** {hours} hour(s)\n"
                        f"**Deadline:** {deadline.strftime('%Y-%m-%d %I:%M %p')}\n"
                        f"**Current time:** {today.strftime('%Y-%m-%d %I:%M %p')}\n"
                        f"**You are {hours_short:.1f} hour(s) late!**\n\n"
                        f"Please contact your manager directly if this is urgent.",
                        ephemeral=True
                    )
                    return
            
            # Show confirmation
            view = ConfirmLeaveView("half_day", self.date.value, self.date.value, 
                                   hours, self.reason.value)
            
            embed = discord.Embed(
                title="📋 Half-Day Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="⏰ Leave Type", value="Half-Day Leave", inline=True)
            embed.add_field(name="📅 Date", value=self.date.value, inline=True)
            embed.add_field(name="⏱️ Duration", value=f"{hours} hour(s)", inline=True)
            embed.add_field(name="✏️ Reason", value=self.reason.value, inline=False)
            # Add validation info based on date
            if request_date == today_date:
                deadline = datetime.combine(today_date, datetime.min.time().replace(hour=19, minute=0)) - timedelta(hours=hours)
                embed.add_field(
                    name="⚠️ Important",
                    value=(
                        f"Half-day leave requires prior approval from your manager.\n"
                        f"**Advance Notice:** Requested at least {hours} hour(s) before 7:00 PM (deadline: {deadline.strftime('%I:%M %p')})"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="⚠️ Important",
                    value="Half-day leave requires prior approval from your manager.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        except ValueError as ve:
            if "time data" in str(ve):
                await interaction.response.send_message(
                    "❌ Invalid date format! Please use YYYY-MM-DD",
                    ephemeral=True
                )
            else:
                raise
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class EmergencyLeaveModal(discord.ui.Modal, title="Emergency Leave Request"):
    """Modal for emergency leave request"""
    date = discord.ui.TextInput(
        label="Date of Emergency Leave",
        placeholder="YYYY-MM-DD (or 'today' for immediate leave)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    reason = discord.ui.TextInput(
        label="Valid Reason for Emergency",
        placeholder="Describe the emergency situation...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    contact_status = discord.ui.TextInput(
        label="Have you informed your employer?",
        placeholder="Yes/No",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate date
            today = datetime.now()
            today_date = today.date()
            
            if self.date.value.lower() == "today":
                date_obj = today
                request_date = today_date
                date_str = today_date.strftime("%Y-%m-%d")
            else:
                date_obj = datetime.strptime(self.date.value, "%Y-%m-%d")
                request_date = date_obj.date()
                date_str = self.date.value
            
            # Validate that date is not in the past
            if request_date < today_date:
                await interaction.response.send_message(
                    f"❌ **Invalid Date!**\n"
                    f"Emergency leave cannot be requested for previous days.\n"
                    f"**Today:** {today_date.strftime('%Y-%m-%d')}\n"
                    f"**Your requested date:** {date_str}\n"
                    f"Please select today or a future date for emergency leave.",
                    ephemeral=True
                )
                return
            
            # Check if employer informed
            informed = self.contact_status.value.lower() in ["yes", "y"]
            
            if not informed:
                await interaction.response.send_message(
                    "⚠️ **IMPORTANT**: You MUST inform your employer immediately about the emergency!\n"
                    "Emergency leave requires immediate notification to your manager/admin.",
                    ephemeral=True
                )
                return
            
            # Show confirmation
            view = ConfirmLeaveView("emergency_leave", date_str, date_str, 
                                   None, self.reason.value)
            
            embed = discord.Embed(
                title="📋 Emergency Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.red()
            )
            embed.add_field(name="🚨 Leave Type", value="Emergency Leave", inline=True)
            embed.add_field(name="📅 Date", value=date_str, inline=True)
            embed.add_field(name="📝 Emergency Reason", value=self.reason.value, inline=False)
            embed.add_field(
                name="✅ Employer Notified",
                value="Yes - Immediately",
                inline=True
            )
            embed.add_field(
                name="⚠️ Important",
                value="Please ensure your manager/admin has been informed. This is a critical requirement.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD or type 'today'",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class ConfirmLeaveView(discord.ui.View):
    """Confirmation view for leave request"""
    def __init__(self, leave_type: str, start_date: str, end_date: str,
                 duration_hours: float = None, reason: str = None, duration_days: int = 1):
        super().__init__(timeout=180)
        self.leave_type = leave_type
        self.start_date = start_date
        self.end_date = end_date
        self.duration_hours = duration_hours
        self.reason = reason
        self.duration_days = duration_days
    
    @discord.ui.button(label="Submit Request", style=discord.ButtonStyle.success, emoji="✅")
    async def submit_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get user from database
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not user:
                await interaction.response.send_message(
                    "❌ User not found in database!",
                    ephemeral=True
                )
                return
            
            # Convert string dates to date objects
            start_date_obj = datetime.strptime(self.start_date, "%Y-%m-%d").date()
            end_date_obj = datetime.strptime(self.end_date, "%Y-%m-%d").date()
            
            # Create leave request in database (without document_url)
            leave_request_id = await LeaveRequestModel.create_leave_request(
                user_id=user['user_id'],
                leave_type=self.leave_type,
                start_date=start_date_obj,
                end_date=end_date_obj,
                duration_hours=self.duration_hours,
                reason=self.reason,
                approval_required=True
            )
            
            # Get leave type display name
            leave_type_display = {
                "paid_leave": "💰 Paid Leave",
                "sick_leave": "🤒 Sick Leave",
                "half_day": "⏰ Half-Day Leave",
                "emergency_leave": "🚨 Emergency Leave"
            }.get(self.leave_type, self.leave_type)
            
            # Send success message
            embed = discord.Embed(
                title="✅ Leave Request Submitted Successfully!",
                description=f"Your {leave_type_display} request has been submitted for approval.",
                color=discord.Color.green()
            )
            embed.add_field(name="Request ID", value=f"`{leave_request_id}`", inline=False)
            embed.add_field(name="Leave Type", value=leave_type_display, inline=True)
            embed.add_field(name="From", value=self.start_date, inline=True)
            embed.add_field(name="To", value=self.end_date, inline=True)
            
            if self.duration_hours:
                embed.add_field(name="Duration", value=f"{self.duration_hours} hour(s)", inline=True)
            else:
                embed.add_field(name="Duration", value=f"{self.duration_days} day(s)", inline=True)
            
            embed.add_field(name="Status", value="⏳ Pending Review", inline=False)
            
            # Add special message for sick leave
            if self.leave_type == "sick_leave":
                embed.add_field(
                    name="📬 Next Steps",
                    value=(
                        "**Remember to inform HR or CEO directly!**\n\n"
                        "• If you have medical documentation, share it with HR/CEO\n"
                        "• Your manager will review your request\n"
                        "• Check status using `/my_leaves` command"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📬 Next Steps",
                    value="Your manager will review your request. You can check the status using `/my_leaves` command.",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            self.stop()
        
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error submitting request: {str(e)}",
                ephemeral=True
            )
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "❌ Leave request cancelled.",
            ephemeral=True
        )
        self.stop()


class ReviewLeaveRequestsView(discord.ui.View):
    """Admin view to approve or reject pending leave requests"""
    def __init__(self, pending_requests, reviewer_discord_id: int):
        super().__init__(timeout=300)
        self.reviewer_discord_id = reviewer_discord_id
        self.selected_request_id = None

        options = []
        leave_type_display = {
            "paid_leave": "Paid",
            "sick_leave": "Sick",
            "half_day": "Half-Day",
            "emergency_leave": "Emergency"
        }

        for req in pending_requests:
            label = f"ID {req['leave_request_id']} • {leave_type_display.get(req['leave_type'], req['leave_type'])}"
            description = f"{req['name']} • {req['start_date']} to {req['end_date']}"
            options.append(discord.SelectOption(
                label=label[:100],
                value=str(req['leave_request_id']),
                description=description[:100]
            ))

        self.leave_select = discord.ui.Select(
            placeholder="Select a leave request",
            options=options,
            min_values=1,
            max_values=1
        )
        self.leave_select.callback = self.on_select
        self.add_item(self.leave_select)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.reviewer_discord_id:
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can review requests.",
                ephemeral=True
            )
            return

        self.selected_request_id = int(self.leave_select.values[0])
        await interaction.response.send_message(
            f"ℹ️ Selected request **#{self.selected_request_id}**. Choose Approve or Reject.",
            ephemeral=True
        )

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.reviewer_discord_id

    async def _ensure_selection(self, interaction: discord.Interaction) -> bool:
        if not self.selected_request_id:
            await interaction.response.send_message(
                "❌ Please select a leave request first.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can approve requests.",
                ephemeral=True
            )
            return

        if not await self._ensure_selection(interaction):
            return

        try:
            admin_user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not admin_user:
                await interaction.response.send_message(
                    "❌ Unable to find your admin record in the system.",
                    ephemeral=True
                )
                return

            request = await LeaveRequestModel.get_leave_request(self.selected_request_id)
            if not request:
                await interaction.response.send_message(
                    "❌ Leave request not found. Try refreshing with the command again.",
                    ephemeral=True
                )
                return

            if request['status'] != 'pending':
                await interaction.response.send_message(
                    f"ℹ️ Request #{self.selected_request_id} is already {request['status']}.",
                    ephemeral=True
                )
                return

            success = await LeaveRequestModel.approve_leave_request(
                self.selected_request_id,
                admin_user['user_id']
            )

            if success:
                if request['leave_type'] == 'paid_leave':
                    start_date = request['start_date']
                    end_date = request['end_date']
                    if isinstance(start_date, datetime):
                        start_date = start_date.date()
                    if isinstance(end_date, datetime):
                        end_date = end_date.date()
                    duration_days = (end_date - start_date).days + 1
                    await LeaveRequestModel.deduct_pending_leave(
                        request['user_id'],
                        max(duration_days, 1)
                    )

                await interaction.response.send_message(
                    f"✅ Approved leave request #{self.selected_request_id}.",
                    ephemeral=True
                )
                self.stop()
            else:
                await interaction.response.send_message(
                    "❌ Failed to approve request. Please try again.",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error approving request: {e}",
                ephemeral=True
            )

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="🛑")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can reject requests.",
                ephemeral=True
            )
            return

        if not await self._ensure_selection(interaction):
            return

        modal = RejectLeaveModal(self)
        await interaction.response.send_modal(modal)


class RejectLeaveModal(discord.ui.Modal, title="Reject Leave Request"):
    """Modal to capture rejection reason"""
    reason = discord.ui.TextInput(
        label="Rejection Reason",
        placeholder="Provide a short reason",
        required=True,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, parent_view: ReviewLeaveRequestsView):
        super().__init__(timeout=180)
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.reviewer_discord_id:
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can reject requests.",
                ephemeral=True
            )
            return

        request_id = self.parent_view.selected_request_id
        if not request_id:
            await interaction.response.send_message(
                "❌ No request selected. Please select a request and try again.",
                ephemeral=True
            )
            return

        try:
            request = await LeaveRequestModel.get_leave_request(request_id)
            if not request:
                await interaction.response.send_message(
                    "❌ Leave request not found. Try refreshing with the command again.",
                    ephemeral=True
                )
                return

            if request['status'] != 'pending':
                await interaction.response.send_message(
                    f"ℹ️ Request #{request_id} is already {request['status']}.",
                    ephemeral=True
                )
                return

            success = await LeaveRequestModel.reject_leave_request(
                request_id,
                self.reason.value
            )

            if success:
                await interaction.response.send_message(
                    f"🛑 Rejected leave request #{request_id}.",
                    ephemeral=True
                )
                self.parent_view.stop()
            else:
                await interaction.response.send_message(
                    "❌ Failed to reject request. Please try again.",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error rejecting request: {e}",
                ephemeral=True
            )