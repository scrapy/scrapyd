from scrapyd.orchestrator_client.api_interfaces.UserApi import UserApi
from scrapyd.orchestrator_client.exception.OrchestratorBadException import OrchestratorBadException
from scrapyd.orchestrator_client.exception.OrchestratorConnectionException import OrchestratorConnectionException
from scrapyd.orchestrator_client.exception.OrchestratorEntityNotFoundException import \
    OrchestratorEntityNotFoundException
import requests
import json
from scrapyd.orchestrator_client.utils import ORCHESTRATOR_URL, INSTANCE_ID
import logging


class ProjectApi:
    __endpoint_path = 'scrapyd_manager/project'

    def __init__(self):
        self.authorization_api = UserApi.get_instance()
        self.logger = logging.getLogger("ProjectApiInterface")

    def get(self, obj_id):
        try:
            response = requests.request(
                'GET',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/{obj_id}/",
                headers=self.authorization_api.get_headers()
            )
            if response.status_code == 200:

                self.logger.debug(f"Successful GET OBJ BY ID operation, response: {str(response.text)}")
                return json.loads(response.text)

            elif response.status_code == 404:

                self.logger.error("Entity not found on GET OBJ BY ID operation")
                return {}

            elif response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("GET OBJ BY ID UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.get(obj_id)

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while getting an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on GET OBJ by ID")

            return None

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex

    def get_by_name(self, name, instance_id=INSTANCE_ID):
        try:
            response = requests.request(
                'GET',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/get_by_name?name={name}&instance_id={instance_id}",
                headers=self.authorization_api.get_headers()
            )
            if response.status_code == 200:

                self.logger.debug(f"Successful GET OBJ BY NAME operation, response: {str(response.text)}")
                return json.loads(response.text)

            elif response.status_code == 404:

                self.logger.error("Entity not found  on GET OBJ BY NAME operation")
                return {}

            elif response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("GET OBJ BY NAME UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.get_by_name(name,instance_id)

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while getting an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on GET OBJ by NAME")

            return None

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex

    def get_all_by_instance_id(self, instance):
        try:
            response = requests.request(
                'GET',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/get_all_by_instance_id?id={instance}",
                headers=self.authorization_api.get_headers()
            )
            if response.status_code == 200:

                self.logger.debug(f"Successful GET OBJ BY NAME operation, response: {str(response.text)}")
                return json.loads(response.text)

            elif response.status_code == 404:

                self.logger.error("Entity not found  on GET OBJ BY NAME operation")
                return {}

            elif response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("GET OBJ BY NAME UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.get_all_by_instance_id(instance)

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while getting an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on GET OBJ by NAME")

            return None

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex

    def add(self, name, version, scrapyd_instance=INSTANCE_ID):
        try:
            if 'platform' in name:
                project_type = 1
            else:
                project_type = 2
            response = requests.request(
                'POST',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/",
                headers=self.authorization_api.get_headers(),
                data=json.dumps({
                    "project_type": project_type,
                    "name": name,
                    "version": version,
                    "scrapyd_instance": scrapyd_instance
                })
            )
            if response.status_code == 201:

                self.logger.debug(f"Successful ADD operation")
                return json.loads(response.text)

            elif response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("ADD OBJ UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.add(name, version, scrapyd_instance)

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while adding an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on ADD OBJ")

            return None

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex

    def update(self, proj_name, **kwargs):
        try:
            old_obj = self.get_by_name(proj_name)
            response = requests.request(
                'PUT',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/{old_obj['id']}/",
                headers=self.authorization_api.get_headers(),
                data=json.dumps(old_obj | kwargs)
            )
            if response.status_code == 200:

                self.logger.debug(f"Successful UPDATE operation")
                return json.loads(response.text)

            elif response.status_code == 404:

                self.logger.error("Entity not found exception on UPDATE operation")
                raise OrchestratorEntityNotFoundException("Entity not found exception on UPDATE operation")

            if response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("UPDATE OBJ UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.update(proj_name, **kwargs)

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while updating an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on UPDATE OBJ")

            return None

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex

    def delete(self, obj_id):
        try:
            response = requests.request(
                'DELETE',
                url=f"{ORCHESTRATOR_URL}/{self.__endpoint_path}/{obj_id}/",
                headers=self.authorization_api.get_headers()
            )
            if response.status_code == 204:

                self.logger.debug(f"Successful DELETE operation")
                return True

            elif response.status_code == 401:
                """
                    Re-authorize the client by refreshing the token and retry the request.
                """
                self.logger.debug("DELETE OBJ UNAUTHORIZED: retrying")
                self.authorization_api.refresh()
                return self.delete(obj_id)

            elif response.status_code == 404:

                self.logger.error("Entity not found exception on DELETE operation")
                raise OrchestratorEntityNotFoundException("Entity not found exception on DELETE operation")

            elif response.status_code == 500 or response.status_code == 400:

                self.logger.error(f"An exception occured while deleting an object. Server's response: {response.text}")
                raise OrchestratorBadException("An unhandled exception occured on DELETE OBJ")

            return False

        except requests.ConnectionError as e:

            self.logger.error("Could not connect to the Orchestrator")
            raise OrchestratorConnectionException("Could not connect to the Orchestrator server")

        except Exception as ex:

            raise ex
