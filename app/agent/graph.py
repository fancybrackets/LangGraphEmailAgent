from functools import lru_cache

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.state import AgentState
from app.agent.tool_registry import get_tools
from app.config import settings


SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are a privacy-first local assistant. "
        "Keep answers clear and practical. "
        "Use available tools when needed."
    )
)


def _should_continue(state: AgentState):
    last_message = state["messages"][-1]
    if getattr(last_message, "tool_calls", None):
        return "tools"
    return END


def _build_graph(model_name: str):
    tools = get_tools()
    tool_node = ToolNode(tools)
    llm = ChatOllama(model=model_name).bind_tools(tools)

    def call_model(state: AgentState):
        messages = [SYSTEM_PROMPT] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", _should_continue)
    workflow.add_edge("tools", "agent")
    return workflow.compile(checkpointer=MemorySaver())


@lru_cache(maxsize=8)
def get_compiled_app(model_name: str | None = None):
    return _build_graph(model_name or settings.default_model)


def run_agent_turn(message: str, thread_id: str, model_name: str | None = None) -> str:
    app = get_compiled_app(model_name)
    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [HumanMessage(content=message)]}

    final_text = ""
    for output in app.stream(inputs, config=config, stream_mode="values"):
        last = output["messages"][-1]
        if isinstance(last, AIMessage) and last.content:
            final_text = last.content
    return final_text or "(No response generated.)"
