"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import confetti from "canvas-confetti";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import SlideUp from "@/components/animations/SlideUp";

// ---------------------------------------------------------------------------
// Zod schema
// ---------------------------------------------------------------------------

export const formSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  subject: z.string().min(5, "Subject must be at least 5 characters"),
  category: z.enum(["billing", "technical", "account", "general"], {
    error: "Category is required",
  }),
  priority: z.enum(["low", "medium", "high", "urgent"], {
    error: "Priority is required",
  }),
  message: z
    .string()
    .min(20, "Message must be at least 20 characters")
    .max(2000, "Message cannot exceed 2000 characters"),
});

type FormValues = z.infer<typeof formSchema>;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function SupportForm() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const confettiFired = useRef(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      email: "",
      subject: "",
      category: undefined,
      priority: undefined,
      message: "",
    },
  });

  const messageLength = form.watch("message").length;

  const onSubmit = async (data: FormValues) => {
    confettiFired.current = false;
    setSubmitting(true);

    try {
      const res = await fetch("/api/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });

      const json = await res.json();

      if (res.ok) {
        const ticketId: string = json.ticket_id;

        // Fire confetti exactly once
        if (!confettiFired.current) {
          confettiFired.current = true;
          confetti({
            particleCount: 80,
            spread: 60,
            origin: { y: 0.6 },
            colors: ["#3B82F6", "#2563EB", "#60A5FA", "#FFFFFF"],
          });
        }

        toast.success(`Ticket created! ID: ${ticketId}`, {
          action: {
            label: "View",
            onClick: () => router.push(`/ticket/${ticketId}`),
          },
        });

        setTimeout(() => {
          router.push(`/ticket/${ticketId}`);
        }, 2000);
      } else {
        toast.error(json.detail ?? "Submission failed. Please try again.");
        setSubmitting(false);
      }
    } catch {
      toast.error("Network error. Please check your connection.");
      setSubmitting(false);
    }
  };

  return (
    <SlideUp delay={0.1}>
      <Card className="bg-slate-900/50 border-slate-700">
        <CardContent className="p-4 sm:p-6">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
              {/* Name */}
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-200">Full Name</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Jane Smith"
                        className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#3B82F6]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Email */}
              <FormField
                control={form.control}
                name="email"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-200">Email</FormLabel>
                    <FormControl>
                      <Input
                        type="email"
                        placeholder="jane@example.com"
                        className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#3B82F6]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Subject */}
              <FormField
                control={form.control}
                name="subject"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-200">Subject</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Brief description of your issue"
                        className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#3B82F6]"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* Category + Priority side by side on sm+ */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-200">Category</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger className="bg-slate-800 border-slate-600 text-white focus:ring-[#3B82F6] min-h-[44px]">
                            <SelectValue placeholder="Select category" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800 border-slate-600 text-white">
                          <SelectItem value="billing">Billing</SelectItem>
                          <SelectItem value="technical">Technical</SelectItem>
                          <SelectItem value="account">Account</SelectItem>
                          <SelectItem value="general">General</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="priority"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-200">Priority</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger className="bg-slate-800 border-slate-600 text-white focus:ring-[#3B82F6] min-h-[44px]">
                            <SelectValue placeholder="Select priority" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent className="bg-slate-800 border-slate-600 text-white">
                          <SelectItem value="low">Low</SelectItem>
                          <SelectItem value="medium">Medium</SelectItem>
                          <SelectItem value="high">High</SelectItem>
                          <SelectItem value="urgent">Urgent</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              {/* Message */}
              <FormField
                control={form.control}
                name="message"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="text-slate-200">Message</FormLabel>
                    <FormControl>
                      <Textarea
                        rows={5}
                        placeholder="Describe your issue in detail..."
                        className="bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#3B82F6] resize-none"
                        {...field}
                      />
                    </FormControl>
                    <div className="flex justify-between items-center">
                      <FormMessage />
                      <span
                        className={`text-xs ml-auto ${
                          messageLength >= 1800
                            ? "text-red-400 font-medium"
                            : "text-slate-500"
                        }`}
                      >
                        {messageLength}/2000
                      </span>
                    </div>
                  </FormItem>
                )}
              />

              {/* Submit */}
              <Button
                type="submit"
                disabled={submitting}
                className="w-full min-h-[44px] bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold focus-visible:ring-2 focus-visible:ring-[#3B82F6]"
              >
                {submitting ? "Submitting..." : "Submit Ticket"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </SlideUp>
  );
}
