from scrapyd.orchestrator_client.exception.OrchestratorExceptionBase import OrchestratorExceptionBase

class OrchestratorSetupException(OrchestratorExceptionBase):
    """ Raised when some error ocurred during the setup process of the scrapyd """
    pass