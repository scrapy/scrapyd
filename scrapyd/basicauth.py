import os

from twisted.cred import credentials, error
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm, Portal
from twisted.internet import defer
from twisted.logger import Logger
from twisted.web.guard import BasicCredentialFactory, HTTPAuthSessionWrapper
from twisted.web.resource import IResource
from zope.interface import implementer

from scrapyd.exceptions import InvalidUsernameError

log = Logger()


# https://docs.twisted.org/en/stable/web/howto/web-in-60/http-auth.html
@implementer(IRealm)
class PublicHTMLRealm:
    def __init__(self, resource):
        self.resource = resource

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            return (IResource, self.resource, lambda: None)
        raise NotImplementedError


@implementer(ICredentialsChecker)
class StringCredentialsChecker:
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, username, password):
        self.username = username.encode()
        self.password = password.encode()

    def requestAvatarId(self, credentials):
        if credentials.username == self.username and credentials.password == self.password:
            return defer.succeed(credentials.username)
        return defer.fail(error.UnauthorizedLogin())


def wrap_resource(resource, config):
    username = os.getenv("SCRAPYD_USERNAME") or config.get("username", "")
    password = os.getenv("SCRAPYD_PASSWORD") or config.get("password", "")
    # https://www.rfc-editor.org/rfc/rfc2617#section-2
    if ":" in username:
        raise InvalidUsernameError

    if username and password:
        log.info("Basic authentication enabled")
        return HTTPAuthSessionWrapper(
            Portal(PublicHTMLRealm(resource), [StringCredentialsChecker(username, password)]),
            [BasicCredentialFactory(b"Scrapyd")],
        )

    log.info("Basic authentication disabled as either `username` or `password` is unset")
    return resource
