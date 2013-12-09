########################################################################
#                                                                      #
#   KMLWorkCommute.py                                                  #
#   11/02/2013                                                         #
#                                                                      #
#   Turn KML data into something we can plot (and then plot it, duh)   #
#                                                                      #
########################################################################

import os
import pykml
import scipy
#import pylab
import matplotlib.pyplot as pylab
from matplotlib.widgets import Slider

from pykml import parser

#-----------------------#
#   Module Constants    #
#-----------------------#

T, X, Y, H = [ 0, 1, 2, 3 ]
T_MIN_REL, T_MAX_REL = [   0, 2 * 60 * 60 ]
T_MIN, T_MAX = [ h * 60 * 60 for h in [ 6 + 5, 8 + 5 ] ]
X_MIN, X_MAX = [ -87.696, -87.652 ]
Y_MIN, Y_MAX = [  41.937,  41.970 ]
H_MIN, H_MAX = [  -8.925, 187.425 ]

#-----------------------#
#   KML parser          #
#-----------------------#

class KMLParser():
    """
    Parse all KML files in a given directory into an object which can
    be plotted (probably as a time series -- maybe even animated if
    we can figure that out
    """
    def __init__( self, directory, timeBinSeconds = 1 ):
        """
        load all the file names, set the basic variables, etc
        """
        if os.path.isdir( directory ):
            self.kmlFiles = [ f for f in os.listdir( directory ) if f.endswith( '.kml' ) ]
        else:
            return ValueError( "{} is not a directory!".format( directory ) )
        
        self.timeBinSeconds = timeBinSeconds
        
        self.kmlDic = {}
    
    
    #-----------------------#
    #   Parse KML files     #
    #-----------------------#
    
    def parseAllKML( self ):
        """
        Open the given directory and parse all KML files within into some 
        object (probably a dictionary) that we can then plot
        """
        for kmlFile in self.kmlFiles:
            self.parseKML( kmlFile )
        
    
    def parseKML( self, fileName ):
        """
        Parse the given KML file into the local object
        """
        kml = self.loadKML( fileName )
        
        nameNow = kml.Document.name
        if nameNow in self.kmlDic:
            #raise ValueError( "redundant kml names for file {}, what to do brah?".format( fileName ) )
            pass
        else:
            self.kmlDic[ nameNow ] = []
        
        #   Get the tour
        tourList = [ x for x in kml.Document.getchildren() if 'id' in x.attrib and x.attrib[ 'id' ] == 'tour' ]
        if len( tourList ) == 1:
            tour = tourList[ 0 ]
        else:
            raise ValueError( "Too many elements in tourlist {}".format( tourList ) )
        
        #   Get the multitrack
        multiTrackList = [ x for x in tour.getchildren() if x.tag == '{http://www.google.com/kml/ext/2.2}MultiTrack' ]
        if len( multiTrackList ) == 1:
            multiTrack = multiTrackList[ 0 ]
        else:
            raise ValueError( "Too many elements in multiTrackList {}".format( multiTrackList ) )
        
        for child in multiTrack.Track.getchildren():
            #   Pull the time for our dictionary key
            if child.tag == '{http://www.opengis.net/kml/2.2}when':
                hr, mn, sc = [ float( el ) for el in child.text.split( 'T' )[ -1 ][ : -1 ].split( ':' ) ]
                self.timeNow = sc + 60 * ( mn + 60 * hr )
                
            elif child.tag == '{http://www.google.com/kml/ext/2.2}coord':
                coords = [ float( el ) for el in child.text.split( ' ' ) ]
                if len( coords ) == 3:
                    x, y, h = coords
                elif len( coords ) == 2:
                    x, y = coords
                    h = 0
                else:
                    raise ValueError( "coord text {} can't be split up in a reasonable way".format( child.text ) )
                
                #   Deal with redundant names
                if type( self.kmlDic[ nameNow ] ) != list:
                    pass
                else:
                    self.kmlDic[ nameNow ].append( [ self.timeNow, x, y, h ] )
            
            elif child.tag == '{http://www.opengis.net/kml/2.2}ExtendedData':
                pass
            else:
                print child.tag
        
        self.kmlDic[ nameNow ] = scipy.array( self.kmlDic[ nameNow ] )
    
    
    def loadKML( self, fileName ):
        """
        return a pykml object that is saved in the kml file fileName
        """
        with open( fileName, 'rb' ) as f:
            kml_str = f.read()
        return parser.fromstring( kml_str )
    
    
    #-----------------------#
    #   Time series plots   #
    #-----------------------#
    
    def sliderUpdate( self, t ):
        """
        The update function for the slider.  
        """
        for ( kmlName, kmlArray ) in self.kmlDic.iteritems():
            #   Make a mask
            mask = kmlArray[ :, 0 ] <= t
            maskArray = kmlArray[ mask ]
            
            if maskArray.shape == ( 0, 4 ):
                maskArray = scipy.array( [ kmlArray[ 0 ] ] )
            
            print maskArray
            
            #   Line plot update
            self.posPlotDic[ kmlName ].set_xdata( maskArray[  : , X ] )
            self.posPlotDic[ kmlName ].set_ydata( maskArray[  : , Y ] )
            self.altPlotDic[ kmlName ].set_xdata( maskArray[  : , T ] - maskArray[ 0, T ] )
            self.altPlotDic[ kmlName ].set_ydata( maskArray[  : , H ] )
            
            #   Head plot update
            self.posPlotDicHead[ kmlName ].set_xdata( maskArray[ -1 , X ] )
            self.posPlotDicHead[ kmlName ].set_ydata( maskArray[ -1 , Y ] )
            self.altPlotDicHead[ kmlName ].set_xdata( maskArray[ -1 , T ] - maskArray[ 0, T ] )
            self.altPlotDicHead[ kmlName ].set_ydata( maskArray[ -1 , H ] )
        
        self.timePosPlot.set_xlim( ( X_MIN, X_MAX ) )
        self.timePosPlot.set_ylim( ( Y_MIN, Y_MAX ) )
        self.timeAltPlot.set_xlim( ( T_MIN_REL, T_MAX_REL ) )
        self.timeAltPlot.set_ylim( ( H_MIN, H_MAX ) )
        self.timeFig.canvas.draw_idle()
        self.timeFig.show()
    
    
    def initializePlotting( self ):
        """
        Create the matplotlib objects which will be used for the time
        series plotting
        """
        #   Create plot objects
        self.timeFig     = pylab.figure( 0, figsize = [ 8.0, 12.0 ] )
        self.timePosPlot = self.timeFig.add_subplot( 211 )
        self.timeAltPlot = self.timeFig.add_subplot( 212 )
        
        #   Arrange axes fields
        self.timeFig.subplots_adjust( bottom = 0.09, top = 0.96, hspace = 0.11 )
        
        #   Create Sliders
        label   = 'Time'
        valMin  = T_MIN
        valMax  = T_MAX
        valInit = T_MIN
        self.timeSliderAx = pylab.axes( [ 0.12, 0.01, 0.78, 0.03 ] )
        self.timeSlider   = Slider( self.timeSliderAx, label = label, valmin = valMin, valmax = valMax, valinit = valInit )
        
        #   Start Plots
        self.posPlotDic     = {}
        self.posPlotDicHead = {}
        self.altPlotDic     = {}
        self.altPlotDicHead = {}
        for ( kmlName, kmlArray ) in self.kmlDic.iteritems():
            t0, x0, y0, h0 = kmlArray[ 0 ]
            self.posPlotDicHead[ kmlName ] = self.timePosPlot.plot( x0, y0, marker = 'o', mew = 2, mfc = None, label = 'Pos, {}'.format( kmlName ) )[ 0 ]
            self.altPlotDicHead[ kmlName ] = self.timeAltPlot.plot( t0, h0, marker = 'o', mew = 2, mfc = None, label = 'Alt, {}'.format( kmlName )  )[ 0 ]
            self.posPlotDic[ kmlName ] = self.timePosPlot.plot( [], [], marker = '.', label = 'Pos Head, {}'.format( kmlName ) )[ 0 ]
            self.altPlotDic[ kmlName ] = self.timeAltPlot.plot( [], [], marker = '.', label = 'Alt Head, {}'.format( kmlName ) )[ 0 ]
            
        #   Slider update function
        sliderFunc = lambda t : self.sliderUpdate( t )
        self.timeSlider.on_changed( sliderFunc )
        
        self.timePosPlot.set_xlim( ( X_MIN, X_MAX ) )
        self.timePosPlot.set_ylim( ( Y_MIN, Y_MAX ) )
        self.timePosPlot.set_xlabel( 'Longitude' )
        self.timePosPlot.set_ylabel( 'Latitude'  )
        
        self.timeAltPlot.set_xlim( ( T_MIN_REL, T_MAX_REL ) )
        self.timeAltPlot.set_ylim( ( H_MIN, H_MAX ) )
        self.timeAltPlot.set_xlabel( 'Relative Time (s)' )
        self.timeAltPlot.set_ylabel( 'Elevation (ft?)'   )
        
    
    def plotTimeSeries( self ):
        """
        Create a pylab plot with a timebar.  As the timebar slides,
        update the location of the 
        """
        
        #   Plotting shit initialization
        self.initializePlotting()
        
