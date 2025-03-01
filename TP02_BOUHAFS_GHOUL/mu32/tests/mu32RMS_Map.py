# -*- coding: utf-8 -*-
from matplotlib import markers
from pyqtgraph.Qt import QtWidgets, QtCore
import numpy as np
import pyqtgraph as pg
from multiprocessing import Process, Manager, Queue
import sched, time, threading
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt
import queue
import threading
sys.path.append('./mu32')
from mu32.core import Mu32, Mu32Exception, mu32log
import multiprocessing as mp
import time
#Sensibilité : -26dBFS pour 104 dB soit 3.17 Pa
FS = 2**23
S = FS*10**(-26/20) / 3.17
Po = 20e-6

mu32log.setLevel( logging.INFO )

event = threading.Event()
signal_q = queue.Queue()

BLOCKSIZE = 2048				# Number of samples per block.
BUFFER_NUMBER = 4				# USB transfer buffer number. should be at least equal to two
SAMPLING_FREQUENCY = 50000		# this is the max frequency
MEMS = range(32)					# the two Mu32 antenna microphones used
MEMS_NUMBER = len( MEMS )
DURATION = 0					# Time re
# This function is responsible for displaying the data
# it is run in its own process to liberate main process
def display(name,q):
    app = pg.mkQApp("Mu32 - Check") 
    mw = QtWidgets.QMainWindow()
    mw.resize(800,400)
    view = pg.GraphicsLayoutWidget()  ## GraphicsView with GraphicsLayout inserted by default
    mw.setCentralWidget(view)
    mw.show()
    mw.setWindowTitle('Mu32 - Check')

    ## create four areas to add plots
    w = view.addPlot()
    
    graph = pg.ScatterPlotItem(
        pxMode=False,  # Set pxMode=False to allow spots to transform with the view
        hoverable=True,
        hoverPen=pg.mkPen('g'),
        hoverSize=1,
    )
    bar = pg.ColorBarItem( values= (0, 90) ) # prepare interactive color bar
    spots = []
    for i in range(4):
        for j in range(8):
            spots.append({'pos': (j,i), 'size': 0.9, 
                          'pen': {'color': 'w', 'width': 2}, 
                          'brush':pg.intColor(i*4+j)})
    graph.addPoints(spots)
    w.addItem(graph)
    w.setAspectLocked(1)
   # w.showAxis(axis='left',show=False)
   # w.showAxis(axis='bottom',show=False)
    w.showGrid(x=True, y=True)
    w.setXRange(-0.5,7.5)
    w.setYRange(-0.5,3.5)
    w.setLabel('bottom','# Micro')
    w.setLabel('left', '# Faisceau')
    
    def update(g,q):
        item = q.get()[1][:]        
        Lvl = 20*np.log10((item+Po)/Po)
        Lvl = [pg.intColor(Lvl[i], 120) for i in range(32)]
        g.setBrush(Lvl)

    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: update(graph,q))
    timer.start(1)

    QtWidgets.QApplication.instance().exec_()

# This is function is responsible for reading some data (IO, serial port, etc)
# and forwarding it to the display
# it is run in a thread
def io(running,q):
    t = 0
    while running.is_set():
        s = mu32.signal_q.get().reshape( mu32.buffer_length, mu32.mems_number).std(axis=0)
        s/=S
        t = np.arange(MEMS_NUMBER)
        q.put([t,s])
        time.sleep(0.0001)
    print("Done")

def callback_end( mu32: Mu32 ):
	"""
	set event for stopping the audio playing loop
	"""
	mu32log.info( ' .stop' )
	event.set()

if __name__ == '__main__':
    q = Queue()
    # Event for stopping the IO thread
    run = threading.Event()
    run.set()

    # Run io function in a thread
    t = threading.Thread(target=io, args=(run,q))
    t.start()


    # Start display process
    p = Process(target=display, args=('Mu32',q))
    p.start()

    try :
        mu32 = Mu32()
        mu32.run( 
                    mems=MEMS,							
                    duration=DURATION,
                    sampling_frequency=SAMPLING_FREQUENCY,
                    buffer_length=BLOCKSIZE,
                    buffers_number=BUFFER_NUMBER,
                    callback_fn=None,
                    post_callback_fn=callback_end
                )
    except Mu32Exception as e:
        print( 'aborting' )
    except ( KeyboardInterrupt, SystemExit ):
        print( 'Program was interrupted' )
    except TypeError as err:
        print( 'TypeError error:', err )
    except:
        print( 'Unexpected error:', sys.exc_info()[0] )



    input("See ? Main process immediately free ! Type any key to quit.")
    run.clear()
    print("Waiting for scheduler thread to join...")
    t.join()
    print("Waiting for graph window process to join...")
    p.join()
    print("Process joined successfully. C YA !")
