Command-line interface
======================

The CLI is simply a wrapper around `twistd <https://docs.twisted.org/en/stable/core/howto/basics.html#twistd>`__.

The most relevant option is ``--logfile`` (``-l``). The ``--nodaemon`` option is always enabled by Scrapyd.

.. code-block:: none

   Usage: scrapyd [options]
   Options:
     -b, --debug          Run the application in the Python Debugger (implies
                          nodaemon),         sending SIGUSR2 will drop into
                          debugger
         --chroot=        Chroot to a supplied directory before running
     -e, --encrypted      The specified tap/aos file is encrypted.
         --euid           Set only effective user-id rather than real user-id.
                          (This option has no effect unless the server is running
                          as root, in which case it means not to shed all
                          privileges after binding ports, retaining the option to
                          regain privileges in cases such as spawning processes.
                          Use with caution.)
     -f, --file=          read the given .tap file [default: twistd.tap]
     -g, --gid=           The gid to run as.  If not specified, the default gid
                          associated with the specified --uid is used.
         --help           Display this help and exit.
         --help-reactors  Display a list of possibly available reactor names.
     -l, --logfile=       log to a specified file, - for stdout
         --logger=        A fully-qualified name to a log observer factory to use
                          for the initial log observer.  Takes precedence over
                          --logfile and --syslog (when available).
     -n, --nodaemon       don't daemonize, don't use default umask of 0077
     -o, --no_save        do not save state on shutdown
         --originalname   Don't try to change the process name
     -p, --profile=       Run in profile mode, dumping results to specified file.
         --pidfile=       Name of the pidfile [default: twistd.pid]
         --prefix=        use the given prefix when syslogging [default: twisted]
         --profiler=      Name of the profiler to use (profile, cprofile).
                          [default: cprofile]
     -r, --reactor=       Which reactor to use (see --help-reactors for a list of
                          possibilities)
     -s, --source=        Read an application from a .tas file (AOT format).
         --savestats      save the Stats object rather than the text output of the
                          profiler.
         --spew           Print an insanely verbose log of everything that happens.
                          Useful when debugging freezes or locks in complex code.
         --syslog         Log to syslog, not to file
     -u, --uid=           The uid to run as.
         --umask=         The (octal) file creation mask to apply.
         --version        Print version information and exit.

   Scrapyd is an application for deploying and running Scrapy spiders.
