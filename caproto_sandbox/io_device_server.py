#!/usr/bin/env python3
import termios
import fcntl
import sys
import os
import threading
import atexit
from time import time,sleep
from datetime import datetime

from caproto.server import pvproperty, PVGroup, ioc_arg_parser, run
from numpy import zeros, random
image_shape = (3960,3960)

class Device(object):

    def init(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def run_once(self):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def start_io_interrupt_monitor(self,new_value_callback):
        '''
        This function monitors the terminal it was run in for keystrokes.
        On each keystroke, it calls new_value_callback with the given keystroke.

        This is used to simulate the concept of an I/O Interrupt-style signal from
        the EPICS world. Those signals depend on hardware to tell EPICS when new
        values are available to be read by way of interrupts - whereas we use
        callbacks here.
        '''
        while True:
            date_time = datetime.fromtimestamp(time())
            t = time()#date_time.strftime("%m/%d/%Y, %H:%M:%S.%f")
            new_value_callback({'t1':t})
            sleep(self.dt1)


class IOInterruptIOC(PVGroup):
    t1 = pvproperty(value=2.0)
    dt1 = pvproperty(value=0.9, dtype = float, precision = 3)
    t2 = pvproperty(value=2.0)
    dt2 = pvproperty(value=0.9, dtype = float, precision = 3)
    arr = zeros(image_shape)
    f_arr = arr.flatten()
    image = pvproperty(value = f_arr, dtype = float)

    # NOTE the decorator used here:
    #@dt1.startup
    #async def dt1(self, instance, async_lib):

    #@dt2.startup
    #async def dt2(self, instance, async_lib):

    @t1.startup
    async def t1(self, instance, async_lib):
        # This method will be called when the server starts up.
        print('* t1 method called at server startup')
        queue = async_lib.ThreadsafeQueue()

        # Start a separate thread that monitors keyboard input, telling it to
        # put new values into our async-friendly queue
        thread = threading.Thread(target=device.start_io_interrupt_monitor,
                                  daemon=True,
                                  kwargs=dict(new_value_callback=queue.put))
        device.dt1 = 1.1
        thread.start()

        # Loop and grab items from the queue one at a time
        while True:
            value = await queue.async_get()
            if 't1' in list(value.keys()):
                await self.t1.write(value['t1'])

    @t2.startup
    async def t2(self, instance, async_lib):
        # This method will be called when the server starts up.
        print('* t2 method called at server startup')
        queue = async_lib.ThreadsafeQueue()

        # Start a separate thread that monitors keyboard input, telling it to
        # put new values into our async-friendly queue
        thread = threading.Thread(target=device.start_io_interrupt_monitor2,
                                  daemon=True,
                                  kwargs=dict(new_value_callback2=queue.put))
        device.dt2 = 1.2
        thread.start()

        # Loop and grab items from the queue one at a time
        while True:
            value = await queue.async_get()
            if 't2' in list(value.keys()):
                await self.t2.write(value['t2'])
            if 'image' in list(value.keys()):
                await self.image.write(value['image'])

device = Device()

if __name__ == '__main__':
    ioc_options, run_options = ioc_arg_parser(
        default_prefix='io_device:',
        desc='Run an IOC that updates via I/O interrupt on key-press events.')

    ioc = IOInterruptIOC(**ioc_options)
    print(ioc.image)
    run(ioc.pvdb, **run_options)