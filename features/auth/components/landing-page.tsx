"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { SteamLoginButton } from "@/features/auth/components/steam-login-button";
import { ChatShell } from "@/features/chat/components/chat-shell";
import { env } from "@/lib/config/env";

type SessionResponse = {
  authenticated: boolean;
  steam_id: string | null;
};

export function LandingPage() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadSession() {
      try {
        const response = await fetch(`${env.apiBaseUrl}/auth/session`, {
          method: "GET",
          credentials: "include",
          cache: "no-store",
        });

        if (!response.ok) {
          throw new Error("Failed to load session");
        }

        const data = (await response.json()) as SessionResponse;

        if (isMounted) {
          setIsSignedIn(Boolean(data.authenticated));
        }
      } catch (error) {
        console.error("Session check failed:", error);

        if (isMounted) {
          setIsSignedIn(false);
        }
      } finally {
        if (isMounted) {
          setIsCheckingSession(false);
        }
      }
    }

    void loadSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const handleSteamSignIn = async () => {
    if (isCheckingSession) return;

    if (isSignedIn) {
      try {
        await fetch(`${env.apiBaseUrl}/auth/logout`, {
          method: "POST",
          credentials: "include",
        });

        setIsSignedIn(false);
      } catch (error) {
        console.error("Logout failed:", error);
      }

      return;
    }

    window.location.href = `${env.apiBaseUrl}/auth/steam`;
  };

  return (
    <div
      className="min-h-dvh text-zinc-100"
      style={{
        background:
          "linear-gradient(135deg, #020202 0%, #120304 22%, #2a0508 48%, #09090b 72%, #000000 100%)",
        backgroundSize: "200% 200%",
        animation: "ambient-gradient 14s ease-in-out infinite",
      }}
    >
      <div className="mx-auto flex min-h-dvh w-full max-w-5xl flex-col px-4 py-6 sm:px-6 lg:px-8">
        <header className="flex h-12 shrink-0 items-center justify-end">
          <SteamLoginButton
            isSignedIn={isSignedIn}
            onClick={handleSteamSignIn}
            compact
          />
        </header>

        <main className="grid flex-1 place-items-center">
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="h-[calc(100dvh-7rem)] w-full"
          >
            <ChatShell isSignedIn={isSignedIn} />
          </motion.section>
        </main>
      </div>
    </div>
  );
}
