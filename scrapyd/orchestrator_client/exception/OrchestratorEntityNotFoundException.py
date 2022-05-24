from scrapyd.orchestrator_client.exception.OrchestratorExceptionBase import OrchestratorExceptionBase

class OrchestratorEntityNotFoundException(OrchestratorExceptionBase):
    """ 
        Received status 500 from OrchestratorServer - unhandled exception
    """
    pass