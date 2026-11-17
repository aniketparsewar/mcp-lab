"""Day 3, Part C: the host-side defense — description pinning.

The host reviews tool descriptions ONCE, out of band, and records a
hash of each approved description. At connect time, a tool is
admitted to the model's tool list only if its live description still
hashes to the approved value. A server that changes its description
after review (or was never reviewed) loses access to the model —
the defense fires BEFORE the model ever sees the text.

This is W6's corpus admission control, one layer up: descriptions
are admitted content, and the host is the admission boundary.
"""
import hashlib


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def admit_tools(tools, approved: dict[str, str]):
    """tools: objects with .name and .description (from list_tools).
    approved: {tool_name: sha256 hex of the reviewed description}.
    Returns (kept_tools, dropped_names).

    TODO (yours): keep a tool only when approved contains its name
    AND _hash(tool.description or "") equals the approved hash.
    Everything else is dropped, by name.
    """
    kept = []
    dropped = []
    for tool in tools:
        expected = approved.get(tool.name)
        if expected is not None and _hash(tool.description or "") == expected:
            kept.append(tool)
        else:
            dropped.append(tool.name)
    return kept, dropped
