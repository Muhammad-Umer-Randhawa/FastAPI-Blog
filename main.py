from fastapi import FastAPI, Request, HTTPException, status, Depends # FastAPI is the main class that we use to create our application. Request is used to access the incoming request data. HTTPException is used to raise HTTP exceptions with specific status codes and messages. status is a module that provides constants for HTTP status codes. Depends is used for dependency injection, allowing us to define dependencies for our endpoints.
from fastapi.exceptions import RequestValidationError # for handling validation error like when someone passes hello instead of an integer when we are expecting an integer
from fastapi.responses import JSONResponse # to manually return JSON responses from our endpoints, especially in error handling scenarios.
from starlette.exceptions import HTTPException as StarletteHTTPException 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from schemas import PostResponse, PostCreate, UserCreate, UserResponse # importing the pydantic models we created in schemas.py

from typing import Annotated
from sqlalchemy import select
from sqlalchemy.orm import Session

import models # Gives access to our post and user models
from database import Base, engine, get_db # Base and engine are for creating tables and get_db is our dependency function that provides database sessions


# Pydantic: It is a data validation and settings management library for Python, based on Python type annotations/ type hints. It is used in FastAPI to define data models and validate incoming request data.
# Data flow is like this: Arequest comes in, pydantic validates it, SQLAlchemy stores or  retrieves the dats, pydantic formats the repsonse and the response goes out. There are clear boundries between eachother

Base.metadata.create_all(bind=engine) # This looks at all of our models from base and creates the tables if they dont already exist. It is idempotent, which means its safe to run multiple times and if that laready exist then nothing owuld happen, and it happens on app startup.



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

@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return templates.TemplateResponse(
        request,
        "home.html",
        {"posts": posts, "title": "Home"},
    )

# This line renders the "home.html" template and injects the 'posts' list into it. The 'request' object is also passed to the template, which is necessary for Jinja2 to function properly.

@app.get("/posts/{post_id}", include_in_schema=False, name="post_page")
def post_page(request: Request, post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
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
def user_posts_page(
    request: Request,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
):
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
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

def create_user(user: UserCreate, db: Annotated[Session, Depends(get_db)]): # This tells FastAPI that before running this function call get_db and pass the result as the db parametrer here. get_db from our satabase.py file creates a session and yields it.
    result = db.execute(
        select(models.User).where(models.User.username == user.username),
    )
    existing_user = result.scalars().first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail = "Username already exists",
        )


    result = db.execute(
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
    db.commit() # It executes the insert and saves it to the db
    db.refresh(new_user) # Reloads the object from the db

    return new_user

@app.get("/api/users/{user_id}", response_model=UserResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]): # gets the user by injecting the db to get the database session
    result = db.execute(
        select(models.User).where(models.User.id == user_id),
    )
    user = result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

@app.get("/api/users/{user_id}/posts", response_model=list[PostResponse])
def get_user_posts(user_id: int, db: Annotated[Session, Depends(get_db)]): # Gets the posts belonging to a user
    result = db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    result = db.execute(select(models.Post).where(models.Post.user_id == user_id))
    posts = result.scalars().all()
    return posts



@app.get("/api/posts", response_model=list[PostResponse]) # A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed. The response_model parameter specifies that the response will be a list of PostResponse objects.
def get_posts(db: Annotated[Session, Depends(get_db)]): # this is an api endpoint that returns a list of all posts. The response_model parameter in the decorator specifies that the response will be a list of PostResponse objects, which is a Pydantic model defined in schemas.py. This means that FastAPI will automatically validate and serialize the response data to match the PostResponse model.
    result = db.execute(select(models.Post))
    posts = result.scalars().all()
    return posts

@app.post( # A post request is what we use to create resources. In this case, we are creating a new post. The decorator defines a POST endpoint at the URL
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)

def create_post(post: PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.User).where(models.User.id == post.user_id))
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
    db.commit()
    db.refresh(new_post)
    return new_post

@app.get("/api/posts/{post_id}", response_model=PostResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]): # this is an api endpoint that returns a single post based on the provided post_id. The post_id is extracted from the URL and passed as an argument to the function.
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if post:
        return post
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, 
        detail="Post not found",
    )

@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"): # JSON response for API requests
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
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
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
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