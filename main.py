from contextlib import asynccontextmanager
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi import FastAPI, Request, HTTPException, status, Depends # FastAPI is the main class that we use to create our application. Request is used to access the incoming request data. HTTPException is used to raise HTTP exceptions with specific status codes and messages. status is a module that provides constants for HTTP status codes. Depends is used for dependency injection, allowing us to define dependencies for our endpoints.
from fastapi.exceptions import RequestValidationError # for handling validation error like when someone passes hello instead of an integer when we are expecting an integer
from starlette.exceptions import HTTPException as StarletteHTTPException 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from schemas import PostResponse, PostCreate, PostUpdate, UserCreate, UserResponse, UserUpdate # importing the pydantic models we created in schemas.py
from typing import Annotated
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import models # Gives access to our post and user models
from database import Base, engine, get_db # Base and engine are for creating tables and get_db is our dependency function that provides database sessions


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
    result = await db.execute(select(models.Post).options(selectinload(models.Post.author)),) # selectinload enforces eager loading(loading ina dvance) rather than lazy loading, its only used at those places where there are relationships, like here we had an author relationship.
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
    )
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {"posts": posts, "user": user, "title": f"{user.username}'s Posts"},
    )

@app.post( 
    "/api/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(user: UserCreate, db: Annotated[AsyncSession, Depends(get_db)]): # This tells FastAPI that before running this function call get_db and pass the result as the db parametrer here. get_db from our satabase.py file creates a session and yields it.
    result = await db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "Username already exists",
        )
    result = await db.execute(
            select(models.User).where(models.User.email == user.email),
        )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "Email already exists",
        )
    new_user = models.User(
        username = user.username,
        email = user.email,
    )
    db.add(new_user) # Stagers the insert
    await db.commit() # It executes the insert and saves it to the db
    await db.refresh(new_user) # Reloads the object from the db
    return new_user

@app.get("/api/users/{user_id}", response_model=UserResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
async def get_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]): # gets the user by injecting the db to get the database session
    result = await db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
async def get_user_posts(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]): # Gets the posts belonging to a user
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
    )
    posts = result.scalars().all()
    return posts

## update_user
@app.patch("/api/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_update.username is not None and user_update.username != user.username:
        result = await db.execute(
            select(models.User).where(models.User.username == user_update.username),
        )
        existing_user = result.scalars().first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )

    if user_update.email is not None and user_update.email != user.email:
        result = await db.execute(
            select(models.User).where(models.User.email == user_update.email),
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    if user_update.username is not None:
        user.username = user_update.username
    if user_update.email is not None:
        user.email = user_update.email
    if user_update.image_file is not None:
        user.image_file = user_update.image_file

    await db.commit()
    await db.refresh(user)
    return user

## delete_user
@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await db.delete(user)
    await db.commit()
    
@app.get("/api/posts", response_model=list[PostResponse]) # A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed. The response_model parameter specifies that the response will be a list of PostResponse objects.
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]): # this is an api endpoint that returns a list of all posts. The response_model parameter in the decorator specifies that the response will be a list of PostResponse objects, which is a Pydantic model defined in schemas.py. This means that FastAPI will automatically validate and serialize the response data to match the PostResponse model.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()
    return posts

@app.post( # A post request is what we use to create resources. In this case, we are creating a new post. The decorator defines a POST endpoint at the URL
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_post(post: PostCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.User).where(models.User.id == post.user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    new_post = models.Post(
        title=post.title,
        content=post.content,
        user_id=post.user_id,
    )
    db.add(new_post)
    await db.commit()
    await db.refresh(new_post, attribute_names=["author"])
    return new_post

@app.get("/api/posts/{post_id}", response_model=PostResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]): # this is an api endpoint that returns a single post based on the provided post_id. The post_id is extracted from the URL and passed as an argument to the function.
    result = db.execute(
        select(models.Post)
        .options(selectinload(models.Posyt.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="Post not found",
    )

@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[AsyncSession, Depends(get_db)],): # This is what will contain the data from the request body when someone is attempting to update a post.
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found",
        )
    # Now we add the update logic but before we update the user_id, we should check if the new user actually exists, it would give an error than letting the databse contraint fail
    # we only do this check if the client sent a different user than what is already on the post.
    if post_data.user_id != post.user_id:
        result = await db.execute(select(models.User).where(models.User.id == post_data.user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await db.commit()
    await db.refresh(post, attribute_names=["author"])
    return post

@app.patch("/api/posts/{post_id}", response_model=PostResponse)
async def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[AsyncSession, Depends(get_db)],): # This is what will contain the data from the request body when someone is attempting to update a post.
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found",
        )
    # We only want to update fields that client actually sent, we dont want to override missing fields with none

    update_data = post_data.model_dump(exclude_unset = True) # without this, if the client sends some fields and not all, pydantic would use the default values for the unsent fields.
    for field , value in update_data.items():
        setattr(post, field, value) 

    await db.commit()
    await db.refresh(post)
    return post

@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)  
async def delete_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):  
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Post not found",
        )
    await db.delete(post)
    await db.commit()


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