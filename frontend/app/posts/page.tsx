"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { PenTool, Plus, Eye, Edit } from "lucide-react";
import { api, BlogPost, PaginatedResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function PostsPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["posts", page],
    queryFn: () =>
      api.get<PaginatedResponse<BlogPost>>(`/posts/?page=${page}`),
  });

  const statusColors: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700",
    generating: "bg-blue-100 text-blue-700",
    review: "bg-purple-100 text-purple-700",
    published: "bg-green-100 text-green-700",
    archived: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Blog Posts</h2>
        <Link href="/posts/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Generate Post
          </Button>
        </Link>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground">Loading...</div>
      ) : (
        <>
          <div className="grid gap-4">
            {data?.results?.map((post) => (
              <Card key={post.id}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      {post.header_image && (
                        <img
                          src={post.header_image}
                          alt=""
                          className="h-16 w-24 rounded object-cover"
                        />
                      )}
                      <div className="space-y-1">
                        <CardTitle className="text-lg line-clamp-1">
                          {post.title}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          {post.author_name} ·{" "}
                          {new Date(post.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`rounded px-2 py-0.5 text-xs ${
                        statusColors[post.status] || statusColors.draft
                      }`}
                    >
                      {post.status}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="mb-4 text-sm text-muted-foreground line-clamp-2">
                    {post.excerpt}
                  </p>
                  <div className="flex items-center justify-between">
                    <div className="text-xs text-muted-foreground">
                      {post.cluster_name && (
                        <span>From cluster: {post.cluster_name}</span>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Link href={`/posts/${post.id}`}>
                        <Button variant="outline" size="sm">
                          <Eye className="mr-2 h-4 w-4" />
                          View
                        </Button>
                      </Link>
                      <Link href={`/posts/${post.id}/edit`}>
                        <Button variant="outline" size="sm">
                          <Edit className="mr-2 h-4 w-4" />
                          Edit
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}

            {(!data?.results || data.results.length === 0) && (
              <Card>
                <CardContent className="flex flex-col items-center justify-center py-12">
                  <PenTool className="mb-4 h-12 w-12 text-muted-foreground" />
                  <h3 className="mb-2 text-lg font-semibold">No posts yet</h3>
                  <p className="mb-4 text-sm text-muted-foreground">
                    Generate your first blog post from a topic cluster
                  </p>
                  <Link href="/posts/new">
                    <Button>
                      <Plus className="mr-2 h-4 w-4" />
                      Generate Post
                    </Button>
                  </Link>
                </CardContent>
              </Card>
            )}
          </div>

          {data && data.results && data.results.length > 0 && (
            <div className="flex items-center justify-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={!data.previous}
              >
                Previous
              </Button>
              <span className="text-sm text-muted-foreground">Page {page}</span>
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
