from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from database import get_db
from schemas import PostCreate, PostResponse, PostUpdate

router = APIRouter()

@router.get("", response_model=list[PostResponse]) # A decorator that defines a GET endpoint at the URL "/api/posts". When a client sends a GET request to this URL, the associated function will be executed. The response_model parameter specifies that the response will be a list of PostResponse objects.
async def get_posts(db: Annotated[AsyncSession, Depends(get_db)]): # this is an api endpoint that returns a list of all posts. The response_model parameter in the decorator specifies that the response will be a list of PostResponse objects, which is a Pydantic model defined in schemas.py. This means that FastAPI will automatically validate and serialize the response data to match the PostResponse model.
    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
    )
    posts = result.scalars().all()
    return posts

@router.post( # A post request is what we use to create resources. In this case, we are creating a new post. The decorator defines a POST endpoint at the URL
    "",
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

@router.get("/{post_id}", response_model=PostResponse)  # A decorator that defines a GET endpoint at the URL "/api/posts/{post_id}". When a client sends a GET request to this URL, the associated function will be executed.
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

@router.put("/{post_id}", response_model=PostResponse)
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

@router.patch("/{post_id}", response_model=PostResponse)
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

@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)  
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