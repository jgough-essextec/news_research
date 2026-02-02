"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Mail, FileText, Layers, PenTool, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, Article, TopicCluster, PaginatedResponse } from "@/lib/api";
import { useToast } from "@/components/ui/use-toast";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: stats, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: async () => {
      // Fetch counts from various endpoints
      const [emails, articles, clusters, posts] = await Promise.all([
        api.get("/emails/").then((r: any) => r.count || 0).catch(() => 0),
        api.get("/articles/").then((r: any) => r.count || 0).catch(() => 0),
        api.get("/clusters/").then((r: any) => r.count || 0).catch(() => 0),
        api.get("/posts/").then((r: any) => r.count || 0).catch(() => 0),
      ]);
      return { emails, articles, clusters, posts };
    },
  });

  const syncEmails = useMutation({
    mutationFn: () => api.post<{ task_id?: string }>("/emails/sync/"),
    onSuccess: (data) => {
      toast({
        title: "Email sync started",
        description: data.task_id ? `Task ID: ${data.task_id}` : "Syncing emails in background...",
      });
      // Refresh stats after a delay to allow processing
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["dashboard-stats"] });
      }, 5000);
    },
    onError: (error: Error) => {
      toast({
        title: "Sync failed",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  const statCards = [
    {
      title: "Newsletter Emails",
      value: stats?.emails || 0,
      icon: Mail,
      description: "Emails processed",
    },
    {
      title: "Articles",
      value: stats?.articles || 0,
      icon: FileText,
      description: "Articles scraped",
    },
    {
      title: "Topic Clusters",
      value: stats?.clusters || 0,
      icon: Layers,
      description: "Active clusters",
    },
    {
      title: "Blog Posts",
      value: stats?.posts || 0,
      icon: PenTool,
      description: "Posts generated",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Overview</h2>
        <Button
          variant="outline"
          size="sm"
          onClick={() => syncEmails.mutate()}
          disabled={syncEmails.isPending}
        >
          <RefreshCw className={`mr-2 h-4 w-4 ${syncEmails.isPending ? "animate-spin" : ""}`} />
          {syncEmails.isPending ? "Syncing..." : "Sync Emails"}
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {isLoading ? "..." : stat.value.toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Articles</CardTitle>
          </CardHeader>
          <CardContent>
            <RecentArticles />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Top Clusters</CardTitle>
          </CardHeader>
          <CardContent>
            <TopClusters />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function RecentArticles() {
  const { data: articles, isLoading } = useQuery({
    queryKey: ["recent-articles"],
    queryFn: () => api.get<PaginatedResponse<Article>>("/articles/?ordering=-created_at&limit=5"),
  });

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-4">
      {articles?.results?.slice(0, 5).map((article) => (
        <div key={article.id} className="flex items-start gap-4">
          <div className="flex-1 space-y-1">
            <p className="text-sm font-medium leading-none line-clamp-1">
              {article.title || "Untitled"}
            </p>
            <p className="text-xs text-muted-foreground">
              {article.publication || "Unknown source"}
            </p>
          </div>
        </div>
      ))}
      {(!articles?.results || articles.results.length === 0) && (
        <p className="text-sm text-muted-foreground">No articles yet</p>
      )}
    </div>
  );
}

function TopClusters() {
  const { data: clusters, isLoading } = useQuery({
    queryKey: ["top-clusters"],
    queryFn: () => api.get<PaginatedResponse<TopicCluster>>("/clusters/?ordering=-priority_score&limit=5"),
  });

  if (isLoading) return <div className="text-sm text-muted-foreground">Loading...</div>;

  return (
    <div className="space-y-4">
      {clusters?.results?.slice(0, 5).map((cluster) => (
        <div key={cluster.id} className="flex items-center gap-4">
          <div className="flex-1 space-y-1">
            <p className="text-sm font-medium leading-none line-clamp-1">
              {cluster.name}
            </p>
            <p className="text-xs text-muted-foreground">
              {cluster.article_count} articles
            </p>
          </div>
        </div>
      ))}
      {(!clusters?.results || clusters.results.length === 0) && (
        <p className="text-sm text-muted-foreground">No clusters yet</p>
      )}
    </div>
  );
}
