"""
Ngrok Tunnel Manager for Phishy AI
Handles ngrok tunnel lifecycle, monitoring, and configuration
"""
import subprocess
import requests
import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import os
import signal
import psutil

logger = logging.getLogger(__name__)

class NgrokManager:
    """Manages ngrok tunnel lifecycle and monitoring"""
    
    def __init__(self, 
                 port: int = 8080, 
                 subdomain: Optional[str] = None,
                 auth_token: Optional[str] = None,
                 config_file: Optional[str] = None):
        self.port = port
        self.subdomain = subdomain
        self.auth_token = auth_token
        self.config_file = config_file or "ngrok.yml"
        self.process = None
        self.tunnel_url = None
        self.public_url = None
        self.status = "inactive"
        
        # File paths
        self.data_dir = Path("data")
        self.tunnel_status_file = self.data_dir / "tunnel_status.json"
        self.data_dir.mkdir(exist_ok=True)
        
        # Setup ngrok config if auth token provided
        if self.auth_token:
            self._setup_ngrok_config()
    
    def _setup_ngrok_config(self):
        """Setup ngrok configuration file"""
        try:
            config_content = f"""
version: "2"
authtoken: {self.auth_token}
tunnels:
  phishy:
    proto: http
    addr: {self.port}
    bind_tls: true
"""
            if self.subdomain:
                config_content += f"    subdomain: {self.subdomain}\n"
            
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            
            logger.info(f"Ngrok config created: {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error creating ngrok config: {e}")
            raise
    
    def start_tunnel(self) -> bool:
        """Start ngrok tunnel"""
        try:
            # Check if ngrok is already running
            if self._is_ngrok_running():
                logger.warning("Ngrok is already running")
                return self._get_existing_tunnel_info()
            
            # Build ngrok command
            cmd = ["ngrok", "http", str(self.port)]
            
            if self.subdomain and self.auth_token:
                cmd.extend(["--subdomain", self.subdomain])
            
            if os.path.exists(self.config_file):
                cmd.extend(["--config", self.config_file])
            
            # Add additional options for development
            cmd.extend([
                "--log", "stdout",
                "--log-level", "info"
            ])
            
            logger.info(f"Starting ngrok with command: {' '.join(cmd)}")
            
            # Start ngrok process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for tunnel to establish
            max_retries = 30
            for i in range(max_retries):
                time.sleep(1)
                if self._get_tunnel_info():
                    self.status = "active"
                    self._save_tunnel_status()
                    logger.info(f"Ngrok tunnel established: {self.public_url}")
                    return True
            
            logger.error("Failed to establish ngrok tunnel within timeout")
            self.stop_tunnel()
            return False
            
        except Exception as e:
            logger.error(f"Error starting ngrok tunnel: {e}")
            self.status = "error"
            return False
    
    def stop_tunnel(self):
        """Stop ngrok tunnel"""
        try:
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                
                self.process = None
                logger.info("Ngrok process terminated")
            
            # Kill any remaining ngrok processes
            self._kill_ngrok_processes()
            
            self.status = "inactive"
            self.tunnel_url = None
            self.public_url = None
            self._save_tunnel_status()
            
        except Exception as e:
            logger.error(f"Error stopping ngrok tunnel: {e}")
    
    def _is_ngrok_running(self) -> bool:
        """Check if ngrok is already running"""
        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _get_existing_tunnel_info(self) -> bool:
        """Get info from existing ngrok tunnel"""
        return self._get_tunnel_info()
    
    def _get_tunnel_info(self) -> bool:
        """Get tunnel information from ngrok API"""
        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                data = response.json()
                
                for tunnel in data.get("tunnels", []):
                    if tunnel.get("proto") == "https":
                        self.public_url = tunnel.get("public_url")
                        self.tunnel_url = self.public_url
                        
                        # Extract tunnel details
                        config = tunnel.get("config", {})
                        logger.info(f"Found tunnel: {self.public_url} -> {config.get('addr')}")
                        return True
                
                logger.warning("No HTTPS tunnel found in ngrok API response")
                return False
                
        except Exception as e:
            logger.error(f"Error getting tunnel info: {e}")
            return False
    
    def _kill_ngrok_processes(self):
        """Kill any running ngrok processes"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if 'ngrok' in proc.info['name'].lower():
                    proc.kill()
                    logger.info(f"Killed ngrok process: {proc.info['pid']}")
        except Exception as e:
            logger.error(f"Error killing ngrok processes: {e}")
    
    def get_tunnel_status(self) -> Dict[str, Any]:
        """Get current tunnel status"""
        if self.status == "active" and not self._get_tunnel_info():
            self.status = "inactive"
        
        return {
            "status": self.status,
            "tunnel_url": self.tunnel_url,
            "public_url": self.public_url,
            "port": self.port,
            "subdomain": self.subdomain,
            "last_checked": datetime.now(timezone.utc).isoformat()
        }
    
    def _save_tunnel_status(self):
        """Save tunnel status to file"""
        try:
            status = self.get_tunnel_status()
            with open(self.tunnel_status_file, 'w') as f:
                json.dump(status, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tunnel status: {e}")
    
    def monitor_tunnel(self, check_interval: int = 30) -> bool:
        """Monitor tunnel health"""
        try:
            if not self._get_tunnel_info():
                logger.warning("Tunnel health check failed")
                self.status = "inactive"
                return False
            
            self.status = "active"
            return True
            
        except Exception as e:
            logger.error(f"Error monitoring tunnel: {e}")
            self.status = "error"
            return False
    
    async def auto_restart_on_failure(self, max_retries: int = 3):
        """Automatically restart tunnel on failure"""
        retries = 0
        
        while retries < max_retries:
            if not self.monitor_tunnel():
                logger.warning(f"Tunnel failed, attempting restart ({retries + 1}/{max_retries})")
                
                self.stop_tunnel()
                await asyncio.sleep(5)  # Wait before restart
                
                if self.start_tunnel():
                    logger.info("Tunnel restarted successfully")
                    return True
                
                retries += 1
                await asyncio.sleep(10)  # Wait before next retry
            else:
                return True
        
        logger.error("Failed to restart tunnel after maximum retries")
        return False
    
    def get_api_endpoints(self) -> Dict[str, str]:
        """Get API endpoints for current tunnel"""
        if not self.public_url:
            return {}
        
        base_url = self.public_url
        return {
            "flag_email": f"{base_url}/email-flagging/flag",
            "websocket": f"{base_url.replace('https://', 'wss://')}/email-flagging/ws",
            "health": f"{base_url}/email-flagging/health",
            "setup": f"{base_url}/email-flagging/plugins/setup",
            "admin": f"{base_url}/email-flagging/admin"
        }
    
    def generate_plugin_config(self, plugin_type: str, user_email: str, organization: str = None) -> Dict[str, Any]:
        """Generate plugin configuration"""
        if not self.public_url:
            raise ValueError("No active tunnel found")
        
        plugin_id = f"{plugin_type}_{user_email}_{int(time.time())}"
        
        return {
            "plugin_id": plugin_id,
            "plugin_type": plugin_type,
            "tunnel_url": self.public_url,
            "api_endpoints": self.get_api_endpoints(),
            "user_email": user_email,
            "organization": organization,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "websocket_url": f"{self.public_url.replace('https://', 'wss://')}/email-flagging/ws/{plugin_id}"
        }

# Singleton instance
ngrok_manager = NgrokManager()

def get_ngrok_manager() -> NgrokManager:
    """Get the global ngrok manager instance"""
    return ngrok_manager

async def update_phishy_tunnel_config(tunnel_url: str):
    """Update Phishy backend with new tunnel URL"""
    try:
        # Update environment variable
        os.environ['BASE_URL'] = tunnel_url
        
        # Update .env file if it exists
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text()
            
            # Replace or add BASE_URL
            lines = content.split('\n')
            updated = False
            
            for i, line in enumerate(lines):
                if line.startswith('BASE_URL='):
                    lines[i] = f'BASE_URL={tunnel_url}'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'BASE_URL={tunnel_url}')
            
            env_file.write_text('\n'.join(lines))
        else:
            # Create .env file
            env_file.write_text(f'BASE_URL={tunnel_url}\n')
        
        logger.info(f"Updated Phishy configuration with tunnel URL: {tunnel_url}")
        
        # Notify email flagging route about tunnel update
        try:
            import requests
            response = requests.post(
                f"http://localhost:8080/email-flagging/tunnel/update",
                params={"tunnel_url": tunnel_url, "public_url": tunnel_url},
                timeout=5
            )
            if response.status_code == 200:
                logger.info("Notified email flagging system about tunnel update")
        except Exception as e:
            logger.warning(f"Could not notify email flagging system: {e}")
        
    except Exception as e:
        logger.error(f"Error updating Phishy tunnel config: {e}")

if __name__ == "__main__":
    # Command line interface for ngrok manager
    import argparse
    
    parser = argparse.ArgumentParser(description="Ngrok Manager for Phishy AI")
    parser.add_argument("command", choices=["start", "stop", "status", "restart"])
    parser.add_argument("--port", type=int, default=8080, help="Port to tunnel")
    parser.add_argument("--subdomain", type=str, help="Ngrok subdomain")
    parser.add_argument("--auth-token", type=str, help="Ngrok auth token")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize manager
    manager = NgrokManager(
        port=args.port,
        subdomain=args.subdomain,
        auth_token=args.auth_token
    )
    
    if args.command == "start":
        if manager.start_tunnel():
            print(f"✅ Tunnel started: {manager.public_url}")
            # Update Phishy configuration
            asyncio.run(update_phishy_tunnel_config(manager.public_url))
        else:
            print("❌ Failed to start tunnel")
            exit(1)
    
    elif args.command == "stop":
        manager.stop_tunnel()
        print("✅ Tunnel stopped")
    
    elif args.command == "status":
        status = manager.get_tunnel_status()
        print(f"Status: {status['status']}")
        if status['tunnel_url']:
            print(f"URL: {status['tunnel_url']}")
    
    elif args.command == "restart":
        manager.stop_tunnel()
        time.sleep(2)
        if manager.start_tunnel():
            print(f"✅ Tunnel restarted: {manager.public_url}")
            asyncio.run(update_phishy_tunnel_config(manager.public_url))
        else:
            print("❌ Failed to restart tunnel")
            exit(1)