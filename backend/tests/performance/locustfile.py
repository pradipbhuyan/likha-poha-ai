from __future__ import annotations

import os

from locust import HttpUser, between, events, task

from app.services.performance_scenarios import (
    VALIDATORS,
    ScenarioRequest,
    auth_headers,
    doubt_requests,
    lesson_requests,
    load_test_users,
    mock_test_requests,
    next_profile_factory,
    public_read_requests,
    student_progress_requests,
)


ENABLE_AI_TASKS = os.getenv("ENABLE_AI_TASKS", "").lower() in {"1", "true", "yes"}
TEST_USERS = load_test_users()
next_profile = next_profile_factory(TEST_USERS)


class LikhaPohaBaseUser(HttpUser):
    abstract = True
    wait_time = between(1, 4)

    def on_start(self):
        self.profile = next_profile()

    def request_json(self, request_def: ScenarioRequest):
        headers = {}
        if request_def.requires_auth:
            headers = auth_headers(self.profile)
            if not headers:
                events.request.fire(
                    request_type="AUTH",
                    name="missing bearer token",
                    response_time=0,
                    response_length=0,
                    exception=RuntimeError(
                        "Add tests/performance/test_users.json or PERFORMANCE_TEST_BEARER_TOKEN."
                    ),
                    context={},
                )
                return None

        kwargs = {}
        if request_def.params:
            kwargs["params"] = request_def.params
        if request_def.json is not None:
            kwargs["json"] = request_def.json
        if headers:
            kwargs["headers"] = headers

        with self.client.request(
            request_def.method,
            request_def.path,
            name=request_def.name,
            catch_response=True,
            **kwargs,
        ) as response:
            if response.status_code >= 400:
                response.failure(f"HTTP {response.status_code}: {response.text[:300]}")
                return response

            try:
                payload = response.json()
            except ValueError:
                payload = None

            validation = VALIDATORS[request_def.validator_name](payload)
            if not validation.ok:
                response.failure(validation.error)
                return response

            response.success()
            return response

    def execute_many(self, request_defs: list[ScenarioRequest]):
        for request_def in request_defs:
            self.request_json(request_def)

    def get_public_read(self):
        self.execute_many(public_read_requests(self.profile))

    def get_student_progress(self):
        self.execute_many(student_progress_requests(self.profile)[:2])

    def save_progress(self):
        self.request_json(student_progress_requests(self.profile)[2])

    def generate_lesson(self):
        if ENABLE_AI_TASKS:
            self.request_json(lesson_requests(self.profile)[0])

    def ask_doubt(self):
        if ENABLE_AI_TASKS:
            self.request_json(doubt_requests(self.profile)[0])

    def generate_mock_test(self):
        if ENABLE_AI_TASKS:
            self.request_json(mock_test_requests(self.profile)[0])


class StudentBrowsingUser(LikhaPohaBaseUser):
    """
    Cheap read-heavy user for the first capacity baseline.

    Safe for local smoke tests because it does not call OpenAI.
    """

    weight = 6

    @task(5)
    def browse_public_content(self):
        self.get_public_read()

    @task(3)
    def browse_student_progress(self):
        self.get_student_progress()

    @task(1)
    def persist_progress(self):
        self.save_progress()


class StudentMixedUser(LikhaPohaBaseUser):
    """
    Realistic student mix. AI calls run only when ENABLE_AI_TASKS=true.
    """

    weight = 3
    wait_time = between(2, 7)

    @task(4)
    def browse(self):
        self.get_public_read()

    @task(3)
    def progress(self):
        self.get_student_progress()
        self.save_progress()

    @task(1)
    def lesson_generation(self):
        self.generate_lesson()

    @task(1)
    def doubt_generation(self):
        self.ask_doubt()


class StudentAIHeavyUser(LikhaPohaBaseUser):
    """
    Spike test for expensive AI actions.

    Run this class explicitly and set ENABLE_AI_TASKS=true only when you are
    ready to spend OpenAI quota and measure the slow paths.
    """

    weight = 1
    wait_time = between(5, 12)

    @task(2)
    def lesson(self):
        self.generate_lesson()

    @task(2)
    def doubt(self):
        self.ask_doubt()

    @task(1)
    def mock_test(self):
        self.generate_mock_test()
