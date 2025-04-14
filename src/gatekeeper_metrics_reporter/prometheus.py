import prometheus_client

from gatekeeper_metrics_reporter.log_setup import logger


class PrometheusManager:
    def __init__(self):
      """Inicializálja a Prometheus menedzsert és eltávolítja az alapértelmezett kollektorokat"""
      self.unregister_default_collectors()
      
      # Create metrics
      self.gatekeeper_audit_violation_reports = prometheus_client.Gauge(
          'gatekeeper_audit_violation_reports',
          'Violation reports from the gatekeeper audit',
          ['constraint_kind','namespace', 'kind', 'name', 'enforcementAction', 'message']
      )
      
      # Create ASGI app
      self.prometheus_asgi_app = prometheus_client.make_asgi_app()

    @classmethod
    def unregister_default_collectors(cls):
        """
        Unregisters the default Prometheus collectors (GC, Platform, and Process collectors).
        This helps reduce the number of default metrics being exported.
        """
        collectors_to_unregister = [
            prometheus_client.GC_COLLECTOR,
            prometheus_client.PLATFORM_COLLECTOR,
            prometheus_client.PROCESS_COLLECTOR
        ]

        for collector in collectors_to_unregister:
            try:
                prometheus_client.REGISTRY.unregister(collector)
            except KeyError:
                # Handle case where collector is already unregistered
                pass
              
    def get_metrics_response(self):
        """Generál egy FastAPI Response objektumot a metrikákkal"""
        return prometheus_client.generate_latest(prometheus_client.REGISTRY)
    
    def clear_violations_metrics(self):
        """Törli a jelenlegi szabálysértés metrikákat"""
        self.gatekeeper_audit_violation_reports.clear()
    
    def record_violation(self, constraint_kind, namespace, kind, name, enforcement_action, message):
        """Rögzít egy szabálysértést a metrikákban"""
        self.gatekeeper_audit_violation_reports.labels(
            constraint_kind=constraint_kind,
            namespace=namespace,
            kind=kind,
            name=name,
            enforcementAction=enforcement_action,
            message=message
        ).set(1)

prometheus_manager = PrometheusManager()
logger.debug("Initialized Prometheus manager")
prometheus_manager.unregister_default_collectors()
logger.debug("Unregistered default collectors")

