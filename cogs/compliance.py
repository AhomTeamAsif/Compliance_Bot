import discord
from discord import app_commands
from discord.ext import commands
from models import UserModel, ComplianceModel

class ComplianceModal(discord.ui.Modal, title='Daily Discipline Compliance'):
    """Modal form for recording compliance"""
    
    def __init__(self, user_id: int, user_name: str):
        super().__init__()
        self.user_id = user_id
        self.user_name = user_name
    
    # Desklog compliance
    desklog = discord.ui.TextInput(
        label='Did employee use Desklog properly?',
        placeholder='Type: yes OR no: reason for non-compliance',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    # Trackabi compliance
    trackabi = discord.ui.TextInput(
        label='Did employee use Trackabi properly?',
        placeholder='Type: yes OR no: reason for non-compliance',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    # Discord compliance
    discord_usage = discord.ui.TextInput(
        label='Did employee use Disord properly?',
        placeholder='Type: yes OR no: reason for non-compliance',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    # Break rules compliance
    break_rules = discord.ui.TextInput(
        label='Did employee follow rules properly?',
        placeholder='Type: yes OR no: reason for non-compliance',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    # Google Drive compliance
    google_drive = discord.ui.TextInput(
        label='Did employee backed up in Google Drive?',
        placeholder='Type: yes OR no: reason for non-compliance',
        style=discord.TextStyle.short,
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Process the compliance form submission"""
        
        # Parse each field (format: "yes" or "no: reason")
        def parse_compliance(text: str):
            text = text.strip().lower()
            if text == 'yes':
                return True, None
            elif text.startswith('no'):
                reason = text[2:].strip().lstrip(':').strip()
                return False, reason if reason else None
            else:
                return None, None
        
        desklog_compliant, desklog_reason = parse_compliance(self.desklog.value)
        trackabi_compliant, trackabi_reason = parse_compliance(self.trackabi.value)
        discord_compliant, discord_reason = parse_compliance(self.discord_usage.value)
        break_compliant, break_reason = parse_compliance(self.break_rules.value)
        drive_compliant, drive_reason = parse_compliance(self.google_drive.value)
        
        # Validate all fields were parsed correctly
        if None in [desklog_compliant, trackabi_compliant, discord_compliant, break_compliant, drive_compliant]:
            await interaction.response.send_message(
                "❌ Invalid format! Use 'yes' or 'no: reason'",
                ephemeral=True
            )
            return
        
        # Save to database
        try:
            compliance_id = await ComplianceModel.create_compliance_record(
                user_id=self.user_id,
                desklog_usage=desklog_compliant,
                desklog_reason=desklog_reason,
                trackabi_usage=trackabi_compliant,
                trackabi_reason=trackabi_reason,
                discord_usage=discord_compliant,
                discord_reason=discord_reason,
                break_usage=break_compliant,
                break_reason=break_reason,
                google_drive_usage=drive_compliant,
                google_drive_reason=drive_reason,
                recorded_by_discord_id=interaction.user.id
            )
            
            # Send success message
            await self.send_compliance_confirmation(
                interaction, 
                compliance_id,
                desklog_compliant, trackabi_compliant, 
                discord_compliant, break_compliant, drive_compliant
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error saving compliance record: {str(e)}",
                ephemeral=True
            )
    
    async def send_compliance_confirmation(self, interaction: discord.Interaction, 
                                          compliance_id: int, desklog: bool, 
                                          trackabi: bool, discord_comp: bool, 
                                          breaks: bool, drive: bool):
        """Send compliance submission confirmation"""
        
        def status_emoji(compliant):
            return "✅" if compliant else "❌"
        
        embed = discord.Embed(
            title="✅ Compliance Record Saved",
            description=f"**Employee:** {self.user_name}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Compliance Summary",
            value=(
                f"{status_emoji(desklog)} **Desklog Usage**\n"
                f"{status_emoji(trackabi)} **Trackabi Usage**\n"
                f"{status_emoji(discord_comp)} **Discord Usage**\n"
                f"{status_emoji(breaks)} **Rules followed**\n"
                f"{status_emoji(drive)} **Google Drive Backup**"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Record ID: {compliance_id}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class UserSelectView(discord.ui.View):
    """View with user dropdown selector"""
    
    def __init__(self, users_list):
        super().__init__(timeout=180)
        self.users_list = users_list
        
        # Create select menu with users
        options = [
            discord.SelectOption(
                label=user['name'],
                value=str(user['user_id']),
                description=f"{user['department']} - {user['position']}"
            )
            for user in users_list
        ]
        
        self.user_select = discord.ui.Select(
            placeholder="Select an employee...",
            options=options,
            min_values=1,
            max_values=1
        )
        self.user_select.callback = self.select_callback
        self.add_item(self.user_select)
    
    async def select_callback(self, interaction: discord.Interaction):
        """Handle user selection and show compliance modal"""
        selected_user_id = int(self.user_select.values[0])
        selected_user = next(u for u in self.users_list if u['user_id'] == selected_user_id)
        
        # Show the compliance modal
        modal = ComplianceModal(
            user_id=selected_user_id,
            user_name=selected_user['name']
        )
        await interaction.response.send_modal(modal)


class Compliance(commands.Cog):
    """Discipline compliance tracking commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="discipline_compliance",
        description="Record daily discipline compliance for an employee"
    )
    async def discipline_compliance(self, interaction: discord.Interaction):
        """Show user selector to record compliance"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get all users
            users = await UserModel.get_all_users()
            
            if not users:
                await interaction.followup.send(
                    "❌ No users found in the database.",
                    ephemeral=True
                )
                return
            
            # Show user selection dropdown
            view = UserSelectView(users)
            await interaction.followup.send(
                "**Select an employee to record compliance:**",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="compliance_history",
        description="View compliance history for a user"
    )
    @app_commands.describe(
        user="Select a user to view history (leave empty for yourself)",
        limit="Number of records to show (default: 5)"
    )
    async def compliance_history(self, interaction: discord.Interaction,user: discord.Member = None, limit: int = 5):
        """View your own compliance history"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # If no user specified, show command executor's history
            target_discord_id = user.id if user else interaction.user.id
        
            # Get user from database
            db_user = await UserModel.get_user_by_discord_id(target_discord_id)
                

            if not db_user:
                target_name = user.display_name if user else "You"
                await interaction.followup.send(
                    f"❌ {target_name} {'is' if user else 'are'} not registered.",
                    ephemeral=True
                )
                return
            
            # Get compliance history
            
            history = await ComplianceModel.get_user_compliance_history(db_user['user_id'], limit)  
            
            if not history:
                await interaction.followup.send(
                    "📋 No compliance records found.",
                    ephemeral=True
                )
                return
            
            # Send history embed
            await self.send_compliance_history(interaction, db_user, history)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    async def send_compliance_history(self, interaction: discord.Interaction, 
                                     user: dict, history: list):
        """Send compliance history embed"""
        
        def status_emoji(compliant):
            return "✅" if compliant else "❌"
        
        embed = discord.Embed(
            title="📊 Compliance History",
            description=f"Last {len(history)} record(s) for {user['name']}",
            color=discord.Color.blue()
        )
        
        for record in history:
            # Format date
            date_str = record['recorded_at'].strftime("%d/%m/%Y %H:%M")
            
            # Build compliance status
            field_value = (
                f"{status_emoji(record['desklog_usage'])} **Desklog**"
                f"{': ' + record['desklog_reason'] if record['desklog_reason'] else ''}\n"
                f"{status_emoji(record['trackabi_usage'])} **Trackabi**"
                f"{': ' + record['trackabi_reason'] if record['trackabi_reason'] else ''}\n"
                f"{status_emoji(record['discord_usage'])} **Discord**"
                f"{': ' + record['discord_reason'] if record['discord_reason'] else ''}\n"
                f"{status_emoji(record['break_usage'])} **Breaks**"
                f"{': ' + record['break_reason'] if record['break_reason'] else ''}\n"
                f"{status_emoji(record['google_drive_usage'])} **Google Drive**"
                f"{': ' + record['google_drive_reason'] if record['google_drive_reason'] else ''}"
            )
            
            embed.add_field(
                name=f"📅 {date_str}",
                value=field_value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Compliance(bot))