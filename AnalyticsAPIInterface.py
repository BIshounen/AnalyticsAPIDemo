import abc
from collections.abc import Hashable


class AnalyticsAPIInterface(metaclass=abc.ABCMeta):

  @classmethod
  def __subclasshook__(cls, subclass):
    return (hasattr(subclass, 'set_parameters') and
            callable(subclass.set_parameters) and
            hasattr(subclass, 'get_device_agent_manifest') and
            callable(subclass.get_device_agent_manifest) or
            NotImplemented)

  @abc.abstractmethod
  def set_parameters(self, parameters: dict):
    raise NotImplemented

  @abc.abstractmethod
  def get_device_agent_manifest(self, device_agent_id: Hashable) -> dict:
    raise NotImplemented
