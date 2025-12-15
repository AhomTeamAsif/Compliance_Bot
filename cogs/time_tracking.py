import discord
from discord import app_commands, ui
from discord.ext import commands
from datetime import datetime, time as dt_time
from models import UserModel, TimeTrackingModel, LateReasonModel, WorkUpdateModel
import pytz

class TaskPlanModal(ui.Modal, title='Your Workday Plan'):
    """Modal form for recording daily tasks"""
    
    task1 = ui.TextInput(
        label='Task 1',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    task2 = ui.TextInput(
        label='Task 2 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    task3 = ui.TextInput(
        label='Task 3 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    task4 = ui.TextInput(
        label='Task 4 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    task5 = ui.TextInput(
        label='Task 5 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User):
        super().__init__()
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process task submission"""
        tasks = []
        for task_input in [self.task1, self.task2, self.task3, self.task4, self.task5]:
            if task_input.value and task_input.value.strip():
                tasks.append(task_input.value.strip())
        
        view = TrackingToolsView(self.user_id, self.time_tracking_id, tasks, self.interaction_user)
        await interaction.response.send_message(
            f"**Tasks recorded!**\n**Have you turned on Desklog and TrackAbi?**\nClick the buttons below:",
            view=view,
            ephemeral=True
        )


class TrackingToolsView(ui.View):
    """View with Desklog and TrackAbi toggle buttons"""
    
    def __init__(self, user_id: int, time_tracking_id: int, tasks: list, interaction_user: discord.User):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.tasks = tasks
        self.interaction_user = interaction_user
        self.desklog_on = False
        self.trackabi_on = False
    
    @ui.button(label="Desklog OFF", style=discord.ButtonStyle.red, custom_id="desklog")
    async def desklog_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle Desklog status"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.desklog_on = not self.desklog_on
        button.label = "Desklog ON" if self.desklog_on else "Desklog OFF"
        button.style = discord.ButtonStyle.green if self.desklog_on else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="TrackAbi OFF", style=discord.ButtonStyle.red, custom_id="trackabi")
    async def trackabi_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle TrackAbi status"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.trackabi_on = not self.trackabi_on
        button.label = "TrackAbi ON" if self.trackabi_on else "TrackAbi OFF"
        button.style = discord.ButtonStyle.green if self.trackabi_on else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Done", style=discord.ButtonStyle.primary, row=1)
    async def done_button(self, interaction: discord.Interaction, button: ui.Button):
        """Save tracking tools status"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        try:
            # Save to database
            await WorkUpdateModel.create_work_update(
                user_id=self.user_id,
                time_tracking_id=self.time_tracking_id,
                tasks=self.tasks,
                desklog_on=self.desklog_on,
                trackabi_on=self.trackabi_on
            )
            
            # Build summary message
            task_list = "\n".join([f"  {i+1}. {task}" for i, task in enumerate(self.tasks)])
            warnings = []
            if not self.desklog_on:
                warnings.append("⚠️ Desklog is OFF")
            if not self.trackabi_on:
                warnings.append("⚠️ TrackAbi is OFF")
            
            warning_text = "\n".join(warnings) if warnings else "✅ All tracking tools are ON"
            
            await interaction.response.edit_message(
                content=(
                    f"**✅ Daily Plan Saved!**\n\n"
                    f"**Your Tasks:**\n{task_list}\n\n"
                    f"**Tracking Status:**\n{warning_text}\n\n"
                    f"{'**REMINDER: Please turn on screen share!**' if warnings else 'Great! Ready to start working.'}"
                ),
                view=None
            )
            
            # Send screen share reminder
            await self.send_screenshare_reminder(self.interaction_user)
            self.stop()
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error saving work plan: {str(e)}",
                ephemeral=True
            )
    
    async def send_screenshare_reminder(self, user: discord.User):
        """Send DM reminder to turn on screen share"""
        try:
            embed = discord.Embed(
                title="🖥️ Screen Share Reminder",
                description="**Please turn on your Discord screen share now!**",
                color=discord.Color.red()
            )
            embed.set_footer(text="This is a reminder for your work session")
            
            reminder_view = ScreenShareReminderView()
            await user.send(embed=embed, view=reminder_view)
        except discord.Forbidden:
            pass


class ScreenShareReminderView(ui.View):
    """Acknowledgment button for screen share reminder"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="Shared!", style=discord.ButtonStyle.green)
    async def acknowledge_button(self, interaction: discord.Interaction, button: ui.Button):
        """Acknowledge screen share started"""
        await interaction.response.edit_message(
            content="✅ Great! Let's start working now.",
            view=None
        )
        self.stop()


class PlanKnownView(ui.View):
    """Ask user if they know their daily plan"""
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
    
    @ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction, button: ui.Button):
        """User knows their plan - show task modal"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt", ephemeral=True)
            return
        
        modal = TaskPlanModal(self.user_id, self.time_tracking_id, self.interaction_user)
        await interaction.response.send_modal(modal)
        self.stop()
    
    @ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction, button: ui.Button):
        """User doesn't know plan yet"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "📝 Please plan your day and update later!",
            ephemeral=True
        )
        
        # Save empty work update
        await WorkUpdateModel.create_work_update(
            user_id=self.user_id,
            time_tracking_id=self.time_tracking_id,
            tasks=[],
            desklog_on=False,
            trackabi_on=False
        )
        self.stop()


class TimeTracking(commands.Cog):
    """Time tracking and attendance commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_late_clockins = {}  # Store pending late clock-ins
    
    @app_commands.command(
        name="clock_in",
        description="Clock in to start your work session"
    )
    @app_commands.describe(reason="Reason for clocking in (use 'Start of the day' for first clock-in)")
    async def clock_in(self, interaction: discord.Interaction, reason: str):
        """Clock in command"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user from database
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            
            if not user:
                await interaction.followup.send(
                    "❌ You are not registered! Please contact an admin.",
                    ephemeral=True
                )
                return
            
            user_id = user['user_id']
            utc_time = datetime.now(pytz.utc)
            utc_time_no_tz = utc_time.replace(tzinfo=None)
            present_date = utc_time.date()
            
            # Check if record exists for today
            existing_record = await TimeTrackingModel.get_today_tracking(user_id, present_date)
            
            if existing_record:
                await self.handle_additional_clockin(
                    interaction, user_id, existing_record, 
                    utc_time, utc_time_no_tz, reason
                )
            else:
                await self.handle_first_clockin(
                    interaction, user_id, utc_time, 
                    utc_time_no_tz, present_date, reason
                )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    async def handle_first_clockin(self, interaction, user_id, utc_time, utc_time_no_tz, present_date, reason):
        """Handle first clock-in of the day"""
        
        if reason.lower().strip() != "start of the day":
            await interaction.followup.send(
                f"❌ First clock-in of the day must be with reason **'Start of the day'**!\n"
                f"(You provided: '{reason}')",
                ephemeral=True
            )
            return
        
        # Check if late (after 4:10 UTC)
        clock_in_time = utc_time_no_tz.time()
        late_threshold = dt_time(4, 10)
        
        if clock_in_time > late_threshold:
            # User is late
            threshold_datetime = datetime.combine(present_date, late_threshold)
            late_seconds = (utc_time_no_tz - threshold_datetime).total_seconds()
            late_minutes = int(late_seconds / 60)
            
            # Store pending clock-in
            self.pending_late_clockins[interaction.user.id] = {
                'user_id': user_id,
                'utc_time': utc_time,
                'utc_time_no_tz': utc_time_no_tz,
                'present_date': present_date,
                'reason': reason,
                'late_minutes': late_minutes
            }
            
            await interaction.followup.send(
                f"⚠️ You are **{late_minutes} minutes late**!\n"
                f"Please use `/late_reason` command to submit your late reason.",
                ephemeral=True
            )
            return
        
        # On time - create record
        time_tracking_id = await TimeTrackingModel.create_time_tracking(
            user_id=user_id,
            starting_time=utc_time,
            present_date=present_date,
            clock_in_time=utc_time_no_tz,
            reason=reason
        )
        
        await interaction.followup.send(
            f"✅ Clocked in at **{utc_time.strftime('%I:%M %p')}** - On time!",
            ephemeral=True
        )
        
        # Ask about daily plan
        view = PlanKnownView(user_id, time_tracking_id, interaction.user)
        await interaction.followup.send(
            "**Do you know your workday plan?**",
            view=view,
            ephemeral=True
        )
    
    async def handle_additional_clockin(self, interaction, user_id, existing_record, utc_time, utc_time_no_tz, reason):
        """Handle additional clock-in (after breaks)"""
        
        record_id = existing_record['id']
        clock_in_times = existing_record['clock_in'] if existing_record['clock_in'] else []
        clock_out_times = existing_record['clock_out'] if existing_record['clock_out'] else []
        end_of_day = existing_record['end_of_the_day']
        current_break_duration = existing_record['break_duration'] if existing_record['break_duration'] else 0
        
        # Check if day ended
        if end_of_day:
            await interaction.followup.send(
                "❌ The day has already ended. You cannot clock in again today!",
                ephemeral=True
            )
            return
        
        # Check if last action was clock-in without clock-out
        if len(clock_in_times) > len(clock_out_times):
            await interaction.followup.send(
                "⚠️ You need to clock out first before clocking in again!",
                ephemeral=True
            )
            return
        
        # Calculate break duration
        if len(clock_out_times) > 0:
            last_clockout = clock_out_times[-1]
            new_break_minutes = int((utc_time_no_tz - last_clockout).total_seconds() / 60)
            total_break_duration = current_break_duration + new_break_minutes
            
            # Update with new clock-in and break duration
            await TimeTrackingModel.add_clock_in(
                tracking_id=record_id,
                clock_in_time=utc_time_no_tz,
                reason=reason,
                break_duration=total_break_duration
            )
            
            await interaction.followup.send(
                f"✅ Clocked in at **{utc_time.strftime('%I:%M %p')}**\n"
                f"**This break duration:** {new_break_minutes} minutes\n"
                f"**Total break duration today:** {total_break_duration} minutes\n"
                f"**Reason:** {reason}",
                ephemeral=True
            )
        else:
            await TimeTrackingModel.add_clock_in(
                tracking_id=record_id,
                clock_in_time=utc_time_no_tz,
                reason=reason
            )
            
            await interaction.followup.send(
                f"✅ Clocked in at **{utc_time.strftime('%I:%M %p')}**\n**Reason:** {reason}",
                ephemeral=True
            )
        
        # Send screen share reminder
        await self.send_screenshare_reminder_dm(interaction.user)
    
    @app_commands.command(
        name="clock_out",
        description="Clock out to end your work session"
    )
    @app_commands.describe(reason="Reason for clocking out (use 'End of the day' to finish)")
    async def clock_out(self, interaction: discord.Interaction, reason: str):
        """Clock out command"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user from database
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            
            if not user:
                await interaction.followup.send(
                    "❌ You are not registered!",
                    ephemeral=True
                )
                return
            
            user_id = user['user_id']
            utc_time = datetime.now(pytz.utc)
            utc_time_no_tz = utc_time.replace(tzinfo=None)
            present_date = utc_time.date()
            
            # Get today's record
            record = await TimeTrackingModel.get_today_tracking(user_id, present_date)
            
            if not record:
                await interaction.followup.send(
                    "❌ You haven't clocked in today!",
                    ephemeral=True
                )
                return
            
            record_id = record['id']
            clock_in_times = record['clock_in'] if record['clock_in'] else []
            clock_out_times = record['clock_out'] if record['clock_out'] else []
            
            # Check if need to clock in first
            if len(clock_out_times) >= len(clock_in_times):
                await interaction.followup.send(
                    "⚠️ You need to clock in first before clocking out!",
                    ephemeral=True
                )
                return
            
            # Calculate total logged time
            clock_out_times_temp = clock_out_times + [utc_time_no_tz]
            total_logged_minutes = 0
            
            for i in range(len(clock_out_times_temp)):
                if i < len(clock_in_times):
                    work_duration = (clock_out_times_temp[i] - clock_in_times[i]).total_seconds() / 60
                    total_logged_minutes += work_duration
            
            current_session_minutes = int((utc_time_no_tz - clock_in_times[-1]).total_seconds() / 60)
            
            # Update clock-out
            await TimeTrackingModel.add_clock_out(
                tracking_id=record_id,
                clock_out_time=utc_time_no_tz,
                reason=reason,
                time_logged=int(total_logged_minutes)
            )
            
            # If not end of day, increment break counter
            if reason.lower().strip() != "end of the day":
                await TimeTrackingModel.increment_break_counter(record_id)
                
                await interaction.followup.send(
                    f"✅ Clocked out at **{utc_time.strftime('%I:%M %p')}**\n"
                    f"**This session duration:** {current_session_minutes} minutes\n"
                    f"**Total time logged today:** {int(total_logged_minutes)} minutes\n"
                    f"**Reason:** {reason}",
                    ephemeral=True
                )
            else:
                # End of the day
                await TimeTrackingModel.end_day(record_id, utc_time)
                
                required_minutes = 480  # 8 hours
                if int(total_logged_minutes) < required_minutes:
                    short_minutes = required_minutes - int(total_logged_minutes)
                    short_hours = short_minutes // 60
                    short_mins = short_minutes % 60
                    
                    await interaction.followup.send(
                        f"✅ Clocked out at **{utc_time.strftime('%I:%M %p')}**\n"
                        f"**This session duration:** {current_session_minutes} minutes\n"
                        f"**Total time logged today:** {int(total_logged_minutes)} minutes "
                        f"({int(total_logged_minutes)//60}h {int(total_logged_minutes)%60}m)\n"
                        f"⚠️ **Warning:** You worked **{short_hours}h {short_mins}m less** than the required 8 hours!\n"
                        f"**Reason:** {reason}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Clocked out at **{utc_time.strftime('%I:%M %p')}**\n"
                        f"**This session duration:** {current_session_minutes} minutes\n"
                        f"**Total time logged today:** {int(total_logged_minutes)} minutes "
                        f"({int(total_logged_minutes)//60}h {int(total_logged_minutes)%60}m)\n"
                        f"**Reason:** {reason}",
                        ephemeral=True
                    )
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="late_reason",
        description="Submit reason for late arrival"
    )
    @app_commands.describe(
        admin_informed="Did you inform admin? (yes/no)",
        reason="Reason for being late"
    )
    async def late_reason(self, interaction: discord.Interaction, admin_informed: str, reason: str):
        """Submit late reason after being flagged as late"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            if interaction.user.id not in self.pending_late_clockins:
                await interaction.followup.send(
                    "❌ No pending late clock-in found. You're either not late or already clocked in.",
                    ephemeral=True
                )
                return
            
            data = self.pending_late_clockins[interaction.user.id]
            is_admin_informed = admin_informed.lower() in ['yes', 'y']
            
            # Create time tracking record
            time_tracking_id = await TimeTrackingModel.create_time_tracking(
                user_id=data['user_id'],
                starting_time=data['utc_time'],
                present_date=data['present_date'],
                clock_in_time=data['utc_time_no_tz'],
                reason=data['reason']
            )
            
            # Record late reason
            await LateReasonModel.create_late_reason(
                user_id=data['user_id'],
                time_tracking_id=time_tracking_id,
                late_mins=data['late_minutes'],
                reason=reason,
                is_admin_informed=is_admin_informed
            )
            
            # Remove from pending
            del self.pending_late_clockins[interaction.user.id]
            
            await interaction.followup.send(
                f"✅ **Clock-in completed!**\n"
                f"**Time:** {data['utc_time'].strftime('%I:%M %p')}\n"
                f"**Late by:** {data['late_minutes']} minutes\n"
                f"**Reason:** {reason}\n"
                f"**Admin Informed:** {'Yes' if is_admin_informed else 'No'}",
                ephemeral=True
            )
            
            # Ask about daily plan
            view = PlanKnownView(data['user_id'], time_tracking_id, interaction.user)
            await interaction.followup.send(
                "**Do you know your workday plan?**",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="clocked_in_status",
        description="View all currently clocked-in employees"
    )
    async def clocked_in_status(self, interaction: discord.Interaction):
        """Show all currently clocked in users"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            present_date = datetime.now(pytz.utc).date()
            current_time = datetime.now(pytz.utc).replace(tzinfo=None)
            
            results = await TimeTrackingModel.get_all_clocked_in_today(present_date)
            
            if not results:
                await interaction.followup.send(
                    "📋 No one is currently clocked in.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="👥 Currently Clocked In",
                description=f"**Total: {len(results)} employee(s)**",
                color=discord.Color.blue()
            )
            
            for record in results:
                name = record['name']
                start_time = record['starting_time']
                last_clock_in = record['last_clock_in']
                logged_mins = record['time_logged_in'] or 0
                breaks = record['break_counter'] or 0
                
                # Format times
                if isinstance(start_time, str):
                    start_time_display = start_time.split()[1][:5]
                else:
                    start_time_display = start_time.strftime('%H:%M')
                
                if isinstance(last_clock_in, str):
                    clock_in_display = last_clock_in.split()[1][:5] if ' ' in last_clock_in else last_clock_in[:5]
                else:
                    clock_in_display = last_clock_in.strftime('%H:%M')
                
                # Calculate current session
                current_session_seconds = (current_time - last_clock_in).total_seconds()
                current_session_mins = int(current_session_seconds / 60)
                total_mins = logged_mins + current_session_mins
                work_hours = total_mins // 60
                work_mins = total_mins % 60
                
                embed.add_field(
                    name=f"👤 {name}",
                    value=(
                        f"**Start:** {start_time_display}\n"
                        f"**Current Clock In:** {clock_in_display}\n"
                        f"**Time Logged:** {work_hours}h {work_mins}m\n"
                        f"**Breaks Taken:** {breaks}"
                    ),
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    async def send_screenshare_reminder_dm(self, user: discord.User):
        """Send screen share reminder via DM"""
        try:
            embed = discord.Embed(
                title="🖥️ Screen Share Reminder",
                description="**Please turn on your Discord screen share now!**",
                color=discord.Color.red()
            )
            embed.set_footer(text="This is a reminder for your work session")
            
            reminder_view = ScreenShareReminderView()
            await user.send(embed=embed, view=reminder_view)
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(TimeTracking(bot))