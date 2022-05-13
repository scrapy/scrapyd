from twisted.cred import credentials, error
from twisted.cred.checkers import ICredentialsChecker
from twisted.cred.portal import IRealm
from twisted.internet import defer
from twisted.web.resource import IResource
from zope.interface import implementer


@implementer(IRealm)
class PublicHTMLRealm(object):

    def __init__(self, resource):
        self.resource = resource

    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            return (IResource, self.resource, lambda: None)
        raise NotImplementedError()


@implementer(ICredentialsChecker)
class StringCredentialsChecker(object):
    credentialInterfaces = (credentials.IUsernamePassword,)

    def __init__(self, username, password):
        self.username = username.encode('utf-8')
        self.password = password.encode('utf-8')

    def requestAvatarId(self, credentials):
        if credentials.username == self.username and credentials.password == self.password:
            return defer.succeed(credentials.username)
        else:
            return defer.fail(error.UnauthorizedLogin())
