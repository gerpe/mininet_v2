"""
NS-3 integration for Mininet.

"""

import threading, time

from mininet.log import info, error, warn, debug
from mininet.link import Intf, Link
from mininet.node import Switch, Node
from mininet.util import quietRun, moveIntf, errRun

import ns.core
import ns.network
import ns.tap_bridge

default_duration = 3600

ns.core.GlobalValue.Bind( "SimulatorImplementationType", ns.core.StringValue( "ns3::RealtimeSimulatorImpl" ) )
ns.core.GlobalValue.Bind( "ChecksumEnabled", ns.core.BooleanValue ( "true" ) )

allIntfs = []

def start():
    global thread
    if 'thread' in globals() and thread.isAlive():
        warn( "NS-3 simulator thread already running." )
        return
    for intf in allIntfs:
        if not intf.nsInstalled:
            intf.nsInstall()
    thread = threading.Thread( target = runthread )
    thread.daemon = True
    thread.start()
    for intf in allIntfs:
        if not intf.inRightNamespace:
            intf.namespaceMove()
    return

def runthread():
    ns.core.Simulator.Stop( ns.core.Seconds( default_duration ) )
    ns.core.Simulator.Run()

def stop():
    ns.core.Simulator.Stop( ns.core.MilliSeconds( 1 ) )
    while thread.isAlive():
        time.sleep( 0.01 )
    return

def clear():
    if thread.isAlive():
        stop()
    ns.core.Simulator.Destroy()
    return


class TBIntf( Intf ):
    def  __init__( self, name, node, port=None, 
                   nsNode=None, nsDevice=None, mode=None, **params ):
        """
        """
        self.name = name
        self.createTap()
        self.delayedMove = True
        if node.inNamespace:
            self.inRightNamespace = False
        else:
            self.inRightNamespace = True
        Intf.__init__( self, name, node, port , **params)
        allIntfs.append( self )
        self.nsNode = nsNode
        self.nsDevice = nsDevice
        self.mode = mode
        self.params = params
        self.nsInstalled = False
        self.tapbridge = ns.tap_bridge.TapBridge()
        if self.nsNode and self.nsDevice and ( self.mode or self.node ):
            self.nsInstall()
        if self.node and self.nsInstalled and self.isInstant(): # instant mode to be implemented in ns-3
            self.namespaceMove()

    def createTap( self ):
        quietRun( 'ip tuntap add ' + self.name + ' mode tap' )

    def nsInstall( self ):
        if not isinstance( self.nsNode, ns.network.Node ):
            warn( "Cannot install TBIntf to ns-3 Node: "
                  "nsNode not specified\n" )
            return
        if not isinstance( self.nsDevice, ns.network.NetDevice ):
            warn( "Cannot install TBIntf to ns-3 Node: "
                  "nsDevice not specified\n" )
            return
        if self.mode is None and self.node is not None:
            if isinstance( self.node, Switch ):
                self.mode = "UseBridge"
            else:
                self.mode = "UseLocal"
        if self.mode is None:
            warn( "Cannot install TBIntf to ns-3 Node: "
                  "cannot determine mode: neither mode nor (mininet) node specified\n" )
            return
        self.tapbridge.SetAttribute ( "Mode", ns.core.StringValue( self.mode ) )
        self.tapbridge.SetAttribute ( "DeviceName", ns.core.StringValue( self.name ) )
        self.tapbridge.SetAttributeFailSafe ( "Instant", ns.core.BooleanValue( True ) ) # to be implemented in ns-3
        self.nsNode.AddDevice( self.tapbridge )
        self.tapbridge.SetBridgedNetDevice( self.nsDevice )
        self.nsInstalled = True

    def namespaceMove( self ):
        loops = 0
        while not self.isConnected():
            time.sleep(0.01)
            loops += 1
            if loops > 10:
                warn( "Cannot move TBIntf to mininet Node namespace: "
                      "ns-3 has not connected yet to the TAP interface\n" )
                return
        moveIntf( self.name, self.node )
        self.inRightNamespace = True
        # IP address has been reset while moving to namespace, needs to be set again
        if self.ip is not None:
            self.setIP( self.ip, self.prefixLen )
        # The same for 'up'
        self.isUp( True )

    def isConnected( self ):
        return self.tapbridge.IsLinkUp()

    def isInstant( self ):
        return False # to be implemented in ns-3

    def cmd( self, *args, **kwargs ):
        "Run a command in our owning node or in root namespace when not yet inRightNamespace"
        if self.inRightNamespace:
            return self.node.cmd( *args, **kwargs )
        else:
            cmd = ' '.join( [ str( c ) for c in args ] )
            return errRun( cmd )[ 0 ]

    def rename( self, newname ):
        "Rename interface"
        if self.nsInstalled and not self.isConnected():
            self.tapbridge.SetAttribute ( "DeviceName", ns.core.StringValue( newname ) )
        Intf.rename( self, newname )
