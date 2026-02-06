import json
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import urlopen

import typer
from dotenv import find_dotenv, load_dotenv
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from core.context import Context
from core.logger import get_logger

_ = load_dotenv(find_dotenv(), override=True)


DESCRIPTION = "Weather agent using tools and LangChain."


SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location.
If you can tell from the question that they mean wherever they are,
use the get_user_location tool to find their location.
"""


OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


@dataclass
class ResponseFormat:
    punny_response: str
    weather_condition: str | None = None


logger = get_logger(__name__)


def _geocode_location(location: str) -> tuple[float, float, str] | None:
    params = {
        "name": location,
        "count": 1,
        "language": "en",
        "format": "json",
    }
    url = OPEN_METEO_GEOCODE_URL + "?" + urlencode(params)
    with urlopen(url, timeout=5) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    results = data.get("results") or []
    if not results:
        return None
    first = results[0]
    latitude = first.get("latitude")
    longitude = first.get("longitude")
    if latitude is None or longitude is None:
        return None
    name = first.get("name") or location
    return float(latitude), float(longitude), str(name)


def _fetch_current_weather(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,wind_speed_10m,weather_code",
    }
    url = OPEN_METEO_FORECAST_URL + "?" + urlencode(params)
    with urlopen(url, timeout=5) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    return data.get("current") or {}


@tool
def get_weather_for_location(location: str) -> str:
    """Get the current weather for a specific location using Open-Meteo."""
    logger.info("get_weather_for_location called with location=%s", location)
    try:
        geo = _geocode_location(location)
        if geo is None:
            return f"I could not find weather data for {location}."
        lat, lon, resolved_name = geo
        current = _fetch_current_weather(lat, lon)
        if not current:
            return f"I could not fetch current weather for {resolved_name}."
        temperature = current.get("temperature_2m")
        wind_speed = current.get("wind_speed_10m")
        parts: list[str] = []
        if temperature is not None:
            parts.append(f"{temperature}°C")
        if wind_speed is not None:
            parts.append(f"wind {wind_speed} m/s")
        details = ", ".join(parts) if parts else "no details available"
        return f"Current weather in {resolved_name}: {details}."
    except Exception:
        logger.exception("Error getting weather for location=%s", location)
        return f"I had trouble getting the weather for {location}."


@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Get the user's location based on their user ID."""
    user_id = runtime.context.user_id
    logger.info("get_user_location called with user_id=%s", user_id)
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


cli = typer.Typer()


def _run_test(city: str) -> None:
    config: RunnableConfig = {"configurable": {"thread_id": "1"}}
    response = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": f"What's the weather like in {city}?"}
            ]
        },
        config=config,
        context=Context(user_id="1"),
    )

    response_msg = response["structured_response"]
    print(f"Punny Response: {response_msg.punny_response}")
    print(f"Weather Condition: {response_msg.weather_condition}")


@cli.command()
def test(city: str = typer.Option(..., "--city", help="City to get weather for")):
    _run_test(city)


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if args and args[0] == "test":
        args = args[1:]
    sys.argv = [sys.argv[0]] + args
    typer.run(test)


TOOLS = [get_weather_for_location, get_user_location]
