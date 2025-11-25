"""
IP Allowlist Middleware
=======================

FastAPI middleware to restrict API access based on client IP address.
Only allows requests from pre-approved IP addresses (Director Service, Text Service, etc.)
"""

import logging
from typing import List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class IPAllowlistMiddleware(BaseHTTPMiddleware):
    """
    Middleware to restrict access based on client IP address.

    Blocks requests from IPs not in the allowlist with 403 Forbidden response.
    """

    def __init__(
        self,
        app,
        allowed_ips: Optional[List[str]] = None,
        allow_local: bool = True,
        enable_allowlist: bool = True
    ):
        """
        Initialize IP allowlist middleware.

        Args:
            app: FastAPI application instance
            allowed_ips: List of allowed IP addresses
            allow_local: Allow localhost/127.0.0.1 (for development)
            enable_allowlist: Enable/disable the allowlist (useful for testing)
        """
        super().__init__(app)
        self.allowed_ips = set(allowed_ips) if allowed_ips else set()
        self.allow_local = allow_local
        self.enable_allowlist = enable_allowlist

        # Add localhost IPs if allow_local is True
        if self.allow_local:
            self.allowed_ips.update([
                "127.0.0.1",
                "localhost",
                "::1",  # IPv6 localhost
                "0.0.0.0"
            ])

        logger.info(f"IP Allowlist Middleware initialized (enabled: {enable_allowlist})")
        logger.info(f"Allowed IPs: {', '.join(self.allowed_ips) if self.allowed_ips else 'NONE (all blocked!)'}")

    async def dispatch(self, request: Request, call_next):
        """
        Process request and check IP allowlist.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response from handler or 403 Forbidden
        """
        # Skip allowlist check if disabled
        if not self.enable_allowlist:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check if IP is allowed
        if not self._is_ip_allowed(client_ip):
            logger.warning(f"Blocked request from unauthorized IP: {client_ip}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "Forbidden",
                    "detail": "Access denied. Your IP address is not authorized to access this service.",
                    "client_ip": client_ip
                }
            )

        # IP is allowed, proceed with request
        logger.debug(f"Allowed request from authorized IP: {client_ip}")
        return await call_next(request)

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.

        Checks X-Forwarded-For, X-Real-IP headers first (for proxy/load balancer).
        Falls back to direct client IP.

        Args:
            request: Incoming request

        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For header (set by proxies/load balancers)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (alternative header for real IP)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        # Fallback if no IP found
        return "unknown"

    def _is_ip_allowed(self, ip: str) -> bool:
        """
        Check if IP is in the allowlist.

        Args:
            ip: IP address to check

        Returns:
            True if IP is allowed, False otherwise
        """
        # If no IPs are configured, block all requests (fail-safe)
        if not self.allowed_ips:
            logger.error("No allowed IPs configured! All requests will be blocked.")
            return False

        # Check if IP is in allowlist
        return ip in self.allowed_ips

    def add_ip(self, ip: str) -> None:
        """
        Add an IP to the allowlist dynamically.

        Args:
            ip: IP address to add
        """
        self.allowed_ips.add(ip)
        logger.info(f"Added IP to allowlist: {ip}")

    def remove_ip(self, ip: str) -> None:
        """
        Remove an IP from the allowlist.

        Args:
            ip: IP address to remove
        """
        self.allowed_ips.discard(ip)
        logger.info(f"Removed IP from allowlist: {ip}")

    def get_allowed_ips(self) -> List[str]:
        """
        Get list of currently allowed IPs.

        Returns:
            List of allowed IP addresses
        """
        return list(self.allowed_ips)


# Helper function to create middleware with settings
def create_ip_allowlist_middleware(
    app,
    allowed_ips_str: Optional[str] = None,
    allow_local: bool = True,
    enable_allowlist: bool = True
):
    """
    Factory function to create IP allowlist middleware from settings.

    Args:
        app: FastAPI application
        allowed_ips_str: Comma-separated string of allowed IPs
        allow_local: Allow localhost
        enable_allowlist: Enable the allowlist

    Returns:
        IPAllowlistMiddleware instance
    """
    # Parse comma-separated IPs
    allowed_ips = []
    if allowed_ips_str:
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(",") if ip.strip()]

    return IPAllowlistMiddleware(
        app=app,
        allowed_ips=allowed_ips,
        allow_local=allow_local,
        enable_allowlist=enable_allowlist
    )
