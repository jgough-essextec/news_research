"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  ExternalLink,
  Calendar,
  FileText,
  Sparkles,
  PenTool,
  Layers,
} from "lucide-react";
import { api, TopicCluster, Article, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function ClusterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const clusterId = params.id as string;

  const { data: cluster, isLoading: clusterLoading } = useQuery({
    queryKey: ["cluster", clusterId],
    queryFn: () => api.get<TopicCluster>(`/clusters/${clusterId}/`),
    enabled: !!clusterId,
  });

  const { data: articles, isLoading: articlesLoading } = useQuery({
    queryKey: ["cluster-articles", clusterId],
    queryFn: () =>
      api.get<PaginatedResponse<Article>>(`/clusters/${clusterId}/articles/`),
    enabled: !!clusterId,
  });

  const generateSummary = useMutation({
    mutationFn: () => api.post(`/clusters/${clusterId}/generate_summary/`),
    onSuccess: () => {
      toast({ title: "Summary generation started" });
      queryClient.invalidateQueries({ queryKey: ["cluster", clusterId] });
    },
    onError: () => {
      toast({ title: "Failed to generate summary", variant: "destructive" });
    },
  });

  const generatePost = useMutation({
    mutationFn: () => api.post(`/clusters/${clusterId}/generate_post/`),
    onSuccess: (data: { post_id: number }) => {
      toast({ title: "Blog post generation started" });
      if (data?.post_id) {
        router.push(`/dashboard/posts/${data.post_id}`);
      }
    },
    onError: () => {
      toast({ title: "Failed to generate blog post", variant: "destructive" });
    },
  });

  if (clusterLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading cluster...</div>
      </div>
    );
  }

  if (!cluster) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Cluster not found</p>
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
          Back to Clusters
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => generateSummary.mutate()}
            disabled={generateSummary.isPending}
          >
            <Sparkles className={`mr-2 h-4 w-4 ${generateSummary.isPending ? "animate-pulse" : ""}`} />
            Generate Summary
          </Button>
          <Button
            onClick={() => generatePost.mutate()}
            disabled={generatePost.isPending}
          >
            <PenTool className={`mr-2 h-4 w-4 ${generatePost.isPending ? "animate-pulse" : ""}`} />
            Generate Blog Post
          </Button>
        </div>
      </div>

      {/* Cluster Header */}
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <Layers className="h-8 w-8 text-primary mt-1" />
          <div>
            <h1 className="text-3xl font-bold">{cluster.name}</h1>
            {cluster.description && (
              <p className="mt-2 text-muted-foreground">{cluster.description}</p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <FileText className="h-4 w-4" />
            {cluster.article_count} articles
          </span>
          <span>Priority Score: {cluster.priority_score.toFixed(1)}</span>
          {cluster.last_article_added_at && (
            <span className="flex items-center gap-1">
              <Calendar className="h-4 w-4" />
              Last updated: {new Date(cluster.last_article_added_at).toLocaleDateString()}
            </span>
          )}
          <span
            className={`rounded px-2 py-0.5 ${
              cluster.is_active
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-700"
            }`}
          >
            {cluster.is_active ? "Active" : "Inactive"}
          </span>
        </div>
      </div>

      {/* Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Cluster Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {cluster.master_summary ? (
            <p className="text-muted-foreground">{cluster.master_summary}</p>
          ) : (
            <div className="text-center py-4">
              <p className="text-muted-foreground italic mb-4">
                No summary generated yet
              </p>
              <Button
                variant="outline"
                onClick={() => generateSummary.mutate()}
                disabled={generateSummary.isPending}
              >
                <Sparkles className="mr-2 h-4 w-4" />
                Generate Summary
              </Button>
            </div>
          )}
          {cluster.summary_generated_at && (
            <p className="mt-4 text-xs text-muted-foreground">
              Generated: {new Date(cluster.summary_generated_at).toLocaleString()}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Articles in Cluster */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Articles in this Cluster ({articles?.results?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {articlesLoading ? (
            <div className="text-center py-4 text-muted-foreground">
              Loading articles...
            </div>
          ) : articles?.results && articles.results.length > 0 ? (
            <div className="space-y-4">
              {articles.results.map((article) => (
                <div
                  key={article.id}
                  className="flex items-start justify-between border-b pb-4 last:border-0 last:pb-0"
                >
                  <div className="space-y-1 flex-1">
                    <Link
                      href={`/dashboard/articles/${article.id}`}
                      className="font-medium hover:underline line-clamp-2"
                    >
                      {article.title || "Untitled Article"}
                    </Link>
                    <p className="text-sm text-muted-foreground">
                      {article.publication || "Unknown source"} ·{" "}
                      {article.publication_date
                        ? new Date(article.publication_date).toLocaleDateString()
                        : "Unknown date"}
                    </p>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {article.excerpt}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 ml-4">
                    <Link href={`/dashboard/articles/${article.id}`}>
                      <Button size="sm" variant="outline">
                        View Article
                      </Button>
                    </Link>
                    <a
                      href={article.canonical_url}
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
            <p className="text-center text-muted-foreground py-4">
              No articles in this cluster yet
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
