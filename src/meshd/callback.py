from typing import Any, Dict, List

class Callback(object):
    """ Callback management
    """
    def __init__(self, ):
        # Callback registry: key -> list of callback functions  
        self._callbacks: Dict[Any, List[callable]] = {}  

        # Global callbacks: called for any change
        self._global_callbacks: List[callable] = []

    def register_callback(self, key: Any, callback: callable) -> None:  
        """Register a callback for a specific key."""  
        if key not in self._callbacks:  
            self._callbacks[key] = []  
        self._callbacks[key].append(callback)  
    
    def unregister_callback(self, key: Any, callback: callable) -> None:  
        """Unregister a callback for a specific key."""  
        if key in self._callbacks and callback in self._callbacks[key]:  
            self._callbacks[key].remove(callback)  
    
    def register_global_callback(self, callback: callable) -> None:  
        """Register a global callback called for any change."""  
        self._global_callbacks.append(callback)  
    
    def unregister_global_callback(self, callback: callable) -> None:  
        """Unregister a global callback."""  
        if callback in self._global_callbacks:  
            self._global_callbacks.remove(callback)
    
    def _trigger_callbacks(self, key: Any, value: Any, operation: str, src_node: Any = None, raise_on_exception = True) -> None:  
        """Trigger registered callbacks for a key change."""  
        # Trigger key-specific callbacks
        if key in self._callbacks:
            for callback in self._callbacks[key]:
                try:
                    callback(self, key, value, operation, src_node)
                except Exception as ex:
                    if raise_on_exception:
                        raise ex
        
        # Trigger global callbacks
        for callback in self._global_callbacks:
            try:
                callback(self, key, value, operation, src_node)
            except Exception as ex:
                if raise_on_exception:
                    raise ex
                