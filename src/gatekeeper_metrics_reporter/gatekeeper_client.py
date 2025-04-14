import requests

from gatekeeper_metrics_reporter.config import CONSTRAINT_API_URL, CONSTRAINTS_API_VERSION, TOKEN
from gatekeeper_metrics_reporter.log_setup import logger
from gatekeeper_metrics_reporter.prometheus import prometheus_manager


class GatekeeperClient:
    """Gatekeeper API kliens a constraint-ek és szabálysértések lekérdezéséhez"""
    
    def __init__(self, base_url: str, token: str, constraints_api_version: str):
        """
        Inicializálja a Gatekeeper API klienst
        
        Args:
            base_url: Az API alap URL-je
            token: Az autentikációs token
            constraints_api_version: Az API verziója a constraint-ekhez
        """
        self.base_url = base_url
        self.token = token
        self.constraints_api_version = constraints_api_version
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
    
    def _make_request(self, path: str):
        """
        Belső metódus API hívásokhoz
        
        Args:
            path: Az API útvonal (a base_url utáni rész)
        
        Returns:
            A válasz JSON objektuma
        
        Raises:
            requests.HTTPError: Ha az API hívás sikertelen
        """
        url = f"{self.base_url}/{path}"
        
        try:
            response = requests.get(url, headers=self.headers)
            logger.debug(f"{url} request is completed")
            logger.debug(f"Response code: {response.status_code}, Response: {response.json()}")
            return response.json()
        except requests.RequestException as e:
            raise requests.HTTPError(f"API request failed: {e}") from e
        
        
    def get_constraints(self):
        """
        Lekérdezi a Gatekeeper API-ból a constraint-ek listáját

        Returns:
            A constraint-ek listája

        Raises:
            HTTPError: Ha az API hívás sikertelen
        """
        try:
            response = self._make_request(f"{self.constraints_api_version}")
            return list(set(list(map(lambda constraint: constraint['kind'], response['resources']))))
        except requests.HTTPError as e:
            logger.error(e)
            raise
        
    def get_constraints_object_per_kind(self, constraint_kind: str):
        """
        Lekérdezi a megadott típusú constraint-ek objektumait

        Args:
            constraint_kind: A constraint típusa

        Returns:
            A constraint objektumok listája

        Raises:
            HTTPError: Ha az API hívás sikertelen
        """
        try:
            response = self._make_request(f"{self.constraints_api_version}/{constraint_kind.lower()}")
            return list(map(lambda constraint_object: constraint_object['metadata']['name'], response['items']))
        except requests.HTTPError as e:
            logger.error(e)
            raise
        
    def _get_violations(self, constraint_kind: str, constraint_object: str):
        """
        Lekérdezi a megadott constraint objektumhoz tartozó szabálysértéseket

        Args:
            constraint_kind: A constraint típusa
            constraint_object: A constraint objektum neve

        Returns:
            A szabálysértések státusza

        Raises:
            HTTPError: Ha az API hívás sikertelen
        """
        try:
            response = self._make_request(f"{self.constraints_api_version}/{constraint_kind.lower()}/{constraint_object}")
            return response['status']
        except requests.HTTPError as e:
            logger.error(e)
            raise
        
    def iterate_over_dict_to_get_violations(self,dictionary: dict) -> dict:
        """
        Rekurzív függvény a szabálysértések lekérdezéséhez

        Args:
            dictionary: A szabálysértések dict-je

        Returns:
            A szabálysértések dict-je
        """
        violations = {}
        for key, value in dictionary.items():
            if len(value) >= 1:
                for nested_value in value:
                    violations[f"{key}"] = self._get_violations(
                                                    constraint_kind=key,
                                                    constraint_object=nested_value)
            else:
                pass
        logger.debug("Make dictionary from constraint kind and objects is completed")
        return violations        
        

    def iterate_over_violation_reports(self, dict: dict):
        """
        Rekurzív függvény a szabálysértések lekérdezéséhez

        Args:
            dict: A szabálysértések dict-je

        Returns:
            A szabálysértések dict-je
        """
        for key,value in dict.items():
            if value['totalViolations'] > 0:
                for violation_array_elements in value['violations']:
                    prometheus_manager.record_violation(constraint_kind=key,
                                    namespace=violation_array_elements.get('namespace',""),
                                    kind=violation_array_elements['kind'],
                                    name=violation_array_elements['name'],
                                    enforcement_action=violation_array_elements['enforcementAction'],
                                    message=violation_array_elements['message'])
            else:
                pass
        logger.debug("Make metric values is completed")        
        
    def get_metrics_info(self):
        list_of_constraints = self.get_constraints()
        # megkapni a kindből a constraints objecteket
        list_of_constraints_object = list(map(lambda constraint_kind: self.get_constraints_object_per_kind(constraint_kind),list_of_constraints))
        # make dict from key: constraint kind and value: constraint object per kind
        dict_of_constraints_and_its_objects = dict(zip(list_of_constraints, list_of_constraints_object))
        violations = self.iterate_over_dict_to_get_violations(dict_of_constraints_and_its_objects)
        dict_of_violations = dict(map(lambda violation_key,violation_value: (violation_key,violation_value), violations.keys(),violations.values()))
        self.iterate_over_violation_reports(dict_of_violations)     


client = GatekeeperClient(
    base_url=CONSTRAINT_API_URL,
    token=TOKEN,
    constraints_api_version=CONSTRAINTS_API_VERSION
)
logger.info("Initialized Gatekeeper client")