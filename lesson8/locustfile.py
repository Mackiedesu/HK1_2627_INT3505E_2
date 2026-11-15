"""Lab 4 starter: weighted tasks, optional 404, and 1% simulated failure in search_by_year.

Run: locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
         -u 10 -r 2 -t 30s --html reports/A.html
"""
import itertools
import random

from locust import HttpUser, between, task

_counter = itertools.count(1)


class BooksUser(HttpUser):
    wait_time = between(1, 3)
    host = "http://127.0.0.1:5000"

    @task(3)
    def list_books(self):
        self.client.get("/books", name="GET /books")

    @task(2)
    def read_book(self):
        book_id = random.randint(1, 50)
        with self.client.get(
            f"/books/{book_id}", name="GET /books/{id}", catch_response=True
        ) as response:
            # Expected 404 (random id absent) is not an operational failure.
            if response.status_code in (200, 404):
                response.success()
            else:
                response.failure(f"Unexpected status {response.status_code}")

    @task(1)
    def create_book(self):
        unique = next(_counter)
        self.client.post(
            "/books",
            json={"title": f"Load test {unique}", "author": "locust", "year": random.randint(1990, 2025)},
            name="POST /books",
        )

    @task(2)
    def search_by_year(self):
        """
        Query books filtered by year and inject a 1% simulated failure rate.
        Note: The 1% injected failure is a client-side artificial failure marked via
        `response.failure("Simulated 500 Internal Server Error (1% injected)")` in Locust
        (the Flask server itself returns HTTP 200 unless overloaded).
        """
        year = random.randint(1990, 2025)
        with self.client.get(
            f"/books?year={year}", name="GET /books?year={year}", catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}")
            elif random.random() < 0.01:
                response.failure("Simulated 500 Internal Server Error (1% client-side injected)")
            else:
                response.success()
