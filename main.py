from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI() 

# this 'app' object is used to define all of our routes and configurations for the
# FastAPI application. It serves as the main entry point for the application, allowing
# us to define endpoints, middleware, and other settings.

posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
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

@app.get("/", response_class = HTMLResponse, include_in_schema=False) ## A decorator that defines a GET endpoint at the root URL ("/"). When a client sends a GET request to this URL, the associated function will be executed.
@app.get("/posts", response_class = HTMLResponse, include_in_schema=False) # the route still works in the browser but it wont appear in the api documentation if we used 'include_in_schema = False'
def home():
    return f"<h1>{posts[0]['title']}</h1>"

@app.get("/api/posts") ## A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed.
def get_posts():
    return posts  