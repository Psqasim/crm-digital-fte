# React 19 Patterns

## Overview

React 19 introduces new patterns for:
- Form handling with Server Actions
- Pending states with transitions
- Optimistic updates
- Enhanced hooks

## useFormStatus

### Purpose

Get the pending state of a form submission (must be used in a child component of `<form>`).

### Implementation

```tsx
// components/SubmitButton.tsx
"use client";

import { useFormStatus } from "react-dom";

export function SubmitButton({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();

  return (
    <button type="submit" disabled={pending}>
      {pending ? "Submitting..." : children}
    </button>
  );
}

// Usage in form
import { SubmitButton } from "./SubmitButton";

export function TaskForm() {
  return (
    <form action={createTask}>
      <input name="title" placeholder="Task title" />
      <SubmitButton>Add Task</SubmitButton>
    </form>
  );
}
```

### Full Status Object

```tsx
"use client";

import { useFormStatus } from "react-dom";

export function FormStatus() {
  const { pending, data, method, action } = useFormStatus();

  return (
    <div>
      {pending && <span>Submitting...</span>}
      {data && <span>Form data available</span>}
    </div>
  );
}
```

### Input Disabling Pattern

```tsx
"use client";

import { useFormStatus } from "react-dom";

export function FormFields() {
  const { pending } = useFormStatus();

  return (
    <>
      <input
        name="title"
        placeholder="Task title"
        disabled={pending}
        className={pending ? "opacity-50" : ""}
      />
      <textarea
        name="description"
        placeholder="Description"
        disabled={pending}
      />
    </>
  );
}
```

## useActionState

### Purpose

Manage state from Server Action responses, including:
- Previous state
- Form action wrapper
- Pending state

### Basic Usage

```tsx
"use client";

import { useActionState } from "react";
import { createTask } from "./actions";

const initialState = {
  message: "",
  errors: {},
};

export function TaskForm() {
  const [state, formAction, isPending] = useActionState(
    createTask,
    initialState
  );

  return (
    <form action={formAction}>
      <input name="title" placeholder="Task title" />

      {state.errors?.title && (
        <p className="text-red-500">{state.errors.title}</p>
      )}

      {state.message && (
        <p className="text-green-500">{state.message}</p>
      )}

      <button type="submit" disabled={isPending}>
        {isPending ? "Creating..." : "Create Task"}
      </button>
    </form>
  );
}
```

### Server Action with State

```tsx
// actions.ts
"use server";

interface ActionState {
  message: string;
  errors?: {
    title?: string;
    description?: string;
  };
}

export async function createTask(
  prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const title = formData.get("title") as string;

  // Validation
  if (!title || title.length < 1) {
    return {
      message: "",
      errors: { title: "Title is required" },
    };
  }

  try {
    await fetch(`${process.env.API_URL}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title }),
    });

    revalidatePath("/tasks");
    return { message: "Task created successfully" };
  } catch (error) {
    return { message: "Failed to create task" };
  }
}
```

### With Redirect After Success

```tsx
// actions.ts
"use server";

import { redirect } from "next/navigation";

export async function createTask(
  prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  const title = formData.get("title") as string;

  if (!title) {
    return { message: "", errors: { title: "Required" } };
  }

  const response = await fetch(`${process.env.API_URL}/tasks`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });

  const task = await response.json();

  revalidatePath("/tasks");
  redirect(`/tasks/${task.id}`); // Redirect on success
}
```

## useOptimistic

### Purpose

Show optimistic UI updates before server confirms the change.

### Basic Usage

```tsx
"use client";

import { useOptimistic } from "react";
import { toggleTask } from "./actions";

interface Task {
  id: string;
  title: string;
  completed: boolean;
}

export function TaskList({ tasks }: { tasks: Task[] }) {
  const [optimisticTasks, addOptimisticTask] = useOptimistic(
    tasks,
    (currentTasks, { id, completed }: { id: string; completed: boolean }) =>
      currentTasks.map((task) =>
        task.id === id ? { ...task, completed } : task
      )
  );

  async function handleToggle(task: Task) {
    // Optimistic update
    addOptimisticTask({ id: task.id, completed: !task.completed });

    // Server action
    await toggleTask(task.id, !task.completed);
  }

  return (
    <ul>
      {optimisticTasks.map((task) => (
        <li key={task.id}>
          <input
            type="checkbox"
            checked={task.completed}
            onChange={() => handleToggle(task)}
          />
          <span className={task.completed ? "line-through" : ""}>
            {task.title}
          </span>
        </li>
      ))}
    </ul>
  );
}
```

### Optimistic Add

```tsx
"use client";

import { useOptimistic } from "react";
import { createTask } from "./actions";

export function TaskListWithAdd({ tasks }: { tasks: Task[] }) {
  const [optimisticTasks, addOptimisticTask] = useOptimistic(
    tasks,
    (currentTasks, newTask: Task) => [...currentTasks, newTask]
  );

  async function handleCreate(formData: FormData) {
    const title = formData.get("title") as string;

    // Optimistic add with temporary ID
    const optimisticTask: Task = {
      id: `temp-${Date.now()}`,
      title,
      completed: false,
    };
    addOptimisticTask(optimisticTask);

    // Server action
    await createTask(formData);
  }

  return (
    <>
      <form action={handleCreate}>
        <input name="title" placeholder="New task" />
        <button type="submit">Add</button>
      </form>

      <ul>
        {optimisticTasks.map((task) => (
          <li key={task.id} className={task.id.startsWith("temp") ? "opacity-50" : ""}>
            {task.title}
          </li>
        ))}
      </ul>
    </>
  );
}
```

### Optimistic Delete

```tsx
"use client";

import { useOptimistic } from "react";
import { deleteTask } from "./actions";

export function TaskList({ tasks }: { tasks: Task[] }) {
  const [optimisticTasks, removeOptimisticTask] = useOptimistic(
    tasks,
    (currentTasks, taskIdToRemove: string) =>
      currentTasks.filter((task) => task.id !== taskIdToRemove)
  );

  async function handleDelete(taskId: string) {
    // Optimistic remove
    removeOptimisticTask(taskId);

    // Server action
    await deleteTask(taskId);
  }

  return (
    <ul>
      {optimisticTasks.map((task) => (
        <li key={task.id}>
          {task.title}
          <button onClick={() => handleDelete(task.id)}>Delete</button>
        </li>
      ))}
    </ul>
  );
}
```

## useTransition

### Purpose

Mark state updates as non-blocking transitions for better UX.

### Basic Usage

```tsx
"use client";

import { useState, useTransition } from "react";

export function TaskFilter({ onFilter }: { onFilter: (filter: string) => Promise<void> }) {
  const [isPending, startTransition] = useTransition();
  const [filter, setFilter] = useState("all");

  function handleFilterChange(newFilter: string) {
    setFilter(newFilter);

    startTransition(async () => {
      await onFilter(newFilter);
    });
  }

  return (
    <div className={isPending ? "opacity-50" : ""}>
      <select
        value={filter}
        onChange={(e) => handleFilterChange(e.target.value)}
        disabled={isPending}
      >
        <option value="all">All</option>
        <option value="active">Active</option>
        <option value="completed">Completed</option>
      </select>
      {isPending && <span>Loading...</span>}
    </div>
  );
}
```

### With Server Action

```tsx
"use client";

import { useTransition } from "react";
import { updateTaskPriority } from "./actions";

export function PrioritySelector({ taskId, currentPriority }: Props) {
  const [isPending, startTransition] = useTransition();

  function handleChange(priority: string) {
    startTransition(async () => {
      await updateTaskPriority(taskId, priority);
    });
  }

  return (
    <select
      value={currentPriority}
      onChange={(e) => handleChange(e.target.value)}
      disabled={isPending}
      className={isPending ? "opacity-50" : ""}
    >
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
    </select>
  );
}
```

## Form Patterns

### Complete Form Example

```tsx
"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";
import { createTask, type ActionState } from "./actions";

function SubmitButton() {
  const { pending } = useFormStatus();

  return (
    <button
      type="submit"
      disabled={pending}
      className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
    >
      {pending ? "Creating..." : "Create Task"}
    </button>
  );
}

function FormFields() {
  const { pending } = useFormStatus();

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="title" className="block text-sm font-medium">
          Title
        </label>
        <input
          id="title"
          name="title"
          type="text"
          disabled={pending}
          className="mt-1 block w-full rounded border px-3 py-2"
          placeholder="Enter task title"
        />
      </div>

      <div>
        <label htmlFor="description" className="block text-sm font-medium">
          Description
        </label>
        <textarea
          id="description"
          name="description"
          disabled={pending}
          className="mt-1 block w-full rounded border px-3 py-2"
          rows={3}
        />
      </div>

      <div>
        <label htmlFor="priority" className="block text-sm font-medium">
          Priority
        </label>
        <select
          id="priority"
          name="priority"
          disabled={pending}
          className="mt-1 block w-full rounded border px-3 py-2"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
        </select>
      </div>
    </div>
  );
}

const initialState: ActionState = { message: "" };

export function TaskForm() {
  const [state, formAction, isPending] = useActionState(createTask, initialState);

  return (
    <form action={formAction} className="space-y-4">
      <FormFields />

      {state.errors && (
        <div className="text-red-500">
          {Object.entries(state.errors).map(([field, errors]) => (
            <p key={field}>{errors?.join(", ")}</p>
          ))}
        </div>
      )}

      {state.message && (
        <p className={state.errors ? "text-red-500" : "text-green-500"}>
          {state.message}
        </p>
      )}

      <SubmitButton />
    </form>
  );
}
```

## Best Practices

### 1. Separate Submit Button Component

```tsx
// Always create a separate component for useFormStatus
function SubmitButton({ children }: { children: React.ReactNode }) {
  const { pending } = useFormStatus();
  return <button disabled={pending}>{pending ? "..." : children}</button>;
}
```

### 2. Type Your Action State

```tsx
interface ActionState {
  success?: boolean;
  message?: string;
  errors?: Record<string, string[]>;
  data?: unknown;
}
```

### 3. Handle Loading States Gracefully

```tsx
<div className={isPending ? "pointer-events-none opacity-50" : ""}>
  {/* Form content */}
</div>
```

### 4. Combine Patterns

```tsx
// useActionState for form state
// useOptimistic for instant feedback
// useFormStatus for button state
export function OptimisticForm({ items }: { items: Item[] }) {
  const [state, formAction] = useActionState(addItem, initialState);
  const [optimisticItems, addOptimistic] = useOptimistic(items, ...);

  return (
    <form action={async (formData) => {
      addOptimistic({ id: "temp", ...formData });
      await formAction(formData);
    }}>
      <SubmitButton>Add</SubmitButton>
    </form>
  );
}
```
