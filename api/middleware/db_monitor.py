import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from api.database import engine

logger = logging.getLogger("db_monitor")

class DBConnectionMonitorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log connection pool statistics if the request takes longer than 0.5 seconds
        if process_time > 0.5:
            pool_status = {
                "connections_in_use": engine.pool.checkedout(),
                "connections_available": engine.pool.checkedin(),
                "total_connections": engine.pool.size(),
                "request_path": request.url.path,
                "process_time": process_time
            }
            logger.info(f"DB Pool Status: {pool_status}")
        
        return response 