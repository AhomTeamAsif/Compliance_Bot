import asyncpg
from config import Config

class Database:
    def __init__(self):
        self.pool = None
    
    async def connect(self):
        """Create database connection pool"""
        self.pool = await asyncpg.create_pool(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            min_size=5,
            max_size=20
        )
        print("✅ Database connected")
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("❌ Database disconnected")
    
    async def execute_sql_file(self, filepath: str):
        """Execute SQL file to create tables"""
        try:
            with open(filepath, 'r') as f:
                sql = f.read()
            
            async with self.pool.acquire() as conn:
                await conn.execute(sql)
            
            print(f"✅ Executed SQL file: {filepath}")
        except Exception as e:
            print(f"❌ Failed to execute SQL file: {e}")
            raise

# Global database instance
db = Database()