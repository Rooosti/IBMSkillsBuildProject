"use client";

import { motion } from "framer-motion";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { GameRecommendationCard } from "./game-recommendation-card";
import type { RecommendedGame } from "@/features/chat/types";

type RecommendationsListProps = {
  recommendations: RecommendedGame[];
};

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0 },
};

export function RecommendationsList({ recommendations }: RecommendationsListProps) {
  if (!recommendations || recommendations.length === 0) return null;

  return (
    <ScrollArea className="mt-4 -mx-2 w-full min-w-0">
      <div className="w-full">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="flex gap-4 px-2 pb-4"
        >
          {recommendations.map((game) => (
            <motion.div key={game.steam_app_id} variants={itemVariants}>
              <GameRecommendationCard game={game} />
            </motion.div>
          ))}
        </motion.div>
      </div>
      <ScrollBar orientation="horizontal" className="h-3 mx-2" />
    </ScrollArea>
  );
}
