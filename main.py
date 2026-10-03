from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

@app.get("/api/posts") # A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed.
def get_posts():
    return posts  