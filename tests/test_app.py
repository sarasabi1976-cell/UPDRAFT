from app import app


def test_dashboard_returns_success():
    app.testing = True

    with app.test_client() as client:
        response = client.get("/api/dashboard")

        assert response.status_code == 200

        data = response.get_json()

        assert "readiness" in data
        assert "stats" in data
        assert "tasks" in data

def test_study_plan_returns_tasks():
    app.testing = True

    with app.test_client() as client:
        response = client.get("/api/plan")

        assert response.status_code == 200

        data = response.get_json()

        assert "items" in data
        assert isinstance(data["items"], list)
def test_update_study_plan_item():
    app.testing = True

    with app.test_client() as client:
        # Give this test session a sample recommendation
        with client.session_transaction() as test_session:
            test_session["career_recommendations"] = [
                {
                    "role": "Test Career",
                    "study_schedule": [
                        {
                            "skill": "programming",
                            "burst_time": 2,
                            "priority": 1
                        }
                    ]
                }
            ]

        # Load the plan so its tasks are created
        plan_response = client.get("/api/plan")
        items = plan_response.get_json()["items"]

        assert items, "Expected at least one study-plan task"

        item_id = items[0]["id"]

        response = client.patch(
            f"/api/plan/items/{item_id}",
            json={"completed": True}
        )

        assert response.status_code == 200
        assert response.get_json()["success"] is True
        assert response.get_json()["item"]["completed"] is True