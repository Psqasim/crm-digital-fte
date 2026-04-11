"use client";

import { useRef, useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import confetti from "canvas-confetti";
import { toast } from "sonner";
import { Copy, CheckCheck, ExternalLink, RotateCcw, Ticket } from "lucide-react";

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

function TicketSuccessCard({ ticketId, onReset }: { ticketId: string; onReset: () => void }) {
  const router = useRouter();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(ticketId);
    setCopied(true);
    toast.success("Ticket ID copied!");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <SlideUp delay={0.05}>
      <Card className="bg-slate-900/50 border-slate-700">
        <CardContent className="p-6 sm:p-8 text-center space-y-6">
          {/* Icon */}
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-full bg-green-500/10 border border-green-500/30 flex items-center justify-center">
              <Ticket className="w-8 h-8 text-green-400" />
            </div>
          </div>

          {/* Title */}
          <div>
            <h2 className="text-xl font-bold text-white mb-1">Ticket Submitted!</h2>
            <p className="text-slate-400 text-sm">
              Your ticket is queued. AI will analyze it within ~30 seconds.
            </p>
          </div>

          {/* Ticket ID block */}
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-4 space-y-3">
            <p className="text-slate-400 text-xs uppercase tracking-wide">Your Ticket ID</p>
            <p className="font-mono text-2xl font-bold text-[#3B82F6] tracking-wider">
              {ticketId}
            </p>
            <button
              onClick={handleCopy}
              className="flex items-center gap-2 mx-auto text-sm bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
            >
              {copied ? (
                <><CheckCheck className="w-4 h-4 text-green-400" /> Copied!</>
              ) : (
                <><Copy className="w-4 h-4" /> Copy Ticket ID</>
              )}
            </button>
          </div>

          {/* Warning */}
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg px-4 py-3 text-left">
            <p className="text-yellow-400 text-xs font-medium mb-0.5">Save this ID</p>
            <p className="text-slate-400 text-xs">
              You&apos;ll need it to check your ticket status. Bookmark the link or copy the ID now.
            </p>
          </div>

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={() => router.push(`/ticket/${ticketId}`)}
              className="flex-1 bg-[#3B82F6] hover:bg-[#2563EB] text-white font-semibold gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              View Ticket Status
            </Button>
            <Button
              variant="outline"
              onClick={onReset}
              className="flex-1 border-slate-600 text-slate-300 hover:text-white hover:bg-slate-800 gap-2"
            >
              <RotateCcw className="w-4 h-4" />
              Submit Another
            </Button>
          </div>
        </CardContent>
      </Card>
    </SlideUp>
  );
}

interface SupportFormProps {
  defaultEmail: string | null;
  defaultName: string | null;
}

export default function SupportForm({ defaultEmail, defaultName }: SupportFormProps) {
  const [submitting, setSubmitting] = useState(false);
  const [submittedTicketId, setSubmittedTicketId] = useState<string | null>(null);
  const confettiFired = useRef(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: defaultName ?? "",
      email: defaultEmail ?? "",
      subject: "",
      category: undefined,
      priority: undefined,
      message: "",
    },
  });

  // Keep values in sync if server-side props arrive after hydration
  useEffect(() => {
    if (defaultEmail) form.setValue("email", defaultEmail, { shouldValidate: false });
    if (defaultName) form.setValue("name", defaultName, { shouldValidate: false });
  }, [defaultEmail, defaultName, form]);

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

        if (!confettiFired.current) {
          confettiFired.current = true;
          confetti({
            particleCount: 80,
            spread: 60,
            origin: { y: 0.6 },
            colors: ["#3B82F6", "#2563EB", "#60A5FA", "#FFFFFF"],
          });
        }

        setSubmittedTicketId(ticketId);
      } else {
        toast.error(json.detail ?? "Submission failed. Please try again.");
        setSubmitting(false);
      }
    } catch {
      toast.error("Network error. Please check your connection.");
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setSubmittedTicketId(null);
    setSubmitting(false);
    form.reset();
  };

  if (submittedTicketId) {
    return <TicketSuccessCard ticketId={submittedTicketId} onReset={handleReset} />;
  }

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
                        readOnly={!!defaultEmail}
                        className={`bg-slate-800 border-slate-600 text-white placeholder:text-slate-500 focus-visible:ring-[#3B82F6] ${
                          defaultEmail ? "opacity-70 cursor-not-allowed select-none" : ""
                        }`}
                        {...field}
                      />
                    </FormControl>
                    {defaultEmail ? (
                      <p className="text-xs text-slate-500 mt-1">
                        Submitting as <span className="text-blue-400">{defaultEmail}</span>
                        {" · "}
                        <a href="/api/auth/signout" className="hover:text-slate-300 underline underline-offset-2">
                          Sign out
                        </a>
                      </p>
                    ) : (
                      <FormMessage />
                    )}
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

              {/* Category + Priority */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="category"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-slate-200">Category</FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
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
                          messageLength >= 1800 ? "text-red-400 font-medium" : "text-slate-500"
                        }`}
                      >
                        {messageLength}/2000
                      </span>
                    </div>
                  </FormItem>
                )}
              />

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
