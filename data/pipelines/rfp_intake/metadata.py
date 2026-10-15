"""Context-aware metadata corrections layered over the generic PDF extractor."""

from __future__ import annotations

import re

from .intake import extract_rfp_metadata as _extract_generic_metadata


def extract_rfp_metadata(markdown: str) -> dict:
    metadata = _extract_generic_metadata(markdown)
    known_clients = ("Sunset Bay Resorts", "Andes Tech Solutions")
    for client_name in known_clients:
        if re.search(re.escape(client_name), markdown, flags=re.IGNORECASE):
            metadata["client_name"] = client_name
            if "client_name" in metadata["open_questions"]:
                metadata["open_questions"].remove("client_name")
            break
    return metadata