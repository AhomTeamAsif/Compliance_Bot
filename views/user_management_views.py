import discord
from discord import ui
from datetime import datetime
from models.user_model import UserModel
from utils.database import db
from utils.verification_helper import check_user_permission, get_all_permissions, get_user_permissions, check_role_hierarchy


# ==================== USER REGISTRATION ====================

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
        
        # Check if user already exists (not deleted)
        exists = await UserModel.user_exists(self.selected_user.id, include_deleted=False)
        if exists:
            await interaction.response.send_message(
                f"❌ **{self.selected_user.mention}** is already registered in the system!",
                ephemeral=True
            )
            self.stop()
            return
        
        # Show department selection
        view = DepartmentSelectView(self.selected_user)
        
        embed = discord.Embed(
            title="👤 User Registration - Step 2/6",
            description=f"Registering **{self.selected_user.mention}**\n\n**Select Department:**",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class DepartmentSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=180)
        self.target_user = target_user
    
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
        view = RoleSelectView(self.target_user, select.values[0])
        
        embed = discord.Embed(
            title="👤 User Registration - Step 3/6",
            description=f"Registering **{self.target_user.mention}**\n\n**Select User Role:**",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class RoleSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, department: str):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.department = department
    
    @discord.ui.select(
        placeholder="Select User Role",
        options=[
            discord.SelectOption(label="ADMIN", value="2", emoji="👑", description="Administrator privileges"),
            discord.SelectOption(label="NORMAL", value="3", emoji="👤", description="Regular user"),
        ]
    )
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        modal = UserRegistrationModal1(self.target_user, self.department, int(select.values[0]))
        await interaction.response.send_modal(modal)
        self.stop()


class UserRegistrationModal1(discord.ui.Modal, title='User Registration - Part 1/3'):
    name = discord.ui.TextInput(label='Full Name', placeholder='Enter full name', required=True, max_length=255)
    position = discord.ui.TextInput(label='Position', placeholder='e.g., Software Engineer, Manager', required=True, max_length=100)
    trackabi_id = discord.ui.TextInput(label='Trackabi ID', placeholder='Enter Trackabi ID', required=True, max_length=100)
    desklog_id = discord.ui.TextInput(label='Desklog ID', placeholder='Enter Desklog ID', required=True, max_length=100)
    pending_leaves = discord.ui.TextInput(label='Pending Leaves', placeholder='Number of pending leaves', required=True, default='10', max_length=3)
    
    def __init__(self, target_user: discord.User, department: str, role_id: int):
        super().__init__()
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            pending_leaves_int = int(self.pending_leaves.value)
            if pending_leaves_int < 0:
                await interaction.response.send_message("❌ Pending leaves must be a positive number!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Pending leaves must be a valid number!", ephemeral=True)
            return
        
        view = ContinueToModal2View(
            target_user=self.target_user, department=self.department, role_id=self.role_id,
            name=self.name.value, position=self.position.value, trackabi_id=self.trackabi_id.value,
            desklog_id=self.desklog_id.value, pending_leaves=pending_leaves_int
        )
        
        embed = discord.Embed(
            title="✅ Part 1 Complete!",
            description=f"**Step 4/6:** Click the button below to continue with contract date",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


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
        modal2 = UserRegistrationModal2(
            target_user=self.target_user, department=self.department, role_id=self.role_id,
            name=self.name, position=self.position, trackabi_id=self.trackabi_id,
            desklog_id=self.desklog_id, pending_leaves=self.pending_leaves
        )
        await interaction.response.send_modal(modal2)
        self.stop()


class UserRegistrationModal2(discord.ui.Modal, title='User Registration - Part 2/3'):
    contract_date = discord.ui.TextInput(
        label='Contract Starting Date', placeholder='YYYY-MM-DD (e.g., 2024-01-15)',
        required=True, max_length=10, style=discord.TextStyle.short
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
        self.contract_date.default = datetime.now().strftime('%Y-%m-%d')
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            contract_started_at = datetime.strptime(self.contract_date.value, '%Y-%m-%d')
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format! Please use YYYY-MM-DD", ephemeral=True)
            return
        
        # Get permissions and show selection
        permissions = await get_all_permissions()
        view = PermissionSelectView(
            target_user=self.target_user, department=self.department, role_id=self.role_id,
            name=self.name, position=self.position, trackabi_id=self.trackabi_id,
            desklog_id=self.desklog_id, pending_leaves=self.pending_leaves,
            contract_started_at=contract_started_at, permissions=permissions
        )
        
        embed = discord.Embed(
            title="👤 User Registration - Step 6/6",
            description=f"**Select Permissions** for {self.target_user.mention}\n\nChoose permissions to grant:",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PermissionSelectView(discord.ui.View):
    def __init__(self, target_user, department, role_id, name, position, trackabi_id, 
                 desklog_id, pending_leaves, contract_started_at, permissions, is_update=False, existing_perms=None):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
        self.name = name
        self.position = position
        self.trackabi_id = trackabi_id
        self.desklog_id = desklog_id
        self.pending_leaves = pending_leaves
        self.contract_started_at = contract_started_at
        self.is_update = is_update
        
        # Create permission options
        options = [
            discord.SelectOption(
                label=p['permission_name'],
                value=str(p['permission_id']),
                description=p['description'][:100] if p['description'] else None,
                default=(str(p['permission_id']) in (existing_perms or []))
            )
            for p in permissions
        ]
        
        self.permission_select = discord.ui.Select(
            placeholder="Select permissions (optional)",
            options=options,
            min_values=0,
            max_values=len(options)
        )
        self.permission_select.callback = self.permission_callback
        self.add_item(self.permission_select)
    
    async def permission_callback(self, interaction: discord.Interaction):
        selected_permission_ids = [int(val) for val in self.permission_select.values]

        # Get the granter's user_id from discord_id
        granter_user = await UserModel.get_user_by_discord_id(interaction.user.id)
        granter_user_id = granter_user['user_id'] if granter_user else None
    
        
        if self.is_update:
            # Update user
            try:
                await UserModel.user_info_update(
                    discord_id=self.target_user.id,
                    name=self.name,
                    department=self.department,
                    position=self.position,
                    trackabi_id=self.trackabi_id,
                    desklog_id=self.desklog_id,
                    role_id=self.role_id,
                    pending_leaves=self.pending_leaves,
                    permission_ids=selected_permission_ids,
                    granted_by=granter_user_id
                )
                
                embed = discord.Embed(
                    title="✅ User Updated Successfully!",
                    description=f"**{self.name}** has been updated in the system.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="👤 Discord User", value=self.target_user.mention, inline=True)
                embed.add_field(name="🔑 Permissions", value=f"{len(selected_permission_ids)} granted", inline=True)
                embed.set_thumbnail(url=self.target_user.display_avatar.url)
                embed.set_footer(text=f"Updated by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Update failed: {str(e)}", ephemeral=True)
        else:
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
                    contract_started_at=self.contract_started_at,
                    permission_ids=selected_permission_ids,
                    granted_by=granter_user_id,
                    registered_by=granter_user_id 
                )
                
                role_name = {1: "SUPER", 2: "ADMIN", 3: "NORMAL"}.get(self.role_id, "NORMAL")
                
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
                embed.add_field(name="🗓️ Contract Start", value=self.contract_started_at.strftime('%Y-%m-%d'), inline=True)
                embed.add_field(name="🏖️ Pending Leaves", value=f"{self.pending_leaves} days", inline=True)
                embed.add_field(name="🔑 Permissions", value=f"{len(selected_permission_ids)} granted", inline=True)
                embed.add_field(name="📊 Trackabi ID", value=f"`{self.trackabi_id}`", inline=True)
                embed.add_field(name="🖥️ Desklog ID", value=f"`{self.desklog_id}`", inline=True)
                
                embed.set_thumbnail(url=self.target_user.display_avatar.url)
                embed.set_footer(text=f"Registered by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except ValueError as e:
                await interaction.response.send_message(f"⚠️ {str(e)}", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"❌ Registration failed: {str(e)}", ephemeral=True)
        
        self.stop()


# ==================== USER UPDATE ====================

class UpdateUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to update",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        
        # Check if user exists (not deleted)
        user = await UserModel.get_user_by_discord_id(selected_user.id, include_deleted=False)
        if not user:
            await interaction.response.send_message(
                f"❌ **{selected_user.mention}** is not registered in the system!",
                ephemeral=True
            )
            self.stop()
            return

        # Check role hierarchy
        can_modify, message = await check_role_hierarchy(interaction.user.id, selected_user.id)
        if not can_modify:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            self.stop()
            return
        
        # Show department selection
        view = UpdateDepartmentSelectView(selected_user, user)
        
        embed = discord.Embed(
            title="✏️ User Update - Step 2/5",
            description=f"Updating **{selected_user.mention}**\n\n**Select Department:**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class UpdateDepartmentSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, user_data):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.user_data = user_data
    
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
        view = UpdateRoleSelectView(self.target_user, select.values[0], self.user_data)
        
        embed = discord.Embed(
            title="✏️ User Update - Step 3/5",
            description=f"Updating **{self.target_user.mention}**\n\n**Select User Role:**",
            color=discord.Color.orange()
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class UpdateRoleSelectView(discord.ui.View):
    def __init__(self, target_user: discord.User, department: str, user_data):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.department = department
        self.user_data = user_data
    
    @discord.ui.select(
        placeholder="Select User Role",
        options=[
            discord.SelectOption(label="ADMIN", value="2", emoji="👑", description="Administrator privileges"),
            discord.SelectOption(label="NORMAL", value="3", emoji="👤", description="Regular user"),
        ]
    )
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        modal = UserUpdateModal(self.target_user, self.department, int(select.values[0]), self.user_data)
        await interaction.response.send_modal(modal)
        self.stop()


class UserUpdateModal(discord.ui.Modal, title='User Update - Part 1/2'):
    name = discord.ui.TextInput(label='Full Name', placeholder='Enter full name', required=True, max_length=255)
    position = discord.ui.TextInput(label='Position', placeholder='e.g., Software Engineer, Manager', required=True, max_length=100)
    trackabi_id = discord.ui.TextInput(label='Trackabi ID', placeholder='Enter Trackabi ID', required=True, max_length=100)
    desklog_id = discord.ui.TextInput(label='Desklog ID', placeholder='Enter Desklog ID', required=True, max_length=100)
    pending_leaves = discord.ui.TextInput(label='Pending Leaves', placeholder='Number of pending leaves', required=True, max_length=3)
    
    def __init__(self, target_user: discord.User, department: str, role_id: int, user_data):
        super().__init__()
        self.target_user = target_user
        self.department = department
        self.role_id = role_id
        self.user_data = user_data
        
        # Pre-fill with existing data
        self.name.default = user_data['name']
        self.position.default = user_data['position']
        self.trackabi_id.default = user_data['trackabi_id']
        self.desklog_id.default = user_data['desklog_id']
        self.pending_leaves.default = str(user_data['pending_leaves'])
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            pending_leaves_int = int(self.pending_leaves.value)
            if pending_leaves_int < 0:
                await interaction.response.send_message("❌ Pending leaves must be a positive number!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Pending leaves must be a valid number!", ephemeral=True)
            return
        
        # Get permissions and show selection
        permissions = await get_all_permissions()
        existing_perms = await get_user_permissions(self.user_data['user_id'])
        existing_perms_str = [str(p) for p in existing_perms]
        
        view = PermissionSelectView(
            target_user=self.target_user, department=self.department, role_id=self.role_id,
            name=self.name.value, position=self.position.value, trackabi_id=self.trackabi_id.value,
            desklog_id=self.desklog_id.value, pending_leaves=pending_leaves_int,
            contract_started_at=None, permissions=permissions, is_update=True, existing_perms=existing_perms_str
        )
        
        embed = discord.Embed(
            title="✏️ User Update - Step 5/5",
            description=f"**Select Permissions** for {self.target_user.mention}\n\nUpdate permissions:",
            color=discord.Color.orange()
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== USER DELETE ====================

class DeleteUserSelectView(discord.ui.View):
    def __init__(self, deleter_user_id: int):
        super().__init__(timeout=180)
        self.deleter_user_id = deleter_user_id
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to delete",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        
        # Check if user exists (not deleted)
        user = await UserModel.get_user_by_discord_id(selected_user.id, include_deleted=False)
        if not user:
            await interaction.response.send_message(
                f"❌ **{selected_user.mention}** is not registered in the system!",
                ephemeral=True
            )
            self.stop()
            return
        
        # Check role hierarchy
        can_modify, message = await check_role_hierarchy(interaction.user.id, selected_user.id)
        if not can_modify:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            self.stop()
            return
        
        # Show confirmation
        view = DeleteConfirmView(selected_user, self.deleter_user_id)
        
        embed = discord.Embed(
            title="⚠️ User Deletion - Confirmation",
            description=f"Are you sure you want to delete **{selected_user.mention}**?\n\n**This action will delete the user from the system.**",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class DeleteConfirmView(discord.ui.View):
    def __init__(self, target_user: discord.User, deleter_user_id: int):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.deleter_user_id = deleter_user_id
    
    @discord.ui.button(label="Confirm Delete", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DeleteReasonModal(self.target_user, self.deleter_user_id)
        await interaction.response.send_modal(modal)
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Deletion cancelled.", ephemeral=True)
        self.stop()


class DeleteReasonModal(discord.ui.Modal, title='User Deletion - Reason'):
    reason = discord.ui.TextInput(
        label='Reason for Deletion',
        placeholder='Enter the reason for deleting this user...',
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, target_user: discord.User, deleter_user_id: int):
        super().__init__()
        self.target_user = target_user
        self.deleter_user_id = deleter_user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        view = DeleteQuestionsView(self.target_user, self.deleter_user_id, self.reason.value)
        
        embed = discord.Embed(
            title="⚠️ User Deletion - Verification (Step 3/5)",
            description=f"Deleting **{self.target_user.mention}**\n\n**Please answer the following questions by clicking the buttons:**",
            color=discord.Color.red()
        )
        embed.add_field(name="ℹ️ Instructions", value="Click Yes or No for each question. The Continue button will activate once all questions are answered.", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class DeleteQuestionsView(discord.ui.View):
    def __init__(self, target_user: discord.User, deleter_user_id: int, reason: str):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.deleter_user_id = deleter_user_id
        self.reason = reason
        
        # Track answers
        self.seniors_informed = None
        self.admins_informed = None
        self.is_with_us = None
        
        # Add buttons
        self.add_item(QuestionButton("Seniors Informed: Yes", "seniors", True, row=0))
        self.add_item(QuestionButton("Seniors Informed: No", "seniors", False, row=0))
        
        self.add_item(QuestionButton("Admins Informed: Yes", "admins", True, row=1))
        self.add_item(QuestionButton("Admins Informed: No", "admins", False, row=1))
        
        self.add_item(QuestionButton("Is With Us: Yes", "withup", True, row=2))
        self.add_item(QuestionButton("Is With Us: No", "withup", False, row=2))
        
        # Continue button
        self.continue_btn = discord.ui.Button(
            label="Continue to Final Step", 
            style=discord.ButtonStyle.danger, 
            emoji="➡️", 
            disabled=True,
            row=3
        )
        self.continue_btn.callback = self.continue_to_final
        self.add_item(self.continue_btn)
    
    def update_answer(self, question_type: str, value: bool):
        """Update answer and check if all questions are answered"""
        if question_type == "seniors":
            self.seniors_informed = value
        elif question_type == "admins":
            self.admins_informed = value
        elif question_type == "withup":
            self.is_with_us = value
        
        # Enable continue button if all answered
        if (self.seniors_informed is not None and 
            self.admins_informed is not None and 
            self.is_with_us is not None):
            self.continue_btn.disabled = False
        
        # Update button styles to show selection
        for item in self.children[:-1]:  # Exclude continue button
            if isinstance(item, QuestionButton):
                if item.question_type == question_type:
                    if item.answer == value:
                        item.style = discord.ButtonStyle.success if value else discord.ButtonStyle.danger
                    else:
                        item.style = discord.ButtonStyle.secondary
    
    async def continue_to_final(self, interaction: discord.Interaction):
        # Don't send modal directly - show a view instead
        view = DeleteFinalConfirmView(
            self.target_user, self.deleter_user_id, self.reason,
            self.seniors_informed, self.admins_informed, self.is_with_us
        )
        
        embed = discord.Embed(
            title="⚠️ User Deletion - Final Confirmation (Step 5/5)",
            description=f"Deleting **{self.target_user.mention}**\n\n**Click the button below to enter your confirmation:**",
            color=discord.Color.red()
        )
        embed.add_field(
            name="⚠️ IMPORTANT",
            value="You must type exactly:\n`I AM TAKING THE FULL RESPONSIBILITY FOR THIS DELETE`",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class QuestionButton(discord.ui.Button):
    def __init__(self, label: str, question_type: str, answer: bool, row: int):
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            row=row
        )
        self.question_type = question_type
        self.answer = answer
    
    async def callback(self, interaction: discord.Interaction):
        # Update the view's answer
        self.view.update_answer(self.question_type, self.answer)
        
        # Update the message to reflect new button states
        await interaction.response.edit_message(view=self.view)

class DeleteFinalConfirmView(discord.ui.View):
    def __init__(self, target_user: discord.User, deleter_user_id: int, reason: str,
                 seniors_informed: bool, admins_informed: bool, is_with_us: bool):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.deleter_user_id = deleter_user_id
        self.reason = reason
        self.seniors_informed = seniors_informed
        self.admins_informed = admins_informed
        self.is_with_us = is_with_us
    
    @discord.ui.button(label="Enter Confirmation", style=discord.ButtonStyle.danger, emoji="✍️")
    async def enter_confirmation(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = DeleteFinalConfirmationModal(
            self.target_user, self.deleter_user_id, self.reason,
            self.seniors_informed, self.admins_informed, self.is_with_us
        )
        await interaction.response.send_modal(modal)
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Deletion cancelled.", ephemeral=True)
        self.stop()



class DeleteFinalConfirmationModal(discord.ui.Modal, title='Final Confirmation'):
    confirmation = discord.ui.TextInput(
        label='Type the sentence below exactly',
        placeholder='I AM TAKING THE FULL RESPONSIBILITY FOR THIS DELETE',
        required=True,
        style=discord.TextStyle.short,
        max_length=60,
        default='I AM TAKING THE FULL RESPONSIBILITY FOR THIS DELETE'
    )
    
    def __init__(self, target_user: discord.User, deleter_user_id: int, reason: str,
                 seniors_informed: bool, admins_informed: bool, is_with_us: bool):
        super().__init__()
        self.target_user = target_user
        self.deleter_user_id = deleter_user_id
        self.reason = reason
        self.seniors_informed = seniors_informed
        self.admins_informed = admins_informed
        self.is_with_us = is_with_us
    
    async def on_submit(self, interaction: discord.Interaction):
        # Check if the typed confirmation matches exactly
        if self.confirmation.value.strip() != "I AM TAKING THE FULL RESPONSIBILITY FOR THIS DELETE":
            await interaction.response.send_message(
                "❌ Confirmation text does not match! Deletion cancelled.\n\nYou must type exactly:\n`I AM TAKING THE FULL RESPONSIBILITY FOR THIS DELETE`",
                ephemeral=True
            )
            return
        
        # Perform soft delete with additional data
        try:
            success = await UserModel.user_removal(
                discord_id=self.target_user.id,
                deleted_by_user_id=self.deleter_user_id,
                reason=self.reason,
                seniors_informed=self.seniors_informed,
                admins_informed=self.admins_informed,
                is_with_us=self.is_with_us
            )
            
            if success:
                embed = discord.Embed(
                    title="✅ User Deleted Successfully",
                    description=f"**{self.target_user.mention}** has been soft-deleted from the system.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="📝 Reason", value=self.reason, inline=False)
                embed.add_field(name="👔 Seniors Informed", value="✅ Yes" if self.seniors_informed else "❌ No", inline=True)
                embed.add_field(name="👑 Admins Informed", value="✅ Yes" if self.admins_informed else "❌ No", inline=True)
                embed.add_field(name="🤝 Is With Us", value="✅ Yes" if self.is_with_us else "❌ No", inline=True)
                embed.set_thumbnail(url=self.target_user.display_avatar.url)
                embed.set_footer(text=f"Deleted by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ User deletion failed!", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Deletion failed: {str(e)}", ephemeral=True)


# ==================== ACTIVE/ALL USERS MODAL ====================

class ActiveAllUsersModal(discord.ui.Modal, title='View Options'):
    view_option = discord.ui.TextInput(
        label='View active or all users?',
        placeholder='Type: active or all',
        required=True,
        style=discord.TextStyle.short,
        max_length=10
    )
    
    def __init__(self, callback_func, discord_id: int = None):
        super().__init__()
        self.callback_func = callback_func
        self.discord_id = discord_id
    
    async def on_submit(self, interaction: discord.Interaction):
        option = self.view_option.value.strip().lower()
        
        if option not in ['active', 'all']:
            await interaction.response.send_message(
                "❌ Invalid option! Please type 'active' or 'all'",
                ephemeral=True
            )
            return
        
        include_deleted = (option == 'all')
        
        # Call the callback function with the option
        if self.discord_id:
            await self.callback_func(interaction, self.discord_id, include_deleted)
        else:
            await self.callback_func(interaction, include_deleted)


# ==================== USER RESTORE ====================

class RestoreUserSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select a user to restore",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        selected_user = select.values[0]
        
        # Check if user exists and is deleted
        user = await UserModel.get_user_by_discord_id(selected_user.id, include_deleted=True)
        if not user:
            await interaction.response.send_message(
                f"❌ **{selected_user.mention}** is not in the system!",
                ephemeral=True
            )
            self.stop()
            return
        
        if not user['is_deleted']:
            await interaction.response.send_message(
                f"❌ **{selected_user.mention}** is not deleted!",
                ephemeral=True
            )
            self.stop()
            return

        
        # Show confirmation
        view = RestoreConfirmView(selected_user)
        
        embed = discord.Embed(
            title="♻️ User Restoration - Confirmation",
            description=f"Are you sure you want to restore **{selected_user.mention}**?",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=selected_user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class RestoreConfirmView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=180)
        self.target_user = target_user
    
    @discord.ui.button(label="Confirm Restore", style=discord.ButtonStyle.success, emoji="♻️")
    async def confirm_restore(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            success = await UserModel.restore_user(self.target_user.id)
            
            if success:
                embed = discord.Embed(
                    title="✅ User Restored Successfully",
                    description=f"**{self.target_user.mention}** has been restored to the system.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"Restored by {interaction.user.name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message("❌ User restoration failed!", ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Restoration failed: {str(e)}", ephemeral=True)
        
        self.stop()
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("❌ Restoration cancelled.", ephemeral=True)
        self.stop()

# ==================== DELETE LOGS PAGINATION ====================

class DeleteLogsPaginationView(discord.ui.View):
    def __init__(self, total_count: int, per_page: int = 15):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.current_page = 1
        self.per_page = per_page
        self.total_count = total_count
        self.total_pages = max(1, (total_count + per_page - 1) // per_page)  
        
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
        logs = await UserModel.get_delete_logs(limit=self.per_page, offset=offset)
        
        if not logs:
            await interaction.response.edit_message(
                content="📋 No deletion logs found on this page!",
                embed=None,
                view=None
            )
            return
        
        embed = discord.Embed(
            title=f"🗑️ User Deletion Logs",
            description=f"**Total Logs:** {self.total_count} | **Page:** {self.current_page}/{self.total_pages}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        
        for log in logs:
            deleted_user_mention = f"<@{log['deleted_user_discord_id']}>" if log['deleted_user_discord_id'] else "Unknown"
            deleted_by_mention = f"<@{log['deleted_by_discord_id']}>" if log['deleted_by_discord_id'] else "Unknown"
            
            field_value = (
                f"**Deleted User:** {deleted_user_mention} ({log['deleted_user_name'] or 'N/A'})\n"
                f"**Department:** {log['deleted_user_department'] or 'N/A'}\n"
                f"**Deleted By:** {deleted_by_mention} ({log['deleted_by_name'] or 'N/A'})\n"
                f"**Reason:** {log['reason'] or 'No reason provided'}\n"
                f"**Seniors Informed:** {'✅ Yes' if log['seniors_informed'] else '❌ No'} | "
                f"**Admins Informed:** {'✅ Yes' if log['admins_informed'] else '❌ No'} | "
                f"**Is With Us:** {'✅ Yes' if log['is_with_us'] else '❌ No'}\n"
                f"**Deleted At:** <t:{int(log['deleted_at'].timestamp())}:F>"
            )
            
            embed.add_field(
                name=f"Log ID: {log['id']} | User ID: {log['deleted_user_id'] or 'N/A'}",
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
            content="✅ Delete logs viewer closed.",
            embed=None,
            view=None
        )
        self.stop()