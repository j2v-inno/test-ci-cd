from __future__ import annotations

import os

from flask import Flask, jsonify, request

from app.items import ItemStore

VERSION = "0.1.0"


def create_app(store: ItemStore | None = None) -> Flask:
    app = Flask(__name__)
    app.config["STORE"] = store or ItemStore()

    @app.get("/health")
    def health():
        return jsonify(status="ok"), 200

    @app.get("/version")
    def version():
        return jsonify(
            version=VERSION,
            environment=os.environ.get("APP_ENV", "local"),
            commit=os.environ.get("GIT_COMMIT", "unknown"),
        ), 200

    @app.get("/items")
    def list_items():
        store: ItemStore = app.config["STORE"]
        return jsonify([item.to_dict() for item in store.list()]), 200

    @app.post("/items")
    def create_item():
        store: ItemStore = app.config["STORE"]
        data = request.get_json(silent=True) or {}
        try:
            item = store.add(name=data.get("name", ""), price=float(data.get("price", 0)))
        except (ValueError, TypeError) as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(item.to_dict()), 201

    @app.get("/items/<int:item_id>")
    def get_item(item_id: int):
        store: ItemStore = app.config["STORE"]
        item = store.get(item_id)
        if item is None:
            return jsonify(error="not found"), 404
        return jsonify(item.to_dict()), 200

    @app.delete("/items/<int:item_id>")
    def delete_item(item_id: int):
        store: ItemStore = app.config["STORE"]
        if not store.delete(item_id):
            return jsonify(error="not found"), 404
        return "", 204

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    # Bind 0.0.0.0 is required so the container's published port is reachable from the host.
    app.run(host="0.0.0.0", port=port)  # nosec B104
