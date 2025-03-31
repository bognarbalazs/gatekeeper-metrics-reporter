import requests
import os
import prometheus_client
import sys
import logging
from pythonjsonlogger import jsonlogger
from fastapi import FastAPI, Response
import uvicorn

# Create app
app = FastAPI(debug=False)

# initialize variables
pod_ip = os.getenv("POD_IP")
http_port = int(os.getenv("HTTP_PORT"))
token = os.getenv("TOKEN")
constraints_apiversion = os.getenv("CONSTRAINTS_APIVERSION")
log_level = os.getenv("LOG_LEVEL")
CONSTRAINT_API_URL = "https://kubernetes.default.svc/apis/constraints.gatekeeper.sh"

# set logger
logger = logging.getLogger(__name__)
level = logging.getLevelName(f'{log_level.upper()}')
logger.setLevel(level)
stdout_handler = logging.StreamHandler(stream=sys.stdout)

# format with JSON
format_output = jsonlogger.JsonFormatter('%(levelname)s : %(name)s : %(message)s : %(asctime)s')

stdout_handler.setFormatter(format_output)
logger.addHandler(stdout_handler)

# # disable default metrics collect
prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)


def get_constraints(token, constraints_apiversion):
    url = f"{CONSTRAINT_API_URL}/{constraints_apiversion}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.request("GET", url, headers=headers, data={})

    logger.debug(f"{CONSTRAINT_API_URL}/{constraints_apiversion} request is completed")
    return list(set(list(map(lambda constraint: constraint['kind'], response.json()['resources']))))


def get_constraints_object_per_kind(token, constraints_apiversion, constraint_kind: str):
    url = f"{CONSTRAINT_API_URL}/{constraints_apiversion}/{constraint_kind.lower()}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.request("GET", url, headers=headers, data={})

    logger.debug(f"{CONSTRAINT_API_URL}/{constraints_apiversion}/{constraint_kind.lower()} request is completed")
    return list(map(lambda constraint_object: constraint_object['metadata']['name'], response.json()['items']))


def get_violations(token, constraints_apiversion, constraint_kind: str, constraint_object: str):
    url = f"{CONSTRAINT_API_URL}/{constraints_apiversion}/{constraint_kind.lower()}/{constraint_object}"
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = requests.request("GET", url, headers=headers, data={})

    logger.debug(f"{CONSTRAINT_API_URL}/{constraints_apiversion}/{constraint_kind.lower()}/{constraint_object} request is completed")
    return response.json()['status']


def iterate_over_dict_to_get_violations(dictionary: dict) -> dict:
    violations = {}
    for key, value in dictionary.items():
        if len(value) >= 1:
            for nested_value in value:
                violations[f"{key}"] = get_violations(token=token,
                                                 constraints_apiversion=constraints_apiversion,
                                                 constraint_kind=key,
                                                 constraint_object=nested_value)
        else:
            pass
    logger.debug("Make dictionary from constraint kind and objects is completed")
    return violations

#Create metrics "class"
gatekeeper_audit_violation_reports = prometheus_client.Gauge('gatekeeper_audit_violation_reports',
                                                        'Violation reports from the gatekeeper audit',
                                                        ['constraint_kind','namespace', 'kind', 'name', 'enforcementAction', 'message'])

def iterate_over_violation_reports(dict: dict):
    for key,value in dict.items():
        if value['totalViolations'] > 0:
            for violation_array_elements in value['violations']:
                if "namespace" in violation_array_elements:
                    gatekeeper_audit_violation_reports.labels(constraint_kind=key,
                                namespace=violation_array_elements['namespace'],
                                kind=violation_array_elements['kind'],
                                name=violation_array_elements['name'],
                                enforcementAction=violation_array_elements['enforcementAction'],
                                message=violation_array_elements['message']).set("1")
                else:
                    gatekeeper_audit_violation_reports.labels(constraint_kind=key,
                                namespace="",
                                kind=violation_array_elements['kind'],
                                name=violation_array_elements['name'],
                                enforcementAction=violation_array_elements['enforcementAction'],
                                message=violation_array_elements['message']).set("1")
        else:
            pass
    logger.debug("Make metric values is completed")
    
    
# Add prometheus asgi middleware to route /metrics requests
metrics_app = prometheus_client.make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/healthz/live")
def liveness():
    try:
        get_constraints(token=token, constraints_apiversion=constraints_apiversion)
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


@app.get("/metrics")
def main():
    try:
        gatekeeper_audit_violation_reports.clear()
        logger.debug("Query chain started")
        # lekérdezni a constraineket, hogy milyen kindok vannak
        list_of_constraints = get_constraints(token=token,
                                              constraints_apiversion=constraints_apiversion)
        # megkapni a kindből a constraints objecteket
        list_of_constraints_object = list(map(lambda constraint_kind: get_constraints_object_per_kind(token=token,
                                                                                                      constraints_apiversion=constraints_apiversion,
                                                                                                      constraint_kind=constraint_kind), list_of_constraints))

        # make dict from key: constraint kind and value: constraint object per kind
        dict_of_constraints_and_its_objects = dict(zip(list_of_constraints, list_of_constraints_object))
        violations = iterate_over_dict_to_get_violations(dict_of_constraints_and_its_objects)
        
        dict_of_violations = dict(map(lambda violation_key,violation_value: (violation_key,violation_value), violations.keys(),violations.values()))
        
        iterate_over_violation_reports(dict_of_violations)
        logger.debug("Query completed")
    except Exception as e:
        logger.error(e)
    return Response(prometheus_client.generate_latest(prometheus_client.REGISTRY), media_type="text/plain")


if __name__ == "__main__":
    try:
        uvicorn.run(app, host=f'{pod_ip}', port=http_port)
    except Exception as e:
        logger.error(e)
