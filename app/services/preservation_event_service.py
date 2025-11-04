from datetime import datetime
from app.models.metadata import (
    PreservationEvent,
    PreservationEventType,
    PreservationEventOutcome,
)
from app.services.db import Database


class PreservationEventService:
    """
    Service for logging and managing PREMIS-compliant preservation events.
    Provides audit trail for all preservation activities.
    """

    def __init__(self, db: Database):
        self.db = db

    async def log_event(
        self,
        artifact_id: str,
        event_type: PreservationEventType,
        outcome: PreservationEventOutcome,
        agent: str = "system",
        detail: str | None = None,
        related_object: str | None = None,
    ) -> PreservationEvent:
        """
        Log a preservation event for an artifact.

        Args:
            artifact_id: Artifact identifier
            event_type: Type of preservation event
            outcome: Outcome of the event (success/failure/warning)
            agent: Agent that performed the event (defaults to "system")
            detail: Additional details about the event
            related_object: Related object identifier

        Returns:
            PreservationEvent object

        Raises:
            PreservationEventServiceError: If logging fails
        """
        event = PreservationEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            agent=agent,
            outcome=outcome,
            detail=detail,
            related_object=related_object,
        )

        try:
            await self.db.add_preservation_event(artifact_id, event)
        except Exception as e:
            raise PreservationEventServiceError(
                f"Failed to log preservation event: {str(e)}"
            )

        return event

    async def log_ingestion(
        self,
        artifact_id: str,
        outcome: PreservationEventOutcome,
        storage_path: str,
        agent: str = "system",
    ) -> PreservationEvent:
        """
        Log an ingestion event (convenience method).

        Args:
            artifact_id: Artifact identifier
            outcome: Outcome of the ingestion
            storage_path: Path where artifact was stored
            agent: Agent that performed ingestion

        Returns:
            PreservationEvent object
        """
        detail = f"Artifact ingested to storage path: {storage_path}"
        return await self.log_event(
            artifact_id=artifact_id,
            event_type=PreservationEventType.INGESTION,
            outcome=outcome,
            agent=agent,
            detail=detail,
            related_object=storage_path,
        )

    async def log_validation(
        self,
        artifact_id: str,
        outcome: PreservationEventOutcome,
        validation_type: str,
        detail: str | None = None,
    ) -> PreservationEvent:
        """
        Log a validation event (convenience method).

        Args:
            artifact_id: Artifact identifier
            outcome: Outcome of the validation
            validation_type: Type of validation performed
            detail: Additional details

        Returns:
            PreservationEvent object
        """
        full_detail = f"Validation type: {validation_type}"
        if detail:
            full_detail += f". {detail}"

        return await self.log_event(
            artifact_id=artifact_id,
            event_type=PreservationEventType.VALIDATION,
            outcome=outcome,
            detail=full_detail,
        )

    async def log_fixity_check(
        self,
        artifact_id: str,
        outcome: PreservationEventOutcome,
        checksums_match: bool,
        algorithms: list[str],
    ) -> PreservationEvent:
        """
        Log a fixity check event (convenience method).

        Args:
            artifact_id: Artifact identifier
            outcome: Outcome of the fixity check
            checksums_match: Whether checksums matched
            algorithms: Algorithms used for verification

        Returns:
            PreservationEvent object
        """
        detail = (
            f"Fixity check using {', '.join(algorithms)}. "
            f"Result: {'checksums match' if checksums_match else 'checksum mismatch'}"
        )

        return await self.log_event(
            artifact_id=artifact_id,
            event_type=PreservationEventType.FIXITY_CHECK,
            outcome=outcome,
            detail=detail,
        )

    async def log_replication(
        self,
        artifact_id: str,
        outcome: PreservationEventOutcome,
        source: str,
        destination: str,
    ) -> PreservationEvent:
        """
        Log a replication event (convenience method).

        Args:
            artifact_id: Artifact identifier
            outcome: Outcome of the replication
            source: Source storage location
            destination: Destination storage location

        Returns:
            PreservationEvent object
        """
        detail = f"Replicated from {source} to {destination}"

        return await self.log_event(
            artifact_id=artifact_id,
            event_type=PreservationEventType.REPLICATION,
            outcome=outcome,
            detail=detail,
            related_object=destination,
        )

    async def log_metadata_extraction(
        self,
        artifact_id: str,
        outcome: PreservationEventOutcome,
        extraction_type: str,
        detail: str | None = None,
    ) -> PreservationEvent:
        """
        Log a metadata extraction event (convenience method).

        Args:
            artifact_id: Artifact identifier
            outcome: Outcome of the extraction
            extraction_type: Type of metadata extracted
            detail: Additional details

        Returns:
            PreservationEvent object
        """
        full_detail = f"Metadata extraction type: {extraction_type}"
        if detail:
            full_detail += f". {detail}"

        return await self.log_event(
            artifact_id=artifact_id,
            event_type=PreservationEventType.METADATA_EXTRACTION,
            outcome=outcome,
            detail=full_detail,
        )

    async def get_events(
        self,
        artifact_id: str,
        event_type: PreservationEventType | None = None,
    ) -> list[PreservationEvent]:
        """
        Get preservation events for an artifact.

        Args:
            artifact_id: Artifact identifier
            event_type: Filter by event type (optional)

        Returns:
            List of PreservationEvent objects

        Raises:
            PreservationEventServiceError: If retrieval fails
        """
        try:
            artifact = await self.db.get_artifact(artifact_id)
            if not artifact:
                raise PreservationEventServiceError(
                    f"Artifact not found: {artifact_id}"
                )

            events = artifact.get("preservation_events", [])

            if event_type:
                events = [e for e in events if e.get("event_type") == event_type.value]

            return [PreservationEvent(**e) for e in events]
        except Exception as e:
            raise PreservationEventServiceError(
                f"Failed to retrieve preservation events: {str(e)}"
            )

    async def get_latest_event(
        self, artifact_id: str, event_type: PreservationEventType
    ) -> PreservationEvent | None:
        """
        Get the most recent event of a specific type.

        Args:
            artifact_id: Artifact identifier
            event_type: Type of event to find

        Returns:
            PreservationEvent object or None if not found
        """
        events = await self.get_events(artifact_id, event_type)
        if not events:
            return None

        # Sort by timestamp descending and return first
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[0]


class PreservationEventServiceError(Exception):
    """Exception raised by PreservationEventService"""

    pass
