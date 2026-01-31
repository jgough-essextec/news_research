"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Mail, RefreshCw, ExternalLink, Check, Clock, X } from "lucide-react";
import { api, NewsletterEmail, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function EmailsPage() {
  const [page, setPage] = useState(1);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["emails", page],
    queryFn: () =>
      api.get<PaginatedResponse<NewsletterEmail>>(
        `/emails/?page=${page}&ordering=-received_date`
      ),
  });

  const syncEmails = useMutation({
    mutationFn: () => api.post("/emails/sync/"),
    onSuccess: () => {
      toast({ title: "Email sync started" });
      // Refetch after a delay to show new emails
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["emails"] });
      }, 5000);
    },
    onError: () => {
      toast({ title: "Failed to sync emails", variant: "destructive" });
    },
  });

  const statusIcon = (email: NewsletterEmail) => {
    if (email.is_processed) {
      return <Check className="h-4 w-4 text-green-500" />;
    }
    return <Clock className="h-4 w-4 text-yellow-500" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Newsletter Emails</h2>
          <p className="text-sm text-muted-foreground">
            Emails fetched from your Gmail AI-News label
          </p>
        </div>
        <Button
          onClick={() => syncEmails.mutate()}
          disabled={syncEmails.isPending}
        >
          <RefreshCw
            className={`mr-2 h-4 w-4 ${syncEmails.isPending ? "animate-spin" : ""}`}
          />
          Sync Emails
        </Button>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : (
        <>
          <div className="grid gap-4">
            {data?.results?.map((email) => (
              <Link key={email.id} href={`/dashboard/emails/${email.id}`}>
                <Card className="hover:border-primary transition-colors cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <Mail className="h-5 w-5 text-muted-foreground" />
                        <div>
                          <CardTitle className="text-base line-clamp-1">
                            {email.subject}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground">
                            From: {email.sender_name || email.sender_email}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {statusIcon(email)}
                        <span className="text-xs text-muted-foreground">
                          {email.is_processed ? "Processed" : "Pending"}
                        </span>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-2">
                      {email.snippet}
                    </p>
                    {email.ai_summary && (
                      <div className="mt-2 text-sm text-muted-foreground">
                        <div className="whitespace-pre-line line-clamp-3">
                          {email.ai_summary}
                        </div>
                      </div>
                    )}
                    <div className="flex items-center justify-between text-xs text-muted-foreground mt-2">
                      <span>
                        Received: {new Date(email.received_date).toLocaleString()}
                      </span>
                      <span>
                        {email.link_count} link{email.link_count !== 1 ? "s" : ""}{" "}
                        extracted
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}

            {(!data?.results || data.results.length === 0) && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <Mail className="mb-4 h-12 w-12 text-muted-foreground" />
                  <h3 className="mb-2 text-lg font-semibold">No emails yet</h3>
                  <p className="mb-4 text-center text-sm text-muted-foreground">
                    Connect your Gmail and create an &quot;AI-News&quot; label to start
                    importing newsletters.
                  </p>
                  <Button
                    onClick={() => syncEmails.mutate()}
                    disabled={syncEmails.isPending}
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Sync Now
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {data && data.results && data.results.length > 0 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {data.results.length} of {data.count} emails
              </p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={!data.previous}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!data.next}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
