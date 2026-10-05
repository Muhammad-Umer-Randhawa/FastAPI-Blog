from fastapi import FastAPI, Request, HTTPException, status
from fastapi.exceptions import RequestValidationError # for handling validation error like when someone passes hello instead of an integer when we are expecting an integer
from fastapi.responses import JSONResponse # to manually return JSON responses from our endpoints, especially in error handling scenarios.
from starlette.exceptions import HTTPException as StarletteHTTPException 
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from schemas import PostResponse, PostCreate # importing the pydantic models we created in schemas.py

# Pydantic: It is a data validation and settings management library for Python, based on Python type annotations/ type hints. It is used in FastAPI to define data models and validate incoming request data.

app = FastAPI() 
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory = "templates")

# this 'app' object is used to define all of our routes and configurations for the
# FastAPI application. It serves as the main entry point for the application, allowing
# us to define endpoints, middleware, and other settings.

posts: list[dict] = [
    {
        "id": 1,
        "author": "John Doe",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

# General pattern: server-side rendering (SSR)
# 1. Route function gathers/builds data (e.g. the 'posts' list)
# 2. Jinja2Templates renders an HTML file from templates/, injecting that data
# 3. Final HTML (not raw data) is sent back to the browser
# Same pattern exists in Flask, Django, Express, Rails, etc. — just different syntax.

@app.get("/", include_in_schema=False, name = "home") # A decorator that defines a GET endpoint at the root URL ("/"). When a client sends a GET request to this URL, the associated function will be executed.
@app.get("/posts", include_in_schema=False, name = "posts") # the route still works in the browser but it wont appear in the api documentation if we used 'include_in_schema = False'
def home(request: Request):
    return templates.TemplateResponse(
        request, 
        "home.html", 
        {"posts": posts, "title": "Home"},
    ) 
# This line renders the "home.html" template and injects the 'posts' list into it. The 'request' object is also passed to the template, which is necessary for Jinja2 to function properly.
@app.get("/posts/{post_id}", include_in_schema=False, name = "post") 
def post_page(request: Request, post_id: int): 
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:100]
            return templates.TemplateResponse(
                request, 
                "post.html", 
                {"post": post, "title": title},
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Post with id {post_id} not found",
    )
@app.get("/api/posts", response_model=list[PostResponse])  # A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed. The response_model parameter specifies that the response will be a list of PostResponse objects.
def get_posts(): # this is an api endpoint that returns a list of all posts. The response_model parameter in the decorator specifies that the response will be a list of PostResponse objects, which is a Pydantic model defined in schemas.py. This means that FastAPI will automatically validate and serialize the response data to match the PostResponse model.
    return posts

@app.post( # A post request is what we use to create resources. In this case, we are creating a new post. The decorator defines a POST endpoint at the URL
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id": new_id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "date_posted": "April 23, 2025",
    }
    posts.append(new_post)
    return new_post

@app.get("/api/posts/{post_id}", response_model=PostResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
def get_post(post_id: int): # this is an api endpoint that returns a single post based on the provided post_id. The post_id is extracted from the URL and passed as an argument to the function.
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Post with id {post_id} not found",
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