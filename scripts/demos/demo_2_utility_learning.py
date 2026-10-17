"""Guide section 27, "Second Demo — Learning From Utility". Requires the
FastAPI service running (with a real ANTHROPIC_API_KEY) at
CORVID_API_BASE_URL.

Run: python scripts/demos/demo_2_utility_learning.py
"""

from _common import client, header, show

PROJECT = "peach-demo2"
GOAL = {
    "project": PROJECT,
    "environment": "production",
    "task": "database_migration",
    "active_tools": ["prisma"],
}


def seed(c) -> None:
    header("Seeding three memories: A (occasionally relevant), B (always useful), C (never useful)")
    c.post(
        "/events",
        json={
            "content": "Production infrastructure for this project runs on AWS.",
            "event_type": "fact", "project_id": PROJECT,
            "metadata": {"environment": "production"},
        },
    )
    c.post(
        "/events",
        json={
            "content": "Never run `prisma migrate dev` against production; always use `prisma migrate deploy`.",
            "event_type": "constraint", "project_id": PROJECT,
            "metadata": {"environment": "production", "tool": "prisma", "task": "database_migration"},
        },
    )
    c.post(
        "/events",
        json={"content": "The README.md file was edited last Tuesday.", "event_type": "observation", "project_id": PROJECT},
    )
    show("Seeded memories", c.get("/memories", params={"project_id": PROJECT}).json())


def run_rounds(c, rounds: int = 8) -> None:
    header(f"Simulating {rounds} production-migration recalls")
    for i in range(rounds):
        recall = c.post("/recall", json={"query": "prepare and run the production migration", "goal_state": GOAL}).json()
        retrieval_id = recall["retrieval_id"]
        returned_ids = [m["id"] for m in recall["working_memory"]]

        memories = {m["content"][:40]: m["id"] for m in c.get("/memories", params={"project_id": PROJECT}).json()}
        used = [mid for label, mid in memories.items() if "migrate dev" in label.lower() and mid in returned_ids]

        c.post(
            "/outcomes",
            json={"retrieval_id": retrieval_id, "outcome": "success" if used else "neutral", "used_memory_ids": used, "reward": 1.0 if used else None},
        )
        print(f"  round {i + 1}: returned {len(returned_ids)} memories, reinforced {len(used)}")


def main() -> None:
    with client() as c:
        seed(c)
        run_rounds(c)

        header("Final state")
        show("Memories after repeated use", c.get("/memories", params={"project_id": PROJECT}).json())

        final_recall = c.post("/recall", json={"query": "prepare and run the production migration", "goal_state": GOAL}).json()
        show("Final recall ranking", final_recall)


if __name__ == "__main__":
    main()
