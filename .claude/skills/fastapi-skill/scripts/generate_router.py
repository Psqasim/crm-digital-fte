#!/usr/bin/env python3
"""
FastAPI Router Generator - Creates CRUD router files

Usage:
    generate_router.py <resource_name> --path <output_path>
    generate_router.py tasks --path src/routers/
    generate_router.py users --path src/routers/ --with-schema

Examples:
    python scripts/generate_router.py tasks --path src/routers/
    python scripts/generate_router.py users --path src/routers/ --with-schema
"""

import sys
import argparse
from pathlib import Path


ROUTER_TEMPLATE = '''"""
{resource_title} Router

CRUD operations for {resource}.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Annotated
{schema_import}

router = APIRouter(
    prefix="/{resource}",
    tags=["{resource_title}"],
    responses={{404: {{"description": "{singular_title} not found"}}}},
)


# Dependency for common query parameters
async def common_parameters(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of items to return"),
):
    return {{"skip": skip, "limit": limit}}


CommonParams = Annotated[dict, Depends(common_parameters)]


@router.get("/", response_model=list[{singular_title}Response])
async def list_{resource}(params: CommonParams):
    """
    List all {resource}.

    - **skip**: Number of items to skip (pagination)
    - **limit**: Maximum number of items to return
    """
    # TODO: Implement listing logic with pagination
    # Example: return await service.list_{resource}(skip=params["skip"], limit=params["limit"])
    return []


@router.get("/{{item_id}}", response_model={singular_title}Response)
async def get_{singular}(item_id: int):
    """
    Get a specific {singular} by ID.

    - **item_id**: The unique identifier of the {singular}
    """
    # TODO: Implement get logic
    # Example: {singular} = await service.get_{singular}(item_id)
    # if not {singular}:
    #     raise HTTPException(status_code=404, detail="{singular_title} not found")
    # return {singular}
    raise HTTPException(status_code=404, detail="{singular_title} not found")


@router.post("/", response_model={singular_title}Response, status_code=201)
async def create_{singular}(data: {singular_title}Create):
    """
    Create a new {singular}.

    - **data**: {singular_title} creation payload
    """
    # TODO: Implement create logic
    # Example: return await service.create_{singular}(data)
    return {{"id": 1, **data.model_dump()}}


@router.put("/{{item_id}}", response_model={singular_title}Response)
async def update_{singular}(item_id: int, data: {singular_title}Update):
    """
    Update an existing {singular}.

    - **item_id**: The unique identifier of the {singular}
    - **data**: Fields to update (all optional)
    """
    # TODO: Implement update logic
    # Example:
    # {singular} = await service.update_{singular}(item_id, data)
    # if not {singular}:
    #     raise HTTPException(status_code=404, detail="{singular_title} not found")
    # return {singular}
    raise HTTPException(status_code=404, detail="{singular_title} not found")


@router.patch("/{{item_id}}", response_model={singular_title}Response)
async def partial_update_{singular}(item_id: int, data: {singular_title}Update):
    """
    Partially update a {singular}.

    Same as PUT but semantically for partial updates.
    """
    return await update_{singular}(item_id, data)


@router.delete("/{{item_id}}", status_code=204)
async def delete_{singular}(item_id: int):
    """
    Delete a {singular}.

    - **item_id**: The unique identifier of the {singular} to delete
    """
    # TODO: Implement delete logic
    # Example:
    # success = await service.delete_{singular}(item_id)
    # if not success:
    #     raise HTTPException(status_code=404, detail="{singular_title} not found")
    return None
'''


SCHEMA_TEMPLATE = '''"""
{resource_title} Schemas

Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class {singular_title}Base(BaseModel):
    """Base schema with shared attributes."""
    title: str = Field(..., min_length=1, max_length=200, description="Title of the {singular}")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")


class {singular_title}Create({singular_title}Base):
    """Schema for creating a new {singular}."""
    pass


class {singular_title}Update(BaseModel):
    """Schema for updating a {singular}. All fields are optional."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)


class {singular_title}Response({singular_title}Base):
    """Schema for {singular} responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {{"from_attributes": True}}


class {singular_title}ListResponse(BaseModel):
    """Schema for paginated list responses."""
    items: list[{singular_title}Response]
    total: int
    skip: int
    limit: int
'''


def singularize(word: str) -> str:
    """Simple singularization (removes trailing 's')."""
    if word.endswith("ies"):
        return word[:-3] + "y"
    elif word.endswith("es"):
        return word[:-2]
    elif word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def to_title_case(word: str) -> str:
    """Convert to TitleCase."""
    return word.replace("_", " ").title().replace(" ", "")


def main():
    parser = argparse.ArgumentParser(
        description="Generate FastAPI router with CRUD operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("resource",
                        help="Resource name in plural (e.g., 'tasks', 'users')")
    parser.add_argument("--path", "-p", type=str, required=True,
                        help="Output path for the router file")
    parser.add_argument("--with-schema", "-s", action="store_true",
                        help="Also generate schema file")

    args = parser.parse_args()

    resource = args.resource.lower()
    singular = singularize(resource)
    resource_title = to_title_case(resource)
    singular_title = to_title_case(singular)

    output_path = Path(args.path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate router
    schema_import = f"from ..schemas.{resource} import {singular_title}Create, {singular_title}Update, {singular_title}Response"

    router_content = ROUTER_TEMPLATE.format(
        resource=resource,
        singular=singular,
        resource_title=resource_title,
        singular_title=singular_title,
        schema_import=schema_import
    )

    router_file = output_path / f"{resource}.py"
    router_file.write_text(router_content)
    print(f"Created router: {router_file}")

    # Generate schema if requested
    if args.with_schema:
        schema_path = output_path.parent / "schemas"
        schema_path.mkdir(parents=True, exist_ok=True)

        schema_content = SCHEMA_TEMPLATE.format(
            resource=resource,
            singular=singular,
            resource_title=resource_title,
            singular_title=singular_title
        )

        schema_file = schema_path / f"{resource}.py"
        schema_file.write_text(schema_content)
        print(f"Created schema: {schema_file}")

    print("\nNext steps:")
    print(f"1. Add router to main.py: from .routers import {resource}")
    print(f"2. Include router: app.include_router({resource}.router, prefix='/api/v1')")
    print("3. Implement the TODO logic in each endpoint")
    print("4. Add tests for the new endpoints")


if __name__ == "__main__":
    main()
