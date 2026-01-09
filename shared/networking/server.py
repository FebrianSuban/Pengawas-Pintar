"""
Server untuk Admin application (FastAPI + WebSocket)
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Set
import json
import asyncio
from datetime import datetime
from .protocol import Message, MessageType


class ProctoringServer:
    """Server untuk admin application"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize server
        
        Args:
            host: Host address
            port: Port number
        """
        self.host = host
        self.port = port
        self.app = FastAPI()
        self.connected_clients: Dict[str, WebSocket] = {}  # participant_id -> websocket
        self.client_info: Dict[str, Dict] = {}  # participant_id -> info
        
        # Setup CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Setup routes
        self._setup_routes()
        
        # Message handlers
        self.message_handlers: Dict[MessageType, callable] = {}
        self.register_handler(MessageType.REGISTER, self._handle_register)
        self.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.register_handler(MessageType.VIOLATION_REPORT, self._handle_violation_report)
        self.register_handler(MessageType.PERMISSION_REQUEST, self._handle_permission_request)
        self.register_handler(MessageType.STATUS_UPDATE, self._handle_status_update)
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/")
        async def root():
            return {"status": "Proctoring Server", "connected_clients": len(self.connected_clients)}
        
        @self.app.get("/participants")
        async def get_participants():
            return {
                "participants": [
                    {
                        "id": pid,
                        "info": info,
                        "connected": pid in self.connected_clients
                    }
                    for pid, info in self.client_info.items()
                ]
            }
        
        @self.app.get("/validate_participant/{participant_id}")
        async def validate_participant(participant_id: str, name: str = None):
            """Validate participant ID and name"""
            # This will be handled by admin app via callback
            if hasattr(self, 'admin_app') and self.admin_app:
                # Ambil data participant saat masih dalam session
                with self.admin_app.db_manager.get_session() as session:
                    from shared.database.models import Participant
                    participant = session.query(Participant).filter_by(participant_id=participant_id).first()
                    if participant:
                        participant_name = participant.name
                        participant_session_id = participant.exam_session_id
                        
                        # Validasi nama
                        if name and participant_name.lower() != name.lower():
                            return {"valid": False, "message": f"Nama tidak sesuai. Nama yang terdaftar: {participant_name}"}
                        
                        # Validasi sesi ujian aktif
                        if not self.admin_app.current_session_id:
                            return {"valid": False, "message": "Sesi ujian belum dimulai oleh pengawas."}
                        
                        if participant_session_id != self.admin_app.current_session_id:
                            return {"valid": False, "message": "ID Peserta tidak terdaftar untuk sesi ujian ini."}
                        
                        return {"valid": True, "participant": {"id": participant_id, "name": participant_name}}
                    return {"valid": False, "message": f"ID Peserta {participant_id} tidak terdaftar"}
            return {"valid": False, "message": "Server belum siap"}
        
        @self.app.websocket("/ws/{participant_id}")
        async def websocket_endpoint(websocket: WebSocket, participant_id: str):
            await websocket.accept()
            self.connected_clients[participant_id] = websocket
            
            try:
                while True:
                    data = await websocket.receive_text()
                    message = Message.from_json(data)
                    await self._handle_message(participant_id, message)
            except WebSocketDisconnect:
                self._disconnect_client(participant_id)
            except Exception as e:
                print(f"Error in websocket: {e}")
                self._disconnect_client(participant_id)
    
    def _disconnect_client(self, participant_id: str):
        """Handle client disconnect"""
        if participant_id in self.connected_clients:
            del self.connected_clients[participant_id]
        if participant_id in self.client_info:
            self.client_info[participant_id]['last_seen'] = datetime.utcnow().isoformat()
            self.client_info[participant_id]['connected'] = False
    
    async def _handle_message(self, participant_id: str, message: Message):
        """Handle incoming message"""
        handler = self.message_handlers.get(message.type)
        if handler:
            await handler(participant_id, message)
        else:
            print(f"No handler for message type: {message.type}")
    
    def register_handler(self, msg_type: MessageType, handler: callable):
        """Register message handler"""
        self.message_handlers[msg_type] = handler
    
    async def _handle_register(self, participant_id: str, message: Message):
        """Handle participant registration"""
        # Handler ini akan di-override oleh admin app
        # Default behavior untuk backward compatibility
        data = message.data
        self.client_info[participant_id] = {
            'name': data.get('name', ''),
            'computer_ip': data.get('computer_ip', ''),
            'computer_name': data.get('computer_name', ''),
            'registered_at': datetime.utcnow().isoformat(),
            'connected': True
        }
        
        # Send acknowledgment
        ack_message = Message(
            MessageType.REGISTER_ACK,
            data={'status': 'registered', 'participant_id': participant_id},
            participant_id=participant_id
        )
        await self.send_message(participant_id, ack_message)
    
    async def _handle_heartbeat(self, participant_id: str, message: Message):
        """Handle heartbeat"""
        if participant_id in self.client_info:
            self.client_info[participant_id]['last_heartbeat'] = datetime.utcnow().isoformat()
            self.client_info[participant_id]['connected'] = True
    
    async def _handle_violation_report(self, participant_id: str, message: Message):
        """Handle violation report"""
        # This will be handled by admin app
        pass
    
    async def _handle_permission_request(self, participant_id: str, message: Message):
        """Handle permission request"""
        # This will be handled by admin app
        pass
    
    async def _handle_status_update(self, participant_id: str, message: Message):
        """Handle status update"""
        if participant_id in self.client_info:
            self.client_info[participant_id].update(message.data)
    
    async def send_message(self, participant_id: str, message: Message) -> bool:
        """Send message to participant"""
        if participant_id in self.connected_clients:
            try:
                websocket = self.connected_clients[participant_id]
                await websocket.send_text(message.to_json())
                return True
            except Exception as e:
                print(f"Error sending message to {participant_id}: {e}")
                self._disconnect_client(participant_id)
                return False
        return False
    
    async def broadcast_message(self, message: Message, exclude: List[str] = None):
        """Broadcast message to all participants"""
        exclude = exclude or []
        for participant_id in list(self.connected_clients.keys()):
            if participant_id not in exclude:
                await self.send_message(participant_id, message)
    
    def get_connected_participants(self) -> List[str]:
        """Get list of connected participant IDs"""
        return list(self.connected_clients.keys())
    
    def get_participant_info(self, participant_id: str) -> Dict:
        """Get participant info"""
        return self.client_info.get(participant_id, {})
    
    def run(self):
        """Run server (blocking)"""
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)
    
    async def start(self):
        """Start server (async)"""
        import uvicorn
        config = uvicorn.Config(self.app, host=self.host, port=self.port)
        server = uvicorn.Server(config)
        await server.serve()
