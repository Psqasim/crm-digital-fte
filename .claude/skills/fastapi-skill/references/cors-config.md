# CORS Configuration

## Overview

CORS (Cross-Origin Resource Sharing) allows your FastAPI backend to accept requests from frontend applications running on different origins (domains, ports, or protocols).

## Basic Setup

### Development Configuration

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Development: Allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js default
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production Configuration

```python
from src.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # From environment
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Environment-Based Config

```python
# src/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    cors_origins: list[str] = [
        "http://localhost:3000",  # Next.js dev
        "http://localhost:5173",  # Vite dev
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        env_file = ".env"

# .env
CORS_ORIGINS=["https://myapp.com","https://admin.myapp.com"]
```

## Configuration Options

### allow_origins

```python
# Specific origins (recommended for production)
allow_origins=["https://myapp.com", "https://admin.myapp.com"]

# Allow all origins (development only!)
allow_origins=["*"]

# WARNING: Cannot use "*" with credentials=True
# This will fail:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,  # Error!
)
```

### allow_origin_regex

```python
# Match multiple subdomains
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.myapp\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Matches: https://app.myapp.com, https://admin.myapp.com
```

### allow_methods

```python
# Specific methods
allow_methods=["GET", "POST", "PUT", "DELETE"]

# All methods
allow_methods=["*"]

# Read-only API
allow_methods=["GET", "OPTIONS"]
```

### allow_headers

```python
# Specific headers
allow_headers=["Authorization", "Content-Type", "X-Request-ID"]

# All headers
allow_headers=["*"]
```

### expose_headers

```python
# Headers the browser can access from response
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    expose_headers=["X-Total-Count", "X-Page", "X-Request-ID"],
)

# Frontend can now read these headers:
# response.headers.get("X-Total-Count")
```

### max_age

```python
# Cache preflight response for 1 hour
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    max_age=3600,  # seconds
)
```

## Complete Production Setup

```python
# src/middleware/cors.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

def setup_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""

    if settings.debug:
        # Development: permissive
        origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
        ]
    else:
        # Production: strict
        origins = settings.cors_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "X-API-Key",
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Page",
            "X-Request-ID",
        ],
        max_age=600,  # 10 minutes
    )

# src/main.py
from src.middleware.cors import setup_cors

app = FastAPI()
setup_cors(app)
```

## Integration with Next.js

### Next.js Fetch Configuration

```typescript
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchTasks() {
  const response = await fetch(`${API_URL}/api/v1/tasks`, {
    credentials: "include",  // Send cookies
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch tasks");
  }

  return response.json();
}

export async function createTask(data: TaskCreate) {
  const response = await fetch(`${API_URL}/api/v1/tasks`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to create task");
  }

  return response.json();
}
```

### With Authentication Token

```typescript
// lib/api.ts
export async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = getAccessToken();  // From your auth state

  const response = await fetch(`${API_URL}${url}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  return response;
}
```

## Debugging CORS Issues

### Common Errors

```
Access to fetch at 'http://localhost:8000/api/tasks'
from origin 'http://localhost:3000' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present.
```

**Solution:** Add the frontend origin to `allow_origins`

```
Access to fetch at 'http://localhost:8000/api/tasks'
from origin 'http://localhost:3000' has been blocked by CORS policy:
The value of the 'Access-Control-Allow-Credentials' header in the response
is '' which must be 'true' when the request's credentials mode is 'include'.
```

**Solution:** Set `allow_credentials=True` and ensure origin is not `"*"`

### Debug Middleware

```python
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class CORSDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"Origin: {request.headers.get('origin')}")
        print(f"Method: {request.method}")

        response = await call_next(request)

        print(f"ACAO: {response.headers.get('access-control-allow-origin')}")
        print(f"ACAC: {response.headers.get('access-control-allow-credentials')}")

        return response

# Add before CORS middleware for debugging
app.add_middleware(CORSDebugMiddleware)
```

### Verify Configuration

```python
@app.get("/cors-test")
async def cors_test():
    """Endpoint to verify CORS is working."""
    return {"cors": "enabled", "message": "If you see this, CORS is configured correctly"}
```

```typescript
// Test from browser console
fetch("http://localhost:8000/cors-test", { credentials: "include" })
  .then(r => r.json())
  .then(console.log)
  .catch(console.error);
```

## Security Considerations

### Don't Use Wildcards in Production

```python
# BAD: Too permissive
allow_origins=["*"]
allow_headers=["*"]
allow_methods=["*"]

# GOOD: Explicit whitelist
allow_origins=["https://myapp.com"]
allow_headers=["Authorization", "Content-Type"]
allow_methods=["GET", "POST", "PUT", "DELETE"]
```

### Validate Origins

```python
from urllib.parse import urlparse

def is_valid_origin(origin: str) -> bool:
    """Validate origin against whitelist."""
    allowed_hosts = ["myapp.com", "admin.myapp.com"]
    parsed = urlparse(origin)
    return parsed.hostname in allowed_hosts

# Dynamic origin validation
class DynamicCORSMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()

            if origin and is_valid_origin(origin):
                # Allow this origin
                pass
```

### Environment-Specific Config

```python
# config.py
class Settings(BaseSettings):
    environment: str = "development"

    @property
    def cors_origins(self) -> list[str]:
        if self.environment == "development":
            return [
                "http://localhost:3000",
                "http://localhost:5173",
            ]
        elif self.environment == "staging":
            return ["https://staging.myapp.com"]
        else:  # production
            return ["https://myapp.com", "https://www.myapp.com"]
```

## Multiple Frontends

```python
# Supporting multiple frontend apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.mycompany.com",      # Main app
        "https://admin.mycompany.com",    # Admin panel
        "https://mobile.mycompany.com",   # Mobile web
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
