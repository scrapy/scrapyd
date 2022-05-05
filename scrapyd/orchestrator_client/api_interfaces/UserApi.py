import requests
import json
import logging
from scrapyd.orchestrator_client.utils import USER, PASSWORD, ORCHESTRATOR_URL
from scrapyd.orchestrator_client.exception.OrchestratorConnectionException import OrchestratorConnectionException
from scrapyd.orchestrator_client.exception.OrchestratorSetupException import OrchestratorSetupException
from scrapyd.orchestrator_client.exception.OrchestratorExceptionBase import OrchestratorExceptionBase


class UserApi:
    __instance = None

    def __init__(self, headers=None):
        self.username = USER
        self.password = PASSWORD
        self.logger = logging.getLogger("UserApiInterface")
        self.refresh_token = None
        self.headers = {
            'Content-Type': 'application/json'
        } if headers is None else headers
        if UserApi.__instance is None:
            UserApi.__instance = self
        else:
            raise PermissionError('Please use the get instance method to create singletons.'
                                  'Another instance was already created')

    def get_headers(self):
        return self.headers

    @staticmethod
    def get_instance():
        """Retrieving an instance of the singleton UserApi"""

        if UserApi.__instance is None:
            UserApi()
        return UserApi.__instance

    def register(self, user, password):
        self.username = user
        self.password = password
        try:
            response = requests.request(
                "POST",
                url=f"{ORCHESTRATOR_URL}/users/register/",
                headers=self.headers,
                data=json.dumps({
                    "username": user,
                    "password": password
                }))
            self.logger.debug(f"Response returned from REGISTER: {json.dumps(response.text)}")
            return json.loads(response.text)
        except requests.ConnectionError as e:
            self.logger.error(f"There was a connection error while registering: {str(e)}")
            raise OrchestratorConnectionException("Could not connect to the orchestrator on REGISTER")

    def login(self, user=None, password=None):
        if user is None or password is None:
            if self.username is None or self.password is None:
                raise OrchestratorSetupException("Username and password are not set")
            else:
                try:
                    response = requests.request(
                        'POST',
                        url=f"{ORCHESTRATOR_URL}/users/login/",
                        headers=self.headers,
                        data=json.dumps({
                            "username": self.username,
                            "password": self.password
                        })
                    )
                    authorization_tokens = json.loads(response.text)
                    self.logger.info(
                        f"Successfully logged in, with access: {authorization_tokens['access']} and refresh {authorization_tokens['refresh']}")

                    """ 
                        Setting and returning headers for authorization
                    """
                    self.headers['Authorization'] = f"Bearer {authorization_tokens['access']}"
                    self.refresh_token = authorization_tokens['refresh']
                    self.logger.debug(f"Response returned from LOGIN: {json.dumps(self.headers)}")
                    return self.headers

                except requests.ConnectionError as e:
                    self.logger.error(f"There was a connection error while logging in: {str(e)}")
                    raise OrchestratorConnectionException("Could not connect to the orchestrator on LOGIN")
        else:
            self.username = user
            self.password = password
            try:
                response = requests.request(
                    'POST',
                    url=f"{ORCHESTRATOR_URL}/users/login/",
                    headers=self.headers,
                    data=json.dumps({
                        "username": user,
                        "password": password
                    })
                )
                authorization_tokens = json.loads(response.text)
                self.logger.info(
                    f"Successfully logged in, with access: {authorization_tokens['access']} and refresh {authorization_tokens['refresh']}")

                """ 
                    Setting and returning headers for authorization
                """
                self.headers['Authorization'] = f"Bearer {authorization_tokens['access']}"
                self.refresh_token = authorization_tokens['refresh']
                self.logger.debug(f"Response returned from LOGIN: {json.dumps(self.headers)}")
                return self.headers
            except requests.ConnectionError as e:
                self.logger.error(f"There was a connection error while logging in: {str(e)}")
                raise OrchestratorConnectionException("Could not connect to the orchestrator on LOGIN")

    def refresh(self):
        """ 
            Refreshing the access token so the authorization persists
            Return the headers with the new authorization token
            In case the refresh token expired or was used previously, a new login operation happens in the background
        """
        if self.refresh_token is not None:
            try:
                response = requests.request(
                    'POST',
                    url=f"{ORCHESTRATOR_URL}/users/login/refresh/",
                    headers=self.headers,
                    data=json.dumps({
                        "refresh": self.refresh_token
                    })
                )
                access_token = json.loads(response.text)['access']
                self.logger.info(f"Successfully refreshed token: {access_token}")

                """
                    Reconfiguring the headers so that the authorization is done correctly
                    Setting refresh_token to None, in order to marked it as used.
                    The next time refresh is requested, a login will be performed instead
                """
                self.headers['Authorization'] = f"Bearer {access_token}"
                self.logger.debug(f"The response returned from REFRESH: {json.dumps(self.headers)}")
                return self.headers
            except requests.ConnectionError as e:
                self.logger.error(f"There was a connection error while refreshing token: {str(e)}")
                raise OrchestratorConnectionException("Could not connect to the orchestrator on REFRESH")
        else:
            try:
                return self.login()
            except OrchestratorExceptionBase as e:
                raise e
