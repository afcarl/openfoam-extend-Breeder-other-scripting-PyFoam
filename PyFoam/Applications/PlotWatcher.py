#  ICE Revision: $Id: /local/openfoam/Python/PyFoam/PyFoam/Applications/PlotWatcher.py 2814 2008-02-24T19:49:36.025041Z bgschaid  $ 
"""
Class that implements pyFoamPlotWatcher
"""

from PyFoam.Execution.GnuplotRunner import GnuplotWatcher

from PyFoamApplication import PyFoamApplication

from CommonPlotLines import CommonPlotLines
from CommonPlotOptions import CommonPlotOptions

from os import path

class PlotWatcher(PyFoamApplication,
                  CommonPlotOptions,
                  CommonPlotLines):
    def __init__(self,args=None):
        description="""
        Gets the name of a logfile which is assumed to be the output of a
        OpenFOAM-solver. Parses the logfile for information about the
        convergence of the solver and generates gnuplot-graphs. Watches the
        file until interrupted.
        """

        CommonPlotOptions.__init__(self,persist=False)
        CommonPlotLines.__init__(self)
        PyFoamApplication.__init__(self,args=args,description=description,usage="%prog [options] <logfile>",interspersed=True,nr=1)

    def addOptions(self):
        CommonPlotOptions.addOptions(self)
        
        self.parser.add_option("--tail",
                               type="long",
                               dest="tail",
                               default=5000L,
                               help="The length at the end of the file that should be output (in bytes)")
        self.parser.add_option("--silent",
                               action="store_true",
                               dest="silent",
                               default=False,
                               help="Logfile is not copied to the terminal")
        self.parser.add_option("--progress",
                               action="store_true",
                               default=False,
                               dest="progress",
                               help="Only prints the progress of the simulation, but swallows all the other output")
        self.parser.add_option("--start",
                               action="store",
                               type="float",
                               default=None,
                               dest="start",
                               help="Start time starting from which the data should be plotted. If undefined the initial time is used")

        self.parser.add_option("--end",
                               action="store",
                               type="float",
                               default=None,
                               dest="end",
                               help="End time until which the data should be plotted. If undefined it is plotted till the end")

        CommonPlotLines.addOptions(self)
                
    def run(self):
        self.processPlotOptions()
        self.processPlotLineOptions(autoPath=path.dirname(self.parser.getArgs()[0]))

        run=GnuplotWatcher(self.parser.getArgs()[0],
                           smallestFreq=self.opts.frequency,
                           persist=self.opts.persist,
                           tailLength=self.opts.tail,
                           silent=self.opts.silent,
                           plotLinear=self.opts.linear,
                           plotCont=self.opts.cont,
                           plotBound=self.opts.bound,
                           plotIterations=self.opts.iterations,
                           plotCourant=self.opts.courant,
                           plotExecution=self.opts.execution,
                           plotDeltaT=self.opts.deltaT,
                           customRegexp=self.plotLines(),
                           writeFiles=self.opts.writeFiles,
                           raiseit=self.opts.raiseit,
                           progress=self.opts.progress,
                           start=self.opts.start,
                           end=self.opts.end)

        run.start()