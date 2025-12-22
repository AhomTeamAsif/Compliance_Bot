import discord
from discord import ui
from datetime import datetime
from models.activity_log_model import ActivityLogModel


# ==================== ACTIVITY LOGS PAGINATION ====================

class ActivityLogsPaginationView(discord.ui.View):
    def __init__(self, total_count: int, per_page: int = 15, user_id: int = None):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.current_page = 1
        self.per_page = per_page
        self.total_count = total_count
        self.total_pages = max(1, (total_count + per_page - 1) // per_page)
        self.user_id = user_id  # If set, filter by user
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page"""
        # Disable first/previous on first page
        self.first_button.disabled = (self.current_page == 1)
        self.prev_button.disabled = (self.current_page == 1)
        
        # Disable next/last on last page
        self.next_button.disabled = (self.current_page >= self.total_pages)
        self.last_button.disabled = (self.current_page >= self.total_pages)
        
        # Update page indicator button label
        self.page_indicator.label = f"Page {self.current_page}/{self.total_pages}"
    
    async def fetch_and_display_logs(self, interaction: discord.Interaction):
        """Fetch logs for current page and display them"""
        offset = (self.current_page - 1) * self.per_page
        
        # Fetch logs based on filter
        if self.user_id:
            logs = await ActivityLogModel.get_activity_logs_by_user(
                user_id=self.user_id,
                limit=self.per_page,
                offset=offset
            )
        else:
            logs = await ActivityLogModel.get_activity_logs(
                limit=self.per_page,
                offset=offset
            )
        
        if not logs:
            await interaction.response.edit_message(
                content="📋 No activity logs found on this page!",
                embed=None,
                view=None
            )
            return
        
        # Create title based on filter
        if self.user_id:
            # Get user info for title
            user_name = logs[0]['user_name'] if logs else "Unknown"
            title = f"📊 Activity Logs - {user_name}"
        else:
            title = f"📊 Activity Logs - All Users"
        
        embed = discord.Embed(
            title=title,
            description=f"**Total Logs:** {self.total_count} | **Page:** {self.current_page}/{self.total_pages}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for log in logs:
            user_mention = f"<@{log['user_discord_id']}>" if log['user_discord_id'] else "Unknown"
            role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(log['user_role_id'], "NORMAL")
            
            field_value = (
                f"**User:** {user_mention} ({log['user_name'] or 'N/A'})\n"
                f"**Department:** {log['user_department'] or 'N/A'}\n"
                f"**Role:** {role_name}\n"
                f"**Command:** `/{log['slash_command_used']}`\n"
                f"**Executed At:** <t:{int(log['created_at'].timestamp())}:f>"
            )
            
            embed.add_field(
                name=f"Log ID: {log['id']} | User ID: {log['user_id']}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Showing logs {offset + 1}-{min(offset + len(logs), self.total_count)} of {self.total_count}")
        
        self.update_buttons()
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except discord.errors.InteractionResponded:
            await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="⏮️ First", style=discord.ButtonStyle.secondary, row=0)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = 1
        await self.fetch_and_display_logs(interaction)
    
    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.primary, row=0)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = max(1, self.current_page - 1)
        await self.fetch_and_display_logs(interaction)
    
    @discord.ui.button(label="Page 1/1", style=discord.ButtonStyle.secondary, disabled=True, row=0)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This button is just for display, no action needed
        await interaction.response.defer()
    
    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.primary, row=0)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = min(self.total_pages, self.current_page + 1)
        await self.fetch_and_display_logs(interaction)
    
    @discord.ui.button(label="Last ⏭️", style=discord.ButtonStyle.secondary, row=0)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.total_pages
        await self.fetch_and_display_logs(interaction)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success, row=1)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Refresh current page (useful for real-time updates)
        await self.fetch_and_display_logs(interaction)
    
    @discord.ui.button(label="❌ Close", style=discord.ButtonStyle.danger, row=1)
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="✅ Activity logs viewer closed.",
            embed=None,
            view=None
        )
        self.stop()