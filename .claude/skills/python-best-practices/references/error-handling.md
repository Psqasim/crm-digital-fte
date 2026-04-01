# Error Handling Patterns

## Table of Contents
- [Exception Hierarchy](#exception-hierarchy)
- [When to Catch vs Propagate](#when-to-catch-vs-propagate)
- [Result Pattern](#result-pattern)
- [Logging Best Practices](#logging-best-practices)

## Exception Hierarchy

### Design Custom Exceptions

```python
class AppError(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    """Invalid input data."""

    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}", code="VALIDATION_ERROR")


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: str | int) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(
            f"{resource} with id '{identifier}' not found",
            code="NOT_FOUND"
        )


class ConflictError(AppError):
    """State conflict (e.g., duplicate, already exists)."""
    pass


class AuthorizationError(AppError):
    """Permission denied."""
    pass
```

### Hierarchy Structure

```
Exception
└── AppError (base)
    ├── ValidationError   # 400 Bad Request
    ├── NotFoundError     # 404 Not Found
    ├── ConflictError     # 409 Conflict
    ├── AuthorizationError # 403 Forbidden
    └── InternalError     # 500 Internal Server Error
```

## When to Catch vs Propagate

### Catch When You Can Handle

```python
def get_user_safely(user_id: int) -> User | None:
    """Catch and handle - return None instead of raising."""
    try:
        return repository.get(user_id)
    except NotFoundError:
        return None  # Handled: returning None is valid response


def process_with_fallback(data: dict) -> Result:
    """Catch and handle - use fallback value."""
    try:
        return expensive_operation(data)
    except TimeoutError:
        logger.warning("Operation timed out, using cached value")
        return get_cached_result()  # Handled: using fallback
```

### Propagate When Caller Should Decide

```python
def get_user(user_id: int) -> User:
    """Propagate - let caller decide how to handle."""
    user = repository.get(user_id)
    if not user:
        raise NotFoundError("User", user_id)
    return user


def process_payment(payment: Payment) -> Receipt:
    """Propagate - caller must handle failures."""
    if not payment.is_valid():
        raise ValidationError("payment", "Invalid payment data")
    return gateway.charge(payment)  # May raise PaymentError
```

### Transform at Boundaries

```python
# API boundary - transform to HTTP response
@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_codes = {
        "VALIDATION_ERROR": 400,
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "UNAUTHORIZED": 403,
    }
    return JSONResponse(
        status_code=status_codes.get(exc.code, 500),
        content={"error": exc.message, "code": exc.code}
    )
```

## Result Pattern

Alternative to exceptions for expected failures.

### Simple Result Type

```python
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Ok(Generic[T]):
    value: T


@dataclass
class Err(Generic[E]):
    error: E


Result = Ok[T] | Err[E]
```

### Usage

```python
def divide(a: float, b: float) -> Result[float, str]:
    if b == 0:
        return Err("Division by zero")
    return Ok(a / b)


def process(data: dict) -> Result[Output, ValidationError]:
    if not data.get("required_field"):
        return Err(ValidationError("required_field", "is required"))
    return Ok(Output(**data))


# Caller handles both cases explicitly
match divide(10, 0):
    case Ok(value):
        print(f"Result: {value}")
    case Err(error):
        print(f"Error: {error}")
```

### When to Use Result vs Exceptions

| Use Result | Use Exceptions |
|------------|----------------|
| Expected failure paths | Unexpected errors |
| Caller must handle | Error can propagate |
| Performance-critical | Rare conditions |
| Multiple error types returned | Single error type |

## Logging Best Practices

### Structured Logging with structlog

```python
import structlog

logger = structlog.get_logger()

def process_task(task_id: int, user_id: int) -> Task:
    log = logger.bind(task_id=task_id, user_id=user_id)

    log.info("processing_started")

    try:
        task = repository.get(task_id)
        if not task:
            log.warning("task_not_found")
            raise NotFoundError("Task", task_id)

        result = do_processing(task)
        log.info("processing_completed", result_status=result.status)
        return result

    except ValidationError as e:
        log.warning("validation_failed", field=e.field, error=e.message)
        raise

    except Exception as e:
        log.exception("unexpected_error")  # Includes traceback
        raise
```

### Log Levels

| Level | When to Use |
|-------|-------------|
| DEBUG | Detailed diagnostic info |
| INFO | Normal operations, milestones |
| WARNING | Recoverable issues, degraded state |
| ERROR | Failures requiring attention |
| CRITICAL | System-wide failures |

### What to Log

```python
# Good: Context-rich, searchable
logger.info(
    "order_created",
    order_id=order.id,
    user_id=user.id,
    total=order.total,
    items_count=len(order.items),
)

# Bad: String interpolation, not searchable
logger.info(f"Created order {order.id} for user {user.id}")
```

### Error Logging Pattern

```python
def safe_operation(data: dict) -> Result:
    correlation_id = generate_correlation_id()
    log = logger.bind(correlation_id=correlation_id)

    try:
        result = risky_operation(data)
        log.info("operation_succeeded")
        return result

    except ValidationError as e:
        # Expected error - warning level, no traceback
        log.warning("validation_error", field=e.field, message=e.message)
        raise

    except Exception as e:
        # Unexpected error - error level, include traceback
        log.exception("unexpected_error", error_type=type(e).__name__)
        raise InternalError(
            f"Operation failed. Reference: {correlation_id}"
        ) from e
```

### Sensitive Data

```python
# Never log sensitive data
logger.info(
    "user_login",
    user_id=user.id,
    email=user.email,
    # password=user.password,  # NEVER
    # token=auth_token,        # NEVER
    # credit_card=card_number, # NEVER
)

# Mask if needed
def mask_email(email: str) -> str:
    name, domain = email.split("@")
    return f"{name[:2]}***@{domain}"

logger.info("user_login", email=mask_email(user.email))
```
