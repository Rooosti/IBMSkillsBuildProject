"use client";

import { Button } from "@/components/ui/button";

type SteamLoginButtonProps = {
  isSignedIn: boolean;
  onClick: () => void;
  compact?: boolean;
};

export function SteamLoginButton({
  isSignedIn,
  onClick,
  compact = false,
}: SteamLoginButtonProps) {
  return (
    <Button
      onClick={onClick}
      variant="ghost"
      className={
        compact
          ? "rounded-2xl bg-white/5 px-4 text-zinc-100 hover:bg-white/10"
          : "w-full rounded-2xl border border-zinc-700/50 bg-white/5 py-6 text-base text-zinc-100 hover:bg-white/10"
      }
    >
      {isSignedIn ? "Steam connected" : "Connect Steam"}
    </Button>
  );
}
