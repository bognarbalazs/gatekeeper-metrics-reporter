from fastapi import FastAPI, Response

from gatekeeper_metrics_reporter.gatekeeper_client import client
from gatekeeper_metrics_reporter.log_setup import logger
from gatekeeper_metrics_reporter.prometheus import prometheus_manager

app = FastAPI()

# Routes
@app.get("/healthz/live")
def liveness():
    try:
        client.get_constraints()
        return Response("OK", status_code=200, media_type="text/plain")
    except Exception as e:
        logger.error(e)
        return Response("NOK", status_code=500, media_type="text/plain")


@app.get("/healthz/ready")
def readiness():
    try:
        return Response("OK", status_code=200, media_type="text/plain")
    except Exception as e:
        logger.error(e)
        return Response("NOK", status_code=500, media_type="text/plain")


# Mounts
@app.get("/metrics")
def metrics():
    try:
        prometheus_manager.clear_violations_metrics()
        client.get_metrics_info()
    except Exception as e:
        logger.error(e)
        raise
    return Response(prometheus_manager.get_metrics_response(), media_type="text/plain")

# Mount ASGI middleware
app.mount("/metrics", prometheus_manager.prometheus_asgi_app)