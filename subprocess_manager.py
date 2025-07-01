"""
Subprocess Manager for MCP Servers

Handles lifecycle management and communication with MCP servers via subprocesses.
Implements JSON-RPC protocol for tool execution.
"""

import asyncio
import json
import logging
import subprocess
import sys
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class MCPProcess:
    """Represents a running MCP server subprocess"""
    server_name: str
    process: subprocess.Popen
    stdin: Any
    stdout: Any
    stderr: Any
    
class SubprocessManager:
    """Manages MCP server subprocesses and JSON-RPC communication"""
    
    def __init__(self):
        self.processes: Dict[str, MCPProcess] = {}
        self.pending_requests: Dict[str, asyncio.Future] = {}
        
    async def start_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Start an MCP server subprocess"""
        if server_name in self.processes:
            logger.info(f"Server {server_name} already running")
            return True
            
        try:
            execution = server_config["execution"]
            command = execution["command"]
            args = execution.get("args", [])
            
            # Build full command
            full_command = [command] + args
            
            # Get environment variables
            env = os.environ.copy()
            
            # Add any required environment variables from config
            for env_var, env_details in server_config.get("environment", {}).items():
                if env_var in env:
                    continue
                # Check if we have it in .env or system
                value = os.getenv(env_var)
                if value:
                    env[env_var] = value
            
            logger.info(f"Starting MCP server: {' '.join(full_command)}")
            
            # Start subprocess
            process = subprocess.Popen(
                full_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env
            )
            
            # Store process info
            self.processes[server_name] = MCPProcess(
                server_name=server_name,
                process=process,
                stdin=process.stdin,
                stdout=process.stdout,
                stderr=process.stderr
            )
            
            # Start async readers for stdout/stderr
            asyncio.create_task(self._read_output(server_name))
            asyncio.create_task(self._read_errors(server_name))
            
            # Send initialization request
            await self._initialize_connection(server_name)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server {server_name}: {e}")
            return False
    
    async def _initialize_connection(self, server_name: str):
        """Send initialization handshake to MCP server"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "mcp-catalog",
                    "version": "1.0.0"
                }
            },
            "id": str(uuid.uuid4())
        }
        
        await self._send_request(server_name, init_request)
        
        # Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        
        await self._send_notification(server_name, initialized_notification)
    
    async def stop_server(self, server_name: str):
        """Stop an MCP server subprocess"""
        if server_name not in self.processes:
            return
            
        try:
            process_info = self.processes[server_name]
            process_info.process.terminate()
            await asyncio.sleep(0.5)  # Give it time to terminate
            
            if process_info.process.poll() is None:
                process_info.process.kill()  # Force kill if needed
                
            del self.processes[server_name]
            logger.info(f"Stopped server {server_name}")
            
        except Exception as e:
            logger.error(f"Error stopping server {server_name}: {e}")
    
    async def execute_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on an MCP server"""
        if server_name not in self.processes:
            # Try to start the server
            logger.info(f"Server {server_name} not running, attempting to start...")
            # We need server config here - this would come from registry
            return {"error": f"Server {server_name} not running"}
        
        # Create JSON-RPC request
        request_id = str(uuid.uuid4())
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": request_id
        }
        
        # Create future for response
        future = asyncio.Future()
        self.pending_requests[request_id] = future
        
        # Send request
        await self._send_request(server_name, request)
        
        # Wait for response (with timeout)
        try:
            response = await asyncio.wait_for(future, timeout=30.0)
            return response
        except asyncio.TimeoutError:
            del self.pending_requests[request_id]
            return {"error": "Tool execution timeout"}
    
    async def _send_request(self, server_name: str, request: Dict[str, Any]):
        """Send a JSON-RPC request to a server"""
        if server_name not in self.processes:
            raise ValueError(f"Server {server_name} not running")
            
        process_info = self.processes[server_name]
        request_str = json.dumps(request) + "\n"
        
        try:
            process_info.stdin.write(request_str)
            process_info.stdin.flush()
            logger.debug(f"Sent request to {server_name}: {request.get('method', 'unknown')}")
        except Exception as e:
            logger.error(f"Failed to send request to {server_name}: {e}")
            raise
    
    async def _send_notification(self, server_name: str, notification: Dict[str, Any]):
        """Send a JSON-RPC notification (no response expected)"""
        await self._send_request(server_name, notification)
    
    async def _read_output(self, server_name: str):
        """Read stdout from MCP server subprocess"""
        if server_name not in self.processes:
            return
            
        process_info = self.processes[server_name]
        buffer = ""
        
        while server_name in self.processes:
            try:
                # Read character by character to handle streaming JSON
                char = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: process_info.stdout.read(1)
                )
                
                if not char:
                    break
                    
                buffer += char
                
                # Try to parse complete JSON objects
                if char == '\n':
                    line = buffer.strip()
                    buffer = ""
                    
                    if line:
                        try:
                            response = json.loads(line)
                            await self._handle_response(server_name, response)
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from {server_name}: {line}")
                    
            except Exception as e:
                logger.error(f"Error reading from {server_name}: {e}")
                break
    
    async def _read_errors(self, server_name: str):
        """Read stderr from MCP server subprocess"""
        if server_name not in self.processes:
            return
            
        process_info = self.processes[server_name]
        
        while server_name in self.processes:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, process_info.stderr.readline
                )
                
                if not line:
                    break
                    
                logger.error(f"[{server_name}] {line.strip()}")
                    
            except Exception as e:
                logger.error(f"Error reading stderr from {server_name}: {e}")
                break
    
    async def _handle_response(self, server_name: str, response: Dict[str, Any]):
        """Handle JSON-RPC response from server"""
        # Check if it's a response to a request
        if "id" in response and response["id"] in self.pending_requests:
            future = self.pending_requests.pop(response["id"])
            
            if "error" in response:
                future.set_result({"error": response["error"]})
            elif "result" in response:
                future.set_result(response["result"])
            else:
                future.set_result({"error": "Invalid response format"})
        
        # Handle notifications or other messages
        elif "method" in response:
            logger.debug(f"Notification from {server_name}: {response['method']}")
    
    async def cleanup(self):
        """Stop all running servers"""
        server_names = list(self.processes.keys())
        for server_name in server_names:
            await self.stop_server(server_name)

# Global subprocess manager instance
_subprocess_manager: Optional[SubprocessManager] = None

def get_subprocess_manager() -> SubprocessManager:
    """Get or create the global subprocess manager"""
    global _subprocess_manager
    if _subprocess_manager is None:
        _subprocess_manager = SubprocessManager()
    return _subprocess_manager