import discord
from discord import ui
from datetime import datetime
import json
from models.user_model import UserModel


# ==================== UPDATE LOGS PAGINATION ====================

class UpdateLogsPaginationView(discord.ui.View):
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
            logs = await UserModel.get_update_logs_by_user(
                user_id=self.user_id,
                limit=self.per_page,
                offset=offset
            )
        else:
            logs = await UserModel.get_update_logs(
                limit=self.per_page,
                offset=offset
            )
        
        if not logs:
            await interaction.response.edit_message(
                content="📋 No update logs found on this page!",
                embed=None,
                view=None
            )
            return
        
        # Get role names mapping
        role_names = {
            1: "SUPER ADMIN",
            2: "ADMIN", 
            3: "NORMAL"
        }
        
        # Create title based on filter
        if self.user_id:
            user_name = logs[0]['updated_user_name'] if logs else "Unknown"
            title = f"📝 Update Logs - {user_name}"
        else:
            title = f"📝 Update Logs - All Users"
        
        embed = discord.Embed(
            title=title,
            description=f"**Total Logs:** {self.total_count} | **Page:** {self.current_page}/{self.total_pages}",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for log in logs:
            updated_user_mention = f"<@{log['updated_user_discord_id']}>" if log['updated_user_discord_id'] else "Unknown"
            updated_by_mention = f"<@{log['updated_by_discord_id']}>" if log['updated_by_discord_id'] else "Unknown"
            
            # Parse JSON values
            old_values = json.loads(log['old_values']) if log['old_values'] else {}
            new_values = json.loads(log['new_values']) if log['new_values'] else {}
            
            # Build field changes text with role name conversion
            changes_text = []
            role_changed = False
            
            if log['fields_updated']:
                for field in log['fields_updated']:
                    old_val = old_values.get(field, 'N/A')
                    new_val = new_values.get(field, 'N/A')
                    
                    # Special handling for role_id
                    if field == 'role_id':
                        old_role_name = role_names.get(old_val, f"Unknown ({old_val})")
                        new_role_name = role_names.get(new_val, f"Unknown ({new_val})")
                        changes_text.append(f"🎭 **Role:** `{old_role_name}` → `{new_role_name}`")
                        role_changed = True
                    else:
                        changes_text.append(f"**{field}:** `{old_val}` → `{new_val}`")
            
            # Build permission changes text
            perm_changes = []
            if log['permissions_added']:
                perm_changes.append(f"✅ Added {len(log['permissions_added'])} permission(s)")
            if log['permissions_removed']:
                perm_changes.append(f"❌ Removed {len(log['permissions_removed'])} permission(s)")
            
            # Build comprehensive field value
            field_value = f"👤 **Updated User:** {updated_user_mention}\n"
            field_value += f"├─ **Name:** {log['updated_user_name'] or 'N/A'}\n"
            field_value += f"├─ **Department:** {log['updated_user_department'] or 'N/A'}\n"
            field_value += f"├─ **User ID:** `{log['updated_user_id']}`\n"
            field_value += f"└─ **Discord ID:** `{log['updated_user_discord_id'] or 'N/A'}`\n\n"
            
            field_value += f"👔 **Updated By:** {updated_by_mention}\n"
            field_value += f"└─ **Name:** {log['updated_by_name'] or 'N/A'}\n\n"
            
            field_value += f"📋 **Update Type:** {log['update_type']}\n"
            
            if role_changed:
                field_value += f"⚠️ **Role Change Detected!**\n"
            
            if changes_text:
                field_value += f"\n📝 **Changes Made:**\n" + "\n".join(changes_text) + "\n"
            
            if perm_changes:
                field_value += f"\n🔐 **Permission Changes:**\n" + "\n".join(perm_changes) + "\n"
            
            field_value += f"\n🕒 **Timestamp:** <t:{int(log['updated_at'].timestamp())}:f>"
            
            # Add emoji indicator for update type
            update_type_emoji = "🔄"
            if log['update_type'] == 'role_change':
                update_type_emoji = "🎭"
            elif log['update_type'] == 'permission_change':
                update_type_emoji = "🔐"
            
            embed.add_field(
                name=f"{update_type_emoji} Log #{log['id']}",
                value=field_value,
                inline=False
            )
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━━━", inline=False)
        
        # Remove last separator
        if embed.fields:
            embed.remove_field(-1)
        
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
            content="✅ Update logs viewer closed.",
            embed=None,
            view=None
        )
        self.stop() 