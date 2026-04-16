import asyncio
import json
import re
import textwrap
from functools import lru_cache
from typing import AsyncGenerator, List, Dict, Any

from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from sqlalchemy import select
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage

from app.core.config import settings
from app.models.chat_message import ChatMessage
from app.services.recommendation_graph import recommendation_graph


def normalize_chat_markdown(text: str) -> str:
    # Remove any JSON-like structures that might have leaked
    text = re.sub(r'\{"name":\s*"[^"]*",\s*"(parameters|arguments)":\s*\{.*\}\}', '', text, flags=re.DOTALL)
    
    text = textwrap.dedent(text).strip()
    text = text.replace("\t", "  ")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text


def load_recent_chat_history_as_langchain(
    db: Session,
    conversation_id: int,
    limit: int = 12,
) -> List[Any]:
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    ).all()

    rows = list(reversed(rows))

    messages = []
    for row in rows:
        if row.role == "user":
            messages.append(HumanMessage(content=row.content))
        elif row.role == "assistant":
            # Pass metadata if it exists (like recommended IDs)
            messages.append(AIMessage(
                content=row.content,
                additional_kwargs={"metadata": row.metadata_json or {}}
            ))
    return messages


async def answer_chat_message_stream(
    db: Session,
    steam_id: str,
    conversation_id: int,
    user_message: str,
) -> AsyncGenerator[dict, None]:
    user_msg_row = ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg_row)
    db.commit()

    history = load_recent_chat_history_as_langchain(
        db=db,
        conversation_id=conversation_id,
        limit=12,
    )

    initial_state = {
        "messages": history,
        "steam_id": steam_id,
        "db": db,
        "user_context": None,
        "candidates": [],
        "ranked_candidates": [],
        "final_recommendations": [],
        "previously_recommended_ids": [],
        "search_queries": [],
        "status": "starting",
        "searched_this_turn": False,
        "latest_search_result_count": 0,
        "latest_search_tools": [],
    }

    final_reply = ""
    final_recommendations = []

    async for event in recommendation_graph.astream(initial_state):
        for node_name, output in event.items():
            if "status" in output:
                yield {"status": output["status"]}

            if "final_recommendations" in output:
                final_recommendations = output.get("final_recommendations") or []

            if "messages" in output:
                last_msg = output["messages"][-1]

                if isinstance(last_msg, AIMessage):
                    if last_msg.content:
                        final_reply = last_msg.content

                    metadata = (last_msg.additional_kwargs or {}).get("metadata", {})
                    if isinstance(metadata, dict) and "recommendations" in metadata:
                        final_recommendations = metadata.get("recommendations") or []

    final_reply_normalized = normalize_chat_markdown(final_reply)

    assistant_msg_row = ChatMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=final_reply_normalized,
        metadata_json={
            "recommendations": final_recommendations
        },
    )
    db.add(assistant_msg_row)
    db.commit()

    yield {
        "reply": final_reply_normalized,
        "recommendations": final_recommendations,
    }
