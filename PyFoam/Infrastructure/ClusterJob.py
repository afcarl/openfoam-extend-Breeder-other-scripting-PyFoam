#  ICE Revision: $Id: /local/openfoam/Python/PyFoam/PyFoam/Infrastructure/Logging.py 1906 2007-08-28T16:16:19.392553Z bgschaid  $ 
"""Encapsulates all necessary things for a cluster-job, like setting up, running, restarting"""

import os
from os import path,unlink
from threading import Thread,Lock,Timer

from PyFoam.Applications.Decomposer import Decomposer
from PyFoam.Applications.Runner import Runner
from PyFoam.Applications.SteadyRunner import SteadyRunner
from PyFoam.Applications.CloneCase import CloneCase
from PyFoam.FoamInformation import changeFoamVersion
from PyFoam.Error import error,warning
from PyFoam import configuration as config

def checkForMessageFromAbove(job):
    if not job.listenToTimer:
        return

    if path.exists(job.stopFile()):
        job.stopJob()
        return
    
    if path.exists(job.checkpointFile()):
        job.writeCheckpoint()
    
    job.timer=Timer(1.,checkForMessageFromAbove,args=[job])
    job.timer.start()
    

class ClusterJob:
    """ All Cluster-jobs are to be derived from this base-class

    The actual jobs are implemented by overriding methods
    
    There is a number of variables in this class that are used to
    'communicate' information between the various stages"""

    def __init__(self,basename,arrayJob=False,hardRestart=False,autoParallel=True,foamVersion=None,multiRegion=False):
        """Initializes the Job
        @param basename: Basis name of the job
        @param arrayJob: this job is a parameter variation. The tasks
        are identified by their task-id
        @param hardRestart: treat the job as restarted
        @param autoParallel: Parallelization is handled by the base-class
        @param foamVersion: The foam-Version that is to be used
        @param multiRegion: This job consists of multiple regions"""

        #        print os.environ
        
        if not os.environ.has_key("JOB_ID"):
            error("Not an SGE-job. Environment variable JOB_ID is missing")
        self.jobID=int(os.environ["JOB_ID"])
        self.jobName=os.environ["JOB_NAME"]
        
        self.basename=path.join(path.abspath(path.curdir),basename)

        sgeRestarted=False
        if os.environ.has_key("RESTARTED"):
            sgeRestarted=(int(os.environ["RESTARTED"])!=0)
            
        if sgeRestarted or hardRestart:
            self.restarted=True
        else:
            self.restarted=False

        if foamVersion==None:
            foamVersion=config().get("OpenFOAM","Version")
            
        changeFoamVersion(foamVersion)

        if not os.environ.has_key("WM_PROJECT_VERSION"):
            error("No OpenFOAM-Version seems to be configured. Set the foamVersion-parameter")
            
        self.autoParallel=autoParallel
        self.multiRegion=multiRegion
        
        self.hostfile=None
        self.nproc=1

        if os.environ.has_key("NSLOTS"):
            self.nproc=int(os.environ["NSLOTS"])
            if self.nproc>1:
                # self.hostfile=os.environ["PE_HOSTFILE"]
                self.hostfile=path.join(os.environ["TMP"],"machines")
                
        self.ordinaryEnd=True
        self.listenToTimer=False

        self.taskID=None
        self.arrayJob=arrayJob
        
        if self.arrayJob:
            self.taskID=int(os.environ["SGE_TASK_ID"])

        ## prepend special paths for the cluster
        os.environ["PATH"]=config().get("ClusterJob","path")+":"+os.environ["PATH"]
        os.environ["LD_LIBRARY_PATH"]=config().get("ClusterJob","ldpath")+":"+os.environ["LD_LIBRARY_PATH"]
        
        self.isDecomposed=False

    def message(self,*txt):
        print "=== CLUSTERJOB: ",
        for t in txt:
            print t,
        print " ==="

    def setState(self,txt):
        self.message("Setting Job state to",txt)
        fName=path.join(self.casedir(),"ClusterJobState")
        f=open(fName,"w")
        f.write(txt+"\n")
        f.close()

    def jobFile(self):
        """The file with the job information"""
        jobfile="%s.%d" % (self.jobName,self.jobID)
        if self.arrayJob:
            jobfile+=".%d" % self.taskID
        jobfile+=".pyFoam.clusterjob"
        jobfile=path.join(path.dirname(self.basename),jobfile)
        
        return jobfile

    def checkpointFile(self):
        """The file that makes the job write a checkpoint"""
        return self.jobFile()+".checkpoint"
    
    def stopFile(self):
        """The file that makes the job write a checkpoint and end"""
        return self.jobFile()+".stop"
    
    def doIt(self):
        """The central logic. Runs the job, sets it up etc"""

        f=open(self.jobFile(),"w")
        f.write(path.basename(self.basename)+"\n")
        f.close()
        
        self.message()
        self.message("Running on directory",self.casename())
        self.message()
        self.setState("Starting up")
        
        parameters=None
        if self.arrayJob:
            parameters=self.taskParameters(self.taskID)
            self.message("Parameters:",parameters)
        if not self.restarted:
            self.setState("Setting up")
            self.setup(parameters)
            if self.autoParallel and self.nproc>1:
                self.setState("Decomposing")
                self.autoDecompose()

            self.isDecomposed=True

            self.setState("Setting up 2")
            self.postDecomposeSetup(parameters)
        else:
            self.setState("Restarting")

        self.isDecomposed=True

        self.setState("Running")
        self.listenToTimer=True
        self.timer=Timer(1.,checkForMessageFromAbove,args=[self])
        self.timer.start()
        
        self.run(parameters)
        self.listenToTimer=False

        if path.exists(self.jobFile()):
            unlink(self.jobFile())
        
        if self.ordinaryEnd:
            self.setState("Post Running")
            self.preReconstructCleanup(parameters)

            self.isDecomposed=False
            
            if self.autoParallel and self.nproc>1:
                self.setState("Reconstructing")
                self.autoReconstruct()

            self.setState("Cleaning")
            self.cleanup(parameters)
            self.setState("Finished")
        else:
            self.setState("Suspended")

        if path.exists(self.stopFile()):
            unlink(self.stopFile())
        if path.exists(self.checkpointFile()):
            unlink(self.checkpointFile())
            
    def casedir(self):
        """Returns the actual directory of the case
        To be overridden if appropriate"""
        if self.arrayJob:
            return "%s.%05d" % (self.basename,self.taskID)
        else:
            return self.basename

    def casename(self):
        """Returns just the name of the case"""
        return path.basename(self.casedir())
    
    def foamRun(self,application,args=[],foamArgs=[],steady=False,multiRegion=None):
        """Runs a foam utility on the case.
        If it is a parallel job and the grid has
        already been decomposed (and not yet reconstructed) it is run in
        parallel
        @param application: the Foam-Application that is to be run
        @param foamArgs: A list if with the additional arguments for the
        Foam-Application
        @param args: A list with additional arguments for the Runner-object
        @param steady: Use the steady-runner
        @param multiRegion: Run this on multiple regions (if None: I don't have an opinion on this)"""

        arglist=args[:]
        if self.isDecomposed and self.nproc>1:
            arglist+=["--procnr=%d" % self.nproc,
                      "--machinefile=%s" % self.hostfile]

        if self.multiRegion:
            if multiRegion==None or multiRegion==True:
                arglist+=["--all-regions"]
        elif multiRegion and not self.multiRegion:
            warning("This is not a multi-region case, so trying to run stuff multi-region won't do any good")
            
        if self.restarted:
            arglist+=["--restart"]
            
        arglist+=[application,".",self.casename()]
        arglist+=foamArgs

        self.message("Executing",arglist)

        if steady:
            self.message("Running Steady")
            runner=SteadyRunner(args=arglist)
        else:
            runner=Runner(args=arglist)
            
    def autoDecompose(self):
        """Automatically decomposes the grid with a metis-algorithm"""

        args=["--method=metis",
              "--clear",
              self.casename(),
              self.nproc]

        if self.multiRegion:
            args.append("--all-regions")
            
        deco=Decomposer(args=args)

    def autoReconstruct(self):
        """Default reconstruction of a parallel run"""

        self.foamRun("reconstructPar",
                     args=["--logname=ReconstructPar"])
        
    def setup(self,parameters):
        """Set up the job. Called in the beginning if the
        job has not been restarted

        Usual tasks include grid conversion/setup, mesh decomposition etc

        @param parameters: a dictionary with parameters"""

        pass

    def postDecomposeSetup(self,parameters):
        """Additional setup, to be executed when the grid is already decomposed

        Usually for tasks that can be done on a decomposed grid

        @param parameters: a dictionary with parameters"""

        pass

    def run(self,parameters):
        """Run the actual job. Usually the solver.
        @param parameters: a dictionary with parameters"""

        pass

    def preReconstructCleanup(self,parameters):
        """Additional cleanup, to be executed when the grid is still decomposed

        Usually for tasks that can be done on a decomposed grid

        @param parameters: a dictionary with parameters"""

        pass

    def cleanup(self,parameters):
        """Clean up after a job
        @param parameters: a dictionary with parameters"""

        pass
    
    def taskParameters(self,id):
        """Parameters for a specific task
        @param id: the id of the task
        @return: a dictionary with parameters for this task"""

        error("taskParameter not implemented. Not a parameterized job")
        
        return {}

    def writeCheckpoint(self):
        if self.listenToTimer:
            f=open(path.join(self.basename,"write"),"w")
            f.write("Jetzt will ich's wissen")
            f.close()
            unlink(self.checkpointFile())
        else:
            warning("I'm not listening to your callbacks")

        self.timer=Timer(1.,checkForMessageFromAbove,args=[self])
            
    def stopJob(self):
        if self.listenToTimer:
            self.ordinaryEnd=False
            f=open(path.join(self.basename,"stop"),"w")
            f.write("Geh z'haus")
            f.close()
            unlink(self.stopFile())
        else:
            warning("I'm not listening to your callbacks")
            
class SolverJob(ClusterJob):
    """A Cluster-Job that executes a solver. It implements the run-function.
    If a template-case is specified, the case is copied"""

    def __init__(self,basename,solver,template=None,cloneParameters=[],arrayJob=False,hardRestart=False,autoParallel=True,foamVersion=None,steady=False,multiRegion=False):
        """@param template: Name of the template-case. It is assumed that
        it resides in the same directory as the actual case
        @param cloneParameters: a list with additional parameters for the
        CloneCase-object that copies the template"""

        ClusterJob.__init__(self,basename,arrayJob=arrayJob,hardRestart=hardRestart,autoParallel=autoParallel,foamVersion=foamVersion,multiRegion=multiRegion)
        self.solver=solver
        self.steady=steady
        if template!=None and not self.restarted:
            template=path.join(path.dirname(self.casedir()),template)
            if path.abspath(basename)==path.abspath(template):
                error("The basename",basename,"and the template",template,"are the same directory")
            clone=CloneCase(args=cloneParameters+[template,self.casedir()])

    def run(self,parameters):
        self.foamRun(self.solver,steady=self.steady,multiRegion=False)
        