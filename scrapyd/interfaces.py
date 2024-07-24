from zope.interface import Attribute, Interface


class IEggStorage(Interface):
    """
    A component that handles storing and retrieving eggs.
    """

    def put(eggfile, project, version):
        """Store the egg (passed in the file object) under the given project and
        version"""

    def get(project, version=None):
        """Return a tuple (version, file) for the egg matching the specified
        project and version. If version is None, the latest version is
        returned. If no egg is found for the given project/version (None, None)
        should be returned."""

    def list(project):
        """Return the list of versions which have eggs stored (for the given
        project) in order (the latest version is the currently used)."""

    def list_projects():
        """
        Return the list of projects from the stored eggs.

        .. versionadded:: 1.3.0
           Move this logic into the interface and its implementations, to allow customization.
        """

    def delete(project, version=None):
        """Delete the egg stored for the given project and version. If should
        also delete the project if no versions are left"""


class IPoller(Interface):
    """
    A component that polls for projects that need to run.
    """

    queues = Attribute(
        """
        An object (like a ``dict``) with a ``__getitem__`` method that accepts a project's name and returns its
        :py:interface:`spider queue<scrapyd.interfaces.ISpiderQueue>`.
        """
    )

    def poll():
        """Called periodically to poll for projects"""

    def next():
        """Return the next message.

        It should return a Deferred which will get fired when there is a new
        project that needs to run, or already fired if there was a project
        waiting to run already.

        The message is a dict containing (at least):

        -  the name of the project to be run in the ``_project`` key
        -  the name of the spider to be run in the ``_spider`` key
        -  a unique identifier for this run in the ``_job`` key

        This message will be passed later to :meth:`scrapyd.interfaces.IEnvironment.get_environment`.
        """

    def update_projects():
        """Called when projects may have changed, to refresh the available
        projects, including at initialization"""


class ISpiderQueue(Interface):
    def add(name, priority, **spider_args):
        """
        Add a spider to the queue given its name a some spider arguments.

        This method can return a deferred.

        .. versionchanged:: 1.3.0
           Add the ``priority`` parameter.
        """

    def pop():
        """Pop the next message from the queue. The messages is a dict
        containing a key ``name`` with the spider name and other keys as spider
        attributes.

        This method can return a deferred."""

    def list():
        """Return a list with the messages in the queue. Each message is a dict
        which must have a ``name`` key (with the spider name), and other optional
        keys that will be used as spider arguments, to create the spider.

        This method can return a deferred."""

    def count():
        """Return the number of spiders in the queue.

        This method can return a deferred."""

    def remove(func):
        """Remove all elements from the queue for which func(element) is true,
        and return the number of removed elements.
        """

    def clear():
        """Clear the queue.

        This method can return a deferred."""


class ISpiderScheduler(Interface):
    """
    A component to schedule spider runs.
    """

    def schedule(project, spider_name, priority, **spider_args):
        """
        Schedule a spider for the given project.

        .. versionchanged:: 1.3.0
           Add the ``priority`` parameter.
        """

    def list_projects():
        """Return the list of available projects"""

    def update_projects():
        """Called when projects may have changed, to refresh the available
        projects, including at initialization"""


class IEnvironment(Interface):
    """
    A component to generate the environment of crawler processes.
    """

    def get_settings(message):
        """
        Return the Scrapy settings to use for running the process.

        ``message`` is the message received from the :meth:`scrapyd.interfaces.IPoller.next` method.

        .. versionadded:: 1.4.2
           Support for overriding Scrapy settings via ``SCRAPY_`` environment variables was removed in Scrapy 2.8.
        """

    def get_environment(message, slot):
        """Return the environment variables to use for running the process.

        ``message`` is the message received from the :meth:`scrapyd.interfaces.IPoller.next` method.
        ``slot`` is the ``Launcher`` slot where the process will be running.
        """


class IJobStorage(Interface):
    """
    A component that handles storing and retrieving finished jobs.

    .. versionadded:: 1.3.0
    """

    def add(job):
        """Add a finished job in the storage."""

    def list():
        """Return a list of the finished jobs."""

    def __len__():
        """Return a number of the finished jobs."""

    def __iter__():
        """Iterate over the finished jobs in reverse order by ``end_time``."""
