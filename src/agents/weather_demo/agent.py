from dataclasses import dataclass

from dotenv import find_dotenv, load_dotenv
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

_ = load_dotenv(find_dotenv(), override=True)


SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question
that they mean wherever they are, use the get_user_location tool to find their location.
"""


@dataclass
class Context:
    user_id: str


@dataclass
class ResponseFormat:
    punny_response: str
    weather_condition: str | None = None


@tool
def get_weather_for_location(location: str) -> str:
    """Get the weather for a specific location."""
    print(">>>[get_weather_for_location] called with location:", location)
    return f"It is sunny in {location}!"


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Get the user's location based on their user ID."""
    user_id = runtime.context.user_id
    print(">>>[get_user_location] called with user_id:", user_id)
    return "Sydney" if user_id == "1" else "Melbourne"


model = init_chat_model("gpt-4.1", temperature=0.5, timeout=10, max_tokens=1000)
checkpointer = InMemorySaver()

agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_weather_for_location, get_user_location],
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer,
)

import typer

cli = typer.Typer()


@cli.command()
def test(city: str = typer.Option(..., "--city", help="City to get weather for")):
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    response = agent.invoke(
        {"messages": [{"role": "user", "content": f"What's the weather like in {city}?"}]},
        config=config,
        context=Context(user_id="1"),
    )

    response_msg = response["structured_response"]
    print(f"Punny Response: {response_msg.punny_response}")
    print(f"Weather Condition: {response_msg.weather_condition}")


if __name__ == "__main__":
    cli()
