class Handoff:
    """Simple Interface based API for handing off control of the mavlink connection to other classes"""

    def __init__(self):
        self._owner = None
        self._master = None

    def execute_handoff(self, owner, master):
        """Execute handoff. Implemented at class level"""
        self._owner = owner
        self._master = master

        self._exit_handoff()


    def _exit_handoff(self):
        """Exit the handoff, perform any cleanup, etc"""
        self._owner = None
        self._master = None
