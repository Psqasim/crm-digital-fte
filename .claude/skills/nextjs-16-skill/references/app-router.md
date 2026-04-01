# App Router Architecture

## File-Based Routing

### Route Segments

```
app/
├── page.tsx              # / (root route)
├── about/
│   └── page.tsx          # /about
├── tasks/
│   ├── page.tsx          # /tasks
│   └── [id]/
│       └── page.tsx      # /tasks/:id (dynamic)
├── blog/
│   └── [...slug]/
│       └── page.tsx      # /blog/* (catch-all)
└── (marketing)/          # Route group (no URL impact)
    ├── pricing/
    │   └── page.tsx      # /pricing
    └── features/
        └── page.tsx      # /features
```

### Special Files

| File | Purpose |
|------|---------|
| `page.tsx` | Route UI (required for route) |
| `layout.tsx` | Shared UI wrapper |
| `loading.tsx` | Loading UI (Suspense) |
| `error.tsx` | Error boundary |
| `not-found.tsx` | 404 UI |
| `route.ts` | API endpoint |
| `template.tsx` | Re-rendered layout |

## Layouts

### Root Layout (Required)

```tsx
// app/layout.tsx
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "Todo App",
  description: "Task management application",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <nav>{/* Navigation */}</nav>
        <main>{children}</main>
        <footer>{/* Footer */}</footer>
      </body>
    </html>
  );
}
```

### Nested Layouts

```tsx
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="dashboard">
      <aside>{/* Sidebar */}</aside>
      <section>{children}</section>
    </div>
  );
}
```

### Layout with Authentication

```tsx
// app/(protected)/layout.tsx
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";

export default async function ProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const session = await auth();

  if (!session) {
    redirect("/login");
  }

  return <>{children}</>;
}
```

## Dynamic Routes

### Single Parameter

```tsx
// app/tasks/[id]/page.tsx
interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function TaskPage({ params }: PageProps) {
  const { id } = await params;
  const task = await getTask(id);

  if (!task) {
    notFound();
  }

  return <TaskDetail task={task} />;
}

// Generate static params for SSG
export async function generateStaticParams() {
  const tasks = await getTasks();
  return tasks.map((task) => ({ id: task.id }));
}
```

### Multiple Parameters

```tsx
// app/[category]/[slug]/page.tsx
interface PageProps {
  params: Promise<{ category: string; slug: string }>;
}

export default async function PostPage({ params }: PageProps) {
  const { category, slug } = await params;
  // ...
}
```

### Catch-All Routes

```tsx
// app/docs/[...slug]/page.tsx
interface PageProps {
  params: Promise<{ slug: string[] }>;
}

export default async function DocsPage({ params }: PageProps) {
  const { slug } = await params;
  // slug = ["getting-started", "installation"] for /docs/getting-started/installation
  const path = slug.join("/");
  // ...
}
```

## Loading States

### Route-Level Loading

```tsx
// app/tasks/loading.tsx
export default function TasksLoading() {
  return (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded w-1/4 mb-4" />
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-gray-200 rounded" />
        ))}
      </div>
    </div>
  );
}
```

### Component-Level Suspense

```tsx
// app/dashboard/page.tsx
import { Suspense } from "react";
import { TaskList } from "./TaskList";
import { TaskListSkeleton } from "./TaskListSkeleton";

export default function DashboardPage() {
  return (
    <div>
      <h1>Dashboard</h1>
      <Suspense fallback={<TaskListSkeleton />}>
        <TaskList />
      </Suspense>
    </div>
  );
}
```

## Error Handling

### Error Boundary

```tsx
"use client"; // Error components must be Client Components

// app/tasks/error.tsx
import { useEffect } from "react";

export default function TasksError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="error-container">
      <h2>Something went wrong!</h2>
      <p>{error.message}</p>
      <button onClick={() => reset()}>Try again</button>
    </div>
  );
}
```

### Not Found

```tsx
// app/tasks/[id]/not-found.tsx
import Link from "next/link";

export default function TaskNotFound() {
  return (
    <div>
      <h2>Task Not Found</h2>
      <p>Could not find the requested task.</p>
      <Link href="/tasks">Back to Tasks</Link>
    </div>
  );
}
```

### Triggering Not Found

```tsx
import { notFound } from "next/navigation";

export default async function TaskPage({ params }: PageProps) {
  const { id } = await params;
  const task = await getTask(id);

  if (!task) {
    notFound(); // Renders not-found.tsx
  }

  return <TaskDetail task={task} />;
}
```

## Navigation

### Link Component

```tsx
import Link from "next/link";

export function Navigation() {
  return (
    <nav>
      <Link href="/">Home</Link>
      <Link href="/tasks">Tasks</Link>
      <Link href="/tasks/new" prefetch={false}>
        New Task
      </Link>
      <Link href={{ pathname: "/tasks", query: { filter: "active" } }}>
        Active Tasks
      </Link>
    </nav>
  );
}
```

### Programmatic Navigation

```tsx
"use client";

import { useRouter } from "next/navigation";

export function TaskActions({ taskId }: { taskId: string }) {
  const router = useRouter();

  const handleDelete = async () => {
    await deleteTask(taskId);
    router.push("/tasks");
    router.refresh(); // Refresh server components
  };

  return <button onClick={handleDelete}>Delete</button>;
}
```

### Active Link Styling

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

export function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isActive = pathname === href;

  return (
    <Link
      href={href}
      className={cn(
        "px-4 py-2 rounded",
        isActive ? "bg-blue-500 text-white" : "text-gray-600"
      )}
    >
      {children}
    </Link>
  );
}
```

## Parallel Routes

### Layout with Slots

```tsx
// app/dashboard/layout.tsx
export default function DashboardLayout({
  children,
  analytics,
  team,
}: {
  children: React.ReactNode;
  analytics: React.ReactNode;
  team: React.ReactNode;
}) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div>{children}</div>
      <div>{analytics}</div>
      <div>{team}</div>
    </div>
  );
}

// app/dashboard/@analytics/page.tsx
// app/dashboard/@team/page.tsx
```

## Intercepting Routes

### Modal Pattern

```
app/
├── tasks/
│   ├── page.tsx          # Full task list
│   └── [id]/
│       └── page.tsx      # Full task detail page
└── @modal/
    └── (.)tasks/
        └── [id]/
            └── page.tsx  # Modal task detail (intercepts)
```

```tsx
// app/@modal/(.)tasks/[id]/page.tsx
import { Modal } from "@/components/Modal";
import { TaskDetail } from "@/components/TaskDetail";

export default async function TaskModal({ params }: PageProps) {
  const { id } = await params;
  const task = await getTask(id);

  return (
    <Modal>
      <TaskDetail task={task} />
    </Modal>
  );
}
```

## Metadata

### Static Metadata

```tsx
// app/tasks/page.tsx
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Tasks | Todo App",
  description: "Manage your tasks",
  openGraph: {
    title: "Tasks",
    description: "Manage your tasks",
  },
};
```

### Dynamic Metadata

```tsx
// app/tasks/[id]/page.tsx
import type { Metadata } from "next";

interface PageProps {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params;
  const task = await getTask(id);

  return {
    title: `${task.title} | Todo App`,
    description: task.description,
  };
}
```
