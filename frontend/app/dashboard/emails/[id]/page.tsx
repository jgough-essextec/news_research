"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  Calendar,
  Mail,
  Sparkles,
  FileText,
  Link as LinkIcon,
  Check,
  Clock,
  AlertCircle,
} from "lucide-react";
import { api, NewsletterEmailDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function EmailDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const emailId = params.id as string;

  const { data: email, isLoading, error } = useQuery({
    queryKey: ["email", emailId],
    queryFn: () => api.get<NewsletterEmailDetail>(`/emails/${emailId}/`),
    enabled: !!emailId,
  });

  const generateSummary = useMutation({
    mutationFn: () => api.post<{ status: string; ai_summary?: string; error?: string }>(
      `/emails/${emailId}/generate_summary/`
    ),
    onSuccess: (data) => {
      if (data.ai_summary) {
        toast({
          title: "Summary generated",
          description: "The AI summary has been created",
        });
        // Immediately update the cache with the new summary
        queryClient.setQueryData(["email", emailId], (old: NewsletterEmailDetail | undefined) => {
          if (old) {
            return { ...old, ai_summary: data.ai_summary };
          }
          return old;
        });
      }
    },
    onError: (error: Error) => {
      toast({
        title: "Failed to generate summary",
        description: error.message,
        variant: "destructive"
      });
    },
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "valid":
        return (
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs bg-green-100 text-green-700">
            <Check className="h-3 w-3" />
            Valid
          </span>
        );
      case "invalid":
        return (
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs bg-red-100 text-red-700">
            <AlertCircle className="h-3 w-3" />
            Invalid
          </span>
        );
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs bg-yellow-100 text-yellow-700">
            <Clock className="h-3 w-3" />
            Pending
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs bg-gray-100 text-gray-700">
            {status}
          </span>
        );
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading email...</div>
      </div>
    );
  }

  if (error || !email) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Email not found</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Emails
        </Button>
      </div>

      {/* Email Header */}
      <div className="space-y-4">
        <h1 className="text-2xl font-bold">{email.subject}</h1>

        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Mail className="h-4 w-4" />
            {email.sender_name || email.sender_email}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {new Date(email.received_date).toLocaleString()}
          </span>
          <span className="flex items-center gap-1">
            <LinkIcon className="h-4 w-4" />
            {email.link_count} link{email.link_count !== 1 ? "s" : ""}
          </span>
          <span
            className={`rounded px-2 py-0.5 ${
              email.is_processed
                ? "bg-green-100 text-green-700"
                : "bg-yellow-100 text-yellow-700"
            }`}
          >
            {email.is_processed ? "Processed" : "Pending"}
          </span>
        </div>
      </div>

      {/* AI Summary */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI Summary
          </CardTitle>
          {!email.ai_summary && (
            <Button
              size="sm"
              onClick={() => generateSummary.mutate()}
              disabled={generateSummary.isPending}
            >
              {generateSummary.isPending ? "Generating..." : "Generate Summary"}
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {email.ai_summary ? (
            <div className="whitespace-pre-line text-muted-foreground">
              {email.ai_summary}
            </div>
          ) : (
            <p className="text-muted-foreground italic">
              No AI summary available. Click &quot;Generate Summary&quot; to create one.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Email Body */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Email Content
          </CardTitle>
        </CardHeader>
        <CardContent>
          {email.raw_html ? (
            <div
              className="prose prose-sm max-w-none dark:prose-invert overflow-auto max-h-[600px]"
              dangerouslySetInnerHTML={{ __html: email.raw_html }}
            />
          ) : (
            <p className="text-muted-foreground italic">
              {email.snippet || "No content available"}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Extracted Links / Articles */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <LinkIcon className="h-5 w-5" />
            Extracted Articles ({email.extracted_links?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {email.extracted_links && email.extracted_links.length > 0 ? (
            <div className="space-y-4">
              {email.extracted_links.map((link) => (
                <div
                  key={link.id}
                  className="flex items-start justify-between gap-4 p-3 rounded-lg border"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusBadge(link.status)}
                      {link.is_valid_article && (
                        <span className="text-xs text-green-600">
                          Valid Article
                        </span>
                      )}
                    </div>
                    <p className="font-medium text-sm line-clamp-1">
                      {link.article_title || link.anchor_text || "Untitled"}
                    </p>
                    <p className="text-xs text-muted-foreground line-clamp-1 mt-1">
                      {link.canonical_url}
                    </p>
                    {link.surrounding_text && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {link.surrounding_text}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {link.article && (
                      <Link href={`/dashboard/articles/${link.article}`}>
                        <Button size="sm" variant="outline">
                          View Article
                        </Button>
                      </Link>
                    )}
                    <a
                      href={link.canonical_url || link.raw_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Button size="sm" variant="ghost">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </a>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground italic">
              No articles extracted from this email yet.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Metadata</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="font-medium">Email ID</dt>
              <dd className="text-muted-foreground">{email.id}</dd>
            </div>
            <div>
              <dt className="font-medium">Gmail Message ID</dt>
              <dd className="text-muted-foreground truncate">
                {email.gmail_message_id}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Received</dt>
              <dd className="text-muted-foreground">
                {new Date(email.received_date).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Processed At</dt>
              <dd className="text-muted-foreground">
                {email.processed_at
                  ? new Date(email.processed_at).toLocaleString()
                  : "Not processed"}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="font-medium">Sender</dt>
              <dd className="text-muted-foreground">
                {email.sender_name} &lt;{email.sender_email}&gt;
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
