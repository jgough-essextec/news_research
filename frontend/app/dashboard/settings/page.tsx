"use client";

import { useSession } from "next-auth/react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { Mail, User, Check, AlertCircle } from "lucide-react";
import { api, User as UserType } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useToast } from "@/components/ui/use-toast";
import { useEffect } from "react";

export default function SettingsPage() {
  const { data: session } = useSession();
  const searchParams = useSearchParams();
  const { toast } = useToast();

  const { data: user, isLoading } = useQuery({
    queryKey: ["current-user"],
    queryFn: () => api.get<UserType>("/auth/me/"),
  });

  // Show toast if redirected from Gmail connection
  useEffect(() => {
    const gmailStatus = searchParams.get("gmail");
    if (gmailStatus === "connected") {
      toast({
        title: "Gmail Connected",
        description: "Your Gmail account has been successfully connected.",
      });
    }
  }, [searchParams, toast]);

  const connectGmail = () => {
    window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/auth/gmail/`;
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">Settings</h2>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Profile Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : user ? (
              <>
                <div>
                  <label className="text-sm font-medium">Email</label>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                </div>
                <div>
                  <label className="text-sm font-medium">Name</label>
                  <p className="text-sm text-muted-foreground">{user.name || "Not set"}</p>
                </div>
                <div>
                  <label className="text-sm font-medium">Role</label>
                  <p className="text-sm text-muted-foreground">
                    {user.is_admin ? "Administrator" : "User"}
                  </p>
                </div>
                <div>
                  <label className="text-sm font-medium">Member Since</label>
                  <p className="text-sm text-muted-foreground">
                    {new Date(user.created_at).toLocaleDateString()}
                  </p>
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Unable to load profile</p>
            )}
          </CardContent>
        </Card>

        {/* Gmail Connection Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="h-5 w-5" />
              Gmail Integration
            </CardTitle>
            <CardDescription>
              Connect your Gmail to import AI newsletters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {isLoading ? (
              <p className="text-sm text-muted-foreground">Loading...</p>
            ) : user?.gmail_connected ? (
              <div className="flex items-center gap-2 text-green-600">
                <Check className="h-5 w-5" />
                <span>Gmail is connected</span>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-start gap-2 text-amber-600">
                  <AlertCircle className="h-5 w-5 mt-0.5" />
                  <span className="text-sm">
                    Gmail is not connected. Connect your account to start importing
                    newsletters.
                  </span>
                </div>
                <Button onClick={connectGmail}>Connect Gmail</Button>
              </div>
            )}

            <div className="border-t pt-4 mt-4">
              <h4 className="font-medium mb-2">How it works</h4>
              <ol className="text-sm text-muted-foreground space-y-2 list-decimal list-inside">
                <li>Create a label called <code className="bg-muted px-1 rounded">AI-News</code> in Gmail</li>
                <li>Apply this label to your AI newsletters</li>
                <li>We&apos;ll automatically fetch and process new emails</li>
              </ol>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
