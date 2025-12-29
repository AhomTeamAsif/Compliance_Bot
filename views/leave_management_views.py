"""Views for leave management UI components"""
import discord
from discord import ui
from datetime import datetime, timedelta
from models.user_model import UserModel
from models.leave_model import LeaveRequestModel
from models.settings_model import SettingsModel


class LeaveTypeSelectView(discord.ui.View):
    """Select leave type"""
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_leave_type = None
    
    @discord.ui.select(
        placeholder="Select Leave Type",
        options=[
            discord.SelectOption(
                label="Non-compliant",
                value="non_compliant",
                emoji="⚠️",
                description="Request 14 to 1 day before the off day"
            ),
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
                label="Emergency Leave",
                value="emergency_leave",
                emoji="🚨",
                description="Inform ASAP with valid reason"
            ),
            discord.SelectOption(
                label="Unpaid Leave",
                value="unpaid_leave",
                emoji="📝",
                description="Unpaid leave request"
            ),
        ]
    )
    async def leave_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_leave_type = select.values[0]

        # Show appropriate modal based on leave type
        if self.selected_leave_type == "non_compliant":
            modal = NonCompliantLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "paid_leave":
            modal = PaidLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "sick_leave":
            # Directly show sick leave modal - no documentation question
            modal = SickLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "emergency_leave":
            modal = EmergencyLeaveModal()
            await interaction.response.send_modal(modal)
        elif self.selected_leave_type == "unpaid_leave":
            modal = UnpaidLeaveModal()
            await interaction.response.send_modal(modal)

        self.stop()


class PaidLeaveModal(discord.ui.Modal, title="Paid Leave Request"):
    """Modal for paid leave request"""
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="DD/MM/YYYY (must be 2+ weeks from today)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    end_date = discord.ui.TextInput(
        label="End Date",
        placeholder="DD/MM/YYYY",
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
            start = datetime.strptime(self.start_date.value, "%d/%m/%Y")
            end = datetime.strptime(self.end_date.value, "%d/%m/%Y")
            today = datetime.now()
            
            # Check if at least 2 weeks in advance
            days_advance = (start - today).days
            if days_advance < 14:
                await interaction.response.send_message(
                    f"❌ Paid leave must be requested at least 2 weeks in advance!\n"
                    f"Current date: {today.strftime('%d/%m/%Y')}\n"
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
                "❌ Invalid date format! Please use DD/MM/YYYY",
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
        placeholder="DD/MM/YYYY",
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
        placeholder="DD/MM/YYYY (blank = single day only)",
        required=False,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate start date
            date_obj = datetime.strptime(self.date.value, "%d/%m/%Y")
            today = datetime.now()
            today_date = today.date()
            request_date = date_obj.date()
            
            # Enforce configurable window: from EARLY hours to LATE hours before anchor time on the requested date
            settings = await SettingsModel.get_sick_leave_settings()
            from config import Config
            anchor_hour = settings.get('anchor_hour') or Config.SICK_LEAVE_ANCHOR_HOUR
            early_hours = settings.get('early_hours') or Config.SICK_LEAVE_EARLY_HOURS
            late_hours = settings.get('late_hours') or Config.SICK_LEAVE_LATE_HOURS
            anchor_dt = datetime.combine(request_date, datetime.min.time().replace(hour=anchor_hour))
            window_start = anchor_dt - timedelta(hours=early_hours)
            window_end = anchor_dt - timedelta(hours=late_hours)
            
            # Current time must be within [window_start, window_end]
            if not (window_start <= today <= window_end):
                await interaction.response.send_message(
                    f"❌ **Outside Allowed Window!**\n"
                    f"You can apply for sick leave for **{self.date.value}** only between "
                    f"**{window_start.strftime('%d/%m/%Y %I:%M %p')}** and **{window_end.strftime('%d/%m/%Y %I:%M %p')}**.\n"
                    f"(Window: {early_hours}h to {late_hours}h before "
                    f"{anchor_hour:02d}:00)",
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
                    end_date_obj = datetime.strptime(end_date_str, "%d/%m/%Y").date()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Invalid end date format! Please use DD/MM/YYYY",
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
            view = ConfirmLeaveView("sick_leave", self.date.value, end_date.strftime("%d/%m/%Y"),
                                   None, self.reason.value, duration_days)
            
            embed = discord.Embed(
                title="📋 Sick Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="🤒 Leave Type", value="Sick Leave", inline=True)
            embed.add_field(name="📅 From", value=self.date.value, inline=True)
            embed.add_field(name="📅 To", value=end_date.strftime("%d/%m/%Y"), inline=True)
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
                    "❌ Invalid date format! Please use DD/MM/YYYY",
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
        placeholder="DD/MM/YYYY",
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
            date_obj = datetime.strptime(self.date.value, "%d/%m/%Y")
            today = datetime.now()
            today_date = today.date()
            request_date = date_obj.date()
            
            # Validate that date is not in the past
            if request_date < today_date:
                await interaction.response.send_message(
                    f"❌ **Invalid Date!**\n"
                    f"Half-day leave can only be requested for today or future dates.\n"
                    f"**Today:** {today_date.strftime('%d/%m/%Y')}\n"
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
                        f"**Deadline:** {deadline.strftime('%d/%m/%Y %I:%M %p')}\n"
                        f"**Current time:** {today.strftime('%d/%m/%Y %I:%M %p')}\n"
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
                    "❌ Invalid date format! Please use DD/MM/YYYY",
                    ephemeral=True
                )
            else:
                raise
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class EmergencyLeaveModal(discord.ui.Modal, title="Emergency Leave Request"):
    """Modal for emergency leave request"""
    reason = discord.ui.TextInput(
        label="Valid Reason for Emergency",
        placeholder="Describe the emergency situation...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph
    )
    
    leaving_time = discord.ui.TextInput(
        label="Planned Leaving Time (HH:MM, 24-hour)",
        placeholder="e.g., 15:30",
        required=True,
        max_length=5,
        style=discord.TextStyle.short
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
            today = datetime.now()
            today_date = today.date()
            request_date = today_date
            date_str = today_date.strftime("%d/%m/%Y")
            
            # Validate leaving time and ensure at least 30 minutes lead
            try:
                leave_time_obj = datetime.strptime(self.leaving_time.value.strip(), "%H:%M").time()
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid time format! Please use HH:MM in 24-hour format (e.g., 15:30).",
                    ephemeral=True
                )
                return
            
            leaving_dt = datetime.combine(today_date, leave_time_obj)
            min_lead = today + timedelta(minutes=30)
            if leaving_dt <= min_lead:
                await interaction.response.send_message(
                    f"❌ You must request at least 30 minutes before your planned leaving time.\n"
                    f"**Current time:** {today.strftime('%d/%m/%Y %H:%M')}\n"
                    f"**Planned leaving:** {leaving_dt.strftime('%d/%m/%Y %H:%M')}\n"
                    f"**Earliest allowed request time for this leave:** {(leaving_dt - timedelta(minutes=30)).strftime('%d/%m/%Y %H:%M')}",
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
            embed.add_field(name="⏰ Planned Leaving Time", value=self.leaving_time.value.strip(), inline=True)
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
        
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class NonCompliantLeaveModal(discord.ui.Modal, title="Non-compliant Leave Request"):
    """Modal for non-compliant leave request"""
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="DD/MM/YYYY (must be 14 to 1 day before)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    end_date = discord.ui.TextInput(
        label="End Date (Optional)",
        placeholder="DD/MM/YYYY (leave blank for single day)",
        required=False,
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
    
    compensating_day = discord.ui.TextInput(
        label="Compensating Day (Optional)",
        placeholder="DD/MM/YYYY (leave blank if not compensating)",
        required=False,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate date
            today = datetime.now()
            today_date = today.date()
            start_date_obj = datetime.strptime(self.start_date.value, "%d/%m/%Y").date()
            
            # Handle end date
            if self.end_date.value.strip():
                try:
                    end_date_obj = datetime.strptime(self.end_date.value, "%d/%m/%Y").date()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Invalid end date format! Please use DD/MM/YYYY",
                        ephemeral=True
                    )
                    return
            else:
                end_date_obj = start_date_obj
                
            # Validate date order
            if end_date_obj < start_date_obj:
                await interaction.response.send_message(
                    "❌ End date must be on or after start date!",
                    ephemeral=True
                )
                return
            
            # Calculate days before the off day (14 to 1 day before)
            # We use start_date for this calculation
            days_before = (start_date_obj - today_date).days
            
            # Validate date range: must be 14 to 1 day before
            if days_before < 1 or days_before > 14:
                await interaction.response.send_message(
                    f"❌ **Invalid Date Range!**\n"
                    f"Non-compliant leave must be requested 14 to 1 day before the off day.\n"
                    f"**Today:** {today_date.strftime('%d/%m/%Y')}\n"
                    f"**Your requested start date:** {self.start_date.value}\n"
                    f"**Days before:** {days_before} (must be between 1 and 14 days)",
                    ephemeral=True
                )
                return
            
            # Validate compensating day if provided
            compensating_date = None
            if self.compensating_day.value.strip():
                try:
                    compensating_date = datetime.strptime(self.compensating_day.value, "%d/%m/%Y").date()
                    # Compensating day should be in the future
                    if compensating_date <= today_date:
                        await interaction.response.send_message(
                            f"❌ **Invalid Compensating Day!**\n"
                            f"Compensating day must be a future date.\n"
                            f"**Today:** {today_date.strftime('%d/%m/%Y')}\n"
                            f"**Your compensating day:** {self.compensating_day.value}",
                            ephemeral=True
                        )
                        return
                except ValueError:
                    await interaction.response.send_message(
                        "❌ Invalid compensating day format! Please use DD/MM/YYYY or leave blank.",
                        ephemeral=True
                    )
                    return
            
            # Check if proof is required (if applied at least 2 days before)
            proof_required = days_before >= 2
            
            # Show confirmation with proof requirement
            view = ConfirmNonCompliantLeaveView(
                self.start_date.value,
                end_date_obj.strftime("%d/%m/%Y"),
                self.reason.value,
                compensating_date.strftime("%d/%m/%Y") if compensating_date else None,
                proof_required,
                days_before
            )
            
            embed = discord.Embed(
                title="📋 Non-compliant Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.orange()
            )
            embed.add_field(name="⚠️ Leave Type", value="Non-compliant Leave", inline=True)
            embed.add_field(name="📅 Start Date", value=self.start_date.value, inline=True)
            embed.add_field(name="📅 End Date", value=end_date_obj.strftime("%d/%m/%Y"), inline=True)
            embed.add_field(name="📊 Days Before", value=f"{days_before} day(s)", inline=True)
            embed.add_field(name="✏️ Reason", value=self.reason.value, inline=False)
            
            if compensating_date:
                embed.add_field(name="🔄 Compensating Day", value=compensating_date.strftime("%d/%m/%Y"), inline=True)
            else:
                embed.add_field(name="🔄 Compensating Day", value="None", inline=True)
            
            if proof_required:
                embed.add_field(
                    name="📄 Proof Required",
                    value=(
                        "**You are expected to provide proof** since you're applying at least 2 days before.\n"
                        "Please send proof to HR/CEO and confirm when done."
                    ),
                    inline=False
                )
            
            embed.add_field(
                name="⚠️ Important",
                value="Your request requires manager approval. You'll be notified once reviewed.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use DD/MM/YYYY",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class UnpaidLeaveModal(discord.ui.Modal, title="Unpaid Leave Request"):
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="DD/MM/YYYY (must be 2+ weeks from today)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    end_date = discord.ui.TextInput(
        label="End Date",
        placeholder="DD/MM/YYYY",
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
            start = datetime.strptime(self.start_date.value, "%d/%m/%Y")
            end = datetime.strptime(self.end_date.value, "%d/%m/%Y")
            today = datetime.now()
            
            days_advance = (start - today).days
            if days_advance < 14:
                await interaction.response.send_message(
                    f"❌ Unpaid leave must be requested at least 2 weeks (14 days) in advance!\n"
                    f"Current date: {today.strftime('%d/%m/%Y')}\n"
                    f"Your requested start date: {self.start_date.value}\n"
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
            
            duration = (end - start).days + 1
            if duration <= 0:
                await interaction.response.send_message(
                    "❌ Duration must be at least 1 day.",
                    ephemeral=True
                )
                return
            
            view = ConfirmLeaveView("unpaid_leave", self.start_date.value, self.end_date.value, 
                                   None, self.reason.value, duration)
            
            embed = discord.Embed(
                title="📋 Unpaid Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="📝 Leave Type", value="Unpaid Leave", inline=True)
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
                "❌ Invalid date format! Please use DD/MM/YYYY",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)


class SickLeaveSettingsModal(discord.ui.Modal, title="Sick Leave Settings"):
    anchor_hour = discord.ui.TextInput(
        label="Anchor Hour (0-23)",
        placeholder="10",
        required=True,
        max_length=2,
        style=discord.TextStyle.short
    )
    early_hours = discord.ui.TextInput(
        label="Early Window Hours (e.g., 12)",
        placeholder="12",
        required=True,
        max_length=2,
        style=discord.TextStyle.short
    )
    late_hours = discord.ui.TextInput(
        label="Late Window Hours (e.g., 2)",
        placeholder="2",
        required=True,
        max_length=2,
        style=discord.TextStyle.short
    )
    async def on_submit(self, interaction: discord.Interaction):
        try:
            ah = int(self.anchor_hour.value)
            eh = int(self.early_hours.value)
            lh = int(self.late_hours.value)
            if ah < 0 or ah > 23:
                await interaction.response.send_message("❌ Anchor hour must be between 0 and 23.", ephemeral=True)
                return
            if eh <= 0 or lh <= 0:
                await interaction.response.send_message("❌ Hours must be positive integers.", ephemeral=True)
                return
            if eh <= lh:
                await interaction.response.send_message("❌ Early hours must be greater than late hours.", ephemeral=True)
                return
            await SettingsModel.update_sick_leave_settings(ah, eh, lh)
            embed = discord.Embed(
                title="✅ Sick Leave Settings Updated",
                description="New window and anchor time have been saved.",
                color=discord.Color.green()
            )
            embed.add_field(name="Anchor Hour", value=str(ah), inline=True)
            embed.add_field(name="Early Hours", value=str(eh), inline=True)
            embed.add_field(name="Late Hours", value=str(lh), inline=True)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid numbers provided.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error saving settings: {e}", ephemeral=True)

class ConfirmNonCompliantLeaveView(discord.ui.View):
    """Confirmation view for non-compliant leave request with proof handling"""
    def __init__(self, start_date: str, end_date: str, reason: str, compensating_day: str = None, 
                 proof_required: bool = False, days_before: int = 0):
        super().__init__(timeout=300)
        self.start_date = start_date
        self.end_date = end_date
        self.reason = reason
        self.compensating_day = compensating_day
        self.proof_required = proof_required
        self.days_before = days_before
        self.proof_confirmed = False
    
    @discord.ui.button(label="I've Sent Proof to HR/CEO", style=discord.ButtonStyle.primary, emoji="📄")
    async def confirm_proof(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Optional button to confirm proof was sent"""
        if not self.proof_required:
            await interaction.response.send_message(
                "ℹ️ Proof is not required for this request (applied less than 2 days before).",
                ephemeral=True
            )
            return
        
        self.proof_confirmed = True
        button.disabled = True
        button.label = "✅ Proof Confirmed"
        button.style = discord.ButtonStyle.success
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "✅ Proof confirmation noted. You can now submit your request.",
            ephemeral=True
        )
    
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
            
            # Convert string date to date object
            start_date_obj = datetime.strptime(self.start_date, "%d/%m/%Y").date()
            end_date_obj = datetime.strptime(self.end_date, "%d/%m/%Y").date()
            
            compensating_date_obj = None
            if self.compensating_day:
                compensating_date_obj = datetime.strptime(self.compensating_day, "%d/%m/%Y").date()
            
            # Create leave request in database
            leave_request_id = await LeaveRequestModel.create_leave_request(
                user_id=user['user_id'],
                leave_type="non_compliant",
                start_date=start_date_obj,
                end_date=end_date_obj,
                duration_hours=None,
                reason=self.reason,
                approval_required=True,
                compensating_day=compensating_date_obj,
                proof_provided=self.proof_confirmed
            )
            
            # Check if user has taken more than 2 non-compliant leaves in a week or month
            await self._check_and_notify_admins(interaction, user['user_id'], start_date_obj)
            
            # Send success message
            embed = discord.Embed(
                title="✅ Non-compliant Leave Request Submitted Successfully!",
                description="Your Non-compliant leave request has been submitted for approval.",
                color=discord.Color.green()
            )
            embed.add_field(name="Request ID", value=f"`{leave_request_id}`", inline=False)
            embed.add_field(name="Leave Type", value="⚠️ Non-compliant Leave", inline=True)
            embed.add_field(name="Start Date", value=self.start_date, inline=True)
            embed.add_field(name="End Date", value=self.end_date, inline=True)
            
            if self.compensating_day:
                embed.add_field(name="Compensating Day", value=self.compensating_day, inline=True)
            
            if self.proof_required:
                proof_status = "✅ Confirmed" if self.proof_confirmed else "⚠️ Pending"
                embed.add_field(name="Proof Status", value=proof_status, inline=False)
                if not self.proof_confirmed:
                    embed.add_field(
                        name="📬 Reminder",
                        value="Please remember to send proof to HR/CEO as required.",
                        inline=False
                    )
            
            embed.add_field(name="Status", value="⏳ Pending Review", inline=False)
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
    
    async def _check_and_notify_admins(self, interaction: discord.Interaction, user_id: int, leave_date):
        """Check if user has 2 or more non-compliant leaves in a week/month and notify admins"""
        try:
            # Get non-compliant leaves for the week (rolling 7-day window ending on leave_date)
            # Count all leaves from 7 days before leave_date up to and including leave_date
            week_start = leave_date - timedelta(days=6)  # 7 days total including leave_date
            week_count = await LeaveRequestModel.get_non_compliant_count(
                user_id, week_start, leave_date
            )
            
            # Get non-compliant leaves for the month (rolling 30-day window ending on leave_date)
            # Count all leaves from 30 days before leave_date up to and including leave_date
            month_start = leave_date - timedelta(days=29)  # 30 days total including leave_date
            month_count = await LeaveRequestModel.get_non_compliant_count(
                user_id, month_start, leave_date
            )
            
            # Notify admins if threshold met (2 or more)
            if week_count >= 2 or month_count >= 2:
                user = await UserModel.get_user_by_discord_id(interaction.user.id)
                if user:
                    await self._send_admin_notification(interaction, user, week_count, month_count, leave_date)
        
        except Exception as e:
            # Silently fail - don't break the request submission
            print(f"Error checking non-compliant leave count: {e}")
    
    async def _send_admin_notification(self, interaction: discord.Interaction, user, week_count: int, month_count: int, leave_date):
        """Send notification to admins about excessive non-compliant leaves"""
        try:
            # Get all admin users (role_id 1 or 2)
            admin_users = await UserModel.get_users_by_role(1, include_deleted=False)  # Super admins
            admin_users.extend(await UserModel.get_users_by_role(2, include_deleted=False))  # Admins
            
            if not admin_users:
                return
            
            # Create notification embed
            embed = discord.Embed(
                title="⚠️ Non-compliant Leave Alert",
                description=f"**{user['name']}** has exceeded the non-compliant leave threshold.",
                color=discord.Color.red()
            )
            embed.add_field(name="Employee", value=f"{user['name']} (ID: {user['user_id']})", inline=False)
            embed.add_field(name="Latest Leave Date", value=leave_date.strftime("%d/%m/%Y"), inline=True)
            embed.add_field(name="Week Count", value=f"{week_count} leave(s) in the last 7 days", inline=False)
            embed.add_field(name="Month Count", value=f"{month_count} leave(s) in the last 30 days", inline=False)
            embed.add_field(
                name="⚠️ Action Required",
                value="This employee has taken 2 or more non-compliant leaves in a week or month.",
                inline=False
            )
            embed.set_footer(text="Automated notification from Compliance Bot")
            
            # Send DM to each admin using interaction.client (bot instance)
            bot = interaction.client
            for admin in admin_users:
                if admin.get('discord_id'):
                    try:
                        # Try to get member from guild
                        admin_member = interaction.guild.get_member(admin['discord_id'])
                        if admin_member:
                            await admin_member.send(embed=embed)
                        else:
                            # If not in cache, fetch the user
                            admin_user_obj = await bot.fetch_user(admin['discord_id'])
                            if admin_user_obj:
                                await admin_user_obj.send(embed=embed)
                    except discord.Forbidden:
                        # User has DMs disabled or blocked the bot
                        print(f"Cannot send DM to admin {admin['name']} (ID: {admin['discord_id']}) - DMs disabled or blocked")
                    except Exception as e:
                        # Other errors
                        print(f"Failed to send DM to admin {admin['name']}: {e}")
        
        except Exception as e:
            print(f"Error sending admin notification: {e}")
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_request(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "❌ Leave request cancelled.",
            ephemeral=True
        )
        self.stop()


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
            start_date_obj = datetime.strptime(self.start_date, "%d/%m/%Y").date()
            end_date_obj = datetime.strptime(self.end_date, "%d/%m/%Y").date()
            
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
            
            # Notify admins if sick leave count exceeds thresholds
            if self.leave_type == "sick_leave":
                await self._check_and_notify_admins_for_sick_leave(interaction, user, start_date_obj)
            
            # Get leave type display name
            leave_type_display = {
                "paid_leave": "💰 Paid Leave",
                "unpaid_leave": "📝 Unpaid Leave",
                "non_compliant": "⚠️ Non-compliant",
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
    
    async def _check_and_notify_admins_for_sick_leave(self, interaction: discord.Interaction, user, leave_date):
        try:
            from datetime import timedelta
            week_start = leave_date - timedelta(days=6)
            month_start = leave_date - timedelta(days=29)
            
            week_count = await LeaveRequestModel.get_sick_leave_count(user['user_id'], week_start, leave_date)
            month_count = await LeaveRequestModel.get_sick_leave_count(user['user_id'], month_start, leave_date)
            
            if week_count >= 2 or month_count >= 2:
                await self._send_admin_notification_for_sick(interaction, user, week_count, month_count, leave_date)
        except Exception as e:
            print(f"Error checking sick leave count: {e}")
    
    async def _send_admin_notification_for_sick(self, interaction: discord.Interaction, user, week_count: int, month_count: int, leave_date):
        try:
            admin_users = await UserModel.get_users_by_role(1, include_deleted=False)
            admin_users.extend(await UserModel.get_users_by_role(2, include_deleted=False))
            
            if not admin_users:
                return
            
            embed = discord.Embed(
                title="⚠️ Sick Leave Alert",
                description=f"**{user['name']}** has exceeded the sick leave threshold.",
                color=discord.Color.red()
            )
            embed.add_field(name="Employee", value=f"{user['name']} (ID: {user['user_id']})", inline=False)
            embed.add_field(name="Latest Sick Leave Date", value=leave_date.strftime("%d/%m/%Y"), inline=True)
            embed.add_field(name="Week Count", value=f"{week_count} sick leave(s) in the last 7 days", inline=False)
            embed.add_field(name="Month Count", value=f"{month_count} sick leave(s) in the last 30 days", inline=False)
            embed.add_field(
                name="⚠️ Action Required",
                value="This employee has taken 2 or more sick leaves in a week or month.",
                inline=False
            )
            embed.set_footer(text="Automated notification from Compliance Bot")
            
            bot = interaction.client
            for admin in admin_users:
                if admin.get('discord_id'):
                    try:
                        admin_member = interaction.guild.get_member(admin['discord_id'])
                        if admin_member:
                            await admin_member.send(embed=embed)
                        else:
                            admin_user_obj = await bot.fetch_user(admin['discord_id'])
                            if admin_user_obj:
                                await admin_user_obj.send(embed=embed)
                    except discord.Forbidden:
                        print(f"Cannot send DM to admin {admin['name']} (ID: {admin['discord_id']}) - DMs disabled or blocked")
                    except Exception as e:
                        print(f"Failed to send DM to admin {admin['name']}: {e}")
        except Exception as e:
            print(f"Error sending admin notification: {e}")
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
            "unpaid_leave": "Unpaid",
            "non_compliant": "Non-compliant",
            "sick_leave": "Sick",
            "emergency_leave": "Emergency",
            "half_day": "Half-Day"
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
