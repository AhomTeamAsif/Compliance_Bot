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
    ScreenShareVerificationView
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
        
        # Must be "Start of the day"
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
                f"⚠️ **You are {late_minutes} minutes late!**\n\n"
                f"Please use `/late_reason` command to submit your late reason.",
                ephemeral=True
            )
            return
        
        # On time - create record (NOT VERIFIED YET)
        time_tracking_id = await TimeTrackingModel.create_time_tracking(
            user_id=user_id,
            starting_time=utc_time_no_tz,
            present_date=present_date,
            clock_in_time=utc_time_no_tz,
            reason=reason,
            screen_share_verified=False  # Not verified yet
        )
        
        await interaction.followup.send(
            f"⏰ Clock-in time recorded: **{utc_time.strftime('%I:%M %p')}** - On time!\n\n"
            f"⚠️ **Clock-in NOT complete yet!** Please continue with the next steps...",
            ephemeral=True
        )
        
        # Ask about daily plan
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
                # End of the day
                await TimeTrackingModel.end_day(record_id, utc_time_no_tz)
                
                required_minutes = 480  # 8 hours
                if int(total_logged_minutes) < required_minutes:
                    short_minutes = required_minutes - int(total_logged_minutes)
                    short_hours = short_minutes // 60
                    short_mins = short_minutes % 60
                    
                    await interaction.followup.send(
                        f"✅ **Clocked out - End of Day**\n\n"
                        f"**Clock-out time:** {utc_time.strftime('%I:%M %p')}\n"
                        f"**This session duration:** {current_session_minutes} minutes\n"
                        f"**Total time logged today:** {int(total_logged_minutes)} minutes "
                        f"({int(total_logged_minutes)//60}h {int(total_logged_minutes)%60}m)\n\n"
                        f"⚠️ **Warning:** You worked **{short_hours}h {short_mins}m less** than the required 8 hours!\n"
                        f"**Reason:** {reason}",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        f"✅ **Clocked out - End of Day**\n\n"
                        f"**Clock-out time:** {utc_time.strftime('%I:%M %p')}\n"
                        f"**This session duration:** {current_session_minutes} minutes\n"
                        f"**Total time logged today:** {int(total_logged_minutes)} minutes "
                        f"({int(total_logged_minutes)//60}h {int(total_logged_minutes)%60}m)\n\n"
                        f"🎉 **Great job today!**\n"
                        f"**Reason:** {reason}",
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
                    f"📱 **Remember:** ⚠️ Please stop screen sharing now...",
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
        morning_meeting="Did you join the morning meeting? (yes/no)",
        reason="Reason for being late"
    )
    async def late_reason(self, interaction: discord.Interaction, admin_informed: str, morning_meeting: str, reason: str):
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
            morning_meeting_attended = morning_meeting.lower() in ['yes', 'y']
            
            # Create time tracking record (NOT VERIFIED YET)
            time_tracking_id = await TimeTrackingModel.create_time_tracking(
                user_id=data['user_id'],
                starting_time=data['utc_time_no_tz'],
                present_date=data['present_date'],
                clock_in_time=data['utc_time_no_tz'],
                reason=data['reason'],
                screen_share_verified=False  # Not verified yet
            )
            
            # Record late reason
            await LateReasonModel.create_late_reason(
                user_id=data['user_id'],
                time_tracking_id=time_tracking_id,
                late_mins=data['late_minutes'],
                reason=reason,
                is_admin_informed=is_admin_informed,
                morning_meeting_attended=morning_meeting_attended
            )
            
            # Remove from pending
            del self.pending_late_clockins[interaction.user.id]
            
            await interaction.followup.send(
                f"✅ **Late reason recorded!**\n\n"
                f"**Time:** {data['utc_time'].strftime('%I:%M %p')}\n"
                f"**Late by:** {data['late_minutes']} minutes\n"
                f"**Reason:** {reason}\n"
                f"**Admin Informed:** {'Yes' if is_admin_informed else 'No'}\n"
                f"**Morning Meeting Attended:** {'Yes' if morning_meeting_attended else 'No'}\n\n"
                f"⚠️ **Clock-in NOT complete yet!** Please continue...",
                ephemeral=True
            )
            
            # Ask about daily plan
            view = PlanKnownView(data['user_id'], time_tracking_id, interaction.user)
            await interaction.followup.send(
                "**📋 Do you know your workday plan?**",
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


async def setup(bot):
    await bot.add_cog(TimeTracking(bot))