"use client";

import { AnimatePresence, motion } from "framer-motion";

type ChatHeaderProps = {
  isSignedIn: boolean;
  status: string;
};

export function ChatHeader({
  isSignedIn,
  status,
}: ChatHeaderProps) {
  const isBusy = status !== "ready" && status !== "awaiting sign-in";
  
  const label = !isSignedIn
    ? "awaiting sign-in"
    : status;

  return (
    <div className="flex items-center justify-between gap-3">
      <motion.div
        layout
        className="
          inline-flex items-center gap-2 rounded-full
          px-3 py-1.5 text-xs text-zinc-300
        "
      >
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={label}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
            className="flex items-center gap-2"
          >
            {isSignedIn && isBusy ? (
              <>
                <motion.span
                  aria-hidden="true"
                  className="flex items-center gap-1"
                >
                  <motion.span
                    className="h-1.5 w-1.5 rounded-full bg-red-400"
                    animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity, delay: 0 }}
                  />
                  <motion.span
                    className="h-1.5 w-1.5 rounded-full bg-red-400"
                    animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity, delay: 0.12 }}
                  />
                  <motion.span
                    className="h-1.5 w-1.5 rounded-full bg-red-400"
                    animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
                    transition={{ duration: 0.8, repeat: Infinity, delay: 0.24 }}
                  />
                </motion.span>

                <span className="text-zinc-200">{status}</span>
              </>
            ) : (
              <>
                <span
                  className={`h-2 w-2 rounded-full ${
                    isSignedIn ? "bg-emerald-400" : "bg-amber-400"
                  }`}
                />
                <span>{label}</span>
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
