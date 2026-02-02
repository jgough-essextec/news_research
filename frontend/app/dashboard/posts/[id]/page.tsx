"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Calendar,
  User,
  Layers,
  Edit,
  ImagePlus,
  Send,
  Archive,
} from "lucide-react";
import { api, BlogPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";

export default function PostDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const postId = params.id as string;

  const { data: post, isLoading, error } = useQuery({
    queryKey: ["post", postId],
    queryFn: () => api.get<BlogPost>(`/posts/${postId}/`),
    enabled: !!postId,
  });

  const generateImage = useMutation({
    mutationFn: () => api.post<void>(`/posts/${postId}/generate_image/`),
    onSuccess: () => {
      toast({ title: "Image generation started" });
      queryClient.invalidateQueries({ queryKey: ["post", postId] });
    },
    onError: () => {
      toast({ title: "Failed to generate image", variant: "destructive" });
    },
  });

  const publishPost = useMutation({
    mutationFn: () => api.post<void>(`/posts/${postId}/publish/`),
    onSuccess: () => {
      toast({ title: "Post published successfully" });
      queryClient.invalidateQueries({ queryKey: ["post", postId] });
    },
    onError: () => {
      toast({ title: "Failed to publish post", variant: "destructive" });
    },
  });

  const archivePost = useMutation({
    mutationFn: () => api.patch<BlogPost>(`/posts/${postId}/`, { status: "archived" }),
    onSuccess: () => {
      toast({ title: "Post archived" });
      queryClient.invalidateQueries({ queryKey: ["post", postId] });
    },
    onError: () => {
      toast({ title: "Failed to archive post", variant: "destructive" });
    },
  });

  const statusColors: Record<string, string> = {
    draft: "bg-yellow-100 text-yellow-700",
    generating: "bg-blue-100 text-blue-700",
    review: "bg-purple-100 text-purple-700",
    published: "bg-green-100 text-green-700",
    archived: "bg-gray-100 text-gray-700",
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-muted-foreground">Loading post...</div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.back()}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">Post not found</p>
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
          Back to Posts
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => generateImage.mutate()}
            disabled={generateImage.isPending || !!post.header_image}
          >
            <ImagePlus className={`mr-2 h-4 w-4 ${generateImage.isPending ? "animate-pulse" : ""}`} />
            {post.header_image ? "Image Generated" : "Generate Image"}
          </Button>
          <Link href={`/dashboard/posts/${postId}/edit`}>
            <Button variant="outline">
              <Edit className="mr-2 h-4 w-4" />
              Edit
            </Button>
          </Link>
          {post.status !== "published" && post.status !== "archived" && (
            <Button
              onClick={() => publishPost.mutate()}
              disabled={publishPost.isPending}
            >
              <Send className={`mr-2 h-4 w-4 ${publishPost.isPending ? "animate-pulse" : ""}`} />
              Publish
            </Button>
          )}
          {post.status !== "archived" && (
            <Button
              variant="outline"
              onClick={() => archivePost.mutate()}
              disabled={archivePost.isPending}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </Button>
          )}
        </div>
      </div>

      {/* Post Header */}
      <div className="space-y-4">
        {post.header_image && (
          <div className="overflow-hidden rounded-lg">
            <img
              src={post.header_image}
              alt=""
              className="w-full max-h-96 object-cover"
            />
          </div>
        )}

        <h1 className="text-3xl font-bold">{post.title}</h1>

        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <User className="h-4 w-4" />
            {post.author_name}
          </span>
          <span className="flex items-center gap-1">
            <Calendar className="h-4 w-4" />
            {new Date(post.created_at).toLocaleDateString()}
          </span>
          {post.published_at && (
            <span className="flex items-center gap-1">
              Published: {new Date(post.published_at).toLocaleDateString()}
            </span>
          )}
          <span
            className={`rounded px-2 py-0.5 ${
              statusColors[post.status] || statusColors.draft
            }`}
          >
            {post.status}
          </span>
        </div>

        {post.source_cluster && post.cluster_name && (
          <Link
            href={`/dashboard/clusters/${post.source_cluster}`}
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            <Layers className="h-4 w-4" />
            From cluster: {post.cluster_name}
          </Link>
        )}
      </div>

      {/* Excerpt */}
      {post.excerpt && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Excerpt</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-muted-foreground italic">{post.excerpt}</p>
          </CardContent>
        </Card>
      )}

      {/* Content */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Content</CardTitle>
        </CardHeader>
        <CardContent>
          {post.content_html ? (
            <div
              className="prose prose-sm max-w-none dark:prose-invert"
              dangerouslySetInnerHTML={{ __html: post.content_html }}
            />
          ) : post.content_markdown ? (
            <div className="prose prose-sm max-w-none dark:prose-invert">
              <pre className="whitespace-pre-wrap font-sans">
                {post.content_markdown}
              </pre>
            </div>
          ) : (
            <p className="text-muted-foreground italic">
              {post.status === "generating"
                ? "Content is being generated..."
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
              <dt className="font-medium">Post ID</dt>
              <dd className="text-muted-foreground">{post.id}</dd>
            </div>
            <div>
              <dt className="font-medium">Slug</dt>
              <dd className="text-muted-foreground">{post.slug}</dd>
            </div>
            <div>
              <dt className="font-medium">Created</dt>
              <dd className="text-muted-foreground">
                {new Date(post.created_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="font-medium">Updated</dt>
              <dd className="text-muted-foreground">
                {new Date(post.updated_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
