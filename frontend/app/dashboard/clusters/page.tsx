"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Layers, FileText, Sparkles } from "lucide-react";
import { api, TopicCluster, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function ClustersPage() {
  const [page, setPage] = useState(1);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["clusters", page],
    queryFn: () =>
      api.get<PaginatedResponse<TopicCluster>>(
        `/clusters/?page=${page}&ordering=-priority_score`
      ),
  });

  const generateSummary = useMutation({
    mutationFn: (clusterId: number) =>
      api.post(`/clusters/${clusterId}/generate_summary/`),
    onSuccess: () => {
      toast({ title: "Summary generation started" });
      queryClient.invalidateQueries({ queryKey: ["clusters"] });
    },
    onError: () => {
      toast({ title: "Failed to generate summary", variant: "destructive" });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Topic Clusters</h2>
        <p className="text-sm text-muted-foreground">
          {data?.count || 0} total clusters
        </p>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {data?.results?.map((cluster) => (
              <Card key={cluster.id} className="flex flex-col">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <Layers className="h-5 w-5 text-primary" />
                    <span className="text-xs text-muted-foreground">
                      Score: {cluster.priority_score.toFixed(1)}
                    </span>
                  </div>
                  <CardTitle className="line-clamp-2 text-lg">
                    {cluster.name}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-1 flex-col">
                  <div className="mb-4 flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileText className="h-4 w-4" />
                      {cluster.article_count} articles
                    </span>
                  </div>

                  {cluster.master_summary ? (
                    <p className="mb-4 line-clamp-3 text-sm text-muted-foreground">
                      {cluster.master_summary}
                    </p>
                  ) : (
                    <p className="mb-4 text-sm italic text-muted-foreground">
                      No summary generated yet
                    </p>
                  )}

                  <div className="mt-auto flex gap-2">
                    <Link href={`/dashboard/clusters/${cluster.id}`} className="flex-1">
                      <Button variant="outline" className="w-full" size="sm">
                        View Details
                      </Button>
                    </Link>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => generateSummary.mutate(cluster.id)}
                      disabled={generateSummary.isPending}
                    >
                      <Sparkles className="h-4 w-4" />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {data && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={!data.previous}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">
                Page {page}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.next}
              >
                Next
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
