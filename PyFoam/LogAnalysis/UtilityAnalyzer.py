#  ICE Revision: $Id: /local/openfoam/Python/PyFoam/PyFoam/LogAnalysis/UtilityAnalyzer.py 8415 2013-07-26T11:32:37.193675Z bgschaid  $
"""Analyze OpenFOAM utility"""

from .FoamLogAnalyzer import FoamLogAnalyzer
from .RegExpLineAnalyzer import RegExpLineAnalyzer

class UtilityAnalyzer(FoamLogAnalyzer):
    """
    Analyzer for non-solver Utilities

    Regular expressions can be added and the data generated by them
    can be accessed
    """
    def __init__(self,progress=False):
        """
        @param progress: Print time progress on console?
        """
        FoamLogAnalyzer.__init__(self,progress=progress)

    def addExpression(self,name,expr,idNr=None):
        """Add a RegExp

        @param name: name of the RegExp
        @param expr: the RegExp
        @param idNr: number of the pattern group that identifies data-sets
        """
        self.addAnalyzer(name,RegExpLineAnalyzer(name,expr,idNr))

    def getData(self,name,time=None,ID=None):
        """Get data

        @param name: name of the RegExp
        @param time: time from which the data set it to be read
        @param ID: identification of the data set
        @return: tuple with the data
        """
        a=self.getAnalyzer(name)
        if a==None:
            return None
        else:
            return a.getData(time=time,ID=ID)

    def getIDs(self,name):
        """Get a list with the available IDs"""
        a=self.getAnalyzer(name)
        if a==None:
            return None
        else:
            return a.getIDs()

    def getTimes(self,name,ID=None):
        """Get a list with the available times for a specific ID"""
        a=self.getAnalyzer(name)
        if a==None:
            return None
        else:
            return a.getTimes(ID=ID)

# Should work with Python3 and Python2
