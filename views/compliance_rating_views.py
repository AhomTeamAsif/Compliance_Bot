"""Simple dynamic views for compliance rating - one text box for additional fields"""
import discord
from discord import ui
from datetime import datetime, timedelta
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
            value="After selecting the date, you'll enter the ratings with an option to add custom fields!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class DuplicateRatingConfirmView(discord.ui.View):
    """Confirmation view when rating already exists for a date"""
    def __init__(self, target_user: discord.User, employee_data: dict, rating_date, existing_count: int):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.employee_data = employee_data
        self.rating_date = rating_date
        self.existing_count = existing_count

    @discord.ui.button(label="Continue Anyway", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def continue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show rating modal
        modal = SimpleEmployeeRatingModal(self.target_user, self.employee_data, self.rating_date)
        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "✅ Rating cancelled.",
            ephemeral=True
        )
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
        existing_ratings = await ComplianceRatingModel.get_ratings_by_date(
            self.employee_data['user_id'],
            rating_date
        )

        if existing_ratings:
            # Show warning with confirmation
            view = DuplicateRatingConfirmView(
                self.target_user,
                self.employee_data,
                rating_date,
                len(existing_ratings)
            )

            embed = discord.Embed(
                title="⚠️ Warning: Duplicate Rating Detected",
                description=(
                    f"**{len(existing_ratings)} rating(s)** already exist for **{self.target_user.mention}** "
                    f"on **{rating_date.strftime('%d/%m/%Y')}**.\n\n"
                    f"Do you want to add another rating for the same date?"
                ),
                color=discord.Color.orange()
            )
            embed.add_field(
                name="⚠️ Note",
                value="Creating multiple ratings for the same date may affect analytics and reports.",
                inline=False
            )

            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            self.stop()
            return

        # Show rating modal
        modal = SimpleEmployeeRatingModal(self.target_user, self.employee_data, rating_date)
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
            existing_ratings = await ComplianceRatingModel.get_ratings_by_date(
                self.employee_data['user_id'],
                rating_date_obj
            )

            if existing_ratings:
                # Show warning with confirmation
                view = DuplicateRatingConfirmView(
                    self.target_user,
                    self.employee_data,
                    rating_date_obj,
                    len(existing_ratings)
                )

                embed = discord.Embed(
                    title="⚠️ Warning: Duplicate Rating Detected",
                    description=(
                        f"**{len(existing_ratings)} rating(s)** already exist for **{self.target_user.mention}** "
                        f"on **{rating_date_obj.strftime('%d/%m/%Y')}**.\n\n"
                        f"Do you want to add another rating for the same date?"
                    ),
                    color=discord.Color.orange()
                )
                embed.add_field(
                    name="⚠️ Note",
                    value="Creating multiple ratings for the same date may affect analytics and reports.",
                    inline=False
                )

                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return

            # Show rating modal
            modal = SimpleEmployeeRatingModal(self.target_user, self.employee_data, rating_date_obj)

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
    def __init__(self, rating_modal: 'SimpleEmployeeRatingModal', target_user: discord.User, rating_date):
        super().__init__(timeout=180)
        self.rating_modal = rating_modal
        self.target_user = target_user
        self.rating_date = rating_date
    
    @discord.ui.button(label="Enter Rating Details", style=discord.ButtonStyle.primary, emoji="📝")
    async def open_modal_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(self.rating_modal)
        self.stop()


class SimpleEmployeeRatingModal(discord.ui.Modal, title="Employee Rating"):
    """Simple modal with fixed fields + one additional fields box"""

    ratings = discord.ui.TextInput(
        label="Ratings:ruleBreaks, Task, Overall(0-10)",
        placeholder="Enter: 0, 8, 8 (breaks, task rating, overall rating)",
        required=True,
        max_length=20,
        style=discord.TextStyle.short,
        default="0, 8, 8"
    )

    task_submission_feedback = discord.ui.TextInput(
        label="Task Submission Feedback",
        placeholder="Provide detailed feedback on task submissions...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )

    overall_performance_feedback = discord.ui.TextInput(
        label="Overall Performance Feedback",
        placeholder="Provide detailed feedback on overall performance...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )

    # THIS IS THE KEY PART - Simple additional fields box
    additional_fields = discord.ui.TextInput(
        label="Additional Fields (Optional)",
        placeholder="field_name: value, field_name2: value2 (e.g., presentation_skill: Excellent)",
        required=False,
        max_length=2000,
        style=discord.TextStyle.paragraph
    )
    
    def __init__(self, target_user: discord.User, employee_data: dict, rating_date):
        super().__init__()
        self.target_user = target_user
        self.employee_data = employee_data
        self.rating_date = rating_date
    
    def parse_additional_fields(self, text: str) -> dict:
        """Parse the additional fields text into a dictionary
        
        Format: field_name: value, field_name2: value2
        or: field_name: value
            field_name2: value2
        """
        if not text or not text.strip():
            return {}
        
        result = {}
        
        # Split by comma or newline
        parts = []
        if ',' in text:
            parts = [p.strip() for p in text.split(',')]
        else:
            parts = [p.strip() for p in text.split('\n')]
        
        for part in parts:
            if ':' in part:
                # Split by first colon only
                key, value = part.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                if key and value:
                    # Clean up the key - replace spaces with underscores
                    clean_key = key.replace(' ', '_').lower()
                    result[clean_key] = value
        
        return result
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Parse the ratings field (format: breaks, task_rating, performance_rating)
            ratings_parts = [x.strip() for x in self.ratings.value.split(',')]

            if len(ratings_parts) != 3:
                await interaction.followup.send(
                    "❌ Invalid ratings format! Please enter exactly 3 values separated by commas.\n"
                    "Format: `breaks, task_rating, overall_rating` (e.g., `0, 8, 8`)",
                    ephemeral=True
                )
                return

            # Validate inputs
            compliance_breaks = int(ratings_parts[0])
            task_rating = int(ratings_parts[1])
            performance_rating = int(ratings_parts[2])

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
            
            # Parse additional fields
            additional_fields_dict = self.parse_additional_fields(self.additional_fields.value)
            
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
                overall_performance_feedback=self.overall_performance_feedback.value,
                custom_ratings=additional_fields_dict
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

            # Show additional fields if present
            if additional_fields_dict:
                additional_text = ""
                for key, value in additional_fields_dict.items():
                    # Make key readable (replace underscores with spaces, title case)
                    readable_key = key.replace('_', ' ').title()
                    additional_text += f"**{readable_key}:** {value}\n"
                
                embed.add_field(
                    name="📊 Additional Fields",
                    value=additional_text[:1024],
                    inline=False
                )
            
            embed.set_footer(text=f"Rating ID: {rating_id}")
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.followup.send(
                f"❌ Please enter valid numbers for ratings and compliance breaks!\nError: {str(e)}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


# ==================== NEW: VIEW RATINGS WITH FLEXIBLE FILTERS ====================

class ViewRatingsSelectView(discord.ui.View):
    """Select employees to view ratings for"""
    def __init__(self):
        super().__init__(timeout=180)
        self.selected_users = []

    @discord.ui.select(
        cls=discord.ui.UserSelect,
        placeholder="Select employees (1 or more)",
        min_values=1,
        max_values=10
    )
    async def user_select(self, interaction: discord.Interaction, select: discord.ui.UserSelect):
        self.selected_users = select.values

        # Validate all users are in the system
        invalid_users = []
        valid_user_data = []

        for user in self.selected_users:
            user_data = await UserModel.get_user_by_discord_id(user.id)
            if not user_data:
                invalid_users.append(user.mention)
            else:
                valid_user_data.append((user, user_data))

        if invalid_users:
            await interaction.response.send_message(
                f"❌ The following users are not registered in the system:\n{', '.join(invalid_users)}",
                ephemeral=True
            )
            return

        # Show date range selection
        view = DateRangeSelectView(valid_user_data)

        embed = discord.Embed(
            title="📊 View Ratings - Step 2/2",
            description=f"**Selected {len(valid_user_data)} employee(s)**\n\n**Choose date range:**",
            color=discord.Color.blue()
        )

        # List selected users
        user_list = "\n".join([f"• {user.mention}" for user, _ in valid_user_data[:10]])
        embed.add_field(
            name="👥 Selected Employees",
            value=user_list,
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        self.stop()


class DateRangeSelectView(discord.ui.View):
    """Select date range for viewing ratings"""
    def __init__(self, user_data_list):
        super().__init__(timeout=180)
        self.user_data_list = user_data_list

    @discord.ui.button(label="All Ratings", style=discord.ButtonStyle.primary, emoji="📋")
    async def all_ratings_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.fetch_and_display_ratings(interaction, None, None)
        self.stop()

    @discord.ui.button(label="Last 7 Days", style=discord.ButtonStyle.secondary, emoji="📅")
    async def last_7_days_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        end_date = datetime.now(pytz.utc).date()
        start_date = end_date - timedelta(days=7)
        await self.fetch_and_display_ratings(interaction, start_date, end_date)
        self.stop()

    @discord.ui.button(label="Last 30 Days", style=discord.ButtonStyle.secondary, emoji="📆")
    async def last_30_days_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        end_date = datetime.now(pytz.utc).date()
        start_date = end_date - timedelta(days=30)
        await self.fetch_and_display_ratings(interaction, start_date, end_date)
        self.stop()

    @discord.ui.button(label="Custom Range", style=discord.ButtonStyle.secondary, emoji="🗓️")
    async def custom_range_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CustomDateRangeModal(self.user_data_list)
        await interaction.response.send_modal(modal)
        self.stop()

    async def fetch_and_display_ratings(self, interaction, start_date, end_date):
        """Fetch and display ratings for selected users and date range"""
        try:
            all_ratings = []

            for user, user_data in self.user_data_list:
                # Get all ratings for this user
                ratings = await ComplianceRatingModel.get_user_ratings(
                    user_data['user_id'],
                    limit=100  # Get more ratings to filter by date
                )

                # Filter by date range if specified
                if start_date and end_date:
                    ratings = [r for r in ratings if start_date <= r['rating_date'] <= end_date]

                for rating in ratings:
                    rating['user_mention'] = user.mention
                    rating['user_name'] = user_data['name']
                    all_ratings.append(rating)

            if not all_ratings:
                date_info = ""
                if start_date and end_date:
                    date_info = f" between {start_date.strftime('%d/%m/%Y')} and {end_date.strftime('%d/%m/%Y')}"

                await interaction.followup.send(
                    f"📋 No ratings found for the selected employee(s){date_info}.",
                    ephemeral=True
                )
                return

            # Sort by date (newest first)
            all_ratings.sort(key=lambda x: x['rating_date'], reverse=True)

            # Create embed(s)
            date_range_text = "All Time"
            if start_date and end_date:
                date_range_text = f"{start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')}"

            # Use pagination if more than 5 ratings
            if len(all_ratings) > 5:
                view = RatingsPaginationView(
                    all_ratings=all_ratings,
                    date_range_text=date_range_text,
                    employee_count=len(self.user_data_list),
                    requester_name=interaction.user.name
                )
                embed = view.create_embed()
                await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            else:
                # No pagination needed for small lists
                embed = self.create_simple_embed(
                    all_ratings,
                    date_range_text,
                    len(self.user_data_list),
                    interaction.user.name
                )
                await interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    def create_simple_embed(self, all_ratings, date_range_text, employee_count, requester_name):
        """Create embed for small rating lists (no pagination)"""
        embed = discord.Embed(
            title="📊 Compliance Ratings Report",
            description=(
                f"**📅 Period:** {date_range_text}\n"
                f"**📈 Total Ratings:** {len(all_ratings)}\n"
                f"**👥 Employees:** {employee_count}\n"
            ),
            color=discord.Color.blue()
        )

        for idx, rating in enumerate(all_ratings, 1):
            rating_date = rating['rating_date']
            if isinstance(rating_date, str):
                date_display = rating_date
            else:
                date_display = rating_date.strftime('%d/%m/%Y')

            # Build the field value with better formatting
            field_value = (
                f"**👤 Employee:** {rating['user_mention']}\n"
                f"**📅 Date:** {date_display}\n"
                f"**👑 Rated By:** {rating['rated_by_name']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"**⚠️ Compliance Breaks:** {rating['compliance_rule_breaks']}\n"
                f"**📋 Task Submission:** {rating['task_submission_rating']}/10\n"
                f"**⭐ Overall Performance:** {rating['overall_performance_rating']}/10\n"
            )

            # Add task submission feedback (truncated)
            if rating.get('task_submission_feedback'):
                feedback_preview = rating['task_submission_feedback'][:100]
                if len(rating['task_submission_feedback']) > 100:
                    feedback_preview += "..."
                field_value += f"**💬 Task Feedback:** {feedback_preview}\n"

            # Add overall performance feedback (truncated)
            if rating.get('overall_performance_feedback'):
                feedback_preview = rating['overall_performance_feedback'][:100]
                if len(rating['overall_performance_feedback']) > 100:
                    feedback_preview += "..."
                field_value += f"**💭 Overall Feedback:** {feedback_preview}\n"

            # Add full custom/additional fields details
            if rating.get('custom_ratings') and isinstance(rating['custom_ratings'], dict):
                if rating['custom_ratings']:
                    field_value += "━━━━━━━━━━━━━━━━━━━\n**✨ Additional Fields:**\n"
                    for key, value in rating['custom_ratings'].items():
                        # Make key readable (replace underscores with spaces, title case)
                        readable_key = key.replace('_', ' ').title()
                        # Truncate long values
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        field_value += f"• **{readable_key}:** {display_value}\n"

            embed.add_field(
                name=f"#{idx} • {rating['user_name']} - {date_display}",
                value=field_value[:1024],
                inline=False
            )

        embed.set_footer(text=f"Requested by {requester_name}")
        return embed


class RatingsPaginationView(discord.ui.View):
    """Pagination view for rating reports"""
    def __init__(self, all_ratings, date_range_text, employee_count, requester_name):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.all_ratings = all_ratings
        self.date_range_text = date_range_text
        self.employee_count = employee_count
        self.requester_name = requester_name
        self.current_page = 0
        self.items_per_page = 5
        self.total_pages = (len(all_ratings) + self.items_per_page - 1) // self.items_per_page

        # Update button states
        self.update_buttons()

    def update_buttons(self):
        """Enable/disable buttons based on current page"""
        # Disable previous button on first page
        self.children[0].disabled = (self.current_page == 0)
        # Disable next button on last page
        self.children[1].disabled = (self.current_page >= self.total_pages - 1)

    def create_embed(self):
        """Create embed for current page"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.all_ratings))
        ratings_page = self.all_ratings[start_idx:end_idx]

        embed = discord.Embed(
            title="📊 Compliance Ratings Report",
            description=(
                f"**📅 Period:** {self.date_range_text}\n"
                f"**📈 Total Ratings:** {len(self.all_ratings)}\n"
                f"**👥 Employees:** {self.employee_count}\n"
                f"**📄 Page:** {self.current_page + 1}/{self.total_pages}\n"
            ),
            color=discord.Color.blue()
        )

        for idx, rating in enumerate(ratings_page, start_idx + 1):
            rating_date = rating['rating_date']
            if isinstance(rating_date, str):
                date_display = rating_date
            else:
                date_display = rating_date.strftime('%d/%m/%Y')

            # Build the field value with better formatting
            field_value = (
                f"**👤 Employee:** {rating['user_mention']}\n"
                f"**📅 Date:** {date_display}\n"
                f"**👑 Rated By:** {rating['rated_by_name']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"**⚠️ Compliance Breaks:** {rating['compliance_rule_breaks']}\n"
                f"**📋 Task Submission:** {rating['task_submission_rating']}/10\n"
                f"**⭐ Overall Performance:** {rating['overall_performance_rating']}/10\n"
            )

            # Add task submission feedback (truncated)
            if rating.get('task_submission_feedback'):
                feedback_preview = rating['task_submission_feedback'][:100]
                if len(rating['task_submission_feedback']) > 100:
                    feedback_preview += "..."
                field_value += f"**💬 Task Feedback:** {feedback_preview}\n"

            # Add overall performance feedback (truncated)
            if rating.get('overall_performance_feedback'):
                feedback_preview = rating['overall_performance_feedback'][:100]
                if len(rating['overall_performance_feedback']) > 100:
                    feedback_preview += "..."
                field_value += f"**💭 Overall Feedback:** {feedback_preview}\n"

            # Add full custom/additional fields details
            if rating.get('custom_ratings') and isinstance(rating['custom_ratings'], dict):
                if rating['custom_ratings']:
                    field_value += "━━━━━━━━━━━━━━━━━━━\n**✨ Additional Fields:**\n"
                    for key, value in rating['custom_ratings'].items():
                        # Make key readable (replace underscores with spaces, title case)
                        readable_key = key.replace('_', ' ').title()
                        # Truncate long values
                        display_value = str(value)[:80]
                        if len(str(value)) > 80:
                            display_value += "..."
                        field_value += f"• **{readable_key}:** {display_value}\n"

            embed.add_field(
                name=f"#{idx} • {rating['user_name']} - {date_display}",
                value=field_value[:1024],
                inline=False
            )

        embed.set_footer(text=f"Page {self.current_page + 1}/{self.total_pages} • Requested by {self.requester_name}")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary, emoji="◀️")
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary, emoji="▶️")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed()
            await interaction.response.edit_message(embed=embed, view=self)


class CustomDateRangeModal(discord.ui.Modal, title="Enter Custom Date Range"):
    """Modal for entering custom date range"""
    start_date = discord.ui.TextInput(
        label="Start Date",
        placeholder="DD/MM/YYYY (e.g., 01/01/2024)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )

    end_date = discord.ui.TextInput(
        label="End Date",
        placeholder="DD/MM/YYYY (e.g., 31/12/2024)",
        required=True,
        max_length=10,
        style=discord.TextStyle.short
    )

    def __init__(self, user_data_list):
        super().__init__()
        self.user_data_list = user_data_list

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Parse dates
            start_date_obj = datetime.strptime(self.start_date.value, '%d/%m/%Y').date()
            end_date_obj = datetime.strptime(self.end_date.value, '%d/%m/%Y').date()

            if start_date_obj > end_date_obj:
                await interaction.followup.send(
                    "❌ Start date must be before or equal to end date!",
                    ephemeral=True
                )
                return

            # Fetch and display ratings
            view = DateRangeSelectView(self.user_data_list)
            await view.fetch_and_display_ratings(interaction, start_date_obj, end_date_obj)

        except ValueError:
            await interaction.followup.send(
                "❌ Invalid date format! Please use **DD/MM/YYYY** format (e.g., 01/01/2024).",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )