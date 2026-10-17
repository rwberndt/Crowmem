"""Guide section 28, "Belief + Episodic Integration". Requires the FastAPI
service running (with a real ANTHROPIC_API_KEY) at CORVID_API_BASE_URL.

Run: python scripts/demos/demo_3_belief_supersession.py
"""

from _common import client, header, show

PROJECT = "peach-demo3"


def main() -> None:
    with client() as c:
        header("Oct 1: Peach uses Stripe")
        ep1 = c.post(
            "/events",
            json={"content": "Peach uses Stripe for payment processing.", "event_type": "fact", "project_id": PROJECT},
        ).json()
        show("Episode", ep1)

        header("Oct 12: Decision made to migrate to Asaas")
        c.post(
            "/events",
            json={
                "content": "Decision: Peach will migrate its payment provider from Stripe to Asaas.",
                "event_type": "decision", "project_id": PROJECT, "metadata": {"decision": True},
            },
        )

        header("Oct 15: Migration completed")
        c.post(
            "/events",
            json={"content": "Migration from Stripe to Asaas completed successfully.", "event_type": "observation", "project_id": PROJECT},
        )

        header("Query: What payment provider do we use?")
        current = c.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "active"}).json()
        show("Active belief", current)

        header("Query: What did we use before?")
        historical = c.get("/beliefs", params={"subject": "Peach", "predicate": "payment_provider", "status": "superseded"}).json()
        show("Superseded belief", historical)

        header("Query: Why did we switch? (retrieve episodes around the decision)")
        episodes = c.get("/episodes", params={"project_id": PROJECT}).json()
        show("Episodes", episodes)


if __name__ == "__main__":
    main()
