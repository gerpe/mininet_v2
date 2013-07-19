"""
NS-3 integration for Mininet.

"""

import threading

import ns.core
import ns.network

default_duration = 3600

ns.core.GlobalValue.Bind("SimulatorImplementationType", ns.core.StringValue("ns3::RealtimeSimulatorImpl"))
ns.core.GlobalValue.Bind("ChecksumEnabled", ns.core.BooleanValue ("true"))

def start():
    global thread
    if ('thread' in globals()):
        if (thread.isAlive() == True):
            raise Exception( "NS-3 simulator thread already running." )
            return
    thread = threading.Thread(target = runthread)
    thread.daemon = True
    thread.start()
    return

def runthread ():
    ns.core.Simulator.Stop(ns.core.Seconds(default_duration))
    ns.core.Simulator.Run()

def stop():
    ns.core.Simulator.Stop()
    while (thread.isAlive() == True):
        pass
    return

def clear():
    if (thread.isAlive()):
        stop()
    ns.core.Simulator.Destroy()
    return
