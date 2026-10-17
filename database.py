# It is going to hold all our database setup code. It will be imported by our main.py and our models file
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db" # This is the connection string for our SQLite database. It specifies that we are using SQLite and the database file is located at ./blog.db.

engine = create_async_engine( # Engine is the connection to the database. It is created using the create_engine function from SQLAlchemy, which takes the database URL and any additional connection arguments as parameters.
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # This argument is specific to SQLite. It allows the database connection to be shared across multiple threads, which is necessary for FastAPI's asynchronous nature.
)
AsyncSessionLocal = async_sessionmaker(  # This is a factory that creates database sessions. A session is aessentially a transaction with the database, each request has its own session and this is a standard FastAPI pattern
    engine, 
    class_ = AsyncSession,
    expire_on_commit = False
)

class Base(DeclarativeBase): # The base
    pass

async def get_db(): 
    async with AsyncSessionLocal() as session: 
        yield session 