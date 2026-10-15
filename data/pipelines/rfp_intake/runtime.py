"""Configure optional runtime adapters before compiling the public intake graph."""

from . import intake as intake_module
from . import workflow as workflow_module
from .metadata import extract_rfp_metadata
from .metrics_adapter import calculate_readability
from .workers import extract_relevant_excerpt, run_department_worker

intake_module.calculate_readability = calculate_readability
workflow_module.extract_rfp_metadata = extract_rfp_metadata
workflow_module._extract_relevant_excerpt = extract_relevant_excerpt
workflow_module.run_department_worker = run_department_worker

from .workflow_entry import classify_rfp, rfp_intake_graph