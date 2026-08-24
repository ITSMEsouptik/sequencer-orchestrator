from dataclasses import dataclass


@dataclass
class SequencerEvent:
    eventId: str
    eventType: str
    aggregatedId: str
    aggregatedType: str
    orderId: str
    patientId: str
    status: str
    timestamp: str
