# SPDX-License-Identifier: BSD-3-Clause
# Copyright (c) 2023, Stephane Capponi and Others

from __future__ import annotations

from collections import defaultdict
from importlib import import_module
from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from socon.conf import settings
from socon.core.exceptions import (
    ImproperlyConfigured,
    ManagerNotFound,
    ManagerNotHooked,
    ServiceNotFound,
)
from socon.core.registry import projects, registry

if TYPE_CHECKING:
    from socon.core.registry.config import RegistryConfig


__all__ = ["managers", "ServiceManager", "Service"]


class ServiceManagerRegistry:
    """Base class that registers all managers"""

    def __init__(self) -> None:
        self.managers: Dict[str, Type[ServiceManager]] = {}

    def get_manager(self, name: str) -> Type[ServiceManager]:
        """Return the service manager with the given name"""
        try:
            return self.managers[name]
        except KeyError:
            raise ManagerNotFound(
                "'{}' does not exist. Choices are:\n{}".format(
                    name, list(self.managers.keys())
                )
            )

    def get_managers(self) -> list[Type[ServiceManager]]:
        """Return a list of all defined managers"""
        return self.managers.values()

    def add_manager(self, manager: Type[ServiceManager]):
        """Add a manager to the registry"""
        name = manager.name
        if name in self.managers:
            raise ImproperlyConfigured(
                "Manager names aren't unique. Duplicates:\n{}".format(name)
            )
        self.managers[name] = manager


# Declared here to avoid import recursion. As Service and ServiceManager
# depend on the registry, putting them in different files increase the
# import complexity.
managers = ServiceManagerRegistry()

# -------------------------------- Base class -------------------------------- #


class Service:
    """
    The base class from which all services ultimately derive.

    Each service must be linked to a ServiceManager by providing it's
    name as a Meta attribute or as a parameter of the service class::

        class Myservice(Service, service_manager = "foo"):
            pass

        class Myservice(Service):

            class Meta:
                service_manager = "foo"

    The service can also be abstract. This is usefull if you want to make
    a service interface. Same as the name of the manager, the abstract attribute
    must be declared in the Meta class or as a parameter of the service class::

        class Myservice(Service, abstract=True):
            pass

        class Myservice(Service):

            class Meta:
                abstract = True
    """

    def __init_subclass__(
        cls, abstract: Optional[bool] = None, service_name: Optional[str] = None
    ) -> None:
        # Get the meta attribute
        attr_meta = cls.__dict__.pop("Meta")

        # Get attribute of the current class
        abstract = abstract or getattr(attr_meta, "abstract", False)
        meta = attr_meta or getattr(cls, "Meta", None)
        base_meta = getattr(cls, "_meta", None)

        # Add to the class the _meta attribute for current and child class
        cls._meta = meta

        # Nothing to do if the current class is abstract
        if abstract is True:
            return

        # Determine the name of the service
        service_name = service_name or getattr(meta, "name")
        if not service_name:
            service_name = cls.__name__.lower()
        cls._meta.name = service_name

        # Set the manager from the base class of this class
        if base_meta:
            if not hasattr(meta, "manager"):
                cls._meta.manager = base_meta.manager

        # If the base class has not been linked to a registry, we raise
        # an error as we won't be able to register the subclass
        if cls._meta.manager is None:
            raise ImproperlyConfigured(
                "{} service must be linked to a manager".format(cls.__name__)
            )

        # Get the manager for this service
        manager = managers.get_manager(cls._meta.manager)

        # Start registering the subclass to the main registry. First required
        # things is to find the registry config that hold the subclass
        module = cls.__module__

        config = registry.get_containing_registry_config(module)
        if config is None:
            raise RuntimeError(
                "{} class isn't in a project, plugin or in the common config. "
                "Check the INSTALLED_PROJECTS, INSTALLED_PLUGINS or the "
                "common config '{}'".format(
                    cls.__name__, settings.get_settings_module_name()
                )
            )

        manager.add_service(config, cls)


class ServiceManager:
    """Main class to register manager registry

    By subclassing your class from the ServiceManager and by explicitly
    placing your class into `managers.py` in a plugin, project or in the common
    config will auto-register the class as as manager. However,
    this class will require that you define two mandatory attribute:

        name: The name of the manager
        lookup_module: The module where we will find services to link to this manager

    """

    # Name of the manager
    name: str = None

    # Name of the module the service manager will look into to import it's services.
    lookup_module: str = None

    def __init__(self) -> None:
        self._services = defaultdict(lambda: defaultdict(dict))
        self._imported_configs = []

    def __init_subclass__(cls, name: str = None, lookup: str = None) -> None:
        # Check the manadatory attributes
        cls.name = cls._get_mandatory_attr("name", name)
        cls.lookup_module = cls._get_mandatory_attr("lookup_module", lookup)

        # Register the manager in the managers registry
        managers.add_manager(cls())

    @classmethod
    def _get_mandatory_attr(cls, attr: str, default: Any = None) -> Any:
        cls_attr = getattr(cls, attr)
        value = cls_attr if cls_attr is not None else default
        if value is None:
            raise ImproperlyConfigured(
                "'{}' must supply a {} attribute".format(cls.__name__, attr)
            )
        return value

    def has_services(self) -> None:
        """Raise an exception if the manager does not contain any services"""
        if not self._services:
            raise ManagerNotHooked(
                "'{}' does not contain any services".format(self.name)
            )
        return True

    def get_modules(self, config: Type[RegistryConfig]) -> Union[list, str]:
        """Return a list of modules to be imported"""
        return "{}.{}".format(config.name, self.lookup_module)

    def auto_discover(self) -> Type[Service]:
        """
        Look into each installed registry config for services. This method
        import all modules returned by :meth:`get_modules()`. When
        a module is imported, it auto-register every services in that module.
        """
        # Find core config services
        core_config = registry.get_socon_common_config()
        self.discover(core_config)

        # In any case if the settings are not configured we can't continue.
        # This is because common, projects and plugins config cannot be
        # registered if the settings is not ready or has error
        if not settings.configured:
            return self

        # Check in the common config
        common_config = registry.get_user_common_config()
        self.discover(common_config)

        # Check in every plugins and projects
        for user_config in registry.get_user_configs():
            self.discover(user_config)

        return self

    def discover(self, config: Union[Type[RegistryConfig], None]) -> None:
        """
        Look into a specific registry config for services. This method import all
        modules return by :meth:`get_modules()` for that specific config.
        """
        if config is None:
            return

        # If the config is in the cache it means that all modules
        # for that config have been imported
        if config.label in self._imported_configs:
            return

        self._imported_configs.append(config.label)
        modules = self.get_modules(config)
        if isinstance(modules, str):
            modules = [modules]
        for module in modules:
            # This will trigger the __init_subclass__ of ServiceManager
            try:
                import_module(module)
            except ModuleNotFoundError:
                pass

    def get_services(self, config: Type[RegistryConfig]) -> dict[str, Type[Service]]:
        """Return a dictionary of services. The key being the name of the service"""
        try:
            registry_config = self._services[config.registry.name]
            return registry_config[config.label]
        except KeyError:
            return {}

    def get_service(
        self, config: Type[RegistryConfig], name: str
    ) -> Union[Type[Service], None]:
        """Return a service for a specific config registry"""
        for service_name, service in self.get_services(config).items():
            if service_name == name:
                return service
        return None

    def get_configs(self, service_name: str) -> list[str]:
        """Return a list of config labels that hold a specific service"""
        holders = []
        for conf in self._services.values():
            for conf_label, services in conf.items():
                if service_name in services:
                    holders.append(conf_label)
        return holders

    def search_service(
        self,
        name: str,
        config: Type[RegistryConfig] = None,
        auto_seach_project: bool = False,
        search_globally: bool = True,
    ) -> Type[Service]:
        """
        Search for a service globally or for a specific registry config. The method
        first search in the given config. If it's not found, we continue and check
        the auto_seach_project is True. In that case we check the SOCON_ACTIVE_PROJECT
        and load the project_config. If we find the service in that config we return
        it. If we still didn't find any service, we check in the common space config,
        the plugins config and finally in the socon builtin config.

        :raises:
            ServiceNotFound: The service was not find in any config.
        """
        exc_msg = "'{}' service was not found in '{}' manager".format(name, self.name)

        # Check in the given config
        if config:
            service = self.get_service(config, name)
            if service is not None:
                return service

        # Auto search the project_config
        if auto_seach_project is True:
            try:
                project_config = projects.get_project_config_by_env()
            except LookupError:
                pass
            else:
                service = self.get_service(name, project_config)
                if service is not None:
                    return service

        # We didn't find any service with this name in the given config or
        # the project_config
        if search_globally is False:
            raise ServiceNotFound(exc_msg)

        configs = []
        if settings.configured:
            # Place common and then plugins at first in the config list. This
            # is important as we first want to look in the user common place,
            # the plugins and finally in socon core module.
            user_settings = registry.get_user_common_config()
            if user_settings:
                configs.append(user_settings)
            configs.extend(registry.plugins.get_registry_configs())

        # Always append at the end the socon common config. It's the last
        # place where we want to look at
        configs.append(registry.get_socon_common_config())

        # Iterate over all configs to find the right service
        for config in configs:
            service = self.get_service(config, name)
            if service is not None:
                return service

        # We didn't find any service with this name
        raise ServiceNotFound(exc_msg)

    def get_services_name(self) -> list[str]:
        """Return a list of all registered services name"""
        names = []
        for config in self._services.values():
            for services in config.values():
                names.extend(list(services.keys()))
        return list(set(names))

    def add_service(self, config: Type[RegistryConfig], service: Type[Service]) -> None:
        """
        Add a service to the manager. This function is automatically
        called from the __init_subclass__ of the service subclass
        """

        # Get the name of the service
        name = service._meta.name

        # Get the config registry name. This is to categorize the services
        # and avoid raising an error if two different config have the same
        # name in two different registry
        configs = self._services[config.registry.name]

        # Save in the registry the config label associated with
        # the label of the service and its class. If the label already
        # exist we raise an ImportError
        if any(name in n for n in configs.get(config.label, [])):
            raise ImproperlyConfigured(
                "'{}' already exist. Duplicates:\n{}".format(name, configs)
            )

        # Save the service to a specific config
        configs[config.label].update({name: service})
