"""
Sample containerized application for LAB EX18 (CI/CD with Jenkins + Docker).

A tiny Flask API with:
- GET /            -> welcome message + version (proves the container is alive)
- GET /health      -> health check (used by orchestrators / smoke tests)
- GET /add/<a>/<b> -> trivial business logic (something for unit tests to exercise)

Kept deliberately small so the *pipeline* is the point of the exercise, not the app.
"""

from flask import Flask, jsonify
import os

app = Flask(__name__)

# Set by the Jenkinsfile / Dockerfile via --build-arg or ENV so you can see,
# at runtime, exactly which build/commit is currently deployed.
APP_VERSION = os.environ.get("APP_VERSION", "dev")


@app.route("/")
def index():
    return jsonify(
        message="Hello from the CI/CD Lab app!",
        version=APP_VERSION,
    )


@app.route("/health")
def health():
    return jsonify(status="ok"), 200


@app.route("/add/<int:a>/<int:b>")
def add(a: int, b: int):
    return jsonify(a=a, b=b, sum=a + b)


if __name__ == "__main__":
    # 0.0.0.0 so it's reachable from outside the container
    app.run(host="0.0.0.0", port=5000)
