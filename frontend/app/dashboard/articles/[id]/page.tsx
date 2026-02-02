"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  Calendar,
  User,
  Building2,
  FileText,
  Layers,
  RefreshCw,
} from "lucide-react";
import { api, ArticleDetail } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function ArticleDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const articleId = params.id as string;

  const { data: article, isLoading, error } = useQuery({
    queryKey: ["article", articleId],
    queryFn: () => api.get<ArticleDetail>(`/articles/${articleId}/`),
    enabled: !!articleId,
  });

  const rescrape = useMutation({
    mutationFn: () => api.post<void>(`/articles/${articleId}/rescrape/`),
    onSuccess: () => {
      toast({ title: "Rescrape started", description: "Article is being re-scraped" });
      queryClient.invalidateQueries({ queryKey: ["article", articleId] });
    },
    onError: () => {
      toast({ title: "Failed to rescrape", variant: "destructive" });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading article...</div>
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Article not found</p>
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
          Back to Articles
        </Button>
        <div className="flex items-center gap-2">
          {article.scrape_status === "failed" && (
            <Button
              variant="outline"
              onClick={() => rescrape.mutate()}
              disabled={rescrape.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${rescrape.isPending ? "animate-spin" : ""}`} />
              Retry Scrape
            </Button>
          )}
          <a
            href={article.canonical_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline">
              <ExternalLink className="mr-2 h-4 w-4" />
              View Original
            </Button>
          </a>
        </div>
      </div>

      {/* Article Header */}
      <div className="space-y-4">
        <h1 className="text-3xl font-bold">{article.title || "Untitled Article"}</h1>

        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          {article.author && (
            <span className="flex items-center gap-1">
              <User className="h-4 w-4" />
              {article.author}
            </span>
          )}
          {article.publication && (
            <span className="flex items-center gap-1">
              <Building2 className="h-4 w-4" />
              {article.publication}
            </span>
          )}
          {article.publication_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              {new Date(article.publication_date).toLocaleDateString()}
            </span>
          )}
          <span className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            {article.word_count} words
          </span>
          <span
            className={`rounded px-2 py-0.5 ${
              article.scrape_status === "success"
                ? "bg-green-100 text-green-700"
                : article.scrape_status === "failed"
                ? "bg-red-100 text-red-700"
                : "bg-yellow-100 text-yellow-700"
            }`}
          >
            {article.scrape_status}
          </span>
        </div>

        {article.topic_cluster && article.cluster_name && (
          <Link
            href={`/dashboard/clusters/${article.topic_cluster}`}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <Layers className="h-4 w-4" />
            {article.cluster_name}
          </Link>
        )}
      </div>

      {/* Open Graph Image */}
      {article.og_image && (
        <div className="overflow-hidden rounded-lg">
          <img
            src={article.og_image}
            alt=""
            className="w-full max-h-96 object-cover"
          />
        </div>
      )}

      {/* Summary */}
      {article.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">AI Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground">{article.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Full Content */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Full Content</CardTitle>
        </CardHeader>
        <CardContent>
          {article.content_text ? (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <div className="whitespace-pre-wrap">{article.content_text}</div>
            </div>
          ) : (
            <p className="text-muted-foreground italic">
              {article.scrape_status === "pending"
                ? "Article content is being scraped..."
                : article.scrape_status === "failed"
                ? "Failed to scrape article content. Try clicking 'Retry Scrape' above."
                : "No content available"}
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
              <dt className="font-medium">Article ID</dt>
              <dd className="text-muted-foreground">{article.id}</dd>
            </div>
            <div>
              <dt className="font-medium">Created</dt>
              <dd className="text-muted-foreground">
                {new Date(article.created_at).toLocaleString()}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="font-medium">URL</dt>
              <dd className="text-muted-foreground break-all">
                <a
                  href={article.canonical_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:underline"
                >
                  {article.canonical_url}
                </a>
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
