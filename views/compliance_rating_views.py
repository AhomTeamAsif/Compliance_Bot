"""Views for compliance rating UI components"""
import discord
from discord import ui
from datetime import datetime
import pytz
from models.compliance_rating_model import ComplianceRatingModel
from models.user_model import UserModel


class EmployeeSelectView(discord.ui.View):
    """Select employee to rate"""
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_user = None
    
    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select an employee to rate",
        min_values=1,
        max_values=1
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_user = select.values[0]
        
        # Check if user exists in system
        employee_data = await UserModel.get_user_by_discord_id(self.selected_user.id)
        if not employee_data:
            await interaction.response.send_message(
                f"❌ **{self.selected_user.mention}** is not registered in the system!",
                ephemeral=True
            )
            self.stop()
            return
        
        # Show rating date selection
        view = RatingDateSelectView(self.selected_user, employee_data)
        
        embed = discord.Embed(
            title="📊 Employee Rating - Step 2/3",
            description=f"Rating **{self.selected_user.mention}**\n\n**Select the rating date:**",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=self.selected_user.display_avatar.url)
        embed.add_field(
            name="ℹ️ What's Next?",
            value="After selecting the date, you'll enter the ratings in a user-friendly form.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class RatingDateSelectView(discord.ui.View):
    """Select rating date (Today or Custom Date)"""
    def __init__(self, target_user: discord.User, employee_data: dict):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.employee_data = employee_data
    
    @discord.ui.button(label="Today", style=discord.ButtonStyle.primary, emoji="📅")
    async def today_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        rating_date = datetime.now(pytz.utc).date()
        
        # Check if rating already exists
        existing_rating = await ComplianceRatingModel.get_rating_by_date(
            self.employee_data['user_id'],
            rating_date
        )
        
        if existing_rating:
            await interaction.response.send_message(
                f"⚠️ A rating already exists for **{self.target_user.mention}** on **{rating_date.strftime('%d/%m/%Y')}**.\n"
                f"Please select a different date or update the existing rating.",
                ephemeral=True
            )
            self.stop()
            return
        
        # Show rating modal
        modal = EmployeeRatingModal(self.target_user, self.employee_data, rating_date)
        await interaction.response.send_modal(modal)
        self.stop()
    
    @discord.ui.button(label="Custom Date", style=discord.ButtonStyle.secondary, emoji="🗓️")
    async def custom_date_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show custom date modal
        modal = CustomDateModal(self.target_user, self.employee_data)
        await interaction.response.send_modal(modal)
        self.stop()


class CustomDateModal(discord.ui.Modal, title="Enter Custom Date"):
    """Modal for entering custom rating date"""
    rating_date = discord.ui.TextInput(
        label="Rating Date",
        placeholder="DD/MM/YYYY (e.g., 30/12/2024)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )
    
    def __init__(self, target_user: discord.User, employee_data: dict):
        super().__init__()
        self.target_user = target_user
        self.employee_data = employee_data
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse date
            rating_date_obj = datetime.strptime(self.rating_date.value, '%d/%m/%Y').date()
            
            # Check if rating already exists
            existing_rating = await ComplianceRatingModel.get_rating_by_date(
                self.employee_data['user_id'],
                rating_date_obj
            )
            
            if existing_rating:
                await interaction.response.send_message(
                    f"⚠️ A rating already exists for **{self.target_user.mention}** on **{rating_date_obj.strftime('%d/%m/%Y')}**.\n"
                    f"Please use a different date or update the existing rating.",
                    ephemeral=True
                )
                return
            
            # Show rating modal
            modal = EmployeeRatingModal(self.target_user, self.employee_data, rating_date_obj)
            
            # Create a view with a button to open the rating modal
            view = OpenRatingModalView(modal, self.target_user, rating_date_obj)
            
            embed = discord.Embed(
                title="✅ Date Confirmed",
                description=f"**Rating Date:** {rating_date_obj.strftime('%d/%m/%Y')}\n\n"
                           f"Click the button below to enter the rating details.",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid date format! Please use **DD/MM/YYYY** format (e.g., 30/12/2024).",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


class OpenRatingModalView(discord.ui.View):
    """View with button to open rating modal"""
    def __init__(self, rating_modal: 'EmployeeRatingModal', target_user: discord.User, rating_date):
        super().__init__(timeout=180)
        self.rating_modal = rating_modal
        self.target_user = target_user
        self.rating_date = rating_date
    
    @discord.ui.button(label="Enter Rating Details", style=discord.ButtonStyle.primary, emoji="📝")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(self.rating_modal)
        self.stop()


class EmployeeRatingModal(discord.ui.Modal, title="Employee Rating"):
    """Main modal for employee rating"""
    
    compliance_rule_breaks = discord.ui.TextInput(
        label="Compliance Rule Breaks",
        placeholder="Number of compliance rule breaks (e.g., 0, 1, 2...)",
        required=True,
        max_length=3,
        style=discord.TextStyle.short,
        default="0"
    )
    
    task_submission_rating = discord.ui.TextInput(
        label="Task Submission Rating (0-10)",
        placeholder="Rate task submission quality (0-10)",
        required=True,
        max_length=2,
        style=discord.TextStyle.short,
        default="8"
    )
    
    task_submission_feedback = discord.ui.TextInput(
        label="Task Submission Feedback",
        placeholder="Provide detailed feedback on task submissions...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )
    
    overall_performance_rating = discord.ui.TextInput(
        label="Overall Performance Rating (0-10)",
        placeholder="Rate overall performance (0-10)",
        required=True,
        max_length=2,
        style=discord.TextStyle.short,
        default="8"
    )
    
    overall_performance_feedback = discord.ui.TextInput(
        label="Overall Performance Feedback",
        placeholder="Provide detailed feedback on overall performance...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, target_user: discord.User, employee_data: dict, rating_date):
        super().__init__()
        self.target_user = target_user
        self.employee_data = employee_data
        self.rating_date = rating_date
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate inputs
            compliance_breaks = int(self.compliance_rule_breaks.value)
            task_rating = int(self.task_submission_rating.value)
            performance_rating = int(self.overall_performance_rating.value)
            
            # Validation checks
            if compliance_breaks < 0:
                await interaction.followup.send(
                    "❌ Compliance rule breaks cannot be negative!",
                    ephemeral=True
                )
                return
            
            if task_rating < 0 or task_rating > 10:
                await interaction.followup.send(
                    "❌ Task submission rating must be between 0 and 10!",
                    ephemeral=True
                )
                return
            
            if performance_rating < 0 or performance_rating > 10:
                await interaction.followup.send(
                    "❌ Overall performance rating must be between 0 and 10!",
                    ephemeral=True
                )
                return
            
            # Get rater data
            rater_data = await UserModel.get_user_by_discord_id(interaction.user.id)
            if not rater_data:
                await interaction.followup.send(
                    "❌ You are not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Create rating
            rating_id = await ComplianceRatingModel.create_rating(
                user_id=self.employee_data['user_id'],
                rated_by_user_id=rater_data['user_id'],
                rating_date=self.rating_date,
                compliance_rule_breaks=compliance_breaks,
                task_submission_rating=task_rating,
                task_submission_feedback=self.task_submission_feedback.value,
                overall_performance_rating=performance_rating,
                overall_performance_feedback=self.overall_performance_feedback.value
            )
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Rating Successfully Recorded",
                description=f"Rating for **{self.target_user.mention}** has been recorded!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📅 Rating Date",
                value=self.rating_date.strftime('%d/%m/%Y'),
                inline=True
            )
            embed.add_field(
                name="👤 Employee",
                value=self.target_user.mention,
                inline=True
            )
            embed.add_field(
                name="👑 Rated By",
                value=interaction.user.mention,
                inline=True
            )
            
            embed.add_field(
                name="⚠️ Compliance Rule Breaks",
                value=f"`{compliance_breaks}`",
                inline=True
            )
            embed.add_field(
                name="📋 Task Submission",
                value=f"`{task_rating}/10`",
                inline=True
            )
            embed.add_field(
                name="⭐ Overall Performance",
                value=f"`{performance_rating}/10`",
                inline=True
            )
            
            embed.add_field(
                name="📝 Task Submission Feedback",
                value=self.task_submission_feedback.value[:500] + ("..." if len(self.task_submission_feedback.value) > 500 else ""),
                inline=False
            )
            embed.add_field(
                name="💬 Overall Performance Feedback",
                value=self.overall_performance_feedback.value[:500] + ("..." if len(self.overall_performance_feedback.value) > 500 else ""),
                inline=False
            )
            
            embed.set_footer(text=f"Rating ID: {rating_id}")
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError:
            await interaction.followup.send(
                "❌ Please enter valid numbers for ratings and compliance breaks!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )