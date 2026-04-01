# Server Components vs Client Components

## Overview

| Aspect | Server Component | Client Component |
|--------|------------------|------------------|
| Directive | None (default) | `"use client"` |
| Rendering | Server only | Server + Client hydration |
| Data fetching | Direct async/await | useEffect or Server Actions |
| Interactivity | None | Full (events, state, effects) |
| Hooks | Cannot use | Can use |
| Browser APIs | Cannot access | Can access |
| Bundle size | Zero JS sent | Included in bundle |

## Server Components (Default)

### When to Use

- Data fetching from databases or APIs
- Accessing backend resources directly
- Keeping sensitive data on server (API keys, tokens)
- Large dependencies that shouldn't be in client bundle
- SEO-critical content

### Data Fetching

```tsx
// app/tasks/page.tsx - Server Component
async function getTasks() {
  const res = await fetch(`${process.env.API_URL}/tasks`, {
    cache: "no-store", // Dynamic data
  });
  return res.json();
}

export default async function TasksPage() {
  const tasks = await getTasks();

  return (
    <ul>
      {tasks.map((task) => (
        <TaskItem key={task.id} task={task} />
      ))}
    </ul>
  );
}
```

### Caching Strategies

```tsx
// Static data (cached indefinitely)
const data = await fetch(url); // Default: cache: "force-cache"

// Dynamic data (never cached)
const data = await fetch(url, { cache: "no-store" });

// Revalidate periodically
const data = await fetch(url, { next: { revalidate: 3600 } }); // 1 hour

// Revalidate on demand (via Server Action)
import { revalidatePath, revalidateTag } from "next/cache";

const data = await fetch(url, { next: { tags: ["tasks"] } });
// Later: revalidateTag("tasks");
```

### Direct Database Access

```tsx
// app/tasks/page.tsx
import { db } from "@/lib/db";

export default async function TasksPage() {
  // Direct database query - only possible in Server Components
  const tasks = await db.query.tasks.findMany({
    where: { completed: false },
    orderBy: { createdAt: "desc" },
  });

  return <TaskList tasks={tasks} />;
}
```

## Client Components

### When to Use

- Event handlers (onClick, onChange, onSubmit)
- React hooks (useState, useEffect, useReducer, useContext)
- Browser APIs (localStorage, window, navigator)
- Custom hooks that depend on state/effects
- Third-party libraries that use client features

### Basic Client Component

```tsx
"use client";

import { useState } from "react";

interface Task {
  id: string;
  title: string;
  completed: boolean;
}

export function TaskItem({ task }: { task: Task }) {
  const [isEditing, setIsEditing] = useState(false);

  return (
    <li>
      {isEditing ? (
        <input defaultValue={task.title} />
      ) : (
        <span onClick={() => setIsEditing(true)}>{task.title}</span>
      )}
    </li>
  );
}
```

### Form with State

```tsx
"use client";

import { useState } from "react";

export function TaskForm({ onSubmit }: { onSubmit: (title: string) => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(title);
      setTitle("");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        disabled={isSubmitting}
        placeholder="New task..."
      />
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Adding..." : "Add Task"}
      </button>
    </form>
  );
}
```

## Composition Patterns

### Server Component with Client Children

```tsx
// app/tasks/page.tsx (Server Component)
import { TaskForm } from "./TaskForm"; // Client Component
import { TaskList } from "./TaskList"; // Client Component

async function getTasks() {
  const res = await fetch(`${process.env.API_URL}/tasks`);
  return res.json();
}

export default async function TasksPage() {
  const tasks = await getTasks(); // Server-side fetch

  return (
    <div>
      <h1>Tasks</h1>
      <TaskForm /> {/* Client Component */}
      <TaskList initialTasks={tasks} /> {/* Pass server data as props */}
    </div>
  );
}
```

### Passing Server Data to Client

```tsx
// Server Component fetches, Client Component displays interactively
// app/dashboard/page.tsx (Server)
import { TaskChart } from "./TaskChart"; // Client

export default async function DashboardPage() {
  const stats = await getTaskStats(); // Server fetch

  return (
    <div>
      <TaskChart data={stats} /> {/* Serializable data passed as prop */}
    </div>
  );
}

// components/TaskChart.tsx (Client)
"use client";

import { Chart } from "chart.js";

export function TaskChart({ data }: { data: TaskStats }) {
  // Use client-side charting library
  return <canvas ref={/* chart setup */} />;
}
```

### Client Component Wrapping Server Component

```tsx
// This pattern uses children to pass Server Components through Client Components

// ClientWrapper.tsx
"use client";

import { useState } from "react";

export function Collapsible({ children }: { children: React.ReactNode }) {
  const [isOpen, setIsOpen] = useState(true);

  return (
    <div>
      <button onClick={() => setIsOpen(!isOpen)}>
        {isOpen ? "Collapse" : "Expand"}
      </button>
      {isOpen && children}
    </div>
  );
}

// page.tsx (Server Component)
import { Collapsible } from "./Collapsible";
import { TaskList } from "./TaskList"; // Server Component

export default async function Page() {
  return (
    <Collapsible>
      <TaskList /> {/* Server Component passed as children */}
    </Collapsible>
  );
}
```

## Context Providers

### Setup Provider as Client Component

```tsx
// providers/ThemeProvider.tsx
"use client";

import { createContext, useContext, useState } from "react";

const ThemeContext = createContext<{
  theme: "light" | "dark";
  toggle: () => void;
} | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  return (
    <ThemeContext.Provider
      value={{
        theme,
        toggle: () => setTheme((t) => (t === "light" ? "dark" : "light")),
      }}
    >
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within ThemeProvider");
  return context;
}
```

### Use in Layout

```tsx
// app/layout.tsx (Server Component)
import { ThemeProvider } from "@/providers/ThemeProvider";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html>
      <body>
        <ThemeProvider>{children}</ThemeProvider>
      </body>
    </html>
  );
}
```

## Anti-Patterns to Avoid

### DON'T: Import Server-Only Code in Client Components

```tsx
// BAD - This will fail
"use client";

import { db } from "@/lib/db"; // Database client

export function TaskForm() {
  const handleSubmit = async () => {
    await db.tasks.create({ ... }); // Cannot use on client!
  };
}
```

### DON'T: Pass Non-Serializable Props

```tsx
// BAD - Functions can't be serialized
// page.tsx (Server)
export default function Page() {
  const handleClick = () => console.log("clicked");

  return <ClientComponent onClick={handleClick} />; // Error!
}

// GOOD - Use Server Actions instead
// actions.ts
"use server";
export async function handleClick() { ... }

// page.tsx
import { handleClick } from "./actions";
export default function Page() {
  return <ClientComponent onClick={handleClick} />; // Server Action is OK
}
```

### DON'T: Mark Everything as Client Component

```tsx
// BAD - Unnecessary "use client"
"use client"; // Not needed!

export function TaskCard({ task }: { task: Task }) {
  // No interactivity, no hooks, no browser APIs
  return (
    <div>
      <h3>{task.title}</h3>
      <p>{task.description}</p>
    </div>
  );
}

// GOOD - Let it be a Server Component
export function TaskCard({ task }: { task: Task }) {
  return (
    <div>
      <h3>{task.title}</h3>
      <p>{task.description}</p>
    </div>
  );
}
```

## Best Practices

### 1. Push Client Boundary Down

```tsx
// GOOD - Only interactive part is client
// TaskCard.tsx (Server)
export function TaskCard({ task }: { task: Task }) {
  return (
    <div>
      <h3>{task.title}</h3>
      <p>{task.description}</p>
      <TaskActions taskId={task.id} /> {/* Only this needs client */}
    </div>
  );
}

// TaskActions.tsx (Client)
"use client";
export function TaskActions({ taskId }: { taskId: string }) {
  return (
    <div>
      <button onClick={() => ...}>Edit</button>
      <button onClick={() => ...}>Delete</button>
    </div>
  );
}
```

### 2. Colocate Client Components

```
app/
└── tasks/
    ├── page.tsx           # Server Component
    ├── TaskList.tsx       # Server Component
    └── components/
        ├── TaskForm.tsx   # Client Component
        └── TaskActions.tsx # Client Component
```

### 3. Use Server Actions for Mutations

```tsx
// Instead of API calls from client, use Server Actions
"use client";

import { createTask } from "./actions";

export function TaskForm() {
  return (
    <form action={createTask}>
      <input name="title" />
      <button type="submit">Add</button>
    </form>
  );
}
```
