"use client";

import Image from "next/image";
import { ExternalLink, Library, Tag } from "lucide-react";
import type { RecommendedGame } from "@/features/chat/types";

type GameRecommendationCardProps = {
  game: RecommendedGame;
};

export function GameRecommendationCard({ game }: GameRecommendationCardProps) {
  const isOwned = game.is_owned;

  return (
    <div className="flex h-[280px] w-[280px] flex-shrink-0 flex-col overflow-hidden rounded-xl border border-zinc-700/50 bg-zinc-900/50 transition-colors hover:bg-zinc-800/50">
      <div className="relative aspect-[460/215] w-full flex-shrink-0 bg-zinc-800">
        {game.header_image_url ? (
          <Image
            src={game.header_image_url}
            alt={game.title}
            fill
            className="object-cover"
            sizes="280px"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-zinc-600">
            No Image
          </div>
        )}

        {isOwned && (
          <div className="absolute top-2 right-2 flex items-center gap-1 rounded-full border border-white/10 bg-blue-600/95 px-2 py-0.5 text-[10px] font-bold text-white shadow-[0_4px_14px_rgba(0,0,0,0.45)] backdrop-blur-sm">
            <Library size={10} />
            Already Own!
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col p-3">
        <div className="mb-1 min-h-[20px]">
          <h3
            className="line-clamp-1 text-sm font-bold text-zinc-100"
            title={game.title}
          >
            {game.title}
          </h3>
        </div>

        <div className="mb-3 min-h-[32px]">
          <p className="line-clamp-2 text-xs text-zinc-400">
            {game.short_description || "No description available."}
          </p>
        </div>

        <div className="mt-auto flex min-h-[28px] items-center justify-between gap-2">
          <div className="flex flex-col justify-center">
            {!isOwned ? (
              <span className="text-xs font-medium text-emerald-400">
                {game.price_formatted || "Free"}
              </span>
            ) : (
              <span className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500">
                Already in Library
              </span>
            )}
          </div>

          <div className="flex min-w-[58px] justify-end">
            {!isOwned && game.store_url && (
              <a
                href={game.store_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 rounded-md bg-zinc-700 px-2 py-1 text-[10px] font-medium text-zinc-200 transition-colors hover:bg-zinc-600"
              >
                Steam <ExternalLink size={10} />
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
