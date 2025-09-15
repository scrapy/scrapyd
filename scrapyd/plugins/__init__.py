"""
Scrapyd Plugin System

This module provides a plugin architecture for extending Scrapyd functionality.
Plugins can hook into various events during spider execution and provide
custom implementations for storage, monitoring, authentication, and more.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
import importlib
import pkg_resources
import logging
from zope.interface import Interface, implementer

logger = logging.getLogger(__name__)


class IScrapydPlugin(Interface):
    """Interface for Scrapyd plugins"""

    def get_name():
        """Return plugin name"""

    def get_version():
        """Return plugin version"""

    def get_description():
        """Return plugin description"""

    def initialize(config):
        """Initialize plugin with configuration"""

    def shutdown():
        """Cleanup plugin resources"""


class ScrapydPlugin(ABC):
    """Base class for Scrapyd plugins"""

    @abstractmethod
    def get_name(self) -> str:
        """Return plugin name"""
        pass

    @abstractmethod
    def get_version(self) -> str:
        """Return plugin version"""
        pass

    def get_description(self) -> str:
        """Return plugin description"""
        return f"{self.get_name()} plugin"

    def get_author(self) -> str:
        """Return plugin author"""
        return "Unknown"

    def get_license(self) -> str:
        """Return plugin license"""
        return "Unknown"

    def get_dependencies(self) -> List[str]:
        """Return list of required dependencies"""
        return []

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin with configuration"""
        pass

    def shutdown(self) -> None:
        """Cleanup plugin resources"""
        pass

    def is_enabled(self, config: Dict[str, Any]) -> bool:
        """Check if plugin should be enabled"""
        return config.get(f'plugin_{self.get_name()}_enabled', True)


class SpiderEventPlugin(ScrapydPlugin):
    """Base class for plugins that handle spider events"""

    def on_spider_scheduled(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Called when a spider is scheduled"""
        pass

    def on_spider_started(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Called when a spider starts execution"""
        pass

    def on_spider_completed(self, project: str, spider: str, job_id: str,
                          success: bool, stats: Dict[str, Any], **kwargs) -> None:
        """Called when a spider completes execution"""
        pass

    def on_spider_cancelled(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Called when a spider is cancelled"""
        pass

    def on_spider_error(self, project: str, spider: str, job_id: str,
                       error: Exception, **kwargs) -> None:
        """Called when a spider encounters an error"""
        pass


class StoragePlugin(ScrapydPlugin):
    """Base class for storage plugins"""

    @abstractmethod
    def store_egg(self, project: str, version: str, egg_data: bytes) -> str:
        """Store project egg file"""
        pass

    @abstractmethod
    def get_egg(self, project: str, version: str) -> bytes:
        """Retrieve project egg file"""
        pass

    @abstractmethod
    def delete_egg(self, project: str, version: Optional[str] = None) -> bool:
        """Delete project egg file(s)"""
        pass

    @abstractmethod
    def list_eggs(self, project: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available eggs"""
        pass


class AuthenticationPlugin(ScrapydPlugin):
    """Base class for authentication plugins"""

    @abstractmethod
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate user credentials"""
        pass

    @abstractmethod
    def authorize(self, username: str, action: str, resource: str) -> bool:
        """Authorize user action on resource"""
        pass

    def get_user_info(self, username: str) -> Dict[str, Any]:
        """Get user information"""
        return {"username": username}


class MonitoringPlugin(ScrapydPlugin):
    """Base class for monitoring plugins"""

    def collect_metrics(self) -> Dict[str, Any]:
        """Collect custom metrics"""
        return {}

    def send_alert(self, level: str, message: str, **kwargs) -> None:
        """Send alert notification"""
        pass

    def health_check(self) -> Dict[str, Any]:
        """Perform health check"""
        return {"status": "ok"}


class PluginManager:
    """Manages plugin lifecycle and discovery"""

    def __init__(self):
        self.plugins: Dict[str, ScrapydPlugin] = {}
        self.event_plugins: List[SpiderEventPlugin] = []
        self.storage_plugins: List[StoragePlugin] = []
        self.auth_plugins: List[AuthenticationPlugin] = []
        self.monitoring_plugins: List[MonitoringPlugin] = []
        self.config: Dict[str, Any] = {}

    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize plugin manager with configuration"""
        self.config = config
        self.discover_plugins()
        self.load_plugins()

    def discover_plugins(self) -> None:
        """Discover plugins using entry points"""
        logger.info("Discovering plugins...")

        # Discover plugins via entry points
        for entry_point in pkg_resources.iter_entry_points('scrapyd.plugins'):
            try:
                plugin_class = entry_point.load()
                plugin = plugin_class()

                if not isinstance(plugin, ScrapydPlugin):
                    logger.warning(f"Plugin {entry_point.name} does not inherit from ScrapydPlugin")
                    continue

                self.plugins[plugin.get_name()] = plugin
                logger.info(f"Discovered plugin: {plugin.get_name()} v{plugin.get_version()}")

            except Exception as e:
                logger.error(f"Failed to load plugin {entry_point.name}: {e}")

        # Discover plugins via configuration
        plugin_modules = self.config.get('plugin_modules', [])
        for module_name in plugin_modules:
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, ScrapydPlugin) and
                        attr != ScrapydPlugin):

                        plugin = attr()
                        self.plugins[plugin.get_name()] = plugin
                        logger.info(f"Discovered plugin from module {module_name}: {plugin.get_name()}")

            except Exception as e:
                logger.error(f"Failed to load plugin module {module_name}: {e}")

    def load_plugins(self) -> None:
        """Load and initialize plugins"""
        logger.info("Loading plugins...")

        for name, plugin in self.plugins.items():
            try:
                if not plugin.is_enabled(self.config):
                    logger.info(f"Plugin {name} is disabled")
                    continue

                # Check dependencies
                missing_deps = self._check_dependencies(plugin)
                if missing_deps:
                    logger.error(f"Plugin {name} missing dependencies: {missing_deps}")
                    continue

                # Initialize plugin
                plugin.initialize(self.config)

                # Categorize plugin
                if isinstance(plugin, SpiderEventPlugin):
                    self.event_plugins.append(plugin)
                if isinstance(plugin, StoragePlugin):
                    self.storage_plugins.append(plugin)
                if isinstance(plugin, AuthenticationPlugin):
                    self.auth_plugins.append(plugin)
                if isinstance(plugin, MonitoringPlugin):
                    self.monitoring_plugins.append(plugin)

                logger.info(f"Loaded plugin: {name} v{plugin.get_version()}")

            except Exception as e:
                logger.error(f"Failed to initialize plugin {name}: {e}")

    def _check_dependencies(self, plugin: ScrapydPlugin) -> List[str]:
        """Check if plugin dependencies are satisfied"""
        missing = []
        for dep in plugin.get_dependencies():
            try:
                pkg_resources.require(dep)
            except pkg_resources.DistributionNotFound:
                missing.append(dep)
        return missing

    def shutdown(self) -> None:
        """Shutdown all plugins"""
        logger.info("Shutting down plugins...")

        for name, plugin in self.plugins.items():
            try:
                plugin.shutdown()
                logger.debug(f"Shutdown plugin: {name}")
            except Exception as e:
                logger.error(f"Error shutting down plugin {name}: {e}")

    def get_plugin(self, name: str) -> Optional[ScrapydPlugin]:
        """Get plugin by name"""
        return self.plugins.get(name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins"""
        return [
            {
                'name': plugin.get_name(),
                'version': plugin.get_version(),
                'description': plugin.get_description(),
                'author': plugin.get_author(),
                'license': plugin.get_license(),
                'enabled': plugin.is_enabled(self.config)
            }
            for plugin in self.plugins.values()
        ]

    # Event handling methods
    def on_spider_scheduled(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Notify all event plugins of spider scheduling"""
        for plugin in self.event_plugins:
            try:
                plugin.on_spider_scheduled(project, spider, job_id, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.get_name()}.on_spider_scheduled: {e}")

    def on_spider_started(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Notify all event plugins of spider start"""
        for plugin in self.event_plugins:
            try:
                plugin.on_spider_started(project, spider, job_id, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.get_name()}.on_spider_started: {e}")

    def on_spider_completed(self, project: str, spider: str, job_id: str,
                          success: bool, stats: Dict[str, Any], **kwargs) -> None:
        """Notify all event plugins of spider completion"""
        for plugin in self.event_plugins:
            try:
                plugin.on_spider_completed(project, spider, job_id, success, stats, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.get_name()}.on_spider_completed: {e}")

    def on_spider_cancelled(self, project: str, spider: str, job_id: str, **kwargs) -> None:
        """Notify all event plugins of spider cancellation"""
        for plugin in self.event_plugins:
            try:
                plugin.on_spider_cancelled(project, spider, job_id, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.get_name()}.on_spider_cancelled: {e}")

    def on_spider_error(self, project: str, spider: str, job_id: str,
                       error: Exception, **kwargs) -> None:
        """Notify all event plugins of spider error"""
        for plugin in self.event_plugins:
            try:
                plugin.on_spider_error(project, spider, job_id, error, **kwargs)
            except Exception as e:
                logger.error(f"Error in plugin {plugin.get_name()}.on_spider_error: {e}")


# Global plugin manager instance
plugin_manager = PluginManager()


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance"""
    return plugin_manager


def register_plugin(plugin: ScrapydPlugin) -> None:
    """Manually register a plugin"""
    plugin_manager.plugins[plugin.get_name()] = plugin


def unregister_plugin(name: str) -> bool:
    """Unregister a plugin by name"""
    if name in plugin_manager.plugins:
        try:
            plugin_manager.plugins[name].shutdown()
            del plugin_manager.plugins[name]
            return True
        except Exception as e:
            logger.error(f"Error unregistering plugin {name}: {e}")
    return False