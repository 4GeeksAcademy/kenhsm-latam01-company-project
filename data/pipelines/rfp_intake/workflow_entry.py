"""Public graph entrypoint with Brasaland-specific metadata extraction installed."""

from . import workflow as _workflow
from .metadata import extract_rfp_metadata

_workflow.extract_rfp_metadata = extract_rfp_metadata
rfp_intake_graph = _workflow.build_rfp_intake_graph()
classify_rfp = _workflow.classify_rfp