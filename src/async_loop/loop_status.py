class SingletonMeta(type):
    """
    The Singleton class can be implemented in different ways in Python. Some
    possible methods include: base class, decorator, metaclass. We will use the
    metaclass because it is best suited for this purpose.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Possible changes to the value of the `__init__` argument do not affect
        the returned instance.
        """
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class LoopStatus(metaclass=SingletonMeta):
    """Singleton that stores if the loop kicking operator is running."""
    operator_running: bool = False

    def __init__(self):
        """Create a new LoopStatus instance."""
        self.operator_running = False

    def update_operator_status(self, status: bool):
        """Update current loop operator status.

        Parameters:
            status: New status of the loop operator.
        """
        self.operator_running = status

    def get_operator_status(self) -> bool:
        """Get current loop operator status.

        Returns:
            bool: Current loop operator status.
        """
        return self.operator_running
