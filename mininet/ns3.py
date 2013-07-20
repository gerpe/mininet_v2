"""
NS-3 integration for Mininet.

"""

import threading, time

from mininet.log import info, error, warn, debug
from mininet.link import Intf, Link
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
    for intf in allintfs:
        if not intf.ns_done:
            intf.nsInstall()
    thread = threading.Thread( target = runthread )
    thread.daemon = True
    thread.start()
    for intf in allintfs:
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
    def  __init__( self, name=None, node=None, port=None, 
                   ns_node=None, ns_device=None, mode=None, **kwargs ):
        """
        """
        allintfs.append( self )
        self.name = name
        self.node = node
        self.port = port
        self.ns_node = ns_node
        self.ns_device = ns_device
        self.mode = mode
        self.kwargs = kwargs
        self.ns_done = False
        self.mn_done = False
        self.tapbridge = ns.tap_bridge.TapBridge()
        if ( self.ns_node and self.ns_device and 
           ( self.mode or self.node ) and
           ( self.name or self.node ) ):
            self.nsInstall()
        if self.node and self.ns_done and self.isInstant():
            self.mnInstall()

    def nsInstall( self ):
        if self.ns_node is None:
            warn( "Cannot install TBIntf to ns-3 Node; "
                  "ns_node not specified" )
            return
        if self.ns_device is None:
            warn( "Cannot install TBIntf to ns-3 Node; "
                  "ns_device not specified" )
            return
        if self.name is None and self.node is not None:
            if self.port is None:
                self.port = self.node.newPort()
                info( "Port not specified, getting new port from (mininet) node" )
            self.name = Link.intfName( self.node, self.port )
        if self.name is None:
            warn( "Cannot install TBIntf to ns-3 Node; "
                  "Neither name nor (mininet) node/port specified" )
            return
        if self.mode is None and self.node is not None:
            if isinstance( self.node, Switch ):
                self.mode = "UseBridge"
            else:
                self.mode = "UseLocal"
        if self.mode is None:
            warn( "Cannot install TBIntf to ns-3 Node; "
                  "Cannot determine mode: neither mode nor (mininet) node specified" )
            return
        self.tapbridge.SetAttribute ( "Mode", ns.core.StringValue( self.mode ) )
        self.tapbridge.SetAttribute ( "DeviceName", ns.core.StringValue( self.name ) )
        self.tapbridge.SetAttributeFailSafe ( "Instant", ns.core.BooleanValue( True ) ) # to be implemented in ns-3
        self.ns_node.AddDevice( self.tapbridge )
        self.tapbridge.SetBridgedNetDevice( self.ns_device )
        self.ns_done = True

    def mnInstall( self ):
        if self.node is None:
            warn( "Cannot install TBIntf to mininet Node; "
                  "(mininet) node not specified" )
            return
        if self.node.inNamespace:
            loops = 0
            while not self.isConnected():
                time.sleep(0.01)
                loops += 1
                if loops > 10:
                    warn( "Cannot install TBIntf to mininet Node; "
                          "ns-3 has not connected yet to the TAP interface" )
                    return
        Intf.__init__( self, self.name, self.node, port=None )
        self.mn_done = True

    def isConnected( self ):
        return self.tapbridge.IsLinkUp()

    def isInstant( self ):
        return False # to be implemented in ns-3

