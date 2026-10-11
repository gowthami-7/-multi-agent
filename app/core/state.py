from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class WorkflowState:
    """Shared state passed between agents during workflow execution."""

    user_request: str = ""

    tasks: List[Dict[str, Any]] = field(default_factory=list)

    current_task_index: int = 0

    research_results: List[Dict[str, Any]] = field(default_factory=list)

    execution_results: List[Dict[str, Any]] = field(default_factory=list)

    verification_results: List[Dict[str, Any]] = field(default_factory=list)

    workflow_status: str = "initialized"

    retry_count: int = 0

    max_retries: int = 2

    final_result: str = ""

    errors: List[str] = field(default_factory=list)

    workflow_log: List[str] = field(default_factory=list)

    def add_log(self, message: str) -> None:
        """Add a status message to the workflow log."""
        self.workflow_log.append(message)

    def add_error(self, message: str) -> None:
        """Record an error and add it to the workflow log."""
        self.errors.append(message)
        self.workflow_log.append(f"ERROR: {message}")

    def reset_retry_count(self) -> None:
        """Reset retries after a successful task."""
        self.retry_count = 0

    def can_retry(self) -> bool:
        """Return whether another retry attempt is available."""
        return self.retry_count < self.max_retries

    def increment_retry(self) -> None:
        """Increment the retry counter."""
        self.retry_count += 1