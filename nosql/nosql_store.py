"""
NoSQL data layer for semi-structured data (free-text feedback, tags, social
metrics, press mentions, pitch deck links, etc.) - the kind of data that
doesn't fit neatly into normalized SQL tables.

Design goal: the REST of the app never imports pymongo directly. It imports
`get_store()` from this file and calls .find() / .insert_one() / .insert_many()
exactly like a pymongo Collection. That means:

  - Locally / in this sandbox (no MongoDB, no internet): documents are
    stored as JSON files under nosql/collections/<name>.json. Zero setup.
  - In production: set MONGO_URI (and optionally MONGO_DB) as env vars and
    install pymongo (already in requirements.txt). get_store() will then
    return a real pymongo Database and every call above hits real MongoDB
    with no code changes anywhere else in the project.
"""
import os
import json
import itertools

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COLLECTIONS_DIR = os.path.join(BASE_DIR, "collections")

MONGO_URI = os.environ.get("MONGO_URI", "").strip()
MONGO_DB_NAME = os.environ.get("MONGO_DB", "incubator_tracker")


class _JsonCollection:
    """Drop-in stand-in for a pymongo Collection, backed by a JSON file."""

    def __init__(self, name):
        self.name = name
        self.path = os.path.join(COLLECTIONS_DIR, f"{name}.json")
        os.makedirs(COLLECTIONS_DIR, exist_ok=True)
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

    def _read(self):
        with open(self.path) as f:
            return json.load(f)

    def _write(self, docs):
        with open(self.path, "w") as f:
            json.dump(docs, f, indent=2, default=str)

    def insert_one(self, doc):
        docs = self._read()
        doc = dict(doc)
        doc.setdefault("_id", len(docs) + 1)
        docs.append(doc)
        self._write(docs)
        return doc["_id"]

    def insert_many(self, doc_list):
        docs = self._read()
        start = len(docs) + 1
        for i, d in enumerate(doc_list):
            d = dict(d)
            d.setdefault("_id", start + i)
            docs.append(d)
        self._write(docs)
        return [d["_id"] for d in docs[-len(doc_list):]]

    @staticmethod
    def _match(doc, query):
        for k, v in (query or {}).items():
            if isinstance(v, dict) and "$in" in v:
                if doc.get(k) not in v["$in"]:
                    return False
            elif doc.get(k) != v:
                return False
        return True

    def find(self, query=None, limit=None):
        docs = [d for d in self._read() if self._match(d, query)]
        return docs[:limit] if limit else docs

    def find_one(self, query=None):
        results = self.find(query)
        return results[0] if results else None

    def count_documents(self, query=None):
        return len(self.find(query))

    def delete_many(self, query=None):
        docs = self._read()
        keep = [d for d in docs if not self._match(d, query)]
        removed = len(docs) - len(keep)
        self._write(keep)
        return removed


class _JsonStore:
    """Drop-in stand-in for a pymongo Database."""

    def __getitem__(self, name):
        return _JsonCollection(name)

    def __getattr__(self, name):
        return _JsonCollection(name)


def get_store():
    """Returns a Mongo-like database object -- real pymongo if MONGO_URI is
    configured, otherwise the local JSON-backed fallback."""
    if MONGO_URI:
        from pymongo import MongoClient
        client = MongoClient(MONGO_URI)
        return client[MONGO_DB_NAME]
    return _JsonStore()


def using_real_mongo():
    return bool(MONGO_URI)
