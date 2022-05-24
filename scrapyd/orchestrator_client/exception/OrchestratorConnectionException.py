from scrapyd.orchestrator_client.exception.OrchestratorExceptionBase import OrchestratorExceptionBase
class OrchestratorConnectionException(OrchestratorExceptionBase):
    """ Raised when scrapyd could not connect to the orchestrator """
    pass