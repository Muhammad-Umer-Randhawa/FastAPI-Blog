# It is going to hold all our database setup code. It will be imported by our main.py and our models file
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db" # This is the connection string for our SQLite database. It specifies that we are using SQLite and the database file is located at ./blog.db.
engine = create_engine( # Engine is the connection to the database. It is created using the create_engine function from SQLAlchemy, which takes the database URL and any additional connection arguments as parameters.
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}, # This argument is specific to SQLite. It allows the database connection to be shared across multiple threads, which is necessary for FastAPI's asynchronous nature.
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # This is a factory that creates database sessions. A session is aessentially a transaction with the database, each request has its own session and this is a standard FastAPI pattern

class Base(DeclarativeBase): # The base
    pass

def get_db(): # This is a dependency function that will be used to get a database session for each request. It uses a context manager to ensure that the session is properly closed after the request is completed.
    with SessionLocal() as db: # it uses a generator using the yield.db. The "with" statement makes the session work as a context manager, like opening a kind of file. This ensures cleanup even if an error occurs
        yield db # FastAPI's dependency injection calls this function for each request and handles that cleanup automatically, 
        # the yield statement allows the function to return a value (the database session) and then continue executing after the request is done, which is where the session is closed.