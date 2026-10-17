"""Guide section 26, "Core MVP Demo". Requires the FastAPI service running
(with a real ANTHROPIC_API_KEY configured) at CORVID_API_BASE_URL.

Run: python scripts/demos/demo_1_production_migration.py
"""

from _common import client, header, show

PROJECT = "peach-demo1"


def main() -> None:
    with client() as c:
        header("Event: agent runs `prisma migrate dev` against production and it fails")
        event = c.post(
            "/events",
            json={
                "content": (
                    "Running `prisma migrate dev` against production failed because production already "
                    "contains applied migrations. The fix is to use `prisma migrate deploy` for production "
                    "instead of `prisma migrate dev`, which is meant for local development only."
                ),
                "event_type": "tool_error",
                "project_id": PROJECT,
                "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
            },
        ).json()
        show("Episode", event)

        if not event["encoded"]:
            print("\n(!) Salience was below the encode threshold -- nothing durable was learned. Stopping demo.")
            return

        memories = c.get("/memories", params={"project_id": PROJECT}).json()
        show("Durable memories extracted", memories)
        if not memories:
            print("\n(!) No memory was extracted -- check ANTHROPIC_API_KEY is set on the running API process.")
            return

        header("Later: goal is 'Deploy the API' -- the query never says 'migrate dev'")
        recall = c.post(
            "/recall",
            json={
                "query": "Deploy the API",
                "goal_state": {
                    "project": PROJECT,
                    "environment": "production",
                    "task": "database_migration",
                    "active_tools": ["prisma"],
                    "active_files": ["prisma/schema.prisma"],
                },
            },
        ).json()
        show("Working memory returned", recall)

        if recall["working_memory"]:
            print("\n>>> The migration warning activated via goal/context match, not query text overlap.")
        else:
            print("\n(!) Nothing activated -- check associations on the extracted memory.")


if __name__ == "__main__":
    main()
