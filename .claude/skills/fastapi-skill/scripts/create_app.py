#!/usr/bin/env python3
"""
FastAPI App Generator - Creates a structured FastAPI application

Usage:
    create_app.py <app_name> --path <output_path>
    create_app.py todo_api --path src/
    create_app.py my_service --path . --with-db

Examples:
    python scripts/create_app.py todo_api --path src/
    python scripts/create_app.py user_service --path . --with-db --with-auth
"""

import sys
import argparse
from pathlib import Path


MAIN_TEMPLATE = '''"""
{app_title} - FastAPI Application

Generated with fastapi-skill
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
{db_import}
from .config import settings
from .routers import {router_import}


app = FastAPI(
    title="{app_title}",
    description="{app_description}",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{db_lifespan}
# Include routers
app.include_router({router_include})


@app.get("/")
async def root():
    """Root endpoint."""
    return {{"message": "Welcome to {app_title}", "docs": "/docs"}}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {{"status": "healthy", "version": "1.0.0"}}
'''


CONFIG_TEMPLATE = '''"""
Application Configuration

Uses pydantic-settings for environment variable management.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "{app_name}"
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    {db_config}

    model_config = {{
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
'''


ROUTER_TEMPLATE = '''"""
{router_title} Router

Handles {router_description}
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated
{schema_import}

router = APIRouter(
    prefix="/{router_prefix}",
    tags=["{router_tag}"],
)


@router.get("/")
async def list_{resource}():
    """List all {resource}."""
    # TODO: Implement listing logic
    return []


@router.get("/{{item_id}}")
async def get_{singular}(item_id: int):
    """Get a specific {singular} by ID."""
    # TODO: Implement get logic
    raise HTTPException(status_code=404, detail="{singular_title} not found")


@router.post("/", status_code=201)
async def create_{singular}():
    """Create a new {singular}."""
    # TODO: Implement create logic
    return {{"id": 1, "message": "{singular_title} created"}}


@router.put("/{{item_id}}")
async def update_{singular}(item_id: int):
    """Update an existing {singular}."""
    # TODO: Implement update logic
    return {{"id": item_id, "message": "{singular_title} updated"}}


@router.delete("/{{item_id}}", status_code=204)
async def delete_{singular}(item_id: int):
    """Delete a {singular}."""
    # TODO: Implement delete logic
    return None
'''


SCHEMAS_TEMPLATE = '''"""
Pydantic Schemas for {resource_title}

Request and response models for API validation.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class {singular_title}Base(BaseModel):
    """Base schema with shared fields."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class {singular_title}Create({singular_title}Base):
    """Schema for creating a new {singular}."""
    pass


class {singular_title}Update(BaseModel):
    """Schema for updating a {singular}. All fields optional."""
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None


class {singular_title}Response({singular_title}Base):
    """Schema for {singular} responses."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {{"from_attributes": True}}


class {singular_title}List(BaseModel):
    """Schema for list of {resource}."""
    items: list[{singular_title}Response]
    total: int
'''


DATABASE_TEMPLATE = '''"""
Database Configuration

SQLModel async database setup.
"""

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from .config import settings


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with async_session() as session:
        yield session
'''


INIT_TEMPLATE = '''"""
{package_name} Package
"""

from .main import app

__all__ = ["app"]
'''


def create_app_structure(app_name: str, output_path: Path, with_db: bool, with_auth: bool):
    """Create the FastAPI app directory structure."""
    app_dir = output_path / app_name

    # Create directories
    (app_dir / "routers").mkdir(parents=True, exist_ok=True)
    (app_dir / "schemas").mkdir(parents=True, exist_ok=True)
    (app_dir / "services").mkdir(parents=True, exist_ok=True)
    if with_db:
        (app_dir / "models").mkdir(parents=True, exist_ok=True)

    app_title = app_name.replace("_", " ").title()

    # Create main.py
    db_import = "from .database import init_db, get_session" if with_db else ""
    db_lifespan = """
@app.on_event("startup")
async def on_startup():
    await init_db()
""" if with_db else ""

    main_content = MAIN_TEMPLATE.format(
        app_title=app_title,
        app_description=f"API for {app_title}",
        db_import=db_import,
        db_lifespan=db_lifespan,
        router_import="items",
        router_include="items.router, prefix='/api/v1'"
    )
    (app_dir / "main.py").write_text(main_content)

    # Create config.py
    db_config = '''# Database
    database_url: str = "postgresql+asyncpg://user:password@localhost/dbname"''' if with_db else ""

    config_content = CONFIG_TEMPLATE.format(
        app_name=app_name,
        db_config=db_config
    )
    (app_dir / "config.py").write_text(config_content)

    # Create routers/__init__.py and items.py
    (app_dir / "routers" / "__init__.py").write_text('from . import items\n\n__all__ = ["items"]\n')

    router_content = ROUTER_TEMPLATE.format(
        router_title="Items",
        router_description="item CRUD operations",
        router_prefix="items",
        router_tag="Items",
        resource="items",
        singular="item",
        singular_title="Item",
        schema_import="from ..schemas.items import ItemCreate, ItemUpdate, ItemResponse"
    )
    (app_dir / "routers" / "items.py").write_text(router_content)

    # Create schemas/__init__.py and items.py
    (app_dir / "schemas" / "__init__.py").write_text('from .items import *\n')

    schemas_content = SCHEMAS_TEMPLATE.format(
        resource_title="Items",
        singular="item",
        singular_title="Item"
    )
    (app_dir / "schemas" / "items.py").write_text(schemas_content)

    # Create services/__init__.py
    (app_dir / "services" / "__init__.py").write_text('# Service layer modules\n')

    # Create database.py if needed
    if with_db:
        (app_dir / "database.py").write_text(DATABASE_TEMPLATE)
        (app_dir / "models" / "__init__.py").write_text('# SQLModel database models\n')

    # Create __init__.py
    init_content = INIT_TEMPLATE.format(package_name=app_name)
    (app_dir / "__init__.py").write_text(init_content)

    return app_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate FastAPI application structure",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument("app_name",
                        help="Name of the application (snake_case)")
    parser.add_argument("--path", "-p", type=str, default=".",
                        help="Output path for the app directory")
    parser.add_argument("--with-db", action="store_true",
                        help="Include database configuration")
    parser.add_argument("--with-auth", action="store_true",
                        help="Include authentication setup")

    args = parser.parse_args()

    output_path = Path(args.path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create the app structure
    app_dir = create_app_structure(
        args.app_name,
        output_path,
        args.with_db,
        args.with_auth
    )

    print(f"Created FastAPI app: {app_dir}")
    print("\nGenerated structure:")
    for path in sorted(app_dir.rglob("*")):
        if path.is_file():
            rel_path = path.relative_to(app_dir)
            print(f"  {rel_path}")

    print("\nNext steps:")
    print(f"1. cd {app_dir}")
    print("2. Install dependencies: pip install fastapi uvicorn pydantic-settings")
    if args.with_db:
        print("3. Install DB deps: pip install sqlmodel sqlalchemy[asyncio] asyncpg")
    print(f"4. Run: uvicorn {args.app_name}.main:app --reload")


if __name__ == "__main__":
    main()
