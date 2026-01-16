from __future__ import annotations

from core.agent_discovery import discover_agents


def main() -> None:
    agents = discover_agents()
    if not agents:
        print("No agents found")
        return
    items = sorted(agents.items())
    width = max(len(slug) for slug, _ in items)
    for slug, info in items:
        description = getattr(info, "description", None)
        if description:
            padding = " " * (width - len(slug))
            print(f"{slug}{padding}  {description}")
        else:
            print(slug)


if __name__ == "__main__":
    main()
