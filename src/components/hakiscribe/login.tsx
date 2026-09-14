import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { LockKeyhole, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { friendlyErrorMessage, hakiApi } from "@/lib/hakiscribe";
import { signIn } from "@/lib/auth";
import { Brand } from "./brand";

export function LoginPage({ next }: { next?: string | undefined }) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const demo = useQuery({
    queryKey: ["demo-credentials"],
    queryFn: hakiApi.demoCredentials,
    retry: false,
  });

  const login = useMutation({
    mutationFn: (body: { email: string; password: string }) => hakiApi.login(body),
    onSuccess: (data) => {
      signIn({ token: data.token, user: data.user });
      const target = next && next.startsWith("/") ? next : "/new";
      window.location.assign(target);
    },
    onError: (err: Error) => {
      setError(friendlyErrorMessage(err, "That email and password did not match an account."));
    },
  });

  function submit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    login.mutate({ email, password });
  }

  function useDemo() {
    const creds = demo.data;
    if (!creds?.enabled || !creds.email || !creds.password) return;
    setEmail(creds.email);
    setPassword(creds.password);
    setError(null);
    login.mutate({ email: creds.email, password: creds.password });
  }

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-6 px-4 py-10">
      <div className="flex flex-col items-center gap-3 text-center">
        <Brand />
        <h1 className="font-serif text-2xl text-foreground">Sign in to your workspace</h1>
        <p className="text-sm text-muted-foreground">
          Recordings, transcripts and drafted documents stay behind this sign-in.
        </p>
      </div>

      <form onSubmit={submit} className="rounded-lg border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="login-email">Email</Label>
            <Input
              id="login-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="advocate@firm.co.ke"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="login-password">Password</Label>
            <Input
              id="login-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? <p className="text-sm text-destructive">{error}</p> : null}

          <Button type="submit" disabled={login.isPending}>
            {login.isPending ? <Loader2 className="mr-2 size-4 animate-spin" aria-hidden /> : null}
            Sign in
          </Button>

          {demo.data?.enabled ? (
            <div className="rounded-md border border-dashed border-border bg-muted/40 p-3">
              <p className="text-xs text-muted-foreground">
                <span className="font-medium text-foreground">Temporary demo access.</span> This shared account exists
                for judging and will be removed before real client work.
              </p>
              <Button
                type="button"
                variant="outline"
                className="mt-2 w-full"
                onClick={useDemo}
                disabled={login.isPending}
              >
                <LockKeyhole className="mr-2 size-4" aria-hidden />
                Use demo credentials
              </Button>
            </div>
          ) : null}
        </div>
      </form>
    </div>
  );
}
