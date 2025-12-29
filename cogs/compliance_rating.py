import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, date
from models.compliance_rating_model import ComplianceRatingModel
from models.user_model import UserModel
from utils.verification_helper import is_admin, is_super_admin
import pytz


class ComplianceRating(commands.Cog):
    """Commands for managing compliance ratings"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ==================== GIVE RATING ====================
    @app_commands.command(
        name="rate_employee",
        description="Rate an employee on compliance, task submission, and overall performance (ADMIN+)"
    )
    @app_commands.describe(
        user="The employee to rate",
        rating_date="Date for the rating (defaults to today)",
        compliance_rule_breaks="Number of compliance rule breaks",
        task_submission_rating="Task submission rating (0-10)",
        task_submission_feedback="Feedback for task submission rating",
        overall_performance_rating="Overall performance rating (0-10)",
        overall_performance_feedback="Feedback for overall performance rating"
    )
    async def rate_employee(
        self,
        interaction: discord.Interaction,
        user: discord.User,
        compliance_rule_breaks: int,
        task_submission_rating: int,
        task_submission_feedback: str,
        overall_performance_rating: int,
        overall_performance_feedback: str,
        rating_date: str = None
    ):
        """Rate an employee"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if admin or super admin
        if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
            await interaction.followup.send(
                "❌ Only ADMIN or SUPER ADMIN can rate employees!",
                ephemeral=True
            )
            return
        
        try:
            # Validate ratings
            if task_submission_rating < 0 or task_submission_rating > 10:
                await interaction.followup.send(
                    "❌ Task submission rating must be between 0 and 10!",
                    ephemeral=True
                )
                return
            
            if overall_performance_rating < 0 or overall_performance_rating > 10:
                await interaction.followup.send(
                    "❌ Overall performance rating must be between 0 and 10!",
                    ephemeral=True
                )
                return
            
            if compliance_rule_breaks < 0:
                await interaction.followup.send(
                    "❌ Compliance rule breaks cannot be negative!",
                    ephemeral=True
                )
                return
            
            # Get employee user data
            employee_data = await UserModel.get_user_by_discord_id(user.id)
            
            if not employee_data:
                await interaction.followup.send(
                    f"❌ {user.mention} is not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Get rater user data
            rater_data = await UserModel.get_user_by_discord_id(interaction.user.id)
            
            if not rater_data:
                await interaction.followup.send(
                    "❌ You are not registered in the system!",
                    ephemeral=True
                )
                return
            
            # Parse rating date or use today
            if rating_date:
                try:
                    rating_date_obj = datetime.strptime(rating_date, '%d/%m/%Y').date()
                except ValueError:
                    await interaction.followup.send(
                        "❌ Invalid date format! Please use DD/MM/YYYY format.",
                        ephemeral=True
                    )
                    return
            else:
                rating_date_obj = datetime.now(pytz.utc).date()
            
            # Check if rating already exists for this date
            existing_rating = await ComplianceRatingModel.get_rating_by_date(
                employee_data['user_id'],
                rating_date_obj
            )
            
            if existing_rating:
                await interaction.followup.send(
                    f"⚠️ A rating already exists for {user.mention} on {rating_date_obj.strftime('%d/%m/%Y')}.\n"
                    f"Please use a different date or update the existing rating.",
                    ephemeral=True
                )
                return
            
            # Create rating
            rating_id = await ComplianceRatingModel.create_rating(
                user_id=employee_data['user_id'],
                rated_by_user_id=rater_data['user_id'],
                rating_date=rating_date_obj,
                compliance_rule_breaks=compliance_rule_breaks,
                task_submission_rating=task_submission_rating,
                task_submission_feedback=task_submission_feedback,
                overall_performance_rating=overall_performance_rating,
                overall_performance_feedback=overall_performance_feedback
            )
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Compliance Rating Recorded",
                description=f"Rating successfully recorded for {user.mention}",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="📅 Rating Date",
                value=rating_date_obj.strftime('%d/%m/%Y'),
                inline=True
            )
            embed.add_field(
                name="⚠️ Compliance Rule Breaks",
                value=str(compliance_rule_breaks),
                inline=True
            )
            embed.add_field(
                name="📋 Task Submission Rating",
                value=f"{task_submission_rating}/10",
                inline=True
            )
            embed.add_field(
                name="📝 Task Submission Feedback",
                value=task_submission_feedback[:500] + ("..." if len(task_submission_feedback) > 500 else ""),
                inline=False
            )
            embed.add_field(
                name="⭐ Overall Performance Rating",
                value=f"{overall_performance_rating}/10",
                inline=True
            )
            embed.add_field(
                name="💬 Overall Performance Feedback",
                value=overall_performance_feedback[:500] + ("..." if len(overall_performance_feedback) > 500 else ""),
                inline=False
            )
            embed.add_field(
                name="👤 Rated By",
                value=interaction.user.mention,
                inline=True
            )
            
            embed.set_footer(text=f"Rating ID: {rating_id}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
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
                
                embed.add_field(
                    name=f"📅 {date_display}",
                    value=field_value,
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
                
                embed.add_field(
                    name=f"👤 {rating['user_name']}",
                    value=field_value,
                    inline=True
                )
            
            embed.set_footer(text=f"Requested by {interaction.user.name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ComplianceRating(bot))

