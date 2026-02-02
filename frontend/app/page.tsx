import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="max-w-2xl text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
          AI News Aggregator
        </h1>
        <p className="mt-6 text-lg leading-8 text-muted-foreground">
          Aggregate AI news from your favorite newsletters, automatically
          deduplicate and cluster related articles, and generate insightful blog
          posts with AI.
        </p>
        <div className="mt-10 flex items-center justify-center gap-x-6">
          <Link href="/login">
            <Button size="lg">Get Started</Button>
          </Link>
        </div>
      </div>
    </main>
  );
}
