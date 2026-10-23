from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi import FastAPI, Request, HTTPException, status, Depends # FastAPI is the main class that we use to create our application. Request is used to access the incoming request data. HTTPException is used to raise HTTP exceptions with specific status codes and messages. status is a module that provides constants for HTTP status codes. Depends is used for dependency injection, allowing us to define dependencies for our endpoints.
from fastapi.exceptions import RequestValidationError # for handling validation error like when someone passes hello instead of an integer when we are expecting an integer
from starlette.exceptions import HTTPException as StarletteHTTPException 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates  
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models # Gives access to our post and user models
from database import Base, engine, get_db # Base and engine are for creating tables and get_db is our dependency function that provides database sessions
from routers import posts, users

# Pydantic: It is a data validation and settings management library for Python, based on Python type annotations/ type hints. It is used in FastAPI to define data models and validate incoming request data.
# Data flow is like this: Arequest comes in, pydantic validates it, SQLAlchemy stores or  retrieves the dats, pydantic formats the repsonse and the response goes out. There are clear boundries between eachother
# PUT: Full replacement. with that you send all the fields for that resource, replacing a record with a new version of that recrod.
# PATCH: is for partial updates, with that you only send what is changed if you only want to update a post for eg.
# Async: Allows your program to handle multiple tasks concurrently.Switching to async means we avoid waiting for something external like a database response, a netwrok request or a file to read because we can do other work in that time. These are called IOBound tasks.
# Lifespan is a modern way in fastapi to handle startup and shutdown events. It replaces the older deprecated on startup and on shutdown decorators

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    #shutdown
    await engine.dispose()
app = FastAPI() 

# this 'app' object is used to define all of our routes and configurations for the
# FastAPI application. It serves as the main entry point for the application, allowing
# us to define endpoints, middleware, and other settings.

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
templates = Jinja2Templates(directory = "templates")

app.include_router(users.router, prefix="/api/users", tags=["users"]) # connects the router to our app, the prefix adds that url prefix to all routes in the router, the routers empty strings become the prefix, the tag parameter organizes the /docs page, it creates collapsable sections so all of the user endpoints appear under a users header and all posts endpoints are under posts header
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

# General pattern: server-side rendering (SSR)
# 1. Route function gathers/builds data (e.g. the 'posts' list)
# 2. Jinja2Templates renders an HTML file from templates/, injecting that data
# 3. Final HTML (not raw data) is sent back to the browser
# Same pattern exists in Flask, Django, Express, Rails, etc. — just different syntax.

# When we define a route with just def, its 
# just a regular function, FastAPI automatically runs it in a seperate thread pool. 
# So this prevents the function from blocking the main event loop. Even with a regular def 
# function here other requests can be processed and this is automatic and works well. 
# If we define a route with async def, then fastapi runs it directly in the main event loop 
# which is more efficient but it means you must await for any IO operations, if you are blocking 
# IO without await, you are bliocking the entire event loop, and thats worse than just using a 
# regular def function.

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(request: Request, db: Annotated[AsyncSession, Depends(get_db)]): 
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc()),
    ) # selectinload enforces eager loading(loading ina dvance) rather than lazy loading, its only used at those places where there are relationships, like here we had an author relationship.
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )

# This line renders the "home.html" template and injects the 'posts' list into it. The 'request' object is also passed to the template, which is necessary for Jinja2 to function properly.

@app.get("/posts/{post_id}", include_in_schema=False, name="post_page")
async def post_page(request: Request, post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if post:
        title = post.title[:50]
        return templates.TemplateResponse(
            request,
            "post.html",
            {"post": post, "title": title},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found") 

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
        .order_by(models.Post.date_posted.desc()),
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )

@app.exception_handler(StarletteHTTPException)
async def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    if request.url.path.startswith("/api"): # JSON response for API requests
        return await http_exception_handler(request, exception)
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )
    return templates.TemplateResponse( # HTML response for non-API requests
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return await request_validation_exception_handler(request, exception)
    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )