import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, time as dt_time
from models.user_model import UserModel
from models.time_tracking_model import TimeTrackingModel
from models.late_reason_model import LateReasonModel
from models.work_update_model import WorkUpdateModel
from models.screen_share_model import ScreenShareModel
from views.clockin_clockout_views import (
    PlanKnownView,
    SimpleScreenShareView,
    ScreenShareVerificationView,
    EndOfDayPromptView
)
import pytz


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
                # Additional clock-in (after break)
                await self.handle_additional_clockin(
                    interaction, user_id, existing_record, 
                    utc_time, utc_time_no_tz, reason
                )
            else:
                # First clock-in of the day
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
        """Handle first clock-in of the day (Start of the day)"""
        
        
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
            # User is late - Show integrated late reason view
            threshold_datetime = datetime.combine(present_date, late_threshold)
            late_seconds = (utc_time_no_tz - threshold_datetime).total_seconds()
            late_minutes = int(late_seconds / 60)
            
            # Import late reason view
            from views.clockin_clockout_views import LateReasonView
            
            # Store data for late reason submission
            late_data = {
                'user_id': user_id,
                'utc_time': utc_time,
                'utc_time_no_tz': utc_time_no_tz,
                'present_date': present_date,
                'reason': reason,
                'late_minutes': late_minutes,
                'interaction': interaction  # Pass interaction for continuation
            }
            
            view = LateReasonView(late_data, interaction.user, self)
            
            embed = discord.Embed(
                title="⏰ Late Arrival Detected",
                description=f"**You are {late_minutes} minutes late.**\n\nPlease provide the required information:",
                color=discord.Color.orange()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            return
        
        # On time - create record (NOT VERIFIED YET)
        time_tracking_id = await TimeTrackingModel.create_time_tracking(
            user_id=user_id,
            starting_time=utc_time_no_tz,
            present_date=present_date,
            clock_in_time=utc_time_no_tz,
            reason=reason,
            screen_share_verified=False
        )
        
        await interaction.followup.send(
            f"⏰ Clock-in time recorded: **{utc_time.strftime('%I:%M %p')}** - On time!\n\n"
            f"⚠️ **Clock-in NOT complete yet!** Please continue with the next steps...",
            ephemeral=True
        )
        
        view = PlanKnownView(user_id, time_tracking_id, interaction.user)
        await interaction.followup.send(
            "**📋 Do you know your workday plan?**",
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
        screen_share_verified = existing_record.get('screen_share_verified', False)
        
        # Check if day ended
        if end_of_day:
            await interaction.followup.send(
                "❌ The day has already ended. You cannot clock in again today!",
                ephemeral=True
            )
            return
        
        # Check if screen share was verified for start of day
        if not screen_share_verified:
            await interaction.followup.send(
                "❌ You haven't completed your initial clock-in yet!\n\n"
                "Please verify your screen share for the start of the day first.",
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
                f"**Reason:** {reason}\n\n"
                f"⚠️ Please start screen sharing now...",
                ephemeral=True
            )
        else:
            await TimeTrackingModel.add_clock_in(
                tracking_id=record_id,
                clock_in_time=utc_time_no_tz,
                reason=reason
            )
            
            await interaction.followup.send(
                f"✅ Clocked in at **{utc_time.strftime('%I:%M %p')}**\n"
                f"**Reason:** {reason}\n\n"
                f"⚠️ Please start screen sharing now...",
                ephemeral=True
            )
        
        # Show simple screen share verification
        view = SimpleScreenShareView(user_id, record_id, interaction.user)
        
        embed = discord.Embed(
            title="🖥️ Screen Share Required",
            description=(
                "**Please start your screen share NOW!**\n\n"
                "Click the button below once you've started streaming."
            ),
            color=discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="clock_out",
        description="Clock out to end your work session or take a break"
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
            screen_share_verified = record.get('screen_share_verified', False)
            
            # Check if screen share was verified
            if not screen_share_verified:
                await interaction.followup.send(
                    "❌ You haven't completed your clock-in yet!\n\n"
                    "Please verify your screen share first.",
                    ephemeral=True
                )
                return
            
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
            
            # End active screen share session
            active_session = await ScreenShareModel.get_active_session_by_user(user_id)
            if active_session:
                await ScreenShareModel.end_session(
                    session_id=active_session['session_id'],
                    reason=f"Clock-out: {reason}"
                )
            
            # Check if end of day
            if reason.lower().strip() == "end of the day":
                # End of the day - show work update prompt
                await TimeTrackingModel.end_day(record_id, utc_time_no_tz)
                
                required_minutes = 480  # 8 hours
                work_hours = int(total_logged_minutes) // 60
                work_mins = int(total_logged_minutes) % 60
                
                if int(total_logged_minutes) < required_minutes:
                    short_minutes = required_minutes - int(total_logged_minutes)
                    short_hours = short_minutes // 60
                    short_mins = short_minutes % 60
                    warning_msg = f"⚠️ **Warning:** You worked **{short_hours}h {short_mins}m less** than required 8 hours!"
                else:
                    warning_msg = "🎉 **Great job today!**"
                
                await interaction.followup.send(
                    f"✅ **Clocked out - End of Day**\n\n"
                    f"**Clock-out time:** {utc_time.strftime('%I:%M %p')}\n"
                    f"**Total time logged:** {work_hours}h {work_mins}m\n\n"
                    f"{warning_msg}\n\n"
                    f"**Next:** Please complete your end-of-day update...",
                    ephemeral=True
                )
                
                # Import and show end of day prompt view
                from views.clockin_clockout_views import EndOfDayPromptView
                
                clock_out_data = {
                    'user_id': user_id,
                    'time_tracking_id': record_id,
                    'total_minutes': int(total_logged_minutes)
                }
                
                # Show button to trigger end of day update modal
                view = EndOfDayPromptView(user_id, record_id, interaction.user, clock_out_data)
                
                await interaction.followup.send(
                    "📝 **Click below to fill out your end-of-day update:**",
                    view=view,
                    ephemeral=True
                )
            else:
                # Taking a break
                await TimeTrackingModel.increment_break_counter(record_id)
                
                await interaction.followup.send(
                    f"✅ **Clocked out for Break**\n\n"
                    f"**Clock-out time:** {utc_time.strftime('%I:%M %p')}\n"
                    f"**This session duration:** {current_session_minutes} minutes\n"
                    f"**Total time logged today:** {int(total_logged_minutes)} minutes\n"
                    f"**Reason:** {reason}\n\n"
                    f"📱 **Remember:** Clock back in when you return!",
                    ephemeral=True
                )
                
                # Show screen share stop reminder for breaks
                from views.clockin_clockout_views import ScreenShareStopReminderView
                
                reminder_embed = discord.Embed(
                    title="🖥️ Screen Share Reminder",
                    description=(
                        "**You're on a break.**\n\n"
                        "📢 Please stop your Discord screen share during your break.\n\n"
                        "✅ You can close this message once you've stopped screen sharing."
                    ),
                    color=discord.Color.orange()
                )
                
                stop_view = ScreenShareStopReminderView()
                await interaction.followup.send(embed=reminder_embed, view=stop_view, ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # @app_commands.command(
    #     name="late_reason",
    #     description="Submit reason for late arrival"
    # )
    # @app_commands.describe(
    #     admin_informed="Did you inform admin? (yes/no)",
    #     morning_meeting="Did you join the morning meeting? (yes/no)",
    #     reason="Reason for being late"
    # )
    # async def late_reason(self, interaction: discord.Interaction, admin_informed: str, morning_meeting: str, reason: str):
    #     """Submit late reason after being flagged as late"""
        
    #     await interaction.response.defer(ephemeral=True)
        
    #     try:
    #         if interaction.user.id not in self.pending_late_clockins:
    #             await interaction.followup.send(
    #                 "❌ No pending late clock-in found. You're either not late or already clocked in.",
    #                 ephemeral=True
    #             )
    #             return
            
    #         data = self.pending_late_clockins[interaction.user.id]
    #         is_admin_informed = admin_informed.lower() in ['yes', 'y']
    #         morning_meeting_attended = morning_meeting.lower() in ['yes', 'y']
            
    #         # Create time tracking record (NOT VERIFIED YET)
    #         time_tracking_id = await TimeTrackingModel.create_time_tracking(
    #             user_id=data['user_id'],
    #             starting_time=data['utc_time_no_tz'],
    #             present_date=data['present_date'],
    #             clock_in_time=data['utc_time_no_tz'],
    #             reason=data['reason'],
    #             screen_share_verified=False  # Not verified yet
    #         )
            
    #         # Record late reason
    #         await LateReasonModel.create_late_reason(
    #             user_id=data['user_id'],
    #             time_tracking_id=time_tracking_id,
    #             late_mins=data['late_minutes'],
    #             reason=reason,
    #             is_admin_informed=is_admin_informed,
    #             morning_meeting_attended=morning_meeting_attended
    #         )
            
    #         # Remove from pending
    #         del self.pending_late_clockins[interaction.user.id]
            
    #         await interaction.followup.send(
    #             f"✅ **Late reason recorded!**\n\n"
    #             f"**Time:** {data['utc_time'].strftime('%I:%M %p')}\n"
    #             f"**Late by:** {data['late_minutes']} minutes\n"
    #             f"**Reason:** {reason}\n"
    #             f"**Admin Informed:** {'Yes' if is_admin_informed else 'No'}\n"
    #             f"**Morning Meeting Attended:** {'Yes' if morning_meeting_attended else 'No'}\n\n"
    #             f"⚠️ **Clock-in NOT complete yet!** Please continue...",
    #             ephemeral=True
    #         )
            
    #         # Ask about daily plan
    #         view = PlanKnownView(data['user_id'], time_tracking_id, interaction.user)
    #         await interaction.followup.send(
    #             "**📋 Do you know your workday plan?**",
    #             view=view,
    #             ephemeral=True
    #         )
            
    #     except Exception as e:
    #         await interaction.followup.send(
    #             f"❌ An error occurred: {str(e)}",
    #             ephemeral=True
    #         )
    
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
                screen_verified = record['screen_share_verified']
                
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
                
                verification_status = "✅ Verified" if screen_verified else "⚠️ Not Verified"
                
                embed.add_field(
                    name=f"👤 {name}",
                    value=(
                        f"**Start:** {start_time_display}\n"
                        f"**Current Clock In:** {clock_in_display}\n"
                        f"**Time Logged:** {work_hours}h {work_mins}m\n"
                        f"**Breaks Taken:** {breaks}\n"
                        f"**Screen Share:** {verification_status}"
                    ),
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(
        name="force_clock_in",
        description="Force clock in a user (ADMIN only)"
    )
    @app_commands.describe(
        user="The user to force clock in",
        reason="Reason for force clock-in"
    )
    async def force_clock_in(self, interaction: discord.Interaction, user: discord.User, reason: str = "Forced by admin"):
        """Admin force clock in"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        from utils.verification_helper import is_admin, is_super_admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send("❌ Only ADMIN can force clock-in users!", ephemeral=True)
            return
        
        try:
            user_data = await UserModel.get_user_by_discord_id(user.id)
            if not user_data:
                await interaction.followup.send(f"❌ {user.mention} is not registered!", ephemeral=True)
                return
            
            user_id = user_data['user_id']
            utc_time = datetime.now(pytz.utc)
            utc_time_no_tz = utc_time.replace(tzinfo=None)
            present_date = utc_time.date()
            
            # Check if already clocked in
            existing_record = await TimeTrackingModel.get_today_tracking(user_id, present_date)
            
            if existing_record and not existing_record['end_of_the_day']:
                await interaction.followup.send(f"⚠️ {user.mention} is already clocked in!", ephemeral=True)
                return
            
            # Force create time tracking
            time_tracking_id = await TimeTrackingModel.create_time_tracking(
                user_id=user_id,
                starting_time=utc_time_no_tz,
                present_date=present_date,
                clock_in_time=utc_time_no_tz,
                reason=f"FORCED: {reason}",
                screen_share_verified=True  # Auto-verified for admin force
            )
            
            await interaction.followup.send(
                f"✅ **Force clocked in {user.mention}**\n"
                f"**Time:** {utc_time.strftime('%I:%M %p')}\n"
                f"**Reason:** {reason}\n"
                f"**Tracking ID:** {time_tracking_id}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="force_clock_out",
        description="Force clock out a user (ADMIN only)"
    )
    @app_commands.describe(
        user="The user to force clock out",
        reason="Reason for force clock-out"
    )
    async def force_clock_out(self, interaction: discord.Interaction, user: discord.User, reason: str = "Forced by admin"):
        """Admin force clock out"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin
        from utils.verification_helper import is_admin, is_super_admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send("❌ Only ADMIN can force clock-out users!", ephemeral=True)
            return
        
        try:
            user_data = await UserModel.get_user_by_discord_id(user.id)
            if not user_data:
                await interaction.followup.send(f"❌ {user.mention} is not registered!", ephemeral=True)
                return
            
            user_id = user_data['user_id']
            utc_time = datetime.now(pytz.utc)
            utc_time_no_tz = utc_time.replace(tzinfo=None)
            present_date = utc_time.date()
            
            # Get today's record
            record = await TimeTrackingModel.get_today_tracking(user_id, present_date)
            
            if not record:
                await interaction.followup.send(f"❌ {user.mention} is not clocked in today!", ephemeral=True)
                return
            
            record_id = record['id']
            clock_in_times = record['clock_in'] if record['clock_in'] else []
            clock_out_times = record['clock_out'] if record['clock_out'] else []
            
            if len(clock_out_times) >= len(clock_in_times):
                await interaction.followup.send(f"⚠️ {user.mention} is already clocked out!", ephemeral=True)
                return
            
            # Calculate total time
            clock_out_times_temp = clock_out_times + [utc_time_no_tz]
            total_logged_minutes = 0
            for i in range(len(clock_out_times_temp)):
                if i < len(clock_in_times):
                    work_duration = (clock_out_times_temp[i] - clock_in_times[i]).total_seconds() / 60
                    total_logged_minutes += work_duration
            
            # Force clock out
            await TimeTrackingModel.add_clock_out(
                tracking_id=record_id,
                clock_out_time=utc_time_no_tz,
                reason=f"FORCED: {reason}",
                time_logged=int(total_logged_minutes)
            )
            
            # End day
            await TimeTrackingModel.end_day(record_id, utc_time_no_tz)
            
            # End screen share
            active_session = await ScreenShareModel.get_active_session_by_user(user_id)
            if active_session:
                await ScreenShareModel.end_session(active_session['session_id'], f"Forced: {reason}")
            
            await interaction.followup.send(
                f"✅ **Force clocked out {user.mention}**\n"
                f"**Time:** {utc_time.strftime('%I:%M %p')}\n"
                f"**Total logged:** {int(total_logged_minutes)//60}h {int(total_logged_minutes)%60}m\n"
                f"**Reason:** {reason}",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @app_commands.command(
        name="user_clockin_info",
        description="View detailed clock-in information for a user"
    )
    @app_commands.describe(user="The user to view (leave empty for yourself)")
    async def user_clockin_info(self, interaction: discord.Interaction, user: discord.User = None):
        """Show detailed clock-in information"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            target_user = user if user else interaction.user
            
            # Get user from database
            user_data = await UserModel.get_user_by_discord_id(target_user.id)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ {target_user.mention} is not registered!",
                    ephemeral=True
                )
                return
            
            user_id = user_data['user_id']
            present_date = datetime.now(pytz.utc).date()
            
            # Get today's tracking record
            record = await TimeTrackingModel.get_today_tracking(user_id, present_date)
            
            if not record:
                await interaction.followup.send(
                    f"📋 {target_user.mention} has not clocked in today!",
                    ephemeral=True
                )
                return
            
            # Build detailed information
            embed = discord.Embed(
                title=f"📊 Clock-in Details - {user_data['name']}",
                description=f"**Date:** {present_date.strftime('%Y-%m-%d')}",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Starting time
            start_time = record['starting_time']
            embed.add_field(
                name="🕐 Start Time",
                value=start_time.strftime('%I:%M %p') if isinstance(start_time, datetime) else str(start_time),
                inline=True
            )
            
            # End time
            end_time = record['end_of_the_day']
            if end_time:
                embed.add_field(
                    name="🕐 End Time",
                    value=end_time.strftime('%I:%M %p') if isinstance(end_time, datetime) else str(end_time),
                    inline=True
                )
            else:
                embed.add_field(name="🕐 End Time", value="Still working", inline=True)
            
            # Screen share verified
            verified = record.get('screen_share_verified', False)
            embed.add_field(
                name="🖥️ Screen Share",
                value="✅ Verified" if verified else "❌ Not Verified",
                inline=True
            )
            
            # Clock-in and clock-out details
            clock_ins = record['clock_in'] if record['clock_in'] else []
            clock_outs = record['clock_out'] if record['clock_out'] else []
            clockin_reasons = record['clockin_reason'] if record['clockin_reason'] else []
            clockout_reasons = record['clockout_reason'] if record['clockout_reason'] else []
            
            # Build sessions detail
            sessions_text = []
            for i in range(len(clock_ins)):
                in_time = clock_ins[i].strftime('%I:%M %p') if isinstance(clock_ins[i], datetime) else str(clock_ins[i])
                in_reason = clockin_reasons[i] if i < len(clockin_reasons) else "N/A"
                
                if i < len(clock_outs):
                    out_time = clock_outs[i].strftime('%I:%M %p') if isinstance(clock_outs[i], datetime) else str(clock_outs[i])
                    out_reason = clockout_reasons[i] if i < len(clockout_reasons) else "N/A"
                    
                    # Calculate session duration
                    if isinstance(clock_ins[i], datetime) and isinstance(clock_outs[i], datetime):
                        duration_mins = int((clock_outs[i] - clock_ins[i]).total_seconds() / 60)
                        duration_text = f"({duration_mins} min)"
                    else:
                        duration_text = ""
                    
                    sessions_text.append(
                        f"**Session {i+1}:**\n"
                        f"├ In: {in_time} - {in_reason}\n"
                        f"└ Out: {out_time} - {out_reason} {duration_text}"
                    )
                else:
                    sessions_text.append(
                        f"**Session {i+1}:**\n"
                        f"└ In: {in_time} - {in_reason}\n"
                        f"  (Currently active)"
                    )
            
            if sessions_text:
                embed.add_field(
                    name=f"🔄 Work Sessions ({len(clock_ins)} total)",
                    value="\n\n".join(sessions_text) if len(sessions_text) <= 5 else "\n\n".join(sessions_text[:5]) + f"\n\n... and {len(sessions_text)-5} more",
                    inline=False
                )
            
            # Time statistics
            total_logged = record['time_logged_in'] or 0
            break_duration = record['break_duration'] or 0
            break_count = record['break_counter'] or 0
            
            embed.add_field(
                name="⏱️ Time Logged",
                value=f"{total_logged//60}h {total_logged%60}m",
                inline=True
            )
            embed.add_field(
                name="☕ Total Break Time",
                value=f"{break_duration} min",
                inline=True
            )
            embed.add_field(
                name="🔢 Break Count",
                value=str(break_count),
                inline=True
            )
            
            # Check for late reason
            from models.late_reason_model import LateReasonModel
            late_reason = await LateReasonModel.get_late_reason_by_tracking_id(record['id'])
            
            if late_reason:
                embed.add_field(
                    name="⏰ Late Arrival",
                    value=(
                        f"**Late by:** {late_reason['late_mins']} minutes\n"
                        f"**Reason:** {late_reason['reason']}\n"
                        f"**Admin Informed:** {'✅' if late_reason['is_admin_informed'] else '❌'}\n"
                        f"**Meeting Attended:** {'✅' if late_reason['morning_meeting_attended'] else '❌'}\n"
                        f"**Approved:** {'✅' if late_reason.get('admin_approval') else '⏳ Pending'}"
                    ),
                    inline=False
                )
            
            embed.set_footer(text=f"Tracking ID: {record['id']}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)



async def setup(bot):
    await bot.add_cog(TimeTracking(bot))