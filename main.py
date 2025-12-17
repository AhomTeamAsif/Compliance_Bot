import discord
from discord.ext import commands
import asyncio
import logging
from config import Config
from utils.database import db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomBot(commands.Bot):
    """Main bot class"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            application_id=Config.APPLICATION_ID
        )
    
    async def setup_hook(self):
        """Load cogs and sync commands when bot starts"""
        logger.info("Connecting to the database...")
        # Connect to database
        await db.connect()
        
        # Create tables from SQL file
        await db.execute_sql_file('databases/schema.sql')
        
        # Load cogs
        logger.info("Loading cogs...")
        await self.load_extension('cogs.user_management')
        await self.load_extension('cogs.screen_share')
        await self.load_extension('cogs.compliance')
        await self.load_extension('cogs.time_tracking')
        
        # Sync commands to guild
        guild = discord.Object(id=Config.GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        logger.info(f"Syncing commands to guild {Config.GUILD_ID}...")
        await self.tree.sync(guild=guild)
        logger.info(f"Commands synced to guild {Config.GUILD_ID}")

    async def on_ready(self):
        """Called when bot connects to Discord"""
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def on_application_command_error(self, ctx: discord.Interaction, error: Exception):
        """Log errors for slash commands"""
        logger.error(f"Error occurred with command {ctx.command} from {ctx.user}: {error}")
        await ctx.response.send_message("An error occurred while processing the command.", ephemeral=True)

    async def close(self):
        """Clean up when bot shuts down"""
        logger.info("Disconnecting from the database...")
        await db.disconnect()
        await super().close()

async def main():
    # Validate config
    Config.validate()
    
    # Create and run bot
    bot = CustomBot()
    async with bot:
        await bot.start(Config.TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
