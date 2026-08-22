from abc import ABC, abstractmethod
from datetime import datetime

from app.models import NewReport, Report


class ReportStore(ABC):
    """Storage-backend-agnostic interface. `local` (JSON file) is used until the
    Firebase Firestore account exists; `firestore` is the real production backend
    (see PLAN.md's stack table) — swapping STORAGE_BACKEND is the only code change
    needed once that account is set up.
    """

    @abstractmethod
    def add_or_increment(self, new_report: NewReport) -> Report:
        """Write a new report, or bump report_count on a matching recent one
        (PS3's duplicate-detection ask — see docs/master-workout/day1-sketches.md)."""

    @abstractmethod
    def list_since(self, since: datetime | None = None) -> list[Report]:
        """All reports at/after `since` (all reports if None)."""

    def counts_by_zone(self, since: datetime | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for report in self.list_since(since):
            counts[report.zone_id] = counts.get(report.zone_id, 0) + report.report_count
        return counts
