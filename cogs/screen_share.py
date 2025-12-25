import discord
from discord.ext import commands
from discord import app_commands
from config import Config
from models import ScreenShareModel, UserModel

class ScreenShare(commands.Cog):
    """Screen sharing management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(
        name="screen_share_on",
        description="Start screen sharing session"
    )
    @app_commands.describe(reason="Reason for screen sharing")
    async def screen_share_on(self, interaction: discord.Interaction, reason: str):
        """Provide screen share instructions to user"""
        
        await interaction.response.defer(ephemeral=True)
        
        # Check if user is registered
        user = await UserModel.get_user_by_discord_id(interaction.user.id)
        if not user:
            await interaction.followup.send(
                "❌ You are not registered! Use `/user_register` first.",
                ephemeral=True
            )
            return
        
        channel = self.bot.get_channel(Config.VOICE_CHANNEL_ID)
        
        try:
            # Check if user already has an active session
            active_session = await ScreenShareModel.get_active_session(user['user_id'])
            if active_session:
                await interaction.followup.send(
                    "⚠️ You already have an active screen share session!",
                    ephemeral=True
                )
                return
            
            # Start new session
            session_id = await ScreenShareModel.start_session(
                user_id=user['user_id'],
                reason=reason
            )
            
            # Send instructions
            await self.send_screen_share_on_instructions(interaction, channel, session_id)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    async def send_screen_share_on_instructions(self, interaction: discord.Interaction, 
                                               channel: discord.VoiceChannel, session_id: int):
        """Send screen share ON instructions to the user"""
        
        embed = discord.Embed(
            title="🖥️ Share Your Screen",
            description=f"Start screen sharing in {channel.mention}",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📋 Follow These Steps:",
            value=(
                "**1️⃣ Join Voice Channel**\n"
                f"   → Click on {channel.mention} to join\n\n"
                "**2️⃣ Start Screen Share**\n"
                "   → Look at the bottom left of Discord\n"
                "   → Click the **'Screen'** button (monitor icon)\n\n"
                "**3️⃣ Select Entire Screen**\n"
                "   → In the popup, choose **'Screens'** tab\n"
                "   → Select your monitor (Screen 1, Screen 2, etc.)\n"
                "   → **DO NOT** select individual applications\n"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"Session ID: {session_id} | Use /screen_share_off when done")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    
    @app_commands.command(
        name="screen_share_off",
        description="Stop screen sharing session"
    )
    @app_commands.describe(reason="Reason for stopping")
    async def screen_share_off(self, interaction: discord.Interaction, reason: str):
        """Provide instructions to stop screen sharing"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user from database
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            
            if not user:
                await interaction.followup.send(
                    "❌ User not found in database!",
                    ephemeral=True
                )
                return
            
            # End the session
            session_id = await ScreenShareModel.end_session(
                user_id=user['user_id'],
                reason=reason
            )
            
            if not session_id:
                await interaction.followup.send(
                    "⚠️ No active screen share session found!",
                    ephemeral=True
                )
                return
            
            # Get session details
            session = await ScreenShareModel.get_session_by_id(session_id)

            channel = self.bot.get_channel(Config.VOICE_CHANNEL_ID)
            
            # Send instructions
            await self.send_screen_share_off_instructions(interaction, channel,session_id, session,reason)
        
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    async def send_screen_share_off_instructions(self, interaction: discord.Interaction, 
                                               channel: discord.VoiceChannel,session_id, session,reason:str):
        """Send screen share OFF instructions to the user"""
        
        embed = discord.Embed(
                title="🛑 Screen Share Stopped",
                description="Your session has been ended",
                color=discord.Color.red()
            )

        embed.add_field(
                name="📊 Session Summary",
                value=(
                    f"**Duration:** {session['duration_minutes']} minutes\n"
                    f"**Session ID:** {session_id}\n"
                    f"**Stop Reason:** {reason}"
                ),
                inline=False
            )
        
        embed.add_field(
            name="📋 Follow These Steps:",
            value=(
                "**1️⃣ Disconnect from Voice Channel**\n"
                f"   → Click on {channel.mention} to join\n\n"
                "**2️⃣ Stop Screen Share**\n"
                "   → Look at the bottom left of Discord\n"
                "   → Click the **'Disconnect'** button (phone icon)\n\n"
               
            ),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="screen_share_status",
        description="Check screen share status across all voice channels"
    )
    async def screen_share_status(self, interaction: discord.Interaction):
        """Show current status of screen sharing in the server"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get active sessions from database
            active_sessions = await ScreenShareModel.get_all_active_sessions()
            
            # Get all voice channels in the guild
            voice_channels = [ch for ch in interaction.guild.channels if isinstance(ch, discord.VoiceChannel)]
            
            # Find all members who are streaming
            streaming_members = []
            total_connected = 0
            
            for channel in voice_channels:
                total_connected += len(channel.members)
                for member in channel.members:
                    if member.voice and member.voice.self_stream:
                        streaming_members.append({
                            'member': member,
                            'channel': channel
                        })
            
            embed = discord.Embed(
                title="📺 Screen Share Status",
                description=f"**Server:** {interaction.guild.name}",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📊 Overview", 
                value=(
                    f"**Voice Channels:** {len(voice_channels)}\n"
                    f"**Connected Members:** {total_connected}\n"
                    f"**Currently Streaming:** {len(streaming_members)}\n"
                    f"**Active Sessions (DB):** {len(active_sessions)}"
                ),
                inline=False
            )
            
            # Show database active sessions
            if active_sessions:
                session_list = []
                for session in active_sessions:
                    duration = int((discord.utils.utcnow() - session['screen_share_on_time']).total_seconds() / 60)
                    session_list.append(
                        f"• **{session['name']}** (ID: {session['session_id']}) - {duration} mins"
                    )
                
                embed.add_field(
                    name="🎥 Active Sessions (Database)",
                    value="\n".join(session_list[:10]) + (f"\n*...and {len(session_list)-10} more*" if len(session_list) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎥 Active Sessions (Database)",
                    value="*No active sessions in database*",
                    inline=False
                )
            
            # Show who's actually streaming in Discord
            if streaming_members:
                streaming_list = []
                for item in streaming_members[:10]:  # Limit to 10
                    streaming_list.append(
                        f"• **{item['member'].display_name}** in {item['channel'].mention}"
                    )
                
                embed.add_field(
                    name="📡 Currently Streaming (Discord)",
                    value="\n".join(streaming_list) + (f"\n*...and {len(streaming_members)-10} more*" if len(streaming_members) > 10 else ""),
                    inline=False
                )
            else:
                embed.add_field(
                    name="📡 Currently Streaming (Discord)",
                    value="*No one is currently streaming*",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(
        name="screen_share_daily_stats",
        description="View screen share stats for a specific day"
    )
    @app_commands.describe(
        date="Date in YYYY-MM-DD format (leave empty for today)",
        user="User to check (ADMIN only, leave empty for yourself)"
    )
    async def screen_share_daily_stats(
        self, 
        interaction: discord.Interaction, 
        date: str = None,
        user: discord.User = None
    ):
        """Show daily screen share statistics"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Determine target user
            target_user = user if user else interaction.user
            
            # Check permissions if viewing another user
            if user and user.id != interaction.user.id:
                from utils.verification_helper import is_admin, is_super_admin
                if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
                    await interaction.followup.send(
                        "❌ Only ADMIN can view other users' stats!",
                        ephemeral=True
                    )
                    return
            
            # Get user from database
            user_data = await UserModel.get_user_by_discord_id(target_user.id)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ {target_user.mention} is not registered!",
                    ephemeral=True
                )
                return
            
            # Parse date
            from datetime import datetime as dt
            if date:
                try:
                    target_date = dt.strptime(date, '%Y-%m-%d').date()
                except ValueError:
                    await interaction.followup.send(
                        "❌ Invalid date format! Use YYYY-MM-DD (e.g., 2024-12-25)",
                        ephemeral=True
                    )
                    return
            else:
                target_date = dt.now().date()
            
            # Get daily stats
            stats = await ScreenShareModel.get_daily_stats(user_data['user_id'], target_date)
            
            if stats['session_count'] == 0:
                await interaction.followup.send(
                    f"📋 No screen share sessions found for **{target_date.strftime('%Y-%m-%d')}**",
                    ephemeral=True
                )
                return
            
            # Build embed
            embed = discord.Embed(
                title=f"📊 Screen Share Stats - {target_date.strftime('%Y-%m-%d')}",
                description=f"Statistics for **{user_data['name']}**",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Total time
            total_mins = stats['total_minutes'] or 0
            hours = total_mins // 60
            mins = total_mins % 60
            
            embed.add_field(
                name="⏱️ Total Screen Share Time",
                value=f"**{hours}h {mins}m** ({total_mins} minutes)",
                inline=False
            )
            
            embed.add_field(
                name="📊 Sessions",
                value=f"**{stats['session_count']}** session(s)",
                inline=True
            )
            
            if stats['first_session']:
                embed.add_field(
                    name="🕐 First Session",
                    value=stats['first_session'].strftime('%I:%M %p'),
                    inline=True
                )
            
            if stats['last_session']:
                embed.add_field(
                    name="🕐 Last Session",
                    value=stats['last_session'].strftime('%I:%M %p'),
                    inline=True
                )
            
            embed.set_footer(text="Use /screen_share_history for detailed session list")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(
        name="screen_share_weekly_report",
        description="View weekly screen share report"
    )
    @app_commands.describe(
        days="Number of days to show (default: 7)",
        user="User to check (ADMIN only, leave empty for yourself)"
    )
    async def screen_share_weekly_report(
        self, 
        interaction: discord.Interaction, 
        days: int = 7,
        user: discord.User = None
    ):
        """Show weekly screen share report"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Determine target user
            target_user = user if user else interaction.user
            
            # Check permissions if viewing another user
            if user and user.id != interaction.user.id:
                from utils.verification_helper import is_admin, is_super_admin
                if not (await is_admin(interaction.user.id) or await is_super_admin(interaction.user.id)):
                    await interaction.followup.send(
                        "❌ Only ADMIN can view other users' reports!",
                        ephemeral=True
                    )
                    return
            
            # Get user from database
            user_data = await UserModel.get_user_by_discord_id(target_user.id)
            
            if not user_data:
                await interaction.followup.send(
                    f"❌ {target_user.mention} is not registered!",
                    ephemeral=True
                )
                return
            
            # Get daily history
            history = await ScreenShareModel.get_user_daily_history(user_data['user_id'], days)
            
            if not history:
                await interaction.followup.send(
                    f"📋 No screen share data found for the last {days} days",
                    ephemeral=True
                )
                return
            
            # Build embed
            embed = discord.Embed(
                title=f"📈 Screen Share Report - Last {days} Days",
                description=f"Report for **{user_data['name']}**",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Calculate totals
            total_sessions = sum(row['session_count'] for row in history)
            total_minutes = sum(row['total_minutes'] or 0 for row in history)
            total_hours = total_minutes // 60
            total_mins = total_minutes % 60
            
            embed.add_field(
                name="📊 Summary",
                value=(
                    f"**Total Time:** {total_hours}h {total_mins}m\n"
                    f"**Total Sessions:** {total_sessions}\n"
                    f"**Days Active:** {len(history)}/{days}"
                ),
                inline=False
            )
            
            # Show daily breakdown
            daily_breakdown = []
            for row in history[:10]:  # Limit to 10 days
                day_mins = row['total_minutes'] or 0
                day_hours = day_mins // 60
                day_mins_rem = day_mins % 60
                
                daily_breakdown.append(
                    f"**{row['date'].strftime('%Y-%m-%d')}**: "
                    f"{day_hours}h {day_mins_rem}m ({row['session_count']} sessions)"
                )
            
            embed.add_field(
                name="📅 Daily Breakdown",
                value="\n".join(daily_breakdown) if daily_breakdown else "No data",
                inline=False
            )
            
            if len(history) > 10:
                embed.set_footer(text=f"Showing 10 of {len(history)} days")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ScreenShare(bot))