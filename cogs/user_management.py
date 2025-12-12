import discord
from discord.ext import commands
from discord import app_commands
from models import UserModel

# Modal for User Registration
class UserRegistrationModal(discord.ui.Modal, title='User Registration'):
    name = discord.ui.TextInput(
        label='Full Name',
        placeholder='Enter your full name',
        required=True,
        max_length=255
    )
    
    department = discord.ui.TextInput(
        label='Department',
        placeholder='e.g., Engineering, Sales, HR',
        required=False,
        max_length=100
    )
    
    position = discord.ui.TextInput(
        label='Position',
        placeholder='e.g., Software Engineer, Manager',
        required=False,
        max_length=100
    )
    
    trackabi_id = discord.ui.TextInput(
        label='Trackabi ID',
        placeholder='Your Trackabi ID',
        required=False,
        max_length=100
    )
    
    desklog_id = discord.ui.TextInput(
        label='Desklog ID',
        placeholder='Your Desklog ID',
        required=False,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_id = await UserModel.user_registration(
                discord_id=interaction.user.id,
                name=self.name.value,
                department=self.department.value or None,
                position=self.position.value or None,
                trackabi_id=self.trackabi_id.value or None,
                desklog_id=self.desklog_id.value or None
            )
            
            embed = discord.Embed(
                title="✅ Registration Successful!",
                description=f"Welcome to the system, **{self.name.value}**!",
                color=discord.Color.green()
            )
            embed.add_field(name="User ID", value=user_id, inline=True)
            embed.add_field(name="Department", value=self.department.value or "Not set", inline=True)
            embed.add_field(name="Position", value=self.position.value or "Not set", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(
                f"⚠️ {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Registration failed: {str(e)}",
                ephemeral=True
            )

# Modal for User Info Update
class UserUpdateModal(discord.ui.Modal, title='Update User Information'):
    name = discord.ui.TextInput(
        label='Full Name',
        required=False,
        max_length=255
    )
    
    department = discord.ui.TextInput(
        label='Department',
        required=False,
        max_length=100
    )
    
    position = discord.ui.TextInput(
        label='Position',
        required=False,
        max_length=100
    )
    
    trackabi_id = discord.ui.TextInput(
        label='Trackabi ID',
        required=False,
        max_length=100
    )
    
    desklog_id = discord.ui.TextInput(
        label='Desklog ID',
        required=False,
        max_length=100
    )
    
    def __init__(self, current_data: dict):
        super().__init__()
        # Pre-fill with current data
        self.name.default = current_data.get('name', '')
        self.department.default = current_data.get('department', '') or ''
        self.position.default = current_data.get('position', '') or ''
        self.trackabi_id.default = current_data.get('trackabi_id', '') or ''
        self.desklog_id.default = current_data.get('desklog_id', '') or ''
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Build update dict with only changed fields
            updates = {}
            if self.name.value: updates['name'] = self.name.value
            if self.department.value: updates['department'] = self.department.value
            if self.position.value: updates['position'] = self.position.value
            if self.trackabi_id.value: updates['trackabi_id'] = self.trackabi_id.value
            if self.desklog_id.value: updates['desklog_id'] = self.desklog_id.value
            
            if not updates:
                await interaction.response.send_message(
                    "⚠️ No changes detected!",
                    ephemeral=True
                )
                return
            
            success = await UserModel.user_info_update(
                discord_id=interaction.user.id,
                **updates
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ Profile Updated!",
                    description="Your information has been updated successfully.",
                    color=discord.Color.green()
                )
                
                for key, value in updates.items():
                    embed.add_field(name=key.replace('_', ' ').title(), value=value, inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(
                    "❌ Failed to update user information!",
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Update failed: {str(e)}",
                ephemeral=True
            )


class UserManagement(commands.Cog):
    """User management and onboarding commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="user_register",
        description="Register yourself in the system"
    )
    async def user_register(self, interaction: discord.Interaction):
        """Show registration modal"""
        # Check if user already registered
        exists = await UserModel.user_exists(interaction.user.id)
        if exists:
            await interaction.response.send_message(
                "⚠️ You are already registered! Use `/user_update` to update your information.",
                ephemeral=True
            )
            return
        
        # Show registration modal
        await interaction.response.send_modal(UserRegistrationModal())
    
    @app_commands.command(
        name="user_update",
        description="Update your user information"
    )
    async def user_update(self, interaction: discord.Interaction):
        """Show update modal with current data"""
        # Get current user data
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        
        if not user:
            await interaction.response.send_message(
                "❌ You are not registered! Use `/user_register` first.",
                ephemeral=True
            )
            return
        
        # Show update modal with current data
        modal = UserUpdateModal(dict(user))
        await interaction.response.send_modal(modal)
    
    @app_commands.command(
        name="user_info",
        description="View your user information"
    )
    async def user_info(self, interaction: discord.Interaction):
        """Display user information"""
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        
        if not user:
            await interaction.response.send_message(
                "❌ You are not registered! Use `/user_register` first.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="👤 User Profile",
            description=f"Information for {interaction.user.mention}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="📛 Name", value=user['name'], inline=True)
        embed.add_field(name="🏢 Department", value=user['department'] or "Not set", inline=True)
        embed.add_field(name="💼 Position", value=user['position'] or "Not set", inline=True)
        embed.add_field(name="🆔 User ID", value=user['user_id'], inline=True)
        embed.add_field(name="📊 Trackabi ID", value=user['trackabi_id'] or "Not set", inline=True)
        embed.add_field(name="🖥️ Desklog ID", value=user['desklog_id'] or "Not set", inline=True)
        
        embed.set_footer(text=f"Registered on: {user['created_at'].strftime('%Y-%m-%d')}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="user_delete",
        description="Delete your account from the system"
    )
    async def user_delete(self, interaction: discord.Interaction):
        """Delete user account with confirmation"""
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        
        if not user:
            await interaction.response.send_message(
                "❌ You are not registered in the system!",
                ephemeral=True
            )
            return
        
        # Create confirmation view
        view = UserDeleteConfirmView(interaction.user.id)
        
        embed = discord.Embed(
            title="⚠️ Account Deletion",
            description="Are you sure you want to delete your account?\n\n"
                       "**This action will:**\n"
                       "• Remove all your user data\n"
                       "• Delete all your screen share history\n"
                       "• Cannot be undone\n",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="user_list",
        description="List all registered users (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def user_list(self, interaction: discord.Interaction):
        """List all users in the system"""
        await interaction.response.defer(ephemeral=True)
        
        users = await UserModel.get_all_users()
        
        if not users:
            await interaction.followup.send(
                "📋 No users registered in the system.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="👥 Registered Users",
            description=f"Total: {len(users)} users",
            color=discord.Color.blue()
        )
        
        for user in users[:25]:  # Discord has 25 fields limit
            value = (
                f"**Department:** {user['department'] or 'N/A'}\n"
                f"**Position:** {user['position'] or 'N/A'}\n"
                f"**Discord ID:** {user['discord_id']}"
            )
            embed.add_field(
                name=f"{user['name']} (ID: {user['user_id']})",
                value=value,
                inline=True
            )
        
        if len(users) > 25:
            embed.set_footer(text=f"Showing 25 of {len(users)} users")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="user_search",
        description="Search for a user (Admin only)"
    )
    @app_commands.describe(query="User name or Discord username to search for")
    @app_commands.checks.has_permissions(administrator=True)
    async def user_search(self, interaction: discord.Interaction, query: str):
        """Search for users by name"""
        await interaction.response.defer(ephemeral=True)
        
        all_users = await UserModel.get_all_users()
        
        # Filter users by query
        matching_users = [
            user for user in all_users 
            if query.lower() in user['name'].lower()
        ]
        
        if not matching_users:
            await interaction.followup.send(
                f"❌ No users found matching '{query}'",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🔍 Search Results for '{query}'",
            description=f"Found {len(matching_users)} user(s)",
            color=discord.Color.blue()
        )
        
        for user in matching_users[:10]:  # Limit to 10 results
            value = (
                f"**Department:** {user['department'] or 'N/A'}\n"
                f"**Position:** {user['position'] or 'N/A'}\n"
                f"**Discord ID:** {user['discord_id']}\n"
                f"**Trackabi ID:** {user['trackabi_id'] or 'N/A'}"
            )
            embed.add_field(
                name=f"{user['name']} (ID: {user['user_id']})",
                value=value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


# Confirmation view for account deletion
class UserDeleteConfirmView(discord.ui.View):
    def __init__(self, discord_id: int):
        super().__init__(timeout=60)
        self.discord_id = discord_id
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message(
                "❌ This is not your deletion request!",
                ephemeral=True
            )
            return
        
        success = await UserModel.user_removal(self.discord_id)
        
        if success:
            embed = discord.Embed(
                title="✅ Account Deleted",
                description="Your account and all associated data have been removed.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Failed to delete account!",
                ephemeral=True
            )
        
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message(
                "❌ This is not your deletion request!",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            "✅ Account deletion cancelled.",
            ephemeral=True
        )
        self.stop()


async def setup(bot):
    await bot.add_cog(UserManagement(bot))