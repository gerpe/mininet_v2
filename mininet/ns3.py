"""
NS-3 integration for Mininet.

"""

import threading, time

from mininet.log import info, error, warn, debug
from mininet.link import Intf
from mininet.node import Switch

import ns.core
import ns.network
import ns.tap_bridge

default_duration = 3600

ns.core.GlobalValue.Bind( "SimulatorImplementationType", ns.core.StringValue( "ns3::RealtimeSimulatorImpl" ) )
ns.core.GlobalValue.Bind( "ChecksumEnabled", ns.core.BooleanValue ( "true" ) )

allintfs = []

def start():
    global thread
    if 'thread' in globals() and thread.isAlive():
        warn( "NS-3 simulator thread already running." )
        return
    thread = threading.Thread( target = runthread )
    thread.daemon = True
    thread.start()
    for intf in allintfs:
        if not intf.ns_done:
            intf.nsInstall()
        if not intf.mn_done:
            intf.mnInstall()
    return

def runthread():
    ns.core.Simulator.Stop( ns.core.Seconds( default_duration ) )
    ns.core.Simulator.Run()

def stop():
    ns.core.Simulator.Stop( ns.core.MilliSeconds( 1 ) )
    while thread.isAlive():
        time.sleep(0.01)
    return

def clear():
    if thread.isAlive():
        stop()
    ns.core.Simulator.Destroy()
    return


class TBIntf( Intf ):
    def  __init__( self, name, ns_node=None, ns_device=None, mn_node=None, mode=None, **kwargs ):
        """
        """
        allintfs.append( self )
        self.name = name
        self.ns_node = ns_node
        self.ns_device = ns_device
        self.mn_node = mn_node
        self.mode = mode
        self.kwargs = kwargs
        self.tapbridge = ns.tap_bridge.TapBridge()
        self.ns_done = False
        self.mn_done = False
        if name and ns_node and ns_device and ( mn_node or mode ):
            self.nsInstall()
        if self.ns_done and self.isInstant() and mn_node:
            self.mnInstall()

    def nsInstall( self ):
        # TODO: Input checking
        if self.mode == None:
            if isinstance( self.mn_node, Switch ):
                self.mode = "UseBridge"
            else:
                self.mode = "UseLocal"
        self.tapbridge.SetAttribute ( "Mode", ns.core.StringValue( self.mode ) )
        self.tapbridge.SetAttribute ( "DeviceName", ns.core.StringValue( self.name ) )
        self.ns_node.AddDevice( self.tapbridge )
        self.tapbridge.SetBridgedNetDevice( self.ns_device )
        self.ns_done = True

    def mnInstall( self ):
        # TODO: Input checking
        if self.mn_node.inNamespace:
            loops = 0
            while not self.isConnected():
                time.sleep(0.01)
                loops += 1
                if loops > 10:
                    warn( "Timeout: cannot install TBIntf to Node; "
                          "ns-3 has not connected yet to the TAP interface" )
                    return
        Intf.__init__( self, self.name, self.mn_node, port=None )
        self.mn_done = True

    def isConnected( self ):
        return self.tapbridge.IsLinkUp()

    def isInstant( self ):
        return False

