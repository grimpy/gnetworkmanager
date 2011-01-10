#!/usr/bin/env python
import dbus
import functools
import logging
from dbus.mainloop.glib import DBusGMainLoop
DBusGMainLoop(set_as_default=True)

class DbusInt(object):
    __bus = dbus.SystemBus()
    __instances = dict()

    @classmethod
    def load(cls, path=None, *args, **kwargs):
        key = cls.__name__, path
        if key not in cls.__instances:
            if path:
                inst = cls(path, *args, **kwargs)
            else:
                inst = cls(*args, **kwargs)
            cls.__instances[key] = inst
        return cls.__instances[key]

    def __init__(self, path, objectpath=None):
        name = self.__class__.__name__
        if not objectpath:
            objectpath = "org.freedesktop.NetworkManager.%s" % name
        self.__callback_registered = False
        self.__callbacks = list()
        self.dbus = dbus.Interface(self.__bus.get_object("org.freedesktop.NetworkManager", path),
                        objectpath)

    def __callback_handler(self, propertyname, propertyvalue):
        logging.info("%s property update of %s with value %s", self.__class__.__name__, propertyname, propertyvalue)
        for callback in self.__callbacks:
            callback(self, propertyname, propertyvalue)

    def register_propertychange_callback(self, callback):
        if not self.__callback_registered:
            self.dbus.connect_to_signal("PropertyChanged", self.__callback_handler)
        self.__callback_registered = True
        self.__callbacks.append(callback)

    def unregister_propertychange_callback(self, callback):
        if callback in self.__callbacks:
            self.__callbacks.remove(callback)

    def __reload(self):
        path = self.dbus.object_path
        interface = self.dbus.dbus_interface
        del self.dbus
        self.dbus = dbus.Interface(self.__bus.get_object("org.freedesktop.NetworkManager", path), interface)

    def __getitem__(self, key):
        pmi = dbus.Interface(self.dbus, "org.freedesktop.DBus.Properties")
        return pmi.Get('', key,byte_arrays=True)

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.dbus.object_path == other.dbus.object_path and \
                self.dbus.dbus_interface == other.dbus.dbus_interface
        return False

    def __str__(self):
        return "<%s object at %s>" % (self.__class__.__name__, hex(id(self)))

    def __repr__(self):
        return "<%s %s object at %s>" % (self.__class__.__name__, self, hex(id(self)))

class AccessPoint(DbusInt):
    pass

class Wireless(DbusInt):
    def __init__(self, path):
        super(self.__class__, self).__init__(path, "org.freedesktop.NetworkManager.Device.Wireless")

    accesspoints = property(fget=lambda s: [ AccessPoint.load(ap) for ap in s.dbus.GetAccessPoints()])



NM_DEVICE_TYPE_UNKNOWN = 0
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2
NM_DEVICE_TYPE_GSM = 3
NM_DEVICE_TYPE_CDMA = 4
class Device(DbusInt):
    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        if self['DeviceType'] == NM_DEVICE_TYPE_WIFI:
            self.wifi = Wireless(self.dbus.object_path)


class Manager(DbusInt):

    def __init__(self):
        super(Manager, self).__init__("/org/freedesktop/NetworkManager", "org.freedesktop.NetworkManager")

    devices = property(fget=lambda s: [ Device.load(dev) for dev in s.dbus.GetDevices()])

if __name__ == '__main__':
    con = Manager.load()
