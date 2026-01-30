"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ExternalLink, Search, Filter, RefreshCw } from "lucide-react";
import { api, Article, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

export default function ArticlesPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["articles", page, search],
    queryFn: () =>
      api.get<PaginatedResponse<Article>>(
        `/articles/?page=${page}&search=${search}`
      ),
  });

  const processPending = useMutation({
    mutationFn: () => api.post("/articles/process_pending/"),
    onSuccess: () => {
      toast({ title: "Processing started", description: "Pending articles are being scraped" });
      queryClient.invalidateQueries({ queryKey: ["articles"] });
    },
    onError: () => {
      toast({ title: "Failed to process articles", variant: "destructive" });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Articles</h2>
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            onClick={() => processPending.mutate()}
            disabled={processPending.isPending}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${processPending.isPending ? "animate-spin" : ""}`} />
            Process Pending
          </Button>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search articles..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 pl-10"
            />
          </div>
          <Button variant="outline" size="icon">
            <Filter className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : (
        <>
          <div className="grid gap-4">
            {data?.results?.map((article) => (
              <Link key={article.id} href={`/dashboard/articles/${article.id}`}>
                <Card className="transition-colors hover:bg-muted/50 cursor-pointer">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg line-clamp-2">
                          {article.title || "Untitled Article"}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          {article.publication || "Unknown source"} ·{" "}
                          {article.publication_date
                            ? new Date(article.publication_date).toLocaleDateString()
                            : "Unknown date"}
                        </p>
                      </div>
                      <a
                        href={article.canonical_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {article.excerpt}
                    </p>
                    <div className="mt-2 flex items-center gap-4 text-xs text-muted-foreground">
                      <span>{article.word_count} words</span>
                      {article.cluster_name && (
                        <Link
                          href={`/dashboard/clusters/${article.topic_cluster}`}
                          className="text-primary hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {article.cluster_name}
                        </Link>
                      )}
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
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>

          {data && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {data.results?.length || 0} of {data.count} articles
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
