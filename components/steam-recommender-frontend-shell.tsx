import React, { useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Steam, SendHorizonal, Gamepad2, ShieldCheck, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

type Message = {
  id: string;
  role: "assistant" | "user";
  content: string;
};

const starterPrompts = [
  "What should I install tonight from my library?",
  "Something like Hades but more relaxed",
  "Good co-op game for two people on Steam Deck",
];

export default function SteamRecommenderFrontendShell() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "Hey there — sign in with Steam to sync your library, then ask for a recommendation in plain English.",
    },
  ]);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const placeholder = useMemo(() => {
    if (!isSignedIn) return "Sign in with Steam to start chatting";
    return "Ask for a game recommendation...";
  }, [isSignedIn]);

  const handleSteamSignIn = () => {
    // Replace this with your real auth redirect, e.g. window.location.href = "/api/auth/steam";
    setIsSignedIn(true);
    setMessages((current) => {
      const alreadyHasPostLogin = current.some((message) => message.id === "post-login");
      if (alreadyHasPostLogin) return current;
      return [
        ...current,
        {
          id: "post-login",
          role: "assistant",
          content:
            "You’re signed in. Your chat is ready — next step is wiring this to Steam sync and the recommendation API.",
        },
      ];
    });
    window.setTimeout(() => inputRef.current?.focus(), 100);
  };

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !isSignedIn) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: trimmed,
    };

    const assistantMessage: Message = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content:
        "Frontend is ready. Wire this message to your /recommendations/query endpoint to return ranked game suggestions with explanations.",
    };

    setMessages((current) => [...current, userMessage, assistantMessage]);
    setInput("");
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-zinc-900 ring-1 ring-zinc-800">
              <Gamepad2 className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm text-zinc-400">Steam-first recommender</p>
              <h1 className="text-lg font-semibold tracking-tight">Play Next</h1>
            </div>
          </div>

          <Button
            onClick={handleSteamSignIn}
            className="rounded-2xl"
            variant={isSignedIn ? "secondary" : "default"}
          >
            <Steam className="mr-2 h-4 w-4" />
            {isSignedIn ? "Steam connected" : "Sign in with Steam"}
          </Button>
        </header>

        <main className="grid flex-1 gap-6 py-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35 }}
            className="flex flex-col gap-4"
          >
            <Card className="rounded-3xl border-zinc-800 bg-zinc-900/70 shadow-2xl shadow-black/20">
              <CardHeader>
                <CardTitle className="text-2xl tracking-tight">Find your next game faster</CardTitle>
                <CardDescription className="text-zinc-400">
                  Sign in with Steam, sync your library, and ask for recommendations in natural language.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-3">
                  <div className="flex items-start gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">Steam-first sign-in</p>
                      <p className="text-sm text-zinc-400">Connect your account and prepare for library sync.</p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-4">
                    <Sparkles className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                      <p className="font-medium">Natural-language requests</p>
                      <p className="text-sm text-zinc-400">Ask for co-op, short sessions, Steam Deck fit, and more.</p>
                    </div>
                  </div>
                </div>

                <Button onClick={handleSteamSignIn} className="w-full rounded-2xl py-6 text-base">
                  <Steam className="mr-2 h-4 w-4" />
                  {isSignedIn ? "Steam connected" : "Continue with Steam"}
                </Button>
              </CardContent>
            </Card>

            <Card className="rounded-3xl border-zinc-800 bg-zinc-900/70">
              <CardHeader>
                <CardTitle className="text-base">Try asking</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-2">
                {starterPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    disabled={!isSignedIn}
                    onClick={() => setInput(prompt)}
                    className="rounded-2xl border border-zinc-800 bg-zinc-950/60 px-4 py-3 text-left text-sm text-zinc-300 transition hover:border-zinc-700 hover:bg-zinc-950 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {prompt}
                  </button>
                ))}
              </CardContent>
            </Card>
          </motion.section>

          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="min-w-0"
          >
            <Card className="flex h-[72vh] flex-col rounded-3xl border-zinc-800 bg-zinc-900/70 shadow-2xl shadow-black/20">
              <CardHeader className="border-b border-zinc-800">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <CardTitle className="text-xl">Recommendation chat</CardTitle>
                    <CardDescription className="text-zinc-400">
                      {isSignedIn
                        ? "Connected and ready for recommendation queries."
                        : "Sign in with Steam to enable chat and library-aware recommendations."}
                    </CardDescription>
                  </div>
                  <div className="rounded-full border border-zinc-800 px-3 py-1 text-xs text-zinc-400">
                    {isSignedIn ? "ready" : "awaiting sign-in"}
                  </div>
                </div>
              </CardHeader>

              <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                <ScrollArea className="min-h-0 flex-1 px-4 py-4 sm:px-6">
                  <div className="mx-auto flex max-w-3xl flex-col gap-4">
                    {messages.map((message) => (
                      <div
                        key={message.id}
                        className={`max-w-[85%] rounded-3xl px-4 py-3 text-sm leading-6 ${
                          message.role === "user"
                            ? "ml-auto bg-zinc-100 text-zinc-900"
                            : "border border-zinc-800 bg-zinc-950/80 text-zinc-200"
                        }`}
                      >
                        {message.content}
                      </div>
                    ))}
                  </div>
                </ScrollArea>

                <div className="border-t border-zinc-800 p-4 sm:p-6">
                  <div className="mx-auto flex max-w-3xl gap-3">
                    <Input
                      ref={inputRef}
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") handleSend();
                      }}
                      placeholder={placeholder}
                      disabled={!isSignedIn}
                      className="h-12 rounded-2xl border-zinc-800 bg-zinc-950"
                    />
                    <Button
                      onClick={handleSend}
                      disabled={!isSignedIn || !input.trim()}
                      className="h-12 rounded-2xl px-4"
                    >
                      <SendHorizonal className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.section>
        </main>
      </div>
    </div>
  );
}
