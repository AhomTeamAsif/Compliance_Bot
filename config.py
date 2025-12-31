import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Discord Config
    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD_ID = int(os.getenv('GUILD_ID', 0))
    VOICE_CHANNEL_ID = int(os.getenv('VOICE_CHANNEL_ID', 0))
    APPLICATION_ID = int(os.getenv('APPLICATION_ID', 0)) if os.getenv('APPLICATION_ID') else None
    
    # Sick Leave Config
    SICK_LEAVE_ANCHOR_HOUR = int(os.getenv('SICK_LEAVE_ANCHOR_HOUR', 10))  # e.g., 10 AM
    SICK_LEAVE_EARLY_HOURS = int(os.getenv('SICK_LEAVE_EARLY_HOURS', 12))  # window start hours before anchor
    SICK_LEAVE_LATE_HOURS = int(os.getenv('SICK_LEAVE_LATE_HOURS', 2))     # window end hours before anchor
    
    # Database Config
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_NAME = os.getenv('DB_NAME')
    DB_USER = os.getenv('DB_USER')
    DB_PASSWORD = os.getenv('DB_PASSWORD')
    
    @classmethod
    def validate(cls):
        """Validate that all required config values are present"""
        if not cls.TOKEN:
            raise ValueError("DISCORD_TOKEN not found in .env file")
        if not cls.GUILD_ID:
            raise ValueError("GUILD_ID not found in .env file")
        if not cls.VOICE_CHANNEL_ID:
            raise ValueError("VOICE_CHANNEL_ID not found in .env file")
        if not cls.DB_NAME:
            raise ValueError("DB_NAME not found in .env file")
        if not cls.DB_USER:
            raise ValueError("DB_USER not found in .env file")
        if not cls.DB_PASSWORD:
            raise ValueError("DB_PASSWORD not found in .env file")
    
    @classmethod
    def get_db_url(cls):
        """Get database connection URL"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
