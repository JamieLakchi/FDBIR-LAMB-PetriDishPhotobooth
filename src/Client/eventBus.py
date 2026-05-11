from typing import Callable, Any
from enum import Enum

#===========---List of used event types and corresponding signature---==========

LOG = "<Log>" # (type: str, msg: str, name: str)

CHANGED_CWD = "<Changed-CWD>" # (path: Path)

FINISHED_ANALYSIS = "<Finished-Analysis>" # (path: Path)

SAVE_ANALYZED = "<Save-Analyzed>" # (path: Path)

SAVE_FINISHED = "<Save-Finished>" # (path: Path)

#===============================================================================

"""
Allows entities to register themselves to listen to events
"""
class EventBus:
    def __init__(self) -> None:
        self.registry: dict[str, dict[int, Callable[..., None]]] = {}
        self.current_id = 0

    def getId(self) -> int:
        """
        Get an unused ID to register with
        """
        current_id = self.current_id
        self.current_id += 1
        return current_id

    def register(self, event: str, id: int, callback: Callable[..., Any]) -> None:
        """
        Registers a callback for an event under given ID, only one callback per ID allowed
        """
        if event in self.registry.keys():
            self.registry[event][id] = callback
        else:
            self.registry[event] = {id: callback}

    def unregister(self, event: str, id: int) -> None:
        """
        Unregisters the callback for an event related to the given ID
        """
        if event in self.registry.keys():
            if id in self.registry[event].keys():
                self.registry[event].pop(id)

    def emit(self, event: str, **kwargs) -> None:
        """
        Emit an event (call all registered callbacks for given event, passing given keyword arguments)
        """
        if event in self.registry.keys():
            for _, command in self.registry[event].items():
                try:
                    command(**kwargs)
                except:
                    pass