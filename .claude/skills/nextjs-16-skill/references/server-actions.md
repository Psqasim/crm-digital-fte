# Server Actions

## Overview

Server Actions are async functions that run on the server, used for:
- Form submissions
- Data mutations (create, update, delete)
- Revalidating cached data
- Redirecting after mutations

## Basic Server Action

### Definition

```tsx
// app/tasks/actions.ts
"use server";

import { revalidatePath } from "next/cache";

export async function createTask(formData: FormData) {
  const title = formData.get("title") as string;

  // Validate
  if (!title || title.length < 1) {
    return { error: "Title is required" };
  }

  // Create task via API
  const response = await fetch(`${process.env.API_URL}/tasks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    return { error: "Failed to create task" };
  }

  // Revalidate the tasks page
  revalidatePath("/tasks");

  return { success: true };
}
```

### Usage in Form

```tsx
// app/tasks/page.tsx
import { createTask } from "./actions";

export default function TasksPage() {
  return (
    <form action={createTask}>
      <input name="title" placeholder="Task title" required />
      <button type="submit">Add Task</button>
    </form>
  );
}
```

## Action Patterns

### With Redirect

```tsx
"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";

export async function createTask(formData: FormData) {
  const title = formData.get("title") as string;

  const response = await fetch(`${process.env.API_URL}/tasks`, {
    method: "POST",
    body: JSON.stringify({ title }),
  });

  const task = await response.json();

  revalidatePath("/tasks");
  redirect(`/tasks/${task.id}`); // Redirect to new task
}
```

### With Parameters (bind)

```tsx
// actions.ts
"use server";

export async function deleteTask(taskId: string) {
  await fetch(`${process.env.API_URL}/tasks/${taskId}`, {
    method: "DELETE",
  });

  revalidatePath("/tasks");
}

// Component
import { deleteTask } from "./actions";

export function TaskItem({ task }: { task: Task }) {
  const deleteWithId = deleteTask.bind(null, task.id);

  return (
    <form action={deleteWithId}>
      <span>{task.title}</span>
      <button type="submit">Delete</button>
    </form>
  );
}
```

### With Non-Form Trigger

```tsx
"use client";

import { toggleTask } from "./actions";

export function TaskCheckbox({ task }: { task: Task }) {
  return (
    <input
      type="checkbox"
      checked={task.completed}
      onChange={async () => {
        await toggleTask(task.id, !task.completed);
      }}
    />
  );
}

// actions.ts
"use server";

export async function toggleTask(taskId: string, completed: boolean) {
  await fetch(`${process.env.API_URL}/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify({ completed }),
  });

  revalidatePath("/tasks");
}
```

## Form Validation

### With Zod

```tsx
// actions.ts
"use server";

import { z } from "zod";

const TaskSchema = z.object({
  title: z.string().min(1, "Title is required").max(200, "Title too long"),
  description: z.string().max(1000).optional(),
  priority: z.enum(["low", "medium", "high"]).default("medium"),
});

export type ActionState = {
  errors?: {
    title?: string[];
    description?: string[];
    priority?: string[];
  };
  message?: string;
};

export async function createTask(
  prevState: ActionState,
  formData: FormData
): Promise<ActionState> {
  // Validate
  const validatedFields = TaskSchema.safeParse({
    title: formData.get("title"),
    description: formData.get("description"),
    priority: formData.get("priority"),
  });

  if (!validatedFields.success) {
    return {
      errors: validatedFields.error.flatten().fieldErrors,
      message: "Invalid fields. Please check your input.",
    };
  }

  // Create task
  try {
    await fetch(`${process.env.API_URL}/tasks`, {
      method: "POST",
      body: JSON.stringify(validatedFields.data),
    });

    revalidatePath("/tasks");
    return { message: "Task created successfully" };
  } catch (error) {
    return { message: "Failed to create task" };
  }
}
```

### Form with useActionState

```tsx
"use client";

import { useActionState } from "react";
import { createTask, type ActionState } from "./actions";

const initialState: ActionState = {};

export function TaskForm() {
  const [state, formAction, isPending] = useActionState(createTask, initialState);

  return (
    <form action={formAction}>
      <div>
        <input name="title" placeholder="Title" />
        {state.errors?.title && (
          <p className="text-red-500">{state.errors.title[0]}</p>
        )}
      </div>

      <div>
        <textarea name="description" placeholder="Description" />
        {state.errors?.description && (
          <p className="text-red-500">{state.errors.description[0]}</p>
        )}
      </div>

      <select name="priority">
        <option value="low">Low</option>
        <option value="medium">Medium</option>
        <option value="high">High</option>
      </select>

      <button type="submit" disabled={isPending}>
        {isPending ? "Creating..." : "Create Task"}
      </button>

      {state.message && <p>{state.message}</p>}
    </form>
  );
}
```

## Optimistic Updates

### With useOptimistic

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
    (state, { id, completed }: { id: string; completed: boolean }) =>
      state.map((task) =>
        task.id === id ? { ...task, completed } : task
      )
  );

  const handleToggle = async (task: Task) => {
    const newCompleted = !task.completed;

    // Optimistic update
    addOptimisticTask({ id: task.id, completed: newCompleted });

    // Server action
    await toggleTask(task.id, newCompleted);
  };

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

## Revalidation Strategies

### revalidatePath

```tsx
"use server";

import { revalidatePath } from "next/cache";

export async function createTask(formData: FormData) {
  await createTaskInDB(formData);

  // Revalidate specific path
  revalidatePath("/tasks");

  // Revalidate with layout
  revalidatePath("/tasks", "layout");

  // Revalidate dynamic route
  revalidatePath("/tasks/[id]", "page");
}
```

### revalidateTag

```tsx
// Fetch with tag
async function getTasks() {
  const res = await fetch(url, {
    next: { tags: ["tasks"] },
  });
  return res.json();
}

// Revalidate by tag
"use server";

import { revalidateTag } from "next/cache";

export async function createTask(formData: FormData) {
  await createTaskInDB(formData);
  revalidateTag("tasks"); // Revalidates all fetches tagged "tasks"
}
```

## Error Handling

### Try-Catch Pattern

```tsx
"use server";

export async function createTask(formData: FormData) {
  try {
    const response = await fetch(`${process.env.API_URL}/tasks`, {
      method: "POST",
      body: JSON.stringify({ title: formData.get("title") }),
    });

    if (!response.ok) {
      const error = await response.json();
      return { error: error.message || "Failed to create task" };
    }

    revalidatePath("/tasks");
    return { success: true };
  } catch (error) {
    console.error("Server action error:", error);
    return { error: "An unexpected error occurred" };
  }
}
```

### With Error Boundary

```tsx
"use server";

export async function deleteTask(taskId: string) {
  const response = await fetch(`${process.env.API_URL}/tasks/${taskId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    // This will be caught by error.tsx
    throw new Error("Failed to delete task");
  }

  revalidatePath("/tasks");
}
```

## Authentication in Actions

```tsx
"use server";

import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";

export async function createTask(formData: FormData) {
  const session = await auth();

  if (!session) {
    redirect("/login");
  }

  const response = await fetch(`${process.env.API_URL}/tasks`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${session.accessToken}`,
    },
    body: JSON.stringify({
      title: formData.get("title"),
      userId: session.user.id,
    }),
  });

  revalidatePath("/tasks");
}
```

## Best Practices

### 1. Colocate Actions with Components

```
app/
└── tasks/
    ├── page.tsx
    ├── actions.ts      # Actions for this route
    └── components/
        └── TaskForm.tsx
```

### 2. Type Your Actions

```tsx
"use server";

interface CreateTaskResult {
  success?: boolean;
  error?: string;
  task?: Task;
}

export async function createTask(formData: FormData): Promise<CreateTaskResult> {
  // ...
}
```

### 3. Keep Actions Focused

```tsx
// GOOD - Single responsibility
export async function createTask(formData: FormData) { ... }
export async function updateTask(taskId: string, formData: FormData) { ... }
export async function deleteTask(taskId: string) { ... }
export async function toggleTaskComplete(taskId: string) { ... }

// BAD - Too many responsibilities
export async function manageTask(action: string, data: any) { ... }
```
