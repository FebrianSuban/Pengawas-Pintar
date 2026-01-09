"""
Protocol untuk komunikasi antara admin dan participant
"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import json


class MessageType(Enum):
    """Jenis pesan"""
    # Participant -> Admin
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    VIOLATION_REPORT = "violation_report"
    PERMISSION_REQUEST = "permission_request"
    STATUS_UPDATE = "status_update"
    
    # Admin -> Participant
    REGISTER_ACK = "register_ack"
    CONFIG_UPDATE = "config_update"
    WARNING = "warning"
    LOCK = "lock"
    UNLOCK = "unlock"
    PERMISSION_RESPONSE = "permission_response"
    EMERGENCY_LOCK = "emergency_lock"
    
    # Bidirectional
    PING = "ping"
    PONG = "pong"


class Message:
    """Pesan untuk komunikasi"""
    
    def __init__(self, msg_type: MessageType, data: Dict[str, Any] = None,
                 participant_id: str = None, timestamp: datetime = None):
        self.type = msg_type
        self.data = data or {}
        self.participant_id = participant_id
        self.timestamp = timestamp or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            'type': self.type.value,
            'data': self.data,
            'participant_id': self.participant_id,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create message from dictionary"""
        return cls(
            msg_type=MessageType(data['type']),
            data=data.get('data', {}),
            participant_id=data.get('participant_id'),
            timestamp=datetime.fromisoformat(data.get('timestamp', datetime.utcnow().isoformat()))
        )
    
    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Create message from JSON string"""
        return cls.from_dict(json.loads(json_str))
    
    def __repr__(self):
        return f"<Message(type={self.type.value}, participant_id={self.participant_id})>"
