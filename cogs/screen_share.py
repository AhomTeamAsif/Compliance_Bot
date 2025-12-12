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
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="screen_share_status",
        description="Check screen share channel status"
    )
    async def screen_share_status(self, interaction: discord.Interaction):
        """Show current status of screen share channel"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            channel = self.bot.get_channel(Config.VOICE_CHANNEL_ID)
            
            if channel is None:
                await interaction.followup.send(
                    "❌ Screen share channel not configured!",
                    ephemeral=True
                )
                return
            
            # Get active sessions from database
            active_sessions = await ScreenShareModel.get_all_active_sessions()
            
            # Check who's currently streaming in voice channel
            streaming_members = [
                member for member in channel.members 
                if member.voice and member.voice.self_stream
            ]
            
            embed = discord.Embed(
                title="📺 Screen Share Status",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Channel", 
                value=channel.mention, 
                inline=True
            )
            
            embed.add_field(
                name="Connected Members", 
                value=f"{len(channel.members)}", 
                inline=True
            )
            
            embed.add_field(
                name="Active Sessions (DB)",
                value=f"{len(active_sessions)}",
                inline=True
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
                    name="🎥 Active Sessions",
                    value="\n".join(session_list),
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎥 Active Sessions",
                    value="*No active sessions in database*",
                    inline=False
                )
            
            # Show who's actually streaming in Discord
            if streaming_members:
                streaming_list = "\n".join([f"• {member.display_name}" for member in streaming_members])
                embed.add_field(
                    name="📡 Currently Streaming (Discord)",
                    value=streaming_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📡 Currently Streaming (Discord)",
                    value="*No one is streaming*",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
    
    @app_commands.command(
        name="screen_share_history",
        description="View your screen share history"
    )
    @app_commands.describe(limit="Number of sessions to show (default: 5)")
    async def screen_share_history(self, interaction: discord.Interaction, limit: int = 5):
        """Show user's screen share history"""
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get user from database
            user = await UserModel.get_user_by_discord_id(interaction.user.id)
            
            if not user:
                await interaction.followup.send(
                    "❌ No history found. You haven't started any screen share sessions yet!",
                    ephemeral=True
                )
                return
            
            # Get history
            sessions = await ScreenShareModel.get_user_history(user['user_id'], limit)
            
            if not sessions:
                await interaction.followup.send(
                    "📋 No screen share history found!",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📊 Screen Share History",
                description=f"Last {len(sessions)} session(s) for {interaction.user.mention}",
                color=discord.Color.blue()
            )
            
            for session in sessions:
                # Format timestamps
                on_time = session['screen_share_on_time'].strftime("%Y-%m-%d %H:%M")
                off_time = session['screen_share_off_time'].strftime("%H:%M") if session['screen_share_off_time'] else "Ongoing"
                
                status = "🟢 Active" if session['screen_share_off_time'] is None else "⚫ Ended"
                duration = session['duration_minutes'] if session['duration_minutes'] else "N/A"
                
                field_value = (
                    f"**Status:** {status}\n"
                    f"**Started:** {on_time}\n"
                    f"**Ended:** {off_time}\n"
                    f"**Duration:** {duration} mins\n"
                )
                
                if session['screen_share_on_reason']:
                    field_value += f"**Reason:** {session['screen_share_on_reason']}\n"
                
                embed.add_field(
                    name=f"Session #{session['session_id']}",
                    value=field_value,
                    inline=True
                )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )


async def setup(bot):
    await bot.add_cog(ScreenShare(bot))