"""
Client untuk Participant application (WebSocket client)
"""
import asyncio
import websockets
from typing import Optional, Callable, Dict
from datetime import datetime
import json
from .protocol import Message, MessageType


class ProctoringClient:
    """Client untuk participant application"""
    
    def __init__(self, server_url: str, participant_id: str):
        """
        Initialize client
        
        Args:
            server_url: URL server (ws://host:port)
            participant_id: ID peserta
        """
        self.server_url = server_url
        self.participant_id = participant_id
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.is_connected = False
        self.reconnect_interval = 5
        self.running = False
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.register_handler(MessageType.REGISTER_ACK, self._handle_register_ack)
        self.register_handler(MessageType.CONFIG_UPDATE, self._handle_config_update)
        self.register_handler(MessageType.WARNING, self._handle_warning)
        self.register_handler(MessageType.LOCK, self._handle_lock)
        self.register_handler(MessageType.UNLOCK, self._handle_unlock)
        self.register_handler(MessageType.PERMISSION_RESPONSE, self._handle_permission_response)
        self.register_handler(MessageType.EMERGENCY_LOCK, self._handle_emergency_lock)
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """Register message handler"""
        self.message_handlers[msg_type] = handler
    
    async def connect(self):
        """Connect to server"""
        try:
            uri = f"{self.server_url}/ws/{self.participant_id}"
            self.websocket = await websockets.connect(uri)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from server"""
        self.is_connected = False
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    async def send_message(self, message: Message) -> bool:
        """Send message to server"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            message.participant_id = self.participant_id
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            print(f"Error sending message: {e}")
            self.is_connected = False
            return False
    
    async def register(self, name: str, computer_ip: str = None, computer_name: str = None):
        """Register dengan server"""
        message = Message(
            MessageType.REGISTER,
            data={
                'name': name,
                'computer_ip': computer_ip,
                'computer_name': computer_name
            },
            participant_id=self.participant_id
        )
        return await self.send_message(message)
    
    async def send_heartbeat(self):
        """Send heartbeat"""
        message = Message(MessageType.HEARTBEAT, participant_id=self.participant_id)
        return await self.send_message(message)
    
    async def send_violation_report(self, violation_type: str, severity: str, description: str):
        """Send violation report"""
        message = Message(
            MessageType.VIOLATION_REPORT,
            data={
                'violation_type': violation_type,
                'severity': severity,
                'description': description
            },
            participant_id=self.participant_id
        )
        return await self.send_message(message)
    
    async def send_permission_request(self, request_type: str = 'leave_seat',
                                     duration_minutes: int = 10, reason: str = None):
        """Send permission request"""
        message = Message(
            MessageType.PERMISSION_REQUEST,
            data={
                'request_type': request_type,
                'duration_minutes': duration_minutes,
                'reason': reason
            },
            participant_id=self.participant_id
        )
        return await self.send_message(message)
    
    async def send_status_update(self, status: Dict):
        """Send status update"""
        message = Message(
            MessageType.STATUS_UPDATE,
            data=status,
            participant_id=self.participant_id
        )
        return await self.send_message(message)
    
    async def _handle_message(self, message: Message):
        """Handle incoming message"""
        handler = self.message_handlers.get(message.type)
        if handler:
            await handler(message)
        else:
            print(f"No handler for message type: {message.type}")
    
    async def _handle_register_ack(self, message: Message):
        """Handle register acknowledgment"""
        print(f"Registered: {message.data}")
    
    async def _handle_config_update(self, message: Message):
        """Handle config update"""
        print(f"Config updated: {message.data}")
    
    async def _handle_warning(self, message: Message):
        """Handle warning"""
        print(f"Warning received: {message.data}")
    
    async def _handle_lock(self, message: Message):
        """Handle lock command"""
        print(f"Lock command: {message.data}")
    
    async def _handle_unlock(self, message: Message):
        """Handle unlock command"""
        print(f"Unlock command: {message.data}")
    
    async def _handle_permission_response(self, message: Message):
        """Handle permission response"""
        print(f"Permission response: {message.data}")
    
    async def _handle_emergency_lock(self, message: Message):
        """Handle emergency lock"""
        print(f"Emergency lock: {message.data}")
    
    async def listen(self):
        """Listen for messages"""
        while self.running and self.is_connected:
            try:
                if self.websocket:
                    data = await self.websocket.recv()
                    message = Message.from_json(data)
                    await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                self.is_connected = False
                break
            except Exception as e:
                print(f"Error in listen: {e}")
                self.is_connected = False
                break
    
    async def start(self, name: str, computer_ip: str = None, computer_name: str = None):
        """Start client dengan auto-reconnect"""
        self.running = True
        
        while self.running:
            if await self.connect():
                # Register
                await self.register(name, computer_ip, computer_name)
                
                # Start listening
                await self.listen()
            
            # Reconnect
            if self.running:
                print(f"Reconnecting in {self.reconnect_interval} seconds...")
                await asyncio.sleep(self.reconnect_interval)
    
    def stop(self):
        """Stop client"""
        self.running = False
        asyncio.create_task(self.disconnect())
