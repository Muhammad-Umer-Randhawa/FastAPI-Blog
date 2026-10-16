from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field # base model: the base class all our pydantic models inherit form. Field lets us add constraints like minimum and maximum. ConfigDict is the modern pydantic version 2 way to configure models

class UserBase(BaseModel): # This is going to be what is shared between UserCreate and UserResponse.
    username: str = Field(min_length=1, max_length=50) # we are using Field to add constraints to the username field. It must be at least 1 character long and no more than 50 characters long.
    email: EmailStr = Field(max_length=120) # we are using EmailStr to validate that the email field is a

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    image_file: str | None
    image_path: str # This is a property on our user model

class UserUpdate(BaseModel):
    username: str | None = Field(default = None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default = None, max_length=120)
    image_file: str | None = Field(default = None, min_length=1, max_length=200)


# PostBase is used for POST
class PostBase(BaseModel): # this is going to be what is shared between both creating and returning posts
    title: str = Field(min_length=1, max_length=100) # we are using Field to add constraints to the title field. It must be at least 1 character long and no more than 100 characters long.
    content: str = Field(min_length=1)

# below is the post create schema
class PostCreate(PostBase): # this is going to be what is used when creating a post. It inherits from PostBase, so it has the same fields and constraints.
    user_id: int # TEMPORARY!!!!

class PostUpdate(BaseModel): # Used for PATCH
    title: str | None = Field(default = None, min_length = 1, max_length=100)
    content: str | None = Field(default = None, min_length=1)

class PostResponse(PostBase): # this is going to be what is used when returning a post. It inherits from PostBase, so it has the same fields and constraints.
    model_config = ConfigDict(from_attributes=True) # this is a pydantic v2 feature that allows us to tell pydantic to read data from attributes of an object instead of just from dictionaries. This is useful when we are working with ORM models like SQLAlchemy, which return objects instead of dictionaries.

    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse # this is a nested schema. It allows us to return the user who created the post along with the post itself. This is useful for displaying the username and profile image of the user who created the post.