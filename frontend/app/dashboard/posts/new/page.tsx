"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Layers, Sparkles } from "lucide-react";
import { api, TopicCluster, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function NewPostPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null);

  const { data: clusters, isLoading } = useQuery({
    queryKey: ["clusters-for-post"],
    queryFn: () =>
      api.get<PaginatedResponse<TopicCluster>>(
        `/clusters/?ordering=-priority_score&page_size=50`
      ),
  });

  const generatePost = useMutation({
    mutationFn: (clusterId: number) =>
      api.post<{ post_id: number }>(`/clusters/${clusterId}/generate_post/`),
    onSuccess: (data) => {
      toast({ title: "Blog post generation started" });
      if (data?.post_id) {
        router.push(`/dashboard/posts/${data.post_id}`);
      } else {
        router.push("/dashboard/posts");
      }
    },
    onError: () => {
      toast({ title: "Failed to generate blog post", variant: "destructive" });
    },
  });

  const handleGenerate = () => {
    if (selectedCluster) {
      generatePost.mutate(selectedCluster);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
      </div>

      <div>
        <h1 className="text-2xl font-bold">Generate New Blog Post</h1>
        <p className="text-muted-foreground mt-1">
          Select a topic cluster to generate a blog post from its articles
        </p>
      </div>

      {/* Cluster Selection */}
      <Card>
        <CardHeader>
          <CardTitle>Select a Topic Cluster</CardTitle>
          <CardDescription>
            Choose a cluster with articles to generate a comprehensive blog post
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading clusters...
            </div>
          ) : clusters?.results && clusters.results.length > 0 ? (
            <div className="grid gap-3 md:grid-cols-2">
              {clusters.results.map((cluster) => (
                <div
                  key={cluster.id}
                  className={`cursor-pointer rounded-lg border p-4 transition-colors ${
                    selectedCluster === cluster.id
                      ? "border-primary bg-primary/5"
                      : "hover:bg-muted/50"
                  }`}
                  onClick={() => setSelectedCluster(cluster.id)}
                >
                  <div className="flex items-start gap-3">
                    <Layers className="h-5 w-5 text-primary mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium line-clamp-1">{cluster.name}</h3>
                      <p className="text-sm text-muted-foreground mt-1">
                        {cluster.article_count} articles · Score: {cluster.priority_score.toFixed(1)}
                      </p>
                      {cluster.master_summary && (
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                          {cluster.master_summary}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Layers className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="font-medium">No clusters available</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Process some articles first to create topic clusters
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Generate Button */}
      <div className="flex justify-end">
        <Button
          size="lg"
          onClick={handleGenerate}
          disabled={!selectedCluster || generatePost.isPending}
        >
          <Sparkles className={`mr-2 h-4 w-4 ${generatePost.isPending ? "animate-pulse" : ""}`} />
          {generatePost.isPending ? "Generating..." : "Generate Blog Post"}
        </Button>
      </div>
    </div>
  );
}
