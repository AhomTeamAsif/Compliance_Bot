"""Views for leave management UI components"""
import discord
from discord import ui
from datetime import datetime, timedelta
import pytz
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
                label="Paid Leave",
                value="paid_leave",
                emoji="💰",
                description="Must be requested at least 2 weeks in advance"
            ),
            discord.SelectOption(
                label="Unpaid Leave",
                value="unpaid_leave",
                emoji="📝",
                description="Unpaid leave request"
            ),
            discord.SelectOption(
                label="Non-compliant",
                value="non_compliant",
                emoji="⚠️",
                description="Request 14 to 1 day before the off day"
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
                label="Half-Day Leave",
                value="half_day",
                emoji="⏰",
                description="Choose between unpaid/non-compliant"
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
        elif self.selected_leave_type == "half_day":
            # Show sub-type selection for half-day
            view = HalfDaySubTypeSelectView()
            embed = discord.Embed(
                title="⏰ Half-Day Leave - Step 2/3",
                description="**Select the sub-type** for your half-day leave:",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Available Sub-Types",
                value=(
                    "**📝 Unpaid** - No deduction from leave balance\n"
                    "**⚠️ Non-compliant** - Short notice half-day leave\n"
                ),
                inline=False
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

        self.stop()

class HalfDaySubTypeSelectView(discord.ui.View):
    """Select half-day leave sub-type (unpaid/non-compliant)"""
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_sub_type = None

    @discord.ui.select(
        placeholder="Select Half-Day Sub-Type",
        options=[
            discord.SelectOption(
                label="Unpaid Half-Day",
                value="half_day_unpaid",
                emoji="📝",
                description="No deduction from leave balance"
            ),
            discord.SelectOption(
                label="Non-compliant Half-Day",
                value="half_day_non_compliant",
                emoji="⚠️",
                description="Short notice half-day leave"
            ),
        ]
    )
    async def half_day_sub_type_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_sub_type = select.values[0]

        # Show appropriate modal based on sub-type
        if self.selected_sub_type == "half_day_unpaid":
            modal = HalfDayUnpaidModal()
            await interaction.response.send_modal(modal)
        elif self.selected_sub_type == "half_day_non_compliant":
            modal = HalfDayNonCompliantModal()
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



class HalfDayUnpaidModal(discord.ui.Modal, title="Unpaid Half-Day Leave Request"):
    """Modal for unpaid half-day leave request"""
    date = discord.ui.TextInput(
        label="Date of Half-Day Leave",
        placeholder="DD/MM/YYYY (must be 2+ weeks from today)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )

    half_selection = discord.ui.TextInput(
    label="Which Half?",
    placeholder="Enter 'Morning' or 'Afternoon'",
    required=True,
    max_length=20,
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

            # Check if at least 2 weeks in advance
            days_advance = (date_obj - today).days
            if days_advance < 14:
                await interaction.response.send_message(
                    f"❌ Unpaid half-day leave must be requested at least 2 weeks in advance!\n"
                    f"Current date: {today.strftime('%d/%m/%Y')}\n"
                    f"Your requested date: {self.date.value}\n"
                    f"Days in advance: {days_advance} (minimum required: 14)",
                    ephemeral=True
                )
                return

            # Validate half selection
            # Validate half selection
            half_value = self.half_selection.value.strip().lower()
            if half_value not in ['morning', 'afternoon']:
                await interaction.response.send_message(
                    "❌ Invalid selection! Please enter either 'Morning' or 'Afternoon'.",
                    ephemeral=True
                )
                return

            # Normalize the value for display
            half_display = "Morning (4 hours)" if half_value == 'morning' else "Afternoon (4 hours)"

            # Show confirmation
            view = ConfirmHalfDayLeaveView("half_day_unpaid", self.date.value, half_display, self.reason.value)

            embed = discord.Embed(
                title="📋 Unpaid Half-Day Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.blue()
            )
            embed.add_field(name="📝 Leave Type", value="Unpaid Half-Day Leave", inline=True)
            embed.add_field(name="📅 Date", value=self.date.value, inline=True)
            embed.add_field(name="⏱️ Duration", value=half_display, inline=True)
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


class HalfDayNonCompliantModal(discord.ui.Modal, title="Non-compliant Half-Day Leave Request"):
    """Modal for non-compliant half-day leave request"""
    date = discord.ui.TextInput(
        label="Date of Half-Day Leave",
        placeholder="DD/MM/YYYY (14 to 1 day before)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )

    half_selection = discord.ui.TextInput(
        label="Which Half?",
        placeholder="Enter 'Morning' or 'Afternoon'",
        required=True,
        max_length=20,
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
            today = datetime.now()
            today_date = today.date()
            date_obj = datetime.strptime(self.date.value, "%d/%m/%Y").date()

            # Calculate days before the off day (14 to 1 day before)
            days_before = (date_obj - today_date).days

            # Validate date range: must be 14 to 1 day before
            if days_before < 1 or days_before > 14:
                await interaction.response.send_message(
                    f"❌ **Invalid Date Range!**\n"
                    f"Non-compliant half-day leave must be requested 14 to 1 day before the off day.\n"
                    f"**Today:** {today_date.strftime('%d/%m/%Y')}\n"
                    f"**Your requested date:** {self.date.value}\n"
                    f"**Days before:** {days_before} (must be between 1 and 14 days)",
                    ephemeral=True
                )
                return

            # Validate half selection
            # Validate half selection
            half_value = self.half_selection.value.strip().lower()
            if half_value not in ['morning', 'afternoon']:
                await interaction.response.send_message(
                    "❌ Invalid selection! Please enter either 'Morning' or 'Afternoon'.",
                    ephemeral=True
                )
                return

            # Normalize the value for display
            half_display = "Morning (4 hours)" if half_value == 'morning' else "Afternoon (4 hours)"

            # Show confirmation
            view = ConfirmHalfDayLeaveView("half_day_non_compliant", self.date.value, half_display, self.reason.value)

            embed = discord.Embed(
                title="📋 Non-compliant Half-Day Leave Request Summary",
                description="Please review your request:",
                color=discord.Color.orange()
            )
            embed.add_field(name="⚠️ Leave Type", value="Non-compliant Half-Day Leave", inline=True)
            embed.add_field(name="📅 Date", value=self.date.value, inline=True)
            embed.add_field(name="⏱️ Duration", value=half_display, inline=True)
            embed.add_field(name="📊 Days Before", value=f"{days_before} day(s)", inline=True)
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


class ConfirmHalfDayLeaveView(discord.ui.View):
    """Confirmation view for half-day leave request"""
    def __init__(self, leave_type: str, date: str, half_display: str, reason: str):
        super().__init__(timeout=180)
        self.leave_type = leave_type
        self.date = date
        self.half_display = half_display
        self.reason = reason

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
            date_obj = datetime.strptime(self.date, "%d/%m/%Y").date()

            # Create leave request in database (4 hours for half-day)
            leave_request_id = await LeaveRequestModel.create_leave_request(
                user_id=user['user_id'],
                leave_type=self.leave_type,
                start_date=date_obj,
                end_date=date_obj,
                duration_hours=4.0,
                reason=self.reason,
                approval_required=True
            )

            # Note: Deduction from pending_leaves happens upon approval, not submission

            # Get leave type display name
            leave_type_display = {
                "half_day_paid": "💰 Paid Half-Day",
                "half_day_unpaid": "📝 Unpaid Half-Day",
                "half_day_non_compliant": "⚠️ Non-compliant Half-Day"
            }.get(self.leave_type, self.leave_type)

            # Send colorful success message
            embed = discord.Embed(
                title="✅ Half-Day Leave Request Submitted Successfully!",
                description=f"🎉 **Your {leave_type_display} leave request has been submitted for approval!**",
                color=0x00FF00  # Bright green color
            )

            # Add visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="🆔 Request ID",
                value=f"```yaml\n{leave_request_id}\n```",
                inline=False
            )
            embed.add_field(
                name="📋 Leave Type",
                value=f"```diff\n+ {leave_type_display}\n```",
                inline=True
            )
            embed.add_field(
                name="📅 Date",
                value=f"```yaml\n{self.date}\n```",
                inline=True
            )
            embed.add_field(
                name="⏱️ Duration",
                value=f"```yaml\n{self.half_display}\n```",
                inline=True
            )

            # Add separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="📊 Status",
                value="```css\n[⏳ Pending Manager Review]\n```",
                inline=False
            )

            embed.add_field(
                name="📬 Next Steps",
                value="```md\n# Your manager will review your request\n- Check status: /my_leaves command\n- You will be notified once reviewed\n```",
                inline=False
            )

            # Add footer with timestamp
            embed.set_footer(
                text=f"✨ Submitted by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            embed.timestamp = datetime.now()

            # Add thumbnail
            embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/check-mark-button_2705.png")

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
        label="Starting Hour of the Day (0-23)",
        placeholder="10",
        required=True,
        max_length=2,
        style=discord.TextStyle.short
    )
    early_hours = discord.ui.TextInput(
        label="Early Window Hours (e.g 12)",
        placeholder=" 12 means 12 hours before the starting Hour of the Day",
        required=True,
        max_length=2,
        style=discord.TextStyle.short
    )
    late_hours = discord.ui.TextInput(
        label="Late Window Hours (e.g., 2)",
        placeholder="2 means 2 hours before the starting Hour of the Day ",
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
                await interaction.response.send_message("❌ Starting Hour of the Day must be between 0 and 23.", ephemeral=True)
                return
            if eh <= 0 or lh <= 0:
                await interaction.response.send_message("❌ Hours must be positive integers.", ephemeral=True)
                return
            if eh <= lh:
                await interaction.response.send_message("❌ Early hours must be greater than late hours.", ephemeral=True)
                return
            await SettingsModel.update_sick_leave_settings(ah, eh, lh)

            # Create colorful success embed with enhanced visibility
            embed = discord.Embed(
                title="✅ Sick Leave Settings Updated Successfully!",
                description="🎉 **The new sick leave window settings have been saved and are now in effect!**",
                color=0x00FF00  # Bright green color
            )

            # Add a visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="⏰ Starting Hour of the Day",
                value=f"```yaml\n{ah:02d}:00 ({ah} hours)\n```",
                inline=True
            )
            embed.add_field(
                name="🕐 Early Window",
                value=f"```diff\n+ {eh} hours before start\n```",
                inline=True
            )
            embed.add_field(
                name="🕑 Late Window",
                value=f"```diff\n+ {lh} hours before start\n```",
                inline=True
            )

            # Add another separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="📋 Application Window",
                value=f"```css\n[Employees can apply from {eh} hours to {lh} hours before {ah:02d}:00]\n```",
                inline=False
            )

            embed.add_field(
                name="🎉 Status",
                value="```diff\n+ Settings Successfully Updated and Applied!\n```",
                inline=False
            )

            # Add footer with timestamp
            embed.set_footer(
                text=f"✨ Updated by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            embed.timestamp = datetime.now()

            # Add a thumbnail for visual appeal
            embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/check-mark-button_2705.png")

            await interaction.response.send_message(embed=embed, ephemeral=False)
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
                "half_day_paid": "💰 Paid Half-Day",
                "half_day_unpaid": "📝 Unpaid Half-Day",
                "half_day_non_compliant": "⚠️ Non-compliant Half-Day",
                "emergency_leave": "🚨 Emergency Leave"
            }.get(self.leave_type, self.leave_type)
            
            # Send colorful success message
            embed = discord.Embed(
                title="✅ Leave Request Submitted Successfully!",
                description=f"🎉 **Your {leave_type_display} request has been submitted for approval!**",
                color=0x00FF00  # Bright green color
            )

            # Add visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="🆔 Request ID",
                value=f"```yaml\n{leave_request_id}\n```",
                inline=False
            )
            embed.add_field(
                name="📋 Leave Type",
                value=f"```diff\n+ {leave_type_display}\n```",
                inline=True
            )
            embed.add_field(
                name="📅 From",
                value=f"```yaml\n{self.start_date}\n```",
                inline=True
            )
            embed.add_field(
                name="📅 To",
                value=f"```yaml\n{self.end_date}\n```",
                inline=True
            )

            if self.duration_hours:
                embed.add_field(
                    name="⏱️ Duration",
                    value=f"```yaml\n{self.duration_hours} hour(s)\n```",
                    inline=True
                )
            else:
                embed.add_field(
                    name="⏱️ Duration",
                    value=f"```yaml\n{self.duration_days} day(s)\n```",
                    inline=True
                )

            # Add separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            embed.add_field(
                name="📊 Status",
                value="```css\n[⏳ Pending Manager Review]\n```",
                inline=False
            )

            # Add special message for sick leave
            if self.leave_type == "sick_leave":
                embed.add_field(
                    name="📬 Next Steps",
                    value=(
                        "```md\n"
                        "# IMPORTANT: Remember to inform HR or CEO directly!\n\n"
                        "- Share medical documentation with HR/CEO\n"
                        "- Manager will review your request\n"
                        "- Check status: /my_leaves command\n"
                        "```"
                    ),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📬 Next Steps",
                    value="```md\n# Your manager will review your request\n- Check status: /my_leaves command\n- You will be notified once reviewed\n```",
                    inline=False
                )

            # Add footer with timestamp
            embed.set_footer(
                text=f"✨ Submitted by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            embed.timestamp = datetime.now()

            # Add thumbnail
            embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/check-mark-button_2705.png")

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
    """Admin view to select pending leave requests (Step 1)"""
    def __init__(self, pending_requests, reviewer_discord_id: int):
        super().__init__(timeout=300)
        self.reviewer_discord_id = reviewer_discord_id
        self.pending_requests = pending_requests

        options = []
        leave_type_display = {
            "paid_leave": "Paid",
            "unpaid_leave": "Unpaid",
            "non_compliant": "Non-compliant",
            "sick_leave": "Sick",
            "emergency_leave": "Emergency",
            "half_day": "Half-Day",
            "half_day_paid": "Paid Half-Day",
            "half_day_unpaid": "Unpaid Half-Day",
            "half_day_non_compliant": "Non-compliant Half-Day"
        }

        for req in pending_requests:
            label = f"ID {req['leave_request_id']} • {leave_type_display.get(req['leave_type'], req['leave_type'])}"
            description = f"{req['name']} • {req['start_date']} to {req['end_date']}"
            options.append(discord.SelectOption(
                label=label[:100],
                value=str(req['leave_request_id']),
                description=description[:100]
            ))

        # Allow multiple selections (up to 25, which is Discord's max)
        max_selections = min(len(options), 25)
        self.leave_select = discord.ui.Select(
            placeholder="Select leave request(s) - You can select multiple",
            options=options,
            min_values=1,
            max_values=max_selections
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

        selected_request_ids = [int(req_id) for req_id in self.leave_select.values]
        count = len(selected_request_ids)
        ids_str = ", ".join([f"#{req_id}" for req_id in selected_request_ids])

        # Show Step 2 view with Approve All and Reject All buttons
        action_view = ReviewLeaveRequestsActionView(selected_request_ids, self.reviewer_discord_id)

        await interaction.response.send_message(
            f"ℹ️ Selected **{count}** request(s): {ids_str}\nChoose **Approve All** or **Reject All** below.",
            view=action_view,
            ephemeral=True
        )


class ReviewLeaveRequestsActionView(discord.ui.View):
    """Admin view to approve or reject selected leave requests (Step 2)"""
    def __init__(self, selected_request_ids: list, reviewer_discord_id: int):
        super().__init__(timeout=300)
        self.selected_request_ids = selected_request_ids
        self.reviewer_discord_id = reviewer_discord_id

    def _is_authorized(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.reviewer_discord_id

    @discord.ui.button(label="Approve All", style=discord.ButtonStyle.success, emoji="✅")
    async def approve(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can approve requests.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            admin_user = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not admin_user:
                await interaction.followup.send(
                    "❌ Unable to find your admin record in the system.",
                    ephemeral=True
                )
                return

            approved_count = 0
            failed_count = 0
            already_processed = 0
            approved_ids = []
            failed_ids = []

            # Process each selected request
            for request_id in self.selected_request_ids:
                request = await LeaveRequestModel.get_leave_request(request_id)
                if not request:
                    failed_count += 1
                    failed_ids.append(request_id)
                    continue

                if request['status'] != 'pending':
                    already_processed += 1
                    continue

                success = await LeaveRequestModel.approve_leave_request(
                    request_id,
                    admin_user['user_id']
                )

                if success:
                    # Handle paid leave deductions
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
                    elif request['leave_type'] == 'half_day_paid':
                        # Deduct 0.5 day for paid half-day leave
                        await LeaveRequestModel.deduct_pending_leave(
                            request['user_id'],
                            0.5
                        )

                    approved_count += 1
                    approved_ids.append(request_id)
                else:
                    failed_count += 1
                    failed_ids.append(request_id)

            # Create enhanced summary embed
            embed = discord.Embed(
                title="✅ Bulk Approval Completed!",
                description="🎉 **Leave request approval process has been completed!**",
                color=0x00FF00 if approved_count > 0 else 0xFFA500  # Green if any approved, orange otherwise
            )

            # Add visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            # Summary statistics
            embed.add_field(
                name="📊 Total Selected",
                value=f"```yaml\n{len(self.selected_request_ids)}\n```",
                inline=True
            )
            embed.add_field(
                name="✅ Approved",
                value=f"```diff\n+ {approved_count}\n```",
                inline=True
            )
            embed.add_field(
                name="❌ Failed/Skipped",
                value=f"```md\n{failed_count + already_processed}\n```",
                inline=True
            )

            # Add separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            # Detailed breakdown
            details = []
            if approved_count > 0:
                approved_ids_str = ', '.join([f'#{id}' for id in approved_ids])
                details.append(f"**✅ Approved ({approved_count}):**\n```yaml\n{approved_ids_str}\n```")

            if already_processed > 0:
                details.append(f"**ℹ️ Already Processed:** {already_processed} request(s)")

            if failed_count > 0:
                failed_ids_str = ', '.join([f'#{id}' for id in failed_ids])
                details.append(f"**❌ Failed ({failed_count}):**\n```diff\n- {failed_ids_str}\n```")

            if details:
                embed.add_field(
                    name="📋 Detailed Breakdown",
                    value="\n\n".join(details),
                    inline=False
                )

            # Add footer with timestamp
            embed.set_footer(
                text=f"✨ Processed by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            embed.timestamp = datetime.now(pytz.UTC)

            # Add thumbnail
            embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/check-mark-button_2705.png")

            await interaction.followup.send(embed=embed, ephemeral=True)
            self.stop()

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error approving requests: {e}",
                ephemeral=True
            )

    @discord.ui.button(label="Reject All", style=discord.ButtonStyle.danger, emoji="🛑")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button):
        if not self._is_authorized(interaction):
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can reject requests.",
                ephemeral=True
            )
            return

        modal = RejectLeaveModal(self)
        await interaction.response.send_modal(modal)


class RejectLeaveModal(discord.ui.Modal, title="Reject Leave Request(s)"):
    """Modal to capture rejection reason for bulk rejection"""
    reason = discord.ui.TextInput(
        label="Rejection Reason",
        placeholder="Provide a short reason for all selected requests",
        required=True,
        max_length=200,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, parent_view: ReviewLeaveRequestsActionView):
        super().__init__(timeout=180)
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.parent_view.reviewer_discord_id:
            await interaction.response.send_message(
                "❌ Only the admin who opened this list can reject requests.",
                ephemeral=True
            )
            return

        request_ids = self.parent_view.selected_request_ids
        if not request_ids:
            await interaction.response.send_message(
                "❌ No requests selected. Please select request(s) and try again.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            rejected_count = 0
            failed_count = 0
            already_processed = 0

            rejected_ids = []
            failed_ids = []
            already_processed_ids = []

            for request_id in request_ids:
                try:
                    request = await LeaveRequestModel.get_leave_request(request_id)
                    if not request:
                        failed_count += 1
                        failed_ids.append(request_id)
                        continue

                    if request['status'] != 'pending':
                        already_processed += 1
                        already_processed_ids.append(request_id)
                        continue

                    success = await LeaveRequestModel.reject_leave_request(
                        request_id,
                        self.reason.value
                    )

                    if success:
                        rejected_count += 1
                        rejected_ids.append(request_id)
                    else:
                        failed_count += 1
                        failed_ids.append(request_id)

                except Exception as e:
                    failed_count += 1
                    failed_ids.append(request_id)

            # Create enhanced summary embed
            embed = discord.Embed(
                title="🛑 Bulk Rejection Completed!",
                description="📋 **Leave request rejection process has been completed!**",
                color=0xFF0000 if rejected_count > 0 else 0xFFA500  # Red if any rejected, orange otherwise
            )

            # Add visual separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            # Summary statistics
            embed.add_field(
                name="📊 Total Selected",
                value=f"```yaml\n{len(request_ids)}\n```",
                inline=True
            )
            embed.add_field(
                name="🛑 Rejected",
                value=f"```diff\n- {rejected_count}\n```",
                inline=True
            )
            embed.add_field(
                name="❌ Failed/Skipped",
                value=f"```md\n{failed_count + already_processed}\n```",
                inline=True
            )

            # Add separator
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━━━━━━━", inline=False)

            # Detailed breakdown
            details = []
            if rejected_count > 0:
                rejected_ids_str = ', '.join([f'#{id}' for id in rejected_ids])
                details.append(f"**🛑 Rejected ({rejected_count}):**\n```diff\n- {rejected_ids_str}\n```")
                details.append(f"**📝 Reason:** {self.reason.value}")

            if already_processed > 0:
                already_processed_ids_str = ', '.join([f'#{id}' for id in already_processed_ids])
                details.append(f"**ℹ️ Already Processed ({already_processed}):**\n```yaml\n{already_processed_ids_str}\n```")

            if failed_count > 0:
                failed_ids_str = ', '.join([f'#{id}' for id in failed_ids])
                details.append(f"**❌ Failed ({failed_count}):**\n```css\n{failed_ids_str}\n```")

            if details:
                embed.add_field(
                    name="📋 Detailed Breakdown",
                    value="\n\n".join(details),
                    inline=False
                )

            # Add footer with timestamp
            embed.set_footer(
                text=f"✨ Processed by {interaction.user.name}",
                icon_url=interaction.user.display_avatar.url if interaction.user.display_avatar else None
            )
            embed.timestamp = datetime.now(pytz.UTC)

            # Add thumbnail (stop sign emoji)
            embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/stop-sign_1f6d1.png")

            await interaction.followup.send(embed=embed, ephemeral=True)
            self.parent_view.stop()

        except Exception as e:
            await interaction.followup.send(
                f"❌ Error rejecting requests: {e}",
                ephemeral=True
            )
