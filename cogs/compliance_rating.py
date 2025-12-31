import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, date
from models.compliance_rating_model import ComplianceRatingModel
from models.user_model import UserModel
from utils.verification_helper import is_admin, is_super_admin
from views.compliance_rating_views import EmployeeSelectView, ViewRatingsSelectView
import pytz


class ComplianceRating(commands.Cog):
    """Commands for managing compliance ratings with simple additional fields"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ==================== GIVE RATING (SIMPLE DYNAMIC) ====================
    @app_commands.command(
        name="rate_employee",
        description="Rate an employee with fixed fields + optional additional fields (ADMIN+)"
    )
    async def rate_employee(self, interaction: discord.Interaction):
        """Rate an employee using intuitive modal interface with simple additional fields"""
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.response.send_message(
                "❌ Only **ADMIN** or **SUPER ADMIN** can rate employees!",
                ephemeral=True
            )
            return
        
        # Show employee selection view
        view = EmployeeSelectView()
        
        embed = discord.Embed(
            title="📊 Employee Rating - Step 1/3",
            description="**Select the employee** you want to rate:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Fixed Rating Categories",
            value=(
                "• **Compliance Rule Breaks** - Track policy violations\n"
                "• **Task Submission Rating** - Quality and timeliness (0-10)\n"
                "• **Overall Performance** - Holistic evaluation (0-10)"
            ),
            inline=False
        )
        embed.add_field(
            name="✨ Additional Fields (Optional)",
            value=(
                "You can add any custom fields in the format:\n"
                "`field_name: value, field_name2: value2`\n\n"
                "**Examples:**\n"
                "• `presentation_skill: Excellent presenter`\n"
                "• `code_quality: Very clean, team_work: Great`\n"
                "• `morning_meetings: Participates well`"
            ),
            inline=False
        )
        embed.set_footer(text="Simple & flexible - add any fields you need!")
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    # ==================== VIEW COMPLIANCE RATINGS ====================
    @app_commands.command(
        name="view_compliance_ratings",
        description="View compliance ratings for an employee (ADMIN+)"
    )
    @app_commands.describe(
        user="The employee to view ratings for",
        limit="Number of ratings to show (default: 10)"
    )
    async def view_compliance_ratings(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        limit: int = 10
    ):
        """View compliance ratings for an employee"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view compliance ratings!",
                ephemeral=True
            )
            return
        
        try:
            # Get employee user data
            employee_data = await UserModel.get_user_by_discord_id(user.id)
            
            if not employee_data:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get ratings
            ratings = await ComplianceRatingModel.get_user_ratings(
                employee_data['user_id'],
                limit=limit
            )
            
            if not ratings:
                await interaction.followup.send(
                    f"📋 No compliance ratings found for {user.mention}.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 Compliance Ratings for {employee_data['name']}",
                description=f"Showing {len(ratings)} most recent rating(s)",
                color=discord.Color.blue()
            )
            
            for rating in ratings:
                rating_date = rating['rating_date']
                if isinstance(rating_date, str):
                    date_display = rating_date
                else:
                    date_display = rating_date.strftime('%d/%m/%Y')
                
                field_value = (
                    f"**Date:** {date_display}\n"
                    f"**Compliance Breaks:** {rating['compliance_rule_breaks']}\n"
                    f"**Task Submission:** {rating['task_submission_rating']}/10\n"
                    f"**Overall Performance:** {rating['overall_performance_rating']}/10\n"
                    f"**Rated By:** {rating['rated_by_name']}"
                )
                
                # Add additional fields if present
                if rating.get('custom_ratings') and isinstance(rating['custom_ratings'], dict):
                    if rating['custom_ratings']:  # Check if not empty
                        field_value += "\n\n**📊 Additional Feedback**\n"
                        for key, value in rating['custom_ratings'].items():
                            # Make key readable
                            readable_key = key.replace('_', ' ').title()
                            field_value += f"• **{readable_key}:** {value}\n"
                
                embed.add_field(
                    name=f"📅 {date_display}",
                    value=field_value[:1024],
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    # ==================== VIEW ALL RATINGS BY DATE ====================
    @app_commands.command(
        name="view_ratings_by_date",
        description="View all compliance ratings for a specific date (ADMIN+)"
    )
    @app_commands.describe(
        rating_date="Date to view ratings for (DD/MM/YYYY format)"
    )
    async def view_ratings_by_date(
        self,
        interaction: discord.Interaction,
        rating_date: str
    ):
        """View all compliance ratings for a specific date"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can view compliance ratings!",
                ephemeral=True
            )
            return
        
        try:
            # Parse date
            try:
                rating_date_obj = datetime.strptime(rating_date, '%d/%m/%Y').date()
            except ValueError:
                await interaction.followup.send(
                    "❌ Invalid date format! Please use DD/MM/YYYY format.",
                    ephemeral=True
                )
                return
            
            # Get ratings
            ratings = await ComplianceRatingModel.get_all_ratings_by_date(rating_date_obj)
            
            if not ratings:
                await interaction.followup.send(
                    f"📋 No compliance ratings found for {rating_date}.",
                    ephemeral=True
                )
                return
            
            # Create embed
            embed = discord.Embed(
                title=f"📊 Compliance Ratings - {rating_date}",
                description=f"Total ratings: {len(ratings)}",
                color=discord.Color.blue()
            )
            
            for rating in ratings:
                field_value = (
                    f"**Compliance Breaks:** {rating['compliance_rule_breaks']}\n"
                    f"**Task Submission:** {rating['task_submission_rating']}/10\n"
                    f"**Overall Performance:** {rating['overall_performance_rating']}/10\n"
                    f"**Rated By:** {rating['rated_by_name']}"
                )
                
                # Add additional fields if present
                if rating.get('custom_ratings') and isinstance(rating['custom_ratings'], dict):
                    if rating['custom_ratings']:  # Check if not empty
                        field_value += "\n\n**📊 Additional:**\n"
                        # Show first 2 additional fields
                        count = 0
                        for key, value in rating['custom_ratings'].items():
                            if count >= 2:
                                remaining = len(rating['custom_ratings']) - 2
                                field_value += f"• ... and {remaining} more\n"
                                break
                            readable_key = key.replace('_', ' ').title()
                            field_value += f"• {readable_key}: {value}\n"
                            count += 1
                
                embed.add_field(
                    name=f"👤 {rating['user_name']}",
                    value=field_value[:1024],
                    inline=True
                )
            
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    # ==================== VIEW RATINGS (FLEXIBLE) ====================
    @app_commands.command(
        name="view_ratings",
        description="View compliance ratings for selected employees in a date range (ADMIN+)"
    )
    async def view_ratings(self, interaction: discord.Interaction):
        """View ratings for multiple employees with flexible date range selection"""

        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.response.send_message(
                "❌ Only **ADMIN** or **SUPER ADMIN** can view compliance ratings!",
                ephemeral=True
            )
            return

        # Show employee selection view
        view = ViewRatingsSelectView()

        embed = discord.Embed(
            title="📊 View Compliance Ratings",
            description="**Select employees** whose ratings you want to view:",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="📋 Next Steps",
            value=(
                "1️⃣ Select one or more employees\n"
                "2️⃣ Choose date range (or view all)\n"
                "3️⃣ View detailed ratings"
            ),
            inline=False
        )
        embed.set_footer(text="You can select multiple employees at once!")

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ComplianceRating(bot))