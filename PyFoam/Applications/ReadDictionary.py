#  ICE Revision: $Id: /local/openfoam/Python/PyFoam/PyFoam/Applications/ReadDictionary.py 2717 2008-01-27T18:25:09.300764Z bgschaid  $ 
"""
Application class that implements pyFoamReadDictionary
"""

import sys,re

from PyFoamApplication import PyFoamApplication

from PyFoam.RunDictionary.ParsedParameterFile import ParsedParameterFile

class ReadDictionary(PyFoamApplication):
    def __init__(self,args=None):
        description="""
Reads a value from a Foam-Dictionary and prints it to the screen.
The description of the value is word. If the value is
non-atomic (a list or a dictionary) it is output in Python-notation.
Parts of the expression can be accessed by using the Python-notation for accessing
sub-expressions.

Example of usage:
      pyFoamReadDictionary.py pitzDaily/0/U "boundaryField['inlet']['type']" 
        """
        
        PyFoamApplication.__init__(self,args=args,description=description,usage="%prog [options] <dictfile> <key>",nr=2,interspersed=True)
        
    def addOptions(self):
        self.parser.add_option("--debug",action="store_true",default=None,dest="debug",help="Debugs the parser")
        
    
    def run(self):
        fName=self.parser.getArgs()[0]
        all=self.parser.getArgs()[1]

        match=re.compile("([a-zA-Z_][a-zA-Z0-9_]*)(.*)").match(all)
        if match==None:
            self.error("Expression",all,"not usable as an expression")
            
        key=match.group(1)
        sub=None
        if len(match.groups())>1:
            if match.group(2)!="":
                sub=match.group(2)
        
        try:
            dictFile=ParsedParameterFile(fName,backup=False,debug=self.opts.debug)
            val=dictFile[key]
        except KeyError:
            self.error("Key: ",key,"not existing in File",fName)
        except IOError,e:
            self.error("Problem with file",fName,":",e)

        if sub==None:
            erg=val
        else:
            try:
                erg=eval(str(val)+sub)
            except Exception,e:
                self.error("Problem with subexpression:",sys.exc_info()[0],":",e)
                
        print erg
            