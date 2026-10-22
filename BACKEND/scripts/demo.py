"""Exercise a running API with isolated demo users; print resource IDs, never secrets."""

import argparse
import secrets
from datetime import UTC, datetime, timedelta

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    suffix = secrets.token_hex(4)
    password = secrets.token_urlsafe(24)
    with httpx.Client(base_url=args.url, timeout=30) as client:

        def call(method, path, expected=200, **kwargs):
            response = client.request(method, "/api/v1" + path, **kwargs)
            if response.status_code != expected:
                raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
            return response.json() if response.content else None

        users = {}
        for role in ("owner", "member", "outsider"):
            email = f"{role}-{suffix}@example.com"
            user = call(
                "POST",
                "/auth/register",
                201,
                json={"email": email, "password": password, "full_name": f"Demo {role}"},
            )
            token = call("POST", "/auth/login", json={"email": email, "password": password})
            users[role] = user | {"headers": {"Authorization": "Bearer " + token["access_token"]}}
        headers = users["owner"]["headers"]
        workspace = call(
            "POST", "/workspaces", 201, json={"name": f"Demo workspace {suffix}"}, headers=headers
        )
        wid = workspace["id"]
        call(
            "POST",
            f"/workspaces/{wid}/members",
            201,
            json={"user_id": users["member"]["id"]},
            headers=headers,
        )
        project = call(
            "POST",
            f"/workspaces/{wid}/projects",
            201,
            json={"name": "Placement portfolio"},
            headers=headers,
        )
        task = call(
            "POST",
            f"/projects/{project['id']}/tasks",
            201,
            json={
                "title": "Verify TaskFlow end to end",
                "priority": "high",
                "assignee_id": users["member"]["id"],
                "due_at": (datetime.now(UTC) + timedelta(minutes=30)).isoformat(),
            },
            headers=headers,
        )
        tid = task["id"]
        path = f"/tasks/{tid}"
        call(
            "PATCH",
            path,
            json={"expected_version": 1, "status": "in_progress"},
            headers=users["member"]["headers"],
        )
        call(
            "PATCH",
            path,
            409,
            json={"expected_version": 1, "title": "Stale write"},
            headers=headers,
        )
        call(
            "POST",
            path + "/comments",
            201,
            json={"body": "Verified assignment and optimistic locking"},
            headers=headers,
        )
        call("GET", path, 404, headers=users["outsider"]["headers"])
        activity = call("GET", path + "/activity", headers=headers)
        print(
            f"Demo passed: {len(activity['items'])} activity events, stale update 409, outsider 404"
        )
        print(f"workspace_id={wid}\nproject_id={project['id']}\ntask_id={tid}")
        print("Reminder is due within one hour; beat should dispatch it within 60 seconds.")


if __name__ == "__main__":
    main()
