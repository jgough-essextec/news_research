"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Save, Eye, Code } from "lucide-react";
import { api, BlogPost } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/use-toast";

export default function PostEditPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const postId = params.id as string;

  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [content, setContent] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const { data: post, isLoading, error } = useQuery({
    queryKey: ["post", postId],
    queryFn: () => api.get<BlogPost>(`/posts/${postId}/`),
    enabled: !!postId,
  });

  useEffect(() => {
    if (post) {
      setTitle(post.title || "");
      setExcerpt(post.excerpt || "");
      setContent(post.content_markdown || "");
    }
  }, [post]);

  const updatePost = useMutation({
    mutationFn: (data: Partial<BlogPost>) =>
      api.patch<BlogPost>(`/posts/${postId}/`, data),
    onSuccess: () => {
      toast({ title: "Post saved successfully" });
      queryClient.invalidateQueries({ queryKey: ["post", postId] });
    },
    onError: () => {
      toast({ title: "Failed to save post", variant: "destructive" });
    },
  });

  const handleSave = () => {
    updatePost.mutate({
      title,
      excerpt,
      content_markdown: content,
    });
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
          Cancel
        </Button>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowPreview(!showPreview)}
          >
            {showPreview ? (
              <>
                <Code className="mr-2 h-4 w-4" />
                Edit
              </>
            ) : (
              <>
                <Eye className="mr-2 h-4 w-4" />
                Preview
              </>
            )}
          </Button>
          <Button
            onClick={handleSave}
            disabled={updatePost.isPending}
          >
            <Save className={`mr-2 h-4 w-4 ${updatePost.isPending ? "animate-pulse" : ""}`} />
            Save
          </Button>
        </div>
      </div>

      {/* Title */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Title</label>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Enter post title..."
          className="text-lg"
        />
      </div>

      {/* Excerpt */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Excerpt</label>
        <Input
          value={excerpt}
          onChange={(e) => setExcerpt(e.target.value)}
          placeholder="Brief description for search results and previews..."
        />
      </div>

      {/* Content */}
      <Card className="min-h-[500px]">
        <CardHeader>
          <CardTitle className="text-lg">
            {showPreview ? "Preview" : "Content (Markdown)"}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {showPreview ? (
            <div className="prose prose-sm max-w-none dark:prose-invert min-h-[400px]">
              {post.content_html ? (
                <div dangerouslySetInnerHTML={{ __html: post.content_html }} />
              ) : (
                <div className="whitespace-pre-wrap">{content}</div>
              )}
            </div>
          ) : (
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full min-h-[400px] resize-y rounded-md border bg-background p-4 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              placeholder="Write your blog post content in Markdown..."
            />
          )}
        </CardContent>
      </Card>

      {/* Tips */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Markdown Tips</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm text-muted-foreground">
            <div>
              <code className="bg-muted px-1 rounded"># Heading 1</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">## Heading 2</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">**bold**</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">*italic*</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">[link](url)</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">- bullet list</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">1. numbered list</code>
            </div>
            <div>
              <code className="bg-muted px-1 rounded">`inline code`</code>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
