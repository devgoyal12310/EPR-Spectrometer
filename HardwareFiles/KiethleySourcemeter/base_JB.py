"""Common instrument resource operations.

Constructing an instrument wraps an existing resource; it never opens a hardware
connection. Driver operations raise contextual errors so an acquisition cannot
continue after a failed instrument action. The standalone safe helpers are for
diagnostics that explicitly permit a missing response.
"""


def safe_query(device, command):
    """Return a stripped response, or None after reporting the failed query."""
    try:
        return device.query(command).strip()
    except Exception as error:
        print(f"Error querying {device!r} with '{command}': {error}")
        return None


def safe_write(device, command):
    """Return whether the resource accepted a write."""
    try:
        device.write(command)
        return True
    except Exception as error:
        print(f"Error writing to {device!r} with '{command}': {error}")
        return False


class InstrumentError(RuntimeError):
    """A failed command with enough instrument context to identify the action."""

    def __init__(self, instrument, operation: str, command: str):
        self.instrument_name = instrument.name
        self.resource_name = str(getattr(instrument._res, "resource_name", instrument.name))
        self.operation = operation
        self.command = command
        super().__init__(
            f"{self.instrument_name} ({self.resource_name}) {operation} failed for {command!r}."
        )


class Instrument:
    selected_scope_model: str
    detected_scope_model: str
    detected_resource: str
    detected_idn: str

    def __init__(self, resource, name=None):
        self._res = resource
        self.name = name or repr(resource)

    def query(self, cmd):
        try:
            return self._res.query(cmd).strip()
        except Exception as error:
            raise InstrumentError(self, "query", cmd) from error

    def query_text(self, cmd) -> str:
        """Read text for parsing, rejecting a failed safe query explicitly."""
        response = self.query(cmd)
        if response is None:
            raise RuntimeError(f"No response from {self.name} for {cmd!r}.")
        return str(response).strip()

    def write(self, cmd):
        try:
            self._res.write(cmd)
            return True
        except Exception as error:
            raise InstrumentError(self, "write", cmd) from error

    def close(self):
        try:
            self._res.close()
        except Exception:
            pass

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self.name}>"
