"""Receive the overlay's real geometry from a KWin script over D-Bus.

On Wayland a client does not know its global window position; Qt's
``QWidget.x()/y()`` stay at 0.  KWin does know it, so the keep-above script
also reports the overlay geometry here whenever it changes.  This lets the app
store the position the user actually dragged the overlay to and restore it on
the next start.
"""
from __future__ import annotations

import os
from collections.abc import Callable

from src.platform_utils import (
    OVERLAY_DBUS_INTERFACE,
    OVERLAY_DBUS_PATH,
    app_dbus_name,
)

try:  # QtDBus is not shipped on every platform
    from PySide6.QtCore import QObject
    from PySide6.QtDBus import QDBusConnection, QDBusVirtualObject

    _HAVE_QTDBUS = True
except Exception:  # pragma: no cover - non-Linux / stripped Qt builds
    _HAVE_QTDBUS = False

    class QDBusVirtualObject(QObject):  # type: ignore[no-redef]
        pass


_GEOMETRY_XML = f"""<node>
  <interface name="{OVERLAY_DBUS_INTERFACE}">
    <method name="Geometry">
      <arg name="token" type="s" direction="in"/>
      <arg name="x" type="i" direction="in"/>
      <arg name="y" type="i" direction="in"/>
      <arg name="width" type="i" direction="in"/>
      <arg name="height" type="i" direction="in"/>
    </method>
  </interface>
</node>"""


class GeometryReceiver(QDBusVirtualObject):
    """Small D-Bus object that a KWin script can call with window geometry."""

    def __init__(
        self,
        callback: Callable[[str, int, int, int, int], None],
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._callback = callback
        self.service = ""
        self.available = False
        self._bus = None
        if not _HAVE_QTDBUS:
            return

        self._bus = QDBusConnection.sessionBus()
        if not self._bus.isConnected():
            return
        if not self._bus.registerVirtualObject(
            OVERLAY_DBUS_PATH, self, QDBusConnection.SingleNode
        ):
            return

        base = app_dbus_name()
        for name in (base, f"{base}.p{os.getpid()}"):
            if self._bus.registerService(name):
                self.service = name
                self.available = True
                break
        if not self.available:
            self._bus.unregisterObject(OVERLAY_DBUS_PATH)

    def close(self) -> None:
        if self._bus is None or not self.available:
            return
        try:
            self._bus.unregisterService(self.service)
            self._bus.unregisterObject(OVERLAY_DBUS_PATH)
        except Exception:
            pass
        self.available = False

    def introspect(self, path: str) -> str:  # noqa: ARG002
        return _GEOMETRY_XML

    def handleMessage(self, message, path: str) -> bool:  # noqa: ARG002
        member = message.member()
        if member == "Introspect":
            self._bus.send(message.createReply(_GEOMETRY_XML))
            return True
        if member != "Geometry":
            return False

        try:
            token, x, y, width, height = message.arguments()
            self._callback(
                str(token), int(x), int(y), int(width), int(height)
            )
        except Exception:
            pass
        self._bus.send(message.createReply())
        return True
