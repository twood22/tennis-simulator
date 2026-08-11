"""Local compatibility entry point for the canonical Flask application."""

from api.index import app


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5002, debug=False)
