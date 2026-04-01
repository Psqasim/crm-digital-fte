# SOLID Principles in Python

## Table of Contents
- [Single Responsibility](#single-responsibility-srp)
- [Open/Closed](#openclosed-ocp)
- [Liskov Substitution](#liskov-substitution-lsp)
- [Interface Segregation](#interface-segregation-isp)
- [Dependency Inversion](#dependency-inversion-dip)

## Single Responsibility (SRP)

A class should have only one reason to change.

### Bad: Multiple Responsibilities

```python
class UserService:
    def create_user(self, data: dict) -> User:
        # Validates data
        # Creates user in database
        # Sends welcome email
        # Logs the action
        pass
```

### Good: Separate Concerns

```python
class UserValidator:
    def validate(self, data: dict) -> dict:
        """Only validates user data."""
        ...

class UserRepository:
    def save(self, user: User) -> User:
        """Only handles database operations."""
        ...

class EmailService:
    def send_welcome(self, user: User) -> None:
        """Only handles email sending."""
        ...

class UserService:
    def __init__(
        self,
        validator: UserValidator,
        repository: UserRepository,
        email: EmailService,
    ) -> None:
        self._validator = validator
        self._repository = repository
        self._email = email

    def create_user(self, data: dict) -> User:
        """Orchestrates user creation."""
        validated = self._validator.validate(data)
        user = User(**validated)
        saved = self._repository.save(user)
        self._email.send_welcome(saved)
        return saved
```

## Open/Closed (OCP)

Open for extension, closed for modification.

### Bad: Modifying Existing Code

```python
class PaymentProcessor:
    def process(self, payment_type: str, amount: float) -> bool:
        if payment_type == "credit_card":
            return self._process_credit_card(amount)
        elif payment_type == "paypal":
            return self._process_paypal(amount)
        # Adding new payment type requires modifying this class
```

### Good: Extend via Abstraction

```python
from abc import ABC, abstractmethod

class PaymentMethod(ABC):
    @abstractmethod
    def process(self, amount: float) -> bool:
        pass

class CreditCardPayment(PaymentMethod):
    def process(self, amount: float) -> bool:
        # Credit card logic
        return True

class PayPalPayment(PaymentMethod):
    def process(self, amount: float) -> bool:
        # PayPal logic
        return True

# New payment method - no modification to existing code
class CryptoPayment(PaymentMethod):
    def process(self, amount: float) -> bool:
        # Crypto logic
        return True

class PaymentProcessor:
    def process(self, method: PaymentMethod, amount: float) -> bool:
        return method.process(amount)
```

## Liskov Substitution (LSP)

Subtypes must be substitutable for their base types.

### Bad: Violating Base Contract

```python
class Bird:
    def fly(self) -> None:
        print("Flying")

class Penguin(Bird):
    def fly(self) -> None:
        raise NotImplementedError("Penguins can't fly!")  # Violates LSP
```

### Good: Proper Abstraction

```python
class Bird(ABC):
    @abstractmethod
    def move(self) -> None:
        pass

class FlyingBird(Bird):
    def move(self) -> None:
        print("Flying")

class SwimmingBird(Bird):
    def move(self) -> None:
        print("Swimming")

class Eagle(FlyingBird):
    pass

class Penguin(SwimmingBird):
    pass

# Both can be used wherever Bird is expected
def exercise_bird(bird: Bird) -> None:
    bird.move()  # Works for all birds
```

## Interface Segregation (ISP)

Clients shouldn't depend on interfaces they don't use.

### Bad: Fat Interface

```python
class Worker(ABC):
    @abstractmethod
    def work(self) -> None: ...

    @abstractmethod
    def eat(self) -> None: ...

    @abstractmethod
    def sleep(self) -> None: ...

class Robot(Worker):
    def work(self) -> None:
        print("Working")

    def eat(self) -> None:
        pass  # Robots don't eat - forced to implement

    def sleep(self) -> None:
        pass  # Robots don't sleep - forced to implement
```

### Good: Segregated Interfaces

```python
class Workable(Protocol):
    def work(self) -> None: ...

class Eatable(Protocol):
    def eat(self) -> None: ...

class Sleepable(Protocol):
    def sleep(self) -> None: ...

class Human:
    def work(self) -> None:
        print("Working")

    def eat(self) -> None:
        print("Eating")

    def sleep(self) -> None:
        print("Sleeping")

class Robot:
    def work(self) -> None:
        print("Working")

# Functions accept only what they need
def assign_work(worker: Workable) -> None:
    worker.work()

def schedule_lunch(eater: Eatable) -> None:
    eater.eat()
```

## Dependency Inversion (DIP)

Depend on abstractions, not concretions.

### Bad: Depending on Concrete Classes

```python
class MySQLDatabase:
    def query(self, sql: str) -> list:
        ...

class UserRepository:
    def __init__(self) -> None:
        self._db = MySQLDatabase()  # Hard dependency

    def get_user(self, user_id: int) -> User:
        return self._db.query(f"SELECT * FROM users WHERE id = {user_id}")
```

### Good: Depend on Abstractions

```python
class Database(Protocol):
    def query(self, sql: str) -> list: ...

class MySQLDatabase:
    def query(self, sql: str) -> list:
        ...

class PostgresDatabase:
    def query(self, sql: str) -> list:
        ...

class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db  # Depends on abstraction

    def get_user(self, user_id: int) -> User:
        return self._db.query(f"SELECT * FROM users WHERE id = {user_id}")

# Easy to swap implementations
repo_mysql = UserRepository(MySQLDatabase())
repo_postgres = UserRepository(PostgresDatabase())
```

## Combined Example

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Abstractions (ISP - segregated interfaces)
class TaskRepository(Protocol):
    def save(self, task: Task) -> Task: ...
    def get(self, task_id: int) -> Task | None: ...

class NotificationService(Protocol):
    def notify(self, user_id: int, message: str) -> None: ...

# Implementations (OCP - can add new ones without changing existing)
class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[int, Task] = {}

    def save(self, task: Task) -> Task:
        self._tasks[task.id] = task
        return task

    def get(self, task_id: int) -> Task | None:
        return self._tasks.get(task_id)

class EmailNotification:
    def notify(self, user_id: int, message: str) -> None:
        # Send email
        pass

# Service (SRP - only orchestrates, DIP - depends on abstractions)
class TaskService:
    def __init__(
        self,
        repo: TaskRepository,
        notifications: NotificationService,
    ) -> None:
        self._repo = repo
        self._notifications = notifications

    def complete_task(self, task_id: int, user_id: int) -> Task:
        task = self._repo.get(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        task.completed = True
        saved = self._repo.save(task)
        self._notifications.notify(user_id, f"Task {task_id} completed")
        return saved
```
