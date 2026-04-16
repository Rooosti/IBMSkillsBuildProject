"use client";

import { forwardRef } from "react";
import { SendHorizonal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ChatInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void | Promise<void>;
  placeholder: string;
  disabled: boolean;
  isSending: boolean;
};

export const ChatInput = forwardRef<HTMLInputElement, ChatInputProps>(
  function ChatInput(
    { value, onChange, onSend, placeholder, disabled, isSending },
    ref
  ) {
    return (
      <div className="mx-auto flex max-w-3xl gap-3">
        <Input
          ref={ref}
          autoFocus={!disabled}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              void onSend();
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className="h-12 rounded-2xl bg-black/20 text-zinc-100 placeholder:text-zinc-500"
        />

        <Button
          onClick={() => void onSend()}
          disabled={disabled || isSending || !value.trim()}
          variant="ghost"
          className="h-12 rounded-2xl px-4 text-zinc-100 hover:bg-white/50"
        >
          <SendHorizonal className="h-4 w-4" />
        </Button>
      </div>
    );
  }
);
