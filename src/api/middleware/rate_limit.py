"""
Rate Limiting Middleware for Local Agent API.
Part of Task API-03: Rate Limiting.

Protects the API from brute-force or accidental heavy load.
Default: 60 requests per minute per IP.
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.utils.logger import log

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    In-memory Rate Limiter using a sliding window.
    """
    
    def __init__(self, app, limit: int = 60, window_secs: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window_secs = window_secs
        # Key: IP, Value: (request_count, window_start_time)
        self.clients: Dict[str, Tuple[int, float]] = {}

    async def dispatch(self, request: Request, call_next):
        # Identify client by host (local API typically localhost)
        client_ip = request.client.host
        now = time.time()
        
        # Cleanup expired entries occasionally (10% chance per request)
        if now % 10 < 1:
            self._cleanup(now)

        if client_ip not in self.clients:
            self.clients[client_ip] = (1, now)
        else:
            count, start_time = self.clients[client_ip]
            
            if now - start_time > self.window_secs:
                # Window expired, reset
                self.clients[client_ip] = (1, now)
            else:
                if count >= self.limit:
                    log.warning(f"Rate limit exceeded for client: {client_ip}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={"detail": "Too many requests. Please slow down."}
                    )
                self.clients[client_ip] = (count + 1, start_time)

        response = await call_next(request)
        
        # Add headers for transparency
        if client_ip in self.clients:
            count, start_time = self.clients[client_ip]
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.limit - count))
            response.headers["X-RateLimit-Reset"] = str(int(start_time + self.window_secs))
            
        return response

    def _cleanup(self, now: float):
        """Remove clients that haven't made a request in the last window."""
        to_delete = [
            ip for ip, (_, start) in self.clients.items() 
            if now - start > self.window_secs
        ]
        for ip in to_delete:
            del self.clients[ip]
