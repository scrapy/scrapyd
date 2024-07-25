from zope.interface import Attribute, Interface


class IEggStorage(Interface):
    """
    A component to store project eggs.
    """

    def put(eggfile, project, version):
        """
        Store the egg (a file object), which represents a ``version`` of the ``project``.
        """

    def get(project, version=None):
        """
        Return ``(version, file)`` for the egg matching the ``project`` and ``version``.

        If ``version`` is ``None``, the latest version and corresponding file are returned.

        If no egg is found, ``(None, None)`` is returned.

        .. tip:: Remember to close the ``file`` when done.
        """

    def list(project):
        """
        Return all versions of the ``project`` in order, with the latest version last.
        """

    def list_projects():
        """
        Return all projects in storage.

        .. versionadded:: 1.3.0
           Move this logic into the interface and its implementations, to allow customization.
        """

    def delete(project, version=None):
        """
        Delete the egg matching the ``project`` and ``version``. Delete the ``project``, if no versions remains.
        """


class IPoller(Interface):
    """
    A component that tracks capacity for new jobs, and starts jobs when ready.
    """

    queues = Attribute(
        """
        An object (like a ``dict``) with a ``__getitem__`` method that accepts a project's name and returns its
        :py:interface:`spider queue<scrapyd.interfaces.ISpiderQueue>` of pending jobs.
        """
    )

    def poll():
        """
        Called periodically to start jobs if there's capacity.
        """

    def next():
        """
        Return the next pending job.

        It should return a Deferred that will be fired when there's capacity, or already fired if there's capacity.

        The pending job is a ``dict`` containing at least the ``_project`` name, ``_spider`` name and ``_job`` ID.
        The job ID is unique, at least within the project.

        The pending job is later passed to :meth:`scrapyd.interfaces.IEnvironment.get_environment`.

        .. seealso:: :meth:`scrapyd.interfaces.ISpiderQueue.pop`
        """

    def update_projects():
        """
        Called when projects may have changed, to refresh the available projects, including at initialization.
        """


class ISpiderQueue(Interface):
    """
    A component to store pending jobs.

    The ``dict`` keys used by the chosen ``ISpiderQueue`` implementation must match the chosen:

    -  :ref:`launcher` service (which calls :meth:`scrapyd.interfaces.IPoller.next`)
    -  :py:interface:`~scrapyd.interfaces.IEnvironment` implementation (see :meth:`scrapyd.interfaces.IPoller.next`)
    -  :ref:`webservices<config-services>` that schedule, cancel or list pending jobs
    """

    def add(name, priority, **spider_args):
        """
        Add a pending job, given the spider ``name``, crawl ``priority`` and keyword arguments, which might include the
        ``_job`` ID, egg ``_version`` and Scrapy ``settings`` depending on the implementation, with keyword arguments
        that are not recognized by the implementation being treated as spider arguments.

        .. versionchanged:: 1.3.0
           Add the ``priority`` parameter.
        """

    def pop():
        """
        Pop the next pending job. The pending job is a ``dict`` containing the spider ``name``. Depending on the
        implementation, other keys might include the ``_job`` ID, egg ``_version`` and Scrapy ``settings``, with
        keyword arguments that are not recognized by the receiver being treated as spider arguments.
        """

    def list():
        """
        Return the pending jobs.

        .. seealso:: :meth:`scrapyd.interfaces.ISpiderQueue.pop`
        """

    def count():
        """
        Return the number of pending jobs.
        """

    def remove(func):
        """
        Remove pending jobs for which ``func(job)`` is true, and return the number of removed pending jobss.
        """

    def clear():
        """
        Remove all pending jobs.
        """


class ISpiderScheduler(Interface):
    """
    A component to schedule jobs.
    """

    def schedule(project, spider_name, priority, **spider_args):
        """
        Schedule a crawl.

        .. versionchanged:: 1.3.0
           Add the ``priority`` parameter.
        """

    def list_projects():
        """
        Return all projects that can be scheduled.
        """

    def update_projects():
        """
        Called when projects may have changed, to refresh the available projects, including at initialization.
        """


class IEnvironment(Interface):
    """
    A component to generate the environment of jobs.

    The chosen ``IEnvironment`` implementation must match the chosen :ref:`launcher` service.
    """

    def get_settings(message):
        """
        Return the Scrapy settings to use for running the process.

        Depending on the chosen :ref:`launcher`, this would be one of more ``LOG_FILE`` or ``FEEDS``.

        .. versionadded:: 1.4.2
           Support for overriding Scrapy settings via ``SCRAPY_`` environment variables was removed in Scrapy 2.8.

        :param message: the pending job received from the :meth:`scrapyd.interfaces.IPoller.next` method
        """

    def get_environment(message, slot):
        """
        Return the environment variables to use for running the process.

        Depending on the chosen :ref:`launcher`, this would be one of more of ``SCRAPY_PROJECT``,
        ``SCRAPYD_EGG_VERSION`` or ``SCRAPY_SETTINGS_MODULE``.

        :param message: the pending job received from the :meth:`scrapyd.interfaces.IPoller.next` method
        :param slot: the :ref:`launcher` slot for tracking the process
        """


class IJobStorage(Interface):
    """
    A component to store finished jobs.

    .. versionadded:: 1.3.0
    """

    def add(job):
        """
        Add a finished job in the storage.
        """

    def list():
        """
        Return the finished jobs.

        .. seealso:: :meth:`scrapyd.interfaces.IJobStorage.__iter__`
        """

    def __len__():
        """
        Return the number of finished jobs.
        """

    def __iter__():
        """
        Iterate over the finished jobs in reverse order by ``end_time``.

        A job has the attributes ``project``, ``spider``, ``job``, ``start_time`` and ``end_time`` and may have the
        attributes ``args`` (``scrapy crawl`` CLI arguments) and ``env`` (environment variables).
        """
