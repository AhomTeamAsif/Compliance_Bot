import discord
from discord import ui
from datetime import datetime
from models.time_tracking_model import TimeTrackingModel
from models.work_update_model import WorkUpdateModel
from models.screen_share_model import ScreenShareModel


# ==================== WORK PLAN MODAL ====================

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
            f"**Tasks recorded!**\n**Have you turned on Desklog and Trackabi?**\nClick the buttons below:",
            view=view,
            ephemeral=True
        )


# ==================== TRACKING TOOLS VIEW ====================

class TrackingToolsView(ui.View):
    """View with Desklog and Trackabi toggle buttons"""
    
    def __init__(self, user_id: int, time_tracking_id: int, tasks: list, interaction_user: discord.User):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.tasks = tasks
        self.interaction_user = interaction_user
        self.desklog_on = False
        self.trackabi_on = False
    
    @ui.button(label="Desklog OFF", style=discord.ButtonStyle.red, custom_id="desklog", row=0)
    async def desklog_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle Desklog status"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.desklog_on = not self.desklog_on
        button.label = "Desklog ON" if self.desklog_on else "Desklog OFF"
        button.style = discord.ButtonStyle.green if self.desklog_on else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Trackabi OFF", style=discord.ButtonStyle.red, custom_id="trackabi", row=0)
    async def trackabi_button(self, interaction: discord.Interaction, button: ui.Button):
        """Toggle Trackabi status"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.trackabi_on = not self.trackabi_on
        button.label = "Trackabi ON" if self.trackabi_on else "Trackabi OFF"
        button.style = discord.ButtonStyle.green if self.trackabi_on else discord.ButtonStyle.red
        await interaction.response.edit_message(view=self)
    
    @ui.button(label="Continue", style=discord.ButtonStyle.primary, row=1)
    async def continue_button(self, interaction: discord.Interaction, button: ui.Button):
        """Save tracking tools status and proceed to screen share"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        try:
            # Save work update to database
            await WorkUpdateModel.create_work_update(
                user_id=self.user_id,
                time_tracking_id=self.time_tracking_id,
                tasks=self.tasks,
                desklog_on=self.desklog_on,
                trackabi_on=self.trackabi_on
            )
            
            # Build summary
            task_list = "\n".join([f"  {i+1}. {task}" for i, task in enumerate(self.tasks)])
            warnings = []
            if not self.desklog_on:
                warnings.append("⚠️ Desklog is OFF")
            if not self.trackabi_on:
                warnings.append("⚠️ Trackabi is OFF")
            
            warning_text = "\n".join(warnings) if warnings else "✅ All tracking tools are ON"
            
            await interaction.response.edit_message(
                content=(
                    f"**✅ Daily Plan Saved!**\n\n"
                    f"**Your Tasks:**\n{task_list}\n\n"
                    f"**Tracking Status:**\n{warning_text}"
                ),
                view=None
            )
            
            # Show screen share verification view
            view = ScreenShareVerificationView(
                self.user_id, 
                self.time_tracking_id, 
                self.interaction_user,
                is_start_of_day=True
            )
            
            embed = discord.Embed(
                title="🖥️ Screen Share Required",
                description=(
                    "**Please start your Discord screen share NOW!**\n\n"
                    "⚠️ **Important:**\n"
                    "• Make sure you're streaming your screen\n"
                    "• Once you've started screen sharing, click the **Verify & Continue** button below\n"
                    "• The system will verify that you're actually streaming\n\n"
                    "**You will NOT be clocked in until screen share is verified!**"
                ),
                color=discord.Color.red()
            )
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            self.stop()
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error saving work plan: {str(e)}",
                ephemeral=True
            )


# ==================== SCREEN SHARE VERIFICATION VIEW ====================

class ScreenShareVerificationView(ui.View):
    """Verify user is actually screen sharing before completing clock-in"""
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User, is_start_of_day: bool = True):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
        self.is_start_of_day = is_start_of_day
    
    @ui.button(label="Verify & Continue", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        """Verify screen share and complete clock-in"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is actually streaming
            member = interaction.guild.get_member(interaction.user.id)
            
            if not member:
                await interaction.followup.send(
                    "❌ Could not verify your status in the server!",
                    ephemeral=True
                )
                return
            
            # Check voice state
            is_streaming = False
            if member.voice:
                # Check if user is in a voice channel and streaming
                if member.voice.self_stream:
                    is_streaming = True
            
            if not is_streaming:
                await interaction.followup.send(
                    "❌ **Screen share not detected!**\n\n"
                    "Please make sure:\n"
                    "• You are in a voice channel\n"
                    "• You have started screen sharing (not just camera)\n"
                    "• Try again after starting screen share",
                    ephemeral=True
                )
                return
            
            # Screen share verified - create session and complete clock-in
            session_id = await ScreenShareModel.start_session(
                user_id=self.user_id,
                time_tracking_id=self.time_tracking_id,
                reason="Start of work session"
            )
            
            # Update time tracking as verified
            await TimeTrackingModel.update_screen_share_verified(self.time_tracking_id, True)
            
            # Success message
            success_msg = (
                f"✅ **Clock-in Complete!**\n\n"
                f"**Screen Share:** Verified ✅\n"
                f"**Session ID:** `{session_id}`\n\n"
            )
            
            if self.is_start_of_day:
                success_msg += "**Your workday has officially started!** 🎉\n\nRemember to keep screen sharing on during work hours."
            else:
                success_msg += "**Break ended - Back to work!** 💼\n\nRemember to keep screen sharing on."
            
            await interaction.followup.send(success_msg, ephemeral=True)
            
            # Stop the view
            await interaction.edit_original_response(
                embed=discord.Embed(
                    title="✅ Verified Successfully",
                    description="Screen share has been verified. You're all set!",
                    color=discord.Color.green()
                ),
                view=None
            )
            self.stop()
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error during verification: {str(e)}",
                ephemeral=True
            )
    
    @ui.button(label="Cancel", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        """Cancel clock-in process"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        # Delete the time tracking record since user didn't complete
        # Note: You might want to handle this differently based on your requirements
        
        await interaction.response.send_message(
            "❌ Clock-in cancelled. Screen share was not verified.\n\n"
            "**You are NOT clocked in.** Please start the clock-in process again when ready.",
            ephemeral=True
        )
        self.stop()


# ==================== SIMPLE SCREEN SHARE PROMPT (for additional clock-ins) ====================

class SimpleScreenShareView(ui.View):
    """Simplified screen share verification for additional clock-ins (after breaks)"""
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
    
    @ui.button(label="I've Started Screen Share", style=discord.ButtonStyle.success, emoji="✅")
    async def verify_button(self, interaction: discord.Interaction, button: ui.Button):
        """Verify screen share for break return"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is streaming
            member = interaction.guild.get_member(interaction.user.id)
            
            if not member:
                await interaction.followup.send(
                    "❌ Could not verify your status!",
                    ephemeral=True
                )
                return
            
            is_streaming = False
            if member.voice and member.voice.self_stream:
                is_streaming = True
            
            if not is_streaming:
                await interaction.followup.send(
                    "❌ **Screen share not detected!**\n\n"
                    "Please start screen sharing and try again.",
                    ephemeral=True
                )
                return
            
            # Get existing session or create new one
            existing_session = await ScreenShareModel.get_session_by_tracking_id(self.time_tracking_id)
            
            if existing_session and not existing_session['screen_share_off_time']:
                # Session still active
                session_id = existing_session['session_id']
            else:
                # Create new session
                session_id = await ScreenShareModel.start_session(
                    user_id=self.user_id,
                    time_tracking_id=self.time_tracking_id,
                    reason="Resumed after break"
                )
            
            await interaction.followup.send(
                f"✅ **Screen Share Verified!**\n\n"
                f"You're back to work. Session ID: `{session_id}`",
                ephemeral=True
            )
            
            await interaction.edit_original_response(
                content="✅ Screen share verified. Back to work!",
                view=None
            )
            self.stop()
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )


# ==================== WORK PLAN PROMPT VIEW ====================

class PlanKnownView(ui.View):
    """Ask user if they know their daily plan"""
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
    
    @ui.button(label="Yes, I know my plan", style=discord.ButtonStyle.green, emoji="✅")
    async def yes_button(self, interaction: discord.Interaction, button: ui.Button):
        """User knows their plan - show task modal"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        modal = TaskPlanModal(self.user_id, self.time_tracking_id, self.interaction_user)
        await interaction.response.send_modal(modal)
        self.stop()
    
    @ui.button(label="No, I'll plan later", style=discord.ButtonStyle.red, emoji="❌")
    async def no_button(self, interaction: discord.Interaction, button: ui.Button):
        """User doesn't know plan - skip to screen share"""
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        await interaction.response.send_message(
            "⚠️ **Please plan your day and update later!**\n\nProceeding to screen share verification...",
            ephemeral=True
        )
        
        # Save empty work update
        await WorkUpdateModel.create_work_update(
            user_id=self.user_id,
            time_tracking_id=self.time_tracking_id,
            tasks=["No plan submitted"],
            desklog_on=False,
            trackabi_on=False
        )
        
        # Show screen share verification
        view = ScreenShareVerificationView(
            self.user_id,
            self.time_tracking_id,
            self.interaction_user,
            is_start_of_day=True
        )
        
        embed = discord.Embed(
            title="🖥️ Screen Share Required",
            description=(
                "**Please start your Discord screen share NOW!**\n\n"
                "⚠️ **Important:**\n"
                "• Make sure you're streaming your screen\n"
                "• Once you've started screen sharing, click the **Verify & Continue** button\n\n"
                "**You will NOT be clocked in until screen share is verified!**"
            ),
            color=discord.Color.red()
        )
        
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        self.stop()

# ==================== LATE REASON VIEW ====================

class LateReasonView(ui.View):
    """View for submitting late reason with button selections"""
    
    def __init__(self, late_data: dict, interaction_user: discord.User, cog):
        super().__init__(timeout=180)
        self.late_data = late_data
        self.interaction_user = interaction_user
        self.cog = cog
        
        # Track selections
        self.admin_informed = None
        self.meeting_attended = None
    
    @ui.button(label="Admin Informed: Yes", style=discord.ButtonStyle.green, custom_id="admin_yes", row=0)
    async def admin_yes_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.admin_informed = True
        await self.update_button_states(interaction, "admin")
    
    @ui.button(label="Admin Informed: No", style=discord.ButtonStyle.red, custom_id="admin_no", row=0)
    async def admin_no_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.admin_informed = False
        await self.update_button_states(interaction, "admin")
    
    @ui.button(label="Meeting Attended: Yes", style=discord.ButtonStyle.green, custom_id="meeting_yes", row=1)
    async def meeting_yes_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.meeting_attended = True
        await self.update_button_states(interaction, "meeting")
    
    @ui.button(label="Meeting Attended: No", style=discord.ButtonStyle.red, custom_id="meeting_no", row=1)
    async def meeting_no_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        self.meeting_attended = False
        await self.update_button_states(interaction, "meeting")
    
    @ui.button(label="Continue with Reason", style=discord.ButtonStyle.primary, disabled=True, row=2)
    async def continue_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        # Show modal for reason
        modal = LateReasonModal(self.late_data, self.admin_informed, self.meeting_attended, self.interaction_user, self.cog)
        await interaction.response.send_modal(modal)
        self.stop()
    
    async def update_button_states(self, interaction: discord.Interaction, button_type: str):
        """Update button states based on selections"""
        
        # Update button styles
        for item in self.children[:-1]:  # Exclude continue button
            if isinstance(item, ui.Button):
                if button_type == "admin" and "Admin" in item.label:
                    if (self.admin_informed and "Yes" in item.label) or (not self.admin_informed and "No" in item.label):
                        item.style = discord.ButtonStyle.success if self.admin_informed else discord.ButtonStyle.danger
                        item.disabled = False
                    else:
                        item.style = discord.ButtonStyle.secondary
                        item.disabled = False
                
                elif button_type == "meeting" and "Meeting" in item.label:
                    if (self.meeting_attended and "Yes" in item.label) or (not self.meeting_attended and "No" in item.label):
                        item.style = discord.ButtonStyle.success if self.meeting_attended else discord.ButtonStyle.danger
                        item.disabled = False
                    else:
                        item.style = discord.ButtonStyle.secondary
                        item.disabled = False
        
        # Enable continue button if both selections made
        if self.admin_informed is not None and self.meeting_attended is not None:
            self.continue_button.disabled = False
        
        await interaction.response.edit_message(view=self)


class LateReasonModal(ui.Modal, title='Late Arrival Reason'):
    reason = ui.TextInput(
        label='Reason for being late',
        style=discord.TextStyle.paragraph,
        placeholder='Explain why you were late...',
        required=True,
        max_length=500
    )
    
    def __init__(self, late_data: dict, admin_informed: bool, meeting_attended: bool, interaction_user: discord.User, cog):
        super().__init__()
        self.late_data = late_data
        self.admin_informed = admin_informed
        self.meeting_attended = meeting_attended
        self.interaction_user = interaction_user
        self.cog = cog
    
    async def on_submit(self, interaction: discord.Interaction):
        from models.time_tracking_model import TimeTrackingModel
        from models.late_reason_model import LateReasonModel
        from views.clockin_clockout_views import PlanKnownView
        
        # Create time tracking record
        time_tracking_id = await TimeTrackingModel.create_time_tracking(
            user_id=self.late_data['user_id'],
            starting_time=self.late_data['utc_time_no_tz'],
            present_date=self.late_data['present_date'],
            clock_in_time=self.late_data['utc_time_no_tz'],
            reason=self.late_data['reason'],
            screen_share_verified=False
        )
        
        # Record late reason
        await LateReasonModel.create_late_reason(
            user_id=self.late_data['user_id'],
            time_tracking_id=time_tracking_id,
            late_mins=self.late_data['late_minutes'],
            reason=self.reason.value,
            is_admin_informed=self.admin_informed,
            morning_meeting_attended=self.meeting_attended
        )
        
        await interaction.response.send_message(
            f"✅ **Late reason recorded!**\n\n"
            f"**Time:** {self.late_data['utc_time'].strftime('%I:%M %p')}\n"
            f"**Late by:** {self.late_data['late_minutes']} minutes\n"
            f"**Reason:** {self.reason.value}\n"
            f"**Admin Informed:** {'✅ Yes' if self.admin_informed else '❌ No'}\n"
            f"**Meeting Attended:** {'✅ Yes' if self.meeting_attended else '❌ No'}\n\n"
            f"⚠️ **Clock-in NOT complete yet!** Please continue...",
            ephemeral=True
        )
        
        # Ask about daily plan
        plan_view = PlanKnownView(self.late_data['user_id'], time_tracking_id, self.interaction_user)
        await interaction.followup.send(
            "**📋 Do you know your workday plan?**",
            view=plan_view,
            ephemeral=True
        )
# ==================== SCREEN SHARE STOP REMINDER ====================

class ScreenShareStopReminderView(ui.View):
    """Reminder to stop screen share after clock-out"""
    
    def __init__(self):
        super().__init__(timeout=300)
    
    @ui.button(label="✅ I've Stopped Screen Share", style=discord.ButtonStyle.success)
    async def stopped_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(
            content="✅ Great! Have a good rest. See you tomorrow! 👋",
            embed=None,
            view=None
        )
        self.stop()

# ==================== END OF DAY WORK UPDATE ====================

class EndOfDayUpdateModal(ui.Modal, title='End of Day Update'):
    """Modal for recording what was accomplished today"""
    
    completed1 = ui.TextInput(
        label='Task Completed 1',
        style=discord.TextStyle.short,
        required=True,
        max_length=200,
        placeholder='Main task completed today'
    )
    completed2 = ui.TextInput(
        label='Task Completed 2 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    completed3 = ui.TextInput(
        label='Task Completed 3 (optional)',
        style=discord.TextStyle.short,
        required=False,
        max_length=200
    )
    issues = ui.TextInput(
        label='Issues/Blockers (optional)',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
        placeholder='Any issues or blockers faced today'
    )
    tomorrow = ui.TextInput(
        label='Plans for Tomorrow (optional)',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300,
        placeholder='What you plan to work on tomorrow'
    )
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User, clock_out_data: dict):
        super().__init__()
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
        self.clock_out_data = clock_out_data
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process end of day update"""
        from models.work_update_model import WorkUpdateModel
        
        completed_tasks = []
        for task_input in [self.completed1, self.completed2, self.completed3]:
            if task_input.value and task_input.value.strip():
                completed_tasks.append(task_input.value.strip())
        
        issues_text = self.issues.value.strip() if self.issues.value else "None"
        tomorrow_text = self.tomorrow.value.strip() if self.tomorrow.value else "Not specified"
        
        # Save end of day update to database
        success = await WorkUpdateModel.update_end_of_day(
            time_tracking_id=self.time_tracking_id,
            completed_tasks=completed_tasks,
            issues=issues_text,
            tomorrow_plans=tomorrow_text
        )
        
        if success:
            await interaction.response.send_message(
                f"✅ **End of Day Update Recorded!**\n\n"
                f"**Completed Tasks:**\n" + "\n".join([f"{i+1}. {task}" for i, task in enumerate(completed_tasks)]) + "\n\n"
                f"**Issues:** {issues_text}\n"
                f"**Tomorrow's Plans:** {tomorrow_text}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ **Could not save end-of-day update!**\n\n"
                f"No work plan was recorded for today. Please contact admin.",
                ephemeral=True
            )
        
        # Complete the clock-out process
        await self.complete_clock_out(interaction)
    
    async def complete_clock_out(self, interaction):
        """Complete the clock-out process"""
        from models.screen_share_model import ScreenShareModel
        
        # End screen share session
        active_session = await ScreenShareModel.get_active_session_by_user(self.user_id)
        if active_session:
            await ScreenShareModel.end_session(
                session_id=active_session['session_id'],
                reason="End of day"
            )
        
        # Show screen share stop reminder
        reminder_embed = discord.Embed(
            title="🖥️ Remember to Stop Screen Share",
            description=(
                "**Your workday has ended!**\n\n"
                "📢 **Please STOP your Discord screen share now.**\n\n"
                "✅ You can close this message once you've stopped screen sharing."
            ),
            color=discord.Color.red()
        )
        
        stop_view = ScreenShareStopReminderView()
        await interaction.followup.send(embed=reminder_embed, view=stop_view, ephemeral=True)

class EndOfDayPromptView(ui.View):
    """Prompt to fill end of day update"""
    
    def __init__(self, user_id: int, time_tracking_id: int, interaction_user: discord.User, clock_out_data: dict):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.time_tracking_id = time_tracking_id
        self.interaction_user = interaction_user
        self.clock_out_data = clock_out_data
    
    @ui.button(label="Fill End of Day Update", style=discord.ButtonStyle.primary, emoji="📝")
    async def fill_update_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.interaction_user.id:
            await interaction.response.send_message("This is not your prompt!", ephemeral=True)
            return
        
        modal = EndOfDayUpdateModal(self.user_id, self.time_tracking_id, self.interaction_user, self.clock_out_data)
        await interaction.response.send_modal(modal)
        self.stop()