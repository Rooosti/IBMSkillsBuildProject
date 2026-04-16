import json
import re
from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_ibm import ChatWatsonx
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.chat_tools import get_game_metadata, get_user_context, search_owned_games
from app.services.llm_tools import TOOLS
from app.services.recommendation_service import rank_games
from app.services.steam_store_search import search_steam_store, vector_search_games


PLANNER_PROMPT = """
You are the planning engine for Play Next.

Your job is ONLY to decide the next tool call or whether the system is ready to rank/respond.
You are NOT allowed to produce user-facing recommendation text.

Rules:
1. NEVER greet the user.
2. NEVER recommend games directly.
3. NEVER produce conversational prose for the user.
4. When you need information, call the appropriate tool.
5. If the user explicitly asks about owned games or says "my library", you MUST call `search_owned_games` first.
6. Only search the Steam store after `search_owned_games` returns zero or insufficient matches when the user asked about owned games.
7. After searches produce viable candidates, do not write an answer here. The graph will rank and respond later.
8. If a search returns zero results and another search path is relevant, call the next search tool immediately.
9. Do not invent games.
10. Do not mention tool names to the user.
"""

RESPONSE_PROMPT = """
You are the Play Next assistant, a professional Steam game recommender.

You are now writing the FINAL user-facing answer.

Rules:
1. Start with a friendly greeting that acknowledges the user's taste based on their library or request.
2. Recommend ONLY the games provided in FINAL_RECOMMENDATIONS.
3. Use the exact titles provided.
4. Never invent, substitute, or hallucinate games.
5. Clearly distinguish between games the user already owns ("From Your Library") and games they can buy ("On the Steam Store"), when both types exist.
6. Explain clearly why each game fits the user.
7. Use bold game titles and clean formatting.
8. Never mention tool names or internal system behavior.
9. If no recommendations are available, respond naturally and briefly based on the user's request without pretending you found games.
"""


class AgentState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    steam_id: str
    db: Session
    user_context: Optional[Dict[str, Any]]
    candidates: List[Dict[str, Any]]
    ranked_candidates: List[Dict[str, Any]]
    final_recommendations: List[Dict[str, Any]]
    previously_recommended_ids: List[int]
    search_queries: List[Dict[str, Any]]
    status: str
    searched_this_turn: bool
    latest_search_result_count: int
    latest_search_tools: List[str]
    next_action: str
    max_price: Optional[int]


def get_llm():
    return ChatWatsonx(
        model_id=settings.watsonx_model_id,
        url=settings.watsonx_url,
        apikey=settings.watsonx_api_key,
        project_id=settings.watsonx_project_id,
        params={
            "max_new_tokens": 1000,
            "temperature": 0.1,
        },
    )


def _extract_previously_recommended_ids(messages: List[AnyMessage]) -> List[int]:
    prev_ids: list[int] = []

    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue

        metadata = msg.additional_kwargs.get("metadata") if msg.additional_kwargs else None
        if metadata and isinstance(metadata, dict):
            recs = metadata.get("recommendations", [])
            for rec in recs:
                if isinstance(rec, dict) and rec.get("steam_app_id"):
                    try:
                        prev_ids.append(int(rec["steam_app_id"]))
                    except (TypeError, ValueError):
                        pass

        if msg.content:
            found = re.findall(r"app/(\d+)", str(msg.content))
            for app_id in found:
                try:
                    prev_ids.append(int(app_id))
                except ValueError:
                    pass

    return list(set(prev_ids))


async def gather_context_node(state: AgentState):
    """
    Entry node for each turn.

    - Gathers user context once and injects it into the conversation as a virtual tool result.
    - Resets transient per-turn fields every invocation.
    """
    base_reset = {
        "candidates": [],
        "ranked_candidates": [],
        "final_recommendations": [],
        "search_queries": [],
        "searched_this_turn": False,
        "latest_search_result_count": 0,
        "latest_search_tools": [],
        "next_action": "",
        "max_price": 1000,
        "status": "starting",
    }

    if state.get("user_context"):
        return {
            **base_reset,
            "previously_recommended_ids": _extract_previously_recommended_ids(state.get("messages", [])),
            "status": "context already gathered",
        }

    context = await get_user_context(state["db"], state["steam_id"])
    prev_ids = _extract_previously_recommended_ids(state.get("messages", []))

    virtual_tool_call_id = "call_context_init"

    ai_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_user_context",
                "args": {},
                "id": virtual_tool_call_id,
                "type": "tool_call",
            }
        ],
    )

    tool_msg = ToolMessage(
        tool_call_id=virtual_tool_call_id,
        content=json.dumps(context, default=str),
    )

    return {
        **base_reset,
        "user_context": context,
        "previously_recommended_ids": prev_ids,
        "messages": [ai_msg, tool_msg],
        "status": "analyzing gaming taste",
    }


async def analyze_request_node(state: AgentState):
    """
    Planner-only node.

    This node may emit tool calls, but it must never emit user-facing prose into the state.
    """
    llm = get_llm().bind_tools(TOOLS)

    non_system_messages = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    turn_messages: list[AnyMessage] = [SystemMessage(content=PLANNER_PROMPT)] + non_system_messages

    latest_user_text = ""
    for msg in reversed(non_system_messages):
        if isinstance(msg, HumanMessage):
            latest_user_text = str(msg.content).lower()
            break

    if "my library" in latest_user_text or "owned" in latest_user_text or "i own" in latest_user_text:
        turn_messages.append(
            SystemMessage(
                content=(
                    "The user is explicitly asking about games they already own. "
                    "You must call search_owned_games first. "
                    "Only search the Steam store after search_owned_games returns zero or insufficient matches."
                )
            )
        )

    if state.get("searched_this_turn"):
        turn_messages.append(
            SystemMessage(
                content=(
                    f"The last search tools used were {state.get('latest_search_tools', [])}. "
                    f"They returned {state.get('latest_search_result_count', 0)} candidates. "
                    "If candidates exist, do not answer the user here. "
                    "Use ranking or choose another relevant search path."
                )
            )
        )

    response = await llm.ainvoke(turn_messages)
    tool_calls = getattr(response, "tool_calls", []) or []

    if tool_calls:
        search_tools = {"search_steam_store", "search_owned_games", "semantic_search_store"}
        next_action = "search" if any(tc["name"] in search_tools for tc in tool_calls) else "tools"
        return {
            "messages": [response],
            "next_action": next_action,
            "status": "thinking",
        }

    if state.get("searched_this_turn") and state.get("candidates"):
        return {
            "next_action": "rank",
            "status": "ready to rank",
        }

    return {
        "next_action": "respond",
        "status": "ready to respond",
    }


def should_continue(state: AgentState):
    return state.get("next_action", "respond")


async def tool_node(state: AgentState):
    """
    Executes non-search tool calls.
    """
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []

    results: list[ToolMessage] = []
    ranked_candidates = state.get("ranked_candidates", [])

    for tool_call in tool_calls:
        name = tool_call["name"]
        args = tool_call.get("args", {}) or {}

        if name == "get_user_context":
            res = await get_user_context(state["db"], state["steam_id"])
            content = json.dumps(res, default=str)

        elif name == "get_game_metadata":
            res = get_game_metadata(state["db"], **args)
            content = json.dumps(res, default=str)

        elif name == "rank_recommendations":
            res = rank_games(
                db=state["db"],
                steam_id=state["steam_id"],
                candidates=args.get("candidates", []),
                previously_recommended_ids=state.get("previously_recommended_ids", []),
                max_price=state.get("max_price"),
            )
            ranked_candidates = res
            content = json.dumps({"ranked_results": res}, default=str)

        else:
            content = json.dumps(
                {"info": f"Tool {name} executed", "status": "success"},
                default=str,
            )

        results.append(
            ToolMessage(
                tool_call_id=tool_call["id"],
                content=content,
            )
        )

    return {
        "messages": results,
        "ranked_candidates": ranked_candidates,
        "status": "processing tools",
    }


async def query_refiner_node(state: AgentState):
    """
    Refines search calls using known user taste.
    """
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []

    user_context = state.get("user_context", {}) or {}
    top_tags = [t["tag"] for t in user_context.get("top_owned_tags", [])[:5] if isinstance(t, dict) and t.get("tag")]
    pref_tags = user_context.get("preferences", {}).get("favorite_tags", []) or []
    combined_taste_tags = list(set(top_tags + pref_tags))

    refined_calls: list[dict[str, Any]] = []

    for tc in tool_calls:
        name = tc["name"]

        if name == "search_steam_store":
            args = dict(tc.get("args", {}) or {})
            query_lower = str(args.get("query_text", "")).lower()

            if any(word in query_lower for word in ["taste", "my games", "like what i play", "recommend"]):
                current_tags = args.get("preferred_tags") or []
                args["preferred_tags"] = list(set(current_tags + combined_taste_tags))

            if any(word in query_lower for word in ["sale", "discount", "deal", "cheap"]):
                current_tags = args.get("preferred_tags") or []
                if "Sales" not in current_tags:
                    args["preferred_tags"] = current_tags + ["Sales"]

            refined_calls.append(
                {
                    "id": tc["id"],
                    "name": name,
                    "args": args,
                }
            )
        else:
            refined_calls.append(tc)

    return {
        "search_queries": refined_calls,
        "status": "refining search",
    }


async def search_node(state: AgentState):
    queries = state.get("search_queries", [])
    if not queries:
        last_message = state["messages"][-1]
        queries = getattr(last_message, "tool_calls", []) or []

    results: list[ToolMessage] = []
    new_candidates: list[dict[str, Any]] = []

    for tc in queries:
        name = tc["name"]
        args = tc.get("args", {}) or {}

        if name == "search_steam_store":
            res = search_steam_store(**args)
            found = res.get("results", []) or []
            new_candidates.extend(found)
            content = json.dumps(res, default=str)

        elif name == "search_owned_games":
            res = search_owned_games(
                db=state["db"],
                steam_id=state["steam_id"],
                **args,
            )
            found = res.get("results", []) or []
            new_candidates.extend(found)
            content = json.dumps(res, default=str)

        elif name == "semantic_search_store":
            res = await vector_search_games(**args)
            found = res.get("results", []) or []
            new_candidates.extend(found)
            content = json.dumps(res, default=str)

        else:
            found = []
            content = json.dumps({"info": "Skipped in search node"}, default=str)

        results.append(
            ToolMessage(
                tool_call_id=tc["id"],
                content=content,
            )
        )

    deduped: dict[int, dict[str, Any]] = {}
    for game in new_candidates:
        app_id = game.get("steam_app_id")
        if not app_id:
            continue
        try:
            deduped[int(app_id)] = game
        except (TypeError, ValueError):
            continue

    final_candidates = list(deduped.values())

    return {
        "messages": results,
        "candidates": final_candidates,
        "searched_this_turn": True,
        "latest_search_result_count": len(final_candidates),
        "latest_search_tools": [tc["name"] for tc in queries],
        "status": "search complete",
    }


def after_search(state: AgentState):
    if state.get("latest_search_result_count", 0) > 0:
        return "rank"
    return "analyze"


def dedupe_games(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[int, dict[str, Any]] = {}

    for game in games:
        app_id = game.get("steam_app_id")
        if not app_id:
            continue

        try:
            app_id_int = int(app_id)
        except (TypeError, ValueError):
            continue

        existing = by_id.get(app_id_int)
        if existing is None:
            by_id[app_id_int] = game
            continue

        if len(json.dumps(game, default=str)) > len(json.dumps(existing, default=str)):
            by_id[app_id_int] = game

    return list(by_id.values())


def rank_node(state: AgentState):
    candidates = dedupe_games(state.get("candidates", []))

    if not candidates:
        return {
            "ranked_candidates": [],
            "final_recommendations": [],
            "status": "no candidates found to rank",
        }

    ranked = rank_games(
        db=state["db"],
        steam_id=state["steam_id"],
        candidates=candidates,
        previously_recommended_ids=state.get("previously_recommended_ids", []),
        max_price=state.get("max_price"),
    )

    return {
        "ranked_candidates": ranked,
        "final_recommendations": ranked[:5],
        "status": "ranking recommendations",
    }


async def respond_node(state: AgentState):
    llm = get_llm()
    final_recommendations = state.get("final_recommendations", [])

    # Strip existing system messages so planner instructions do not leak into the final answer generation.
    base_messages = [m for m in state["messages"] if not isinstance(m, SystemMessage)]
    messages: list[AnyMessage] = [SystemMessage(content=RESPONSE_PROMPT)] + base_messages

    if final_recommendations:
        allowed_games = [
            {
                "steam_app_id": game.get("steam_app_id"),
                "title": game.get("title"),
                "is_owned": game.get("is_owned"),
                "short_description": game.get("short_description"),
                "price_formatted": game.get("price_formatted"),
                "store_url": game.get("store_url"),
            }
            for game in final_recommendations
        ]

        messages.append(
            SystemMessage(
                content=(
                    "You must only discuss the following exact games and no others. "
                    "Use the exact titles provided. Do not invent or substitute games.\n"
                    f"FINAL_RECOMMENDATIONS: {json.dumps(allowed_games, default=str)}"
                )
            )
        )
    else:
        messages.append(
            SystemMessage(
                content=(
                    "No new candidates were found. Respond naturally to the user's last message. "
                    "Do not pretend that recommendations were found."
                )
            )
        )

    response = await llm.ainvoke(messages)

    final_ai_message = AIMessage(
        content=response.content,
        additional_kwargs={
            **(response.additional_kwargs or {}),
            "metadata": {
                "recommendations": final_recommendations,
            },
        },
        response_metadata=getattr(response, "response_metadata", {}),
    )

    return {
        "messages": [final_ai_message],
        "status": "complete",
    }


def create_recommendation_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("analyze", analyze_request_node)
    workflow.add_node("refine", query_refiner_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("search", search_node)
    workflow.add_node("rank", rank_node)
    workflow.add_node("respond", respond_node)

    workflow.set_entry_point("gather_context")
    workflow.add_edge("gather_context", "analyze")

    workflow.add_conditional_edges(
        "analyze",
        should_continue,
        {
            "tools": "tools",
            "search": "refine",
            "rank": "rank",
            "respond": "respond",
            END: END,
        },
    )

    workflow.add_edge("tools", "analyze")
    workflow.add_edge("refine", "search")

    workflow.add_conditional_edges(
        "search",
        after_search,
        {
            "rank": "rank",
            "analyze": "analyze",
        },
    )

    workflow.add_edge("rank", "respond")
    workflow.add_edge("respond", END)

    return workflow.compile()


recommendation_graph = create_recommendation_graph()
