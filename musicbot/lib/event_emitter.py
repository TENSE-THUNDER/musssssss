import asyncio
import collections
import traceback
from typing import TYPE_CHECKING, Any, Callable, DefaultDict, List, Set

if TYPE_CHECKING:
    AsyncTask = asyncio.Task[Any]
else:
    AsyncTask = asyncio.Task

EventCallback = Callable[..., Any]
EventList = List[EventCallback]
EventDict = DefaultDict[str, EventList]


class EventEmitter:
    def __init__(self) -> None:
        """
        Manage a collection of events and an event loop to run callbacks
        that are also co-routines.
        """
        self._events: EventDict = collections.defaultdict(list)
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
        self._task_pool: Set[AsyncTask] = set()

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """
        Trigger all callbacks registered with `event` to be fired using
        the arguments passed to this function.
        """
        if event not in self._events:
            return

        for cb in list(self._events[event]):
            try:
                if asyncio.iscoroutinefunction(cb):
                    # Create the task and save a reference to ensure it is not
                    # garbage collected early.
                    t = self.loop.create_task(
                        cb(*args, **kwargs),
                        name=f"MB_EE_{type(self).__name__}_{cb.__name__}",
                    )
                    self._task_pool.add(t)
                    t.add_done_callback(self._task_pool.discard)
                else:
                    cb(*args, **kwargs)

            except Exception:  # pylint: disable=broad-exception-caught
                traceback.print_exc()

    def on(self, event: str, callback: EventCallback) -> Any:
        """
        Schedule a `callback` to run each time `event` is emitted.
        """
        self._events[event].append(callback)
        return self

    def off(self, event: str, callback: EventCallback) -> Any:
        """
        Remove a scheduled `callback` from the `event` register.
        """
        self._events[event].remove(callback)

        if not self._events[event]:
            del self._events[event]

        return self

    def once(self, event: str, callback: EventCallback) -> Any:
        """
        Schedule a `callback` function to fire only once, the first time
        an `even` gets fired.
        """

        def callback_off(*args: Any, **kwargs: Any) -> Any:
            self.off(event, callback_off)
            return callback(*args, **kwargs)

        return self.on(event, callback_off)
