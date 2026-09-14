from uuid import UUID
from app.core.errors import APIError
from app.database.registrations import RegistrationDatabaseError, RegistrationRepository
from app.services.notifications import NotificationService


class AdminRegistrationService:
    def __init__(self, repository: RegistrationRepository, notifications: NotificationService) -> None:
        self._repository, self._notifications = repository, notifications

    def _error(self, error: RegistrationDatabaseError) -> APIError:
        text = error.message.lower()
        if "not found" in text: return APIError(404, "registration_not_found", "The registration does not exist.")
        if "capacity" in text: return APIError(409, "event_full", "This event is full.")
        if "pending" in text: return APIError(409, "request_not_pending", "The registration request is no longer pending.")
        if "closed" in text or "past" in text: return APIError(409, "event_not_eligible", "Registration is not available for this event.")
        return APIError(503, "registration_unavailable", "Registration is temporarily unavailable.")

    def list_requests(self, status: str | None, event_id: UUID | None) -> list[dict[str, object]]:
        rows = self._repository.list_all(status, event_id)
        attendee_ids = list({UUID(str(row["attendee_id"])) for row in rows})
        event_ids = list({UUID(str(row["event_id"])) for row in rows})
        profiles = self._repository.profiles(attendee_ids)
        events = self._repository.get_events(event_ids)
        return [
            {
                "registration_id": row["id"], "attendee_id": row["attendee_id"],
                "attendee_name": profiles.get(UUID(str(row["attendee_id"])), {}).get("full_name"),
                "attendee_email": self._repository.attendee_email(UUID(str(row["attendee_id"]))),
                "event_id": row["event_id"], "event_title": events[UUID(str(row["event_id"]))]["title"],
                "event_starts_at": events[UUID(str(row["event_id"]))]["starts_at"],
                "status": row["status"], "created_at": row["created_at"],
            }
            for row in rows
        ]

    def approve(self, registration_id: UUID) -> dict[str, object]:
        try: row = self._repository.approve_atomic(registration_id)
        except RegistrationDatabaseError as error: raise self._error(error)
        event = self._repository.get_events([UUID(str(row["event_id"]))])[UUID(str(row["event_id"]))]
        self._notifications.create(UUID(str(row["attendee_id"])), "registration_approved", "Registration approved", f"Your registration for {event['title']} has been approved.", UUID(str(row["event_id"])), registration_id)
        return row

    def reject(self, registration_id: UUID) -> dict[str, object]:
        try: row = self._repository.reject_atomic(registration_id)
        except RegistrationDatabaseError as error: raise self._error(error)
        event = self._repository.get_events([UUID(str(row["event_id"]))])[UUID(str(row["event_id"]))]
        self._notifications.create(UUID(str(row["attendee_id"])), "registration_rejected", "Registration request not approved", f"Your registration request for {event['title']} was not approved.", UUID(str(row["event_id"])), registration_id)
        return row
