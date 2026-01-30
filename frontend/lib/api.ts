const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const response = await fetch(url, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async patch<T>(endpoint: string, data: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }
}

export const api = new ApiClient(API_BASE_URL);

// Type definitions for API responses
export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  email: string;
  name: string;
  avatar_url: string;
  gmail_connected: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface NewsletterEmail {
  id: number;
  gmail_message_id: string;
  sender_email: string;
  sender_name: string;
  subject: string;
  received_date: string;
  snippet: string;
  is_processed: boolean;
  processed_at: string | null;
  link_count: number;
  created_at: string;
}

export interface Article {
  id: number;
  canonical_url: string;
  title: string;
  author: string;
  publication: string;
  publication_date: string | null;
  excerpt: string;
  word_count: number;
  scrape_status: string;
  topic_cluster: number | null;
  cluster_name: string | null;
  og_image: string;
  created_at: string;
}

// Extended article interface with full content for detail view
export interface ArticleDetail extends Article {
  content_text: string;
  content_html: string;
  summary: string;
  embedding_status: string;
  scraped_at: string | null;
  updated_at: string;
}

export interface TopicCluster {
  id: number;
  name: string;
  slug: string;
  description: string;
  primary_article: number | null;
  primary_article_title: string | null;
  article_count: number;
  priority_score: number;
  master_summary: string;
  summary_generated_at: string | null;
  is_active: boolean;
  last_article_added_at: string | null;
  created_at: string;
}

export interface BlogPost {
  id: number;
  title: string;
  slug: string;
  content_markdown: string;
  content_html: string;
  excerpt: string;
  status: string;
  created_by: number;
  author_name: string;
  source_cluster: number | null;
  cluster_name: string | null;
  header_image: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}
