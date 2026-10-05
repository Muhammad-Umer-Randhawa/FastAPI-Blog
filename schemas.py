from pydantic import BaseModel, ConfigDict, Field # base model: the base class all out pydantic models inherit form. Field lets us add constraints like minimum and maximum. ConfigDict is the modern pydantic version 2 way to configure models

class PostBase(BaseModel): # this is going to be what is shared between both creating and returning posts
    title: str = Field(min_length=1, max_length=100) # we are using Field to add constraints to the title field. It must be at least 1 character long and no more than 100 characters long.
    content: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=50)

# below is the post create schema
class PostCreate(PostBase): # this is going to be what is used when creating a post. It inherits from PostBase, so it has the same fields and constraints.
    pass

class PostResponse(PostBase): # this is going to be what is used when returning a post. It inherits from PostBase, so it has the same fields and constraints.
    id: int
    date_posted: str

    model_config = ConfigDict(from_attributes=True) # this is a pydantic v2 feature that allows us to tell pydantic to read data from attributes of an object instead of just from dictionaries. This is useful when we are working with ORM models like SQLAlchemy, which return objects instead of dictionaries.
    