import discord
from discord.ext import commands
from discord import app_commands
from models import UserModel
from datetime import datetime
from typing import Optional

# Utility function to check if user is admin or super
async def is_admin_or_super(interaction: discord.Interaction) -> bool:
    """Check if user has admin (role_id 2) or super (role_id 1) privileges"""
    user_data = await UserModel.get_user_by_discord_id(interaction.user.id)
    if not user_data:
        return False
    return user_data['role_id'] in [1, 2]



# ==================== USER REGISTRATION ====================

# User Selection View for Registration
class RegisterUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_user = None
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to register",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_user = select.values[0]
        
        # Show department selection
        view = DepartmentSelectView(self.selected_user)
        
        embed = discord.Embed(
            title="👤 User Registration - Step 2",
            description=f"Registering **{self.selected_user.mention}**\n\n**Select Department:**",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


# Department Selection View (Updated to go to Role selection)
class DepartmentSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.selected_department = None
    
    @discord.ui.select(
        placeholder="Select Department",
        options=[
            discord.SelectOption(label="DEV", value="DEV", emoji="💻"),
            discord.SelectOption(label="R&D", value="R&D", emoji="🔬"),
            discord.SelectOption(label="HR", value="HR", emoji="👥"),
            discord.SelectOption(label="UI/UX", value="UI/UX", emoji="🎨"),
            discord.SelectOption(label="Others", value="Others", emoji="📋"),
        ]
    )
    async def department_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_department = select.values[0]
        
        # Show role selection
        view = RoleSelectView(self.target_user, self.selected_department)
        
        embed = discord.Embed(
            title="👤 User Registration - Step 3",
            description=f"Registering **{self.target_user.mention}**\n\n**Select User Role:**",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


# Role Selection View
class RoleSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, department: str):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.department = department
        self.selected_role = None
    
    @discord.ui.select(
        placeholder="Select User Role",
        options=[
            discord.SelectOption(label="ADMIN", value="2", emoji="👑", description="Administrator privileges"),
            discord.SelectOption(label="NORMAL", value="3", emoji="👤", description="Regular user"),
        ]
    )
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_role = int(select.values[0])
        
        # Show first modal
        modal = UserRegistrationModal1(self.target_user, self.department, self.selected_role)
        await interaction.response.send_modal(modal)
        self.stop()


# First Registration Modal (Updated to accept role_id)
class UserRegistrationModal1(discord.ui.Modal, title='User Registration - Part 1/2'):
    name = discord.ui.TextInput(
        label='Full Name',
        placeholder='Enter full name',
        required=True,
        max_length=255
    )
    
    position = discord.ui.TextInput(
        label='Position',
        placeholder='e.g., Software Engineer, Manager',
        required=True,
        max_length=100
    )
    
    trackabi_id = discord.ui.TextInput(
        label='Trackabi ID',
        placeholder='Enter Trackabi ID',
        required=True,
        max_length=100
    )
    
    desklog_id = discord.ui.TextInput(
        label='Desklog ID',
        placeholder='Enter Desklog ID',
        required=True,
        max_length=100
    )
    
    pending_leaves = discord.ui.TextInput(
        label='Pending Leaves',
        placeholder='Number of pending leaves',
        required=True,
        default='10',
        max_length=3
    )
    
    def __init__(self, target_user: discord.User, department: str, role_id: int):
        super().__init__()
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate pending_leaves is a number
        try:
            pending_leaves_int = int(self.pending_leaves.value)
            if pending_leaves_int < 0:
                await interaction.response.send_message(
                    "❌ Pending leaves must be a positive number!",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Pending leaves must be a valid number!",
                ephemeral=True
            )
            return
        
        # Create a view with a button to continue
        view = ContinueToModal2View(
            target_user=self.target_user,
            department=self.department,
            role_id=self.role_id,
            name=self.name.value,
            position=self.position.value,
            trackabi_id=self.trackabi_id.value,
            desklog_id=self.desklog_id.value,
            pending_leaves=pending_leaves_int
        )
        
        embed = discord.Embed(
            title="✅ Part 1 Complete!",
            description=f"**Step 4/5:** Click the button below to continue with contract date",
            color=discord.Color.green()
        )
        
        # Respond with a message containing the button
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# Intermediate view with button to show second modal (Updated with role_id)
class ContinueToModal2View(discord.ui.View):
    def __init__(self, target_user: discord.User, department: str, role_id: int, name: str,
                 position: str, trackabi_id: str, desklog_id: str, pending_leaves: int):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
        self.name = name
        self.position = position
        self.trackabi_id = trackabi_id
        self.desklog_id = desklog_id
        self.pending_leaves = pending_leaves
    
    @discord.ui.button(label="Continue to Step 5", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Now show the second modal
        modal2 = UserRegistrationModal2(
            target_user=self.target_user,
            department=self.department,
            role_id=self.role_id,
            name=self.name,
            position=self.position,
            trackabi_id=self.trackabi_id,
            desklog_id=self.desklog_id,
            pending_leaves=self.pending_leaves
        )
        await interaction.response.send_modal(modal2)
        self.stop()


# Second Registration Modal (Updated with role_id)
class UserRegistrationModal2(discord.ui.Modal, title='User Registration - Part 2/2'):
    contract_date = discord.ui.TextInput(
        label='Contract Starting Date',
        placeholder='YYYY-MM-DD (e.g., 2024-01-15)',
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    def __init__(self, target_user: discord.User, department: str, role_id: int, name: str, 
                 position: str, trackabi_id: str, desklog_id: str, pending_leaves: int):
        super().__init__()
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
        self.name = name
        self.position = position
        self.trackabi_id = trackabi_id
        self.desklog_id = desklog_id
        self.pending_leaves = pending_leaves
        
        # Set today's date as default
        self.contract_date.default = datetime.now().strftime('%Y-%m-%d')
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate and parse date
        try:
            contract_started_at = datetime.strptime(self.contract_date.value, '%Y-%m-%d')
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD (e.g., 2024-01-15)",
                ephemeral=True
            )
            return
        
        # Register user
        try:
            user_id = await UserModel.user_registration(
                discord_id=self.target_user.id,
                name=self.name,
                department=self.department,
                position=self.position,
                trackabi_id=self.trackabi_id,
                desklog_id=self.desklog_id,
                role_id=self.role_id,
                pending_leaves=self.pending_leaves,
                contract_started_at=contract_started_at
            )
            
            # Get role name for display
            if self.role_id == 1:
                role_name = "SUPER"
            elif self.role_id == 2:
                role_name = "ADMIN"
            else:  # role_id == 3
                role_name = "NORMAL"
            
            # Create detailed summary embed
            embed = discord.Embed(
                title="✅ User Registration Successful!",
                description=f"**{self.name}** has been successfully registered in the system.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="🆔 User ID", value=f"`{user_id}`", inline=True)
            embed.add_field(name="👤 Discord User", value=self.target_user.mention, inline=True)
            embed.add_field(name="📛 Full Name", value=self.name, inline=True)
            
            embed.add_field(name="🏢 Department", value=self.department, inline=True)
            embed.add_field(name="💼 Position", value=self.position, inline=True)
            embed.add_field(name="👑 Role", value=role_name, inline=True)
            
            embed.add_field(name="🗓️ Contract Start", value=contract_started_at.strftime('%Y-%m-%d'), inline=True)
            embed.add_field(name="🏖️ Pending Leaves", value=f"{self.pending_leaves} days", inline=True)
            embed.add_field(name="📊 Trackabi ID", value=f"`{self.trackabi_id}`", inline=True)
            
            embed.add_field(name="🖥️ Desklog ID", value=f"`{self.desklog_id}`", inline=True)
            
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            embed.set_footer(text=f"Registered by {interaction.user.name}")
            
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


# ==================== USER UPDATE ====================

# User Selection View for Update
class UpdateUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_user = None
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to update",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_user = select.values[0]
        
        # Check if user is registered
        user_data = await UserModel.get_user_by_discord_id(self.selected_user.id)
        
        if not user_data:
            await interaction.response.send_message(
                f"❌ {self.selected_user.mention} is not registered in the system!",
                ephemeral=True
            )
            return
        
        # Show department selection with current department
        view = UpdateDepartmentSelectView(self.selected_user, dict(user_data))
        
        embed = discord.Embed(
            title="✏️ User Update - Step 2",
            description=f"Updating information for **{self.selected_user.mention}**\n\n**Select Department:**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=self.selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


# Department Selection for Update (Updated to go to Role selection)
class UpdateDepartmentSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, current_data: dict):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.current_data = current_data
    
    @discord.ui.select(
        placeholder="Select Department",
        options=[
            discord.SelectOption(label="DEV", value="DEV", emoji="💻"),
            discord.SelectOption(label="R&D", value="R&D", emoji="🔬"),
            discord.SelectOption(label="HR", value="HR", emoji="👥"),
            discord.SelectOption(label="UI/UX", value="UI/UX", emoji="🎨"),
            discord.SelectOption(label="Others", value="Others", emoji="📋"),
        ]
    )
    async def department_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_department = select.values[0]
        
        # Show role selection
        view = UpdateRoleSelectView(self.target_user, self.current_data, selected_department)
        
        embed = discord.Embed(
            title="✏️ User Update - Step 3",
            description=f"Updating **{self.target_user.mention}**\n\n**Select User Role:**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


# NEW: Role Selection View for Update
class UpdateRoleSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, current_data: dict, department: str):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.current_data = current_data
        self.department = department
    
    @discord.ui.select(
        placeholder="Select User Role",
        options=[
            discord.SelectOption(label="ADMIN", value="2", emoji="👑", description="Administrator privileges"),
            discord.SelectOption(label="NORMAL", value="3", emoji="👤", description="Regular user"),
        ]
    )
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_role = int(select.values[0])
        
        # Show update modal
        modal = UserUpdateModal1(self.target_user, self.current_data, self.department, selected_role)
        await interaction.response.send_modal(modal)
        self.stop()


# Update Modal 1 (Updated to accept role_id)
class UserUpdateModal1(discord.ui.Modal, title='Update User - Part 1/2'):
    name = discord.ui.TextInput(
        label='Full Name',
        required=True,
        max_length=255
    )
    
    position = discord.ui.TextInput(
        label='Position',
        required=True,
        max_length=100
    )
    
    trackabi_id = discord.ui.TextInput(
        label='Trackabi ID',
        required=True,
        max_length=100
    )
    
    desklog_id = discord.ui.TextInput(
        label='Desklog ID',
        required=True,
        max_length=100
    )
    
    pending_leaves = discord.ui.TextInput(
        label='Pending Leaves',
        required=True,
        max_length=3
    )
    
    def __init__(self, target_user: discord.User, current_data: dict, department: str, role_id: int):
        super().__init__()
        self.target_user = target_user
        self.current_data = current_data
        self.department = department
        self.role_id = role_id
        
        # Pre-fill with current data
        self.name.default = current_data.get('name', '')
        self.position.default = current_data.get('position', '') or ''
        self.trackabi_id.default = current_data.get('trackabi_id', '') or ''
        self.desklog_id.default = current_data.get('desklog_id', '') or ''
        self.pending_leaves.default = str(current_data.get('pending_leaves', 10))
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate pending_leaves
        try:
            pending_leaves_int = int(self.pending_leaves.value)
            if pending_leaves_int < 0:
                await interaction.response.send_message(
                    "❌ Pending leaves must be a positive number!",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Pending leaves must be a valid number!",
                ephemeral=True
            )
            return
        
        # Create button view to continue
        view = ContinueToUpdateModal2View(
            target_user=self.target_user,
            current_data=self.current_data,
            department=self.department,
            role_id=self.role_id,
            name=self.name.value,
            position=self.position.value,
            trackabi_id=self.trackabi_id.value,
            desklog_id=self.desklog_id.value,
            pending_leaves=pending_leaves_int
        )
        
        embed = discord.Embed(
            title="✅ Part 1 Complete!",
            description=f"**Step 4/5:** Click the button below to continue with contract date",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# Continue button for update (Updated with role_id)
class ContinueToUpdateModal2View(discord.ui.View):
    def __init__(self, target_user: discord.User, current_data: dict, department: str, role_id: int,
                 name: str, position: str, trackabi_id: str, desklog_id: str, pending_leaves: int):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.current_data = current_data
        self.department = department
        self.role_id = role_id
        self.name = name
        self.position = position
        self.trackabi_id = trackabi_id
        self.desklog_id = desklog_id
        self.pending_leaves = pending_leaves
    
    @discord.ui.button(label="Continue to Step 5", style=discord.ButtonStyle.primary, emoji="➡️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal2 = UserUpdateModal2(
            target_user=self.target_user,
            current_data=self.current_data,
            department=self.department,
            role_id=self.role_id,
            name=self.name,
            position=self.position,
            trackabi_id=self.trackabi_id,
            desklog_id=self.desklog_id,
            pending_leaves=self.pending_leaves
        )
        await interaction.response.send_modal(modal2)
        self.stop()


# Update Modal 2 (Updated with role_id)
class UserUpdateModal2(discord.ui.Modal, title='Update User - Part 2/2'):
    contract_date = discord.ui.TextInput(
        label='Contract Starting Date',
        placeholder='YYYY-MM-DD (e.g., 2024-01-15)',
        required=True,
        max_length=10
    )
    
    def __init__(self, target_user: discord.User, current_data: dict, department: str, role_id: int,
                 name: str, position: str, trackabi_id: str, desklog_id: str, pending_leaves: int):
        super().__init__()
        self.target_user = target_user
        self.current_data = current_data
        self.department = department
        self.role_id = role_id
        self.name = name
        self.position = position
        self.trackabi_id = trackabi_id
        self.desklog_id = desklog_id
        self.pending_leaves = pending_leaves
        
        # Pre-fill with current contract date
        if current_data.get('contract_started_at'):
            self.contract_date.default = current_data['contract_started_at'].strftime('%Y-%m-%d')
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate date
        try:
            contract_started_at = datetime.strptime(self.contract_date.value, '%Y-%m-%d')
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use YYYY-MM-DD",
                ephemeral=True
            )
            return
        
        # Update user
        try:
            success = await UserModel.user_info_update(
                discord_id=self.target_user.id,
                name=self.name,
                department=self.department,
                position=self.position,
                trackabi_id=self.trackabi_id,
                desklog_id=self.desklog_id,
                role_id=self.role_id,  # Now updating role_id too
                pending_leaves=self.pending_leaves
            )
            
            if success:
                # Get role name for display
                if self.role_id == 1:
                    role_name = "SUPER"
                elif self.role_id == 2:
                    role_name = "ADMIN"
                else:  # role_id == 3
                    role_name = "NORMAL"
                
                embed = discord.Embed(
                    title="✅ User Updated Successfully!",
                    description=f"Information for **{self.name}** has been updated.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                
                embed.add_field(name="👤 Discord User", value=self.target_user.mention, inline=True)
                embed.add_field(name="📛 Full Name", value=self.name, inline=True)
                embed.add_field(name="🏢 Department", value=self.department, inline=True)
                
                embed.add_field(name="💼 Position", value=self.position, inline=True)
                embed.add_field(name="👑 Role", value=role_name, inline=True)
                embed.add_field(name="🗓️ Contract Start", value=contract_started_at.strftime('%Y-%m-%d'), inline=True)
                
                embed.add_field(name="🏖️ Pending Leaves", value=f"{self.pending_leaves} days", inline=True)
                embed.add_field(name="📊 Trackabi ID", value=f"`{self.trackabi_id}`", inline=True)
                embed.add_field(name="🖥️ Desklog ID", value=f"`{self.desklog_id}`", inline=True)
                
                embed.set_thumbnail(url=self.target_user.display_avatar.url)
                embed.set_footer(text=f"Updated by {interaction.user.name}")
                
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


# ==================== USER DELETE ====================

# User Selection View for Delete
class DeleteUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to delete",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        
        user = await UserModel.get_user_by_discord_id(selected_user.id)
        
        if not user:
            await interaction.response.send_message(
                f"❌ {selected_user.mention} is not registered in the system!",
                ephemeral=True
            )
            return
        
        # Show confirmation view
        view = UserDeleteConfirmView(selected_user, user['name'])
        
        embed = discord.Embed(
            title="⚠️ User Account Deletion",
            description=f"You are about to delete the account for **{user['name']}** ({selected_user.mention})\n\n"
                       "**This action will permanently remove:**\n"
                       "• All user profile data\n"
                       "• Associated attendance records\n"
                       "• Leave history\n"
                       "• All related information\n\n"
                       "⚠️ **This cannot be undone!**",
            color=discord.Color.red()
        )
        
        embed.add_field(name="User ID", value=f"`{user['user_id']}`", inline=True)
        embed.add_field(name="Name", value=user['name'], inline=True)
        embed.add_field(name="Department", value=user['department'] or "N/A", inline=True)
        
        embed.set_thumbnail(url=selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


# Delete Confirmation Modal
class DeleteConfirmationModal(discord.ui.Modal, title='Confirm Account Deletion'):
    confirmation = discord.ui.TextInput(
        label='Type CONFIRM_DELETE to confirm',
        placeholder='Type CONFIRM_DELETE (in capital letters)',
        required=True,
        max_length=15,
        style=discord.TextStyle.short
    )
    
    def __init__(self, selected_user: discord.User, user_name: str):
        super().__init__()
        self.selected_user = selected_user
        self.user_name = user_name
    
    async def on_submit(self, interaction: discord.Interaction):
        if self.confirmation.value != "CONFIRM_DELETE":
            await interaction.response.send_message(
                "❌ Confirmation failed! You must type exactly **CONFIRM_DELETE** (in capitals) to confirm deletion.",
                ephemeral=True
            )
            return
        
        # Delete user
        success = await UserModel.user_removal(self.selected_user.id)
        
        if success:
            embed = discord.Embed(
                title="✅ Account Deleted Successfully",
                description=f"The account for **{self.user_name}** ({self.selected_user.mention}) has been permanently removed from the system.",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"Deleted by {interaction.user.name}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Failed to delete account! The user may have already been removed.",
                ephemeral=True
            )


# Confirmation View for Delete
class UserDeleteConfirmView(discord.ui.View):
    def __init__(self, selected_user: discord.User, user_name: str):
        super().__init__(timeout=60)
        self.selected_user = selected_user
        self.user_name = user_name
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show modal for typing DELETE
        modal = DeleteConfirmationModal(self.selected_user, self.user_name)
        await interaction.response.send_modal(modal)
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ Account deletion cancelled. No changes were made.",
            ephemeral=True
        )
        self.stop()

# ==================== USER INFO VIEW ====================

class InfoUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to view information",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        
        user_data = await UserModel.get_user_by_discord_id(selected_user.id)
        
        if not user_data:
            await interaction.response.send_message(
                f"❌ {selected_user.mention} is not registered in the system!",
                ephemeral=True
            )
            return
        
        # Map role_id to role name
        role_map = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}
        role_name = role_map.get(user_data['role_id'], "UNKNOWN")
        
        # Create detailed info embed
        embed = discord.Embed(
            title=f"📋 User Profile: {user_data['name']}",
            description=f"Complete profile information for **{selected_user.mention}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Basic Information
        embed.add_field(name="🆔 User ID", value=f"`{user_data['user_id']}`", inline=True)
        embed.add_field(name="👤 Discord ID", value=f"`{selected_user.id}`", inline=True)
        embed.add_field(name="📛 Full Name", value=user_data['name'], inline=True)
        
        # Employment Information
        embed.add_field(name="🏢 Department", value=user_data['department'] or "N/A", inline=True)
        embed.add_field(name="💼 Position", value=user_data['position'] or "N/A", inline=True)
        embed.add_field(name="👑 Role", value=role_name, inline=True)
        
        # Contract Information
        if user_data['contract_started_at']:
            contract_date = user_data['contract_started_at'].strftime('%Y-%m-%d')
        else:
            contract_date = "N/A"
        
        embed.add_field(name="🗓️ Contract Started", value=contract_date, inline=True)
        embed.add_field(name="🏖️ Pending Leaves", value=f"{user_data['pending_leaves']} days", inline=True)
        
        # Tool IDs
        embed.add_field(name="📊 Trackabi ID", value=f"`{user_data['trackabi_id'] or 'N/A'}`", inline=True)
        embed.add_field(name="🖥️ Desklog ID", value=f"`{user_data['desklog_id'] or 'N/A'}`", inline=True)
        
        # Metadata
        if user_data['created_at']:
            created_at = user_data['created_at'].strftime('%Y-%m-%d %H:%M')
        else:
            created_at = "N/A"
        
        if user_data['updated_at']:
            updated_at = user_data['updated_at'].strftime('%Y-%m-%d %H:%M')
        else:
            updated_at = "N/A"
        
        embed.add_field(name="📅 Registered On", value=created_at, inline=False)
        embed.add_field(name="✏️ Last Updated", value=updated_at, inline=False)
        
        # Set thumbnail and footer
        embed.set_thumbnail(url=selected_user.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        self.stop()


# ==================== COG CLASS ====================

class UserManagement(commands.Cog):
    """User management and onboarding commands - Admin only"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="user_register",
        description="Register a new user in the system (Admin/Super only)"
    )
    async def user_register(self, interaction: discord.Interaction):
        """Register a new user - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command! Only Admin and Super users can register users.",
                ephemeral=True
            )
            return
        
        # Show user selection view
        view = RegisterUserSelectView()
        
        embed = discord.Embed(
            title="👤 User Registration - Step 1",
            description="**Select a Discord user to register in the system**",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="user_update",
        description="Update user information (Admin/Super only)"
    )
    async def user_update(self, interaction: discord.Interaction):
        """Update user information - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
            return
        
        # Show user selection view
        view = UpdateUserSelectView()
        
        embed = discord.Embed(
            title="✏️ User Update - Step 1",
            description="**Select a Discord user to update their information**",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="user_info",
        description="View user information (Admin/Super only)"
    )
    async def user_info(self, interaction: discord.Interaction):
        """Display user information - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
            return
        
        # Show user selection view
        view = InfoUserSelectView()
        
        embed = discord.Embed(
            title="👤 User Information",
            description="**Select a Discord user to view their profile information**",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="user_delete",
        description="Delete a user from the system (Admin/Super only)"
    )
    async def user_delete(self, interaction: discord.Interaction):
        """Delete user account - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
            return
        
        # Show user selection view
        view = DeleteUserSelectView()
        
        embed = discord.Embed(
            title="🗑️ User Account Deletion",
            description="**Select a Discord user to delete their account from the system**",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(
        name="user_list",
        description="List all registered users (Admin/Super only)"
    )
    async def user_list(self, interaction: discord.Interaction):
        """List all users in the system - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
            return
        
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
            description=f"Total: **{len(users)}** users in the system",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for user in users[:25]:  # Discord has 25 fields limit
            discord_user = self.bot.get_user(int(user['discord_id']))
            user_mention = discord_user.mention if discord_user else f"ID: {user['discord_id']}"
            
            value = (
                f"**Name:** {user['name']}\n"
                f"**User:** {user_mention}\n"
                f"**Department:** {user['department'] or 'N/A'}\n"
                f"**Position:** {user['position'] or 'N/A'}\n"
                f"**Leaves:** {user['pending_leaves']} days"
            )
            embed.add_field(
                name=f"ID: {user['user_id']}",
                value=value,
                inline=True
            )
        
        if len(users) > 25:
            embed.set_footer(text=f"Showing 25 of {len(users)} users")
        else:
            embed.set_footer(text=f"Displayed by {interaction.user.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="user_search",
        description="Search for a user by name (Admin/Super only)"
    )
    @app_commands.describe(query="User name to search for")
    async def user_search(self, interaction: discord.Interaction, query: str):
        """Search for users by name - Admin only"""
        
        # Check if command user is admin or super
        if not await is_admin_or_super(interaction):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        all_users = await UserModel.get_all_users()
        
        # Filter users by query
        matching_users = [
            user for user in all_users 
            if query.lower() in user['name'].lower()
        ]
        
        if not matching_users:
            await interaction.followup.send(
                f"❌ No users found matching '**{query}**'",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"🔍 Search Results",
            description=f"Found **{len(matching_users)}** user(s) matching '**{query}**'",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        for user in matching_users[:10]:  # Limit to 10 results
            discord_user = self.bot.get_user(int(user['discord_id']))
            user_mention = discord_user.mention if discord_user else f"ID: {user['discord_id']}"
            
            value = (
                f"**User:** {user_mention}\n"
                f"**Department:** {user['department'] or 'N/A'}\n"
                f"**Position:** {user['position'] or 'N/A'}\n"
                f"**Trackabi:** `{user['trackabi_id'] or 'N/A'}`\n"
                f"**Desklog:** `{user['desklog_id'] or 'N/A'}`\n"
                f"**Leaves:** {user['pending_leaves']} days"
            )
            embed.add_field(
                name=f"{user['name']} (ID: {user['user_id']})",
                value=value,
                inline=False
            )
        
        if len(matching_users) > 10:
            embed.set_footer(text=f"Showing 10 of {len(matching_users)} results")
        else:
            embed.set_footer(text=f"Search by {interaction.user.name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(UserManagement(bot))