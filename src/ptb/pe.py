#!/usr/bin/env python3

"""
Local and/or grid parallel execution, with checkpointing and optional debugging.

Implemented through SGE and the multiprocessing module.

The function to call in parallel should look like:
    
#################################################
def func(start_state, *args, **kwargs)
    
    if start_state is not None:
        # ... restore state from start_state ...
    
    # loop of your demanding iterative calculation, say:            
    for x in X:                        
        # ... perform calculation ...
        
        if ptb.pe.progressrep( progress ):
            # ... prepare state ...
            # ... close pending resources ...
            return ptb.pe.checkpoint( state )
            
    return [result]
#################################################

It is recommended to use only small arguments and return only small sized variables.
Use files for large results.
    
The instance's stdout/stderr is saved into temporary directories below log_path, unless
the debug mode is used.

The framework may ask the function to checkpoint, that is, to provide a pickleable state
that can be used to continue the process. This works as the following: func() must regularly
call the ptb.pe.progressrep() function with a progress report indicator between 0 and 1,
where 0 means function done nothing yet, 1 means function is finished. Then you should examine
its return value: if False, no further work is needed. The function will return True after
'timeout' minutes are passed. Then the checkpoint state must be prepared, and the function
must end with "return ptb.pe.checkpoint(state)". Be prepared to terminate the process before the call. 

Progress is shown in the launching instance by bars if "show_bars" is set, otherwise 

The progressrep() call should be not too frequent, as it involves writing the progress into a
file. But also call progressrep function often enough for the state to be saved between the
timeout and SIGXCPU killing the job (this is currently 10 minutes in the short queue). 

If the function was terminated by checkpointing, the framework will automatically re-schedule
the same function call, with "start_state" set to the latest state saved in a checkpoint.
"start_state" has a value of None in the first call. 

Otherwise, the function should end with a return statement, returning the value of the computation
if any.

Exceptions are caught, treated as "error" finish, and the traceback string of the Exception is
returned in a ParexecErrorReturn variable. The function should not return a value that is an instance of
BaseException (as it is not necessary pickle-able), it should throw the exception instead.

It is possible to force writing a checkpoint state without exiting by

    ptb.pe.write_checkpoint(state, tag)
    
This may come handy if an error is captured within func(), and one wishes to examine the
state. Here "tag" is an extra string the statefile is going to have in the cp_path directory,
for example, it may contain a string describing the error. Then

    ptb.pe.restore_checkpoint(checkpoint_file)

can be used to re-run the call from the checkpoint, in order to debug the error. The function
name and the arguments are restored from the checkpoint file.

Saved states are saved below cp_path (default is /data/scratch/grid/${USER}/checkpoints/),
and are passed through lightweight compression. They are removed when a checkpoint is
restored, but if a job gets killed during checkpointing, it may become necessary to clean
this directory.

Performance tips:

Grid instances are used only if local instances are not enough to run all jobs. Local
instances are not asked to checkpoint (but you can do it yourself with write_checkpoint()).
Jobs listed first are submitted to local execution, and checkpointed grid jobs may get
transferred to local execution. This means that it is recommended to put jobs that
take a longer time in the head of the parameter list (e.g. US Low runs in a trading simulator).

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

import multiprocessing
import logging
import os
import numpy as np
import lz4.frame
import pickle
import time
import tqdm
import traceback

import ptb.tools

from time import sleep
from typing import Callable
from collections import namedtuple
from contextlib import redirect_stderr, redirect_stdout
from multiprocessing import Process, Pipe

Cpdata = namedtuple("Cpdata", ["state", "func", "input"])
"""
A PDS that is pickled into checkpoints.
"""

class ParexecErrorReturn:
    """
    A type for a variable that is returned in case of an error. Currently, it only contains
    a string, that may be the formatted traceback of an Exception raised by the function,
    or the "terminated" string if the job was detected to be terminated (say by killing it
    if local or cancelling it on the grid).
    
    Many Exceptions cannot be pickled, hence the need for this.
    """
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return self.msg
  
def start(
        func: Callable,
        inputs: list, 
        basename: str=None,
        jobids: list=None,
        debug: bool=False,
        num_locals: int=-1,
        num_remotes: int=1e10,
        project: str=os.getenv("PAREXEC_DEFAULT_PROJECT"),
        log_path: str=os.getenv("PAREXEC_LOG_PATH"),
        cp_path: str= "/data/scratch/grid/" + os.getenv("USER", default="UNKNOWN") + "/checkpoints/",
        priority: int=None,
        timeout: float=45,
        memory: float=8, # in GB
        threads: str=None,
        show_bars: bool=True
        ) -> list:
    """
    Launch func() in parallel with parameters stored in 'input'.
            
    It returns the list of values that were returned by each instance after they
    have terminated. If the function terminated with an error, it returns a ParexecErrorReturn for
    that particular job.

    Inputs:
        
        func:
            The function to execute in parallel. It should have the signature of:
            
                def func(start_state, *args, **kwargs)
                
            Check the module docstring for further instructions.
            
        inputs:
            A list of (args, kwargs) tuples to pass to func. Each list item defines a new parallel 
            job to run. Each item must be pickleable.
            
        basename:
            A string that is going to be used as a base name of grid submissions. If None,
            then the callable's __name__ field is used.
             
        jobids:
            A string that identifies each job. Must be unique. Will be shown on job feedback.
            Must have the same len() as inputs and must be unique, or it can be None to ask
            for generating one automatically.

        debug:
            If true, do not execute in parallel at all, only run jobs one-by-one from this
            instance. This allows setting breakpoints and testing func() in a debugger.
            
        num_locals:
            Maximal number of local instances to use (via multiprocessing).
            If it is -1, it is set to multiprocessing.cpu_count().

        num_remotes:
            Maximal number of grid instances to use.

        project:
            The grid submission project to use.

        log_path:
            The path where scheduler log and the stdout / stderr for each job should be dumped.
            
        cp_path:
            The path where checkpoint and progress files should be dumped.
            This must be a directory prepared for large and continuous
            data transfers.
             
        priority:
            A priority value for grid submissions. Allows users to prioritize their own jobs.
            See -js parameter of qsub. None means the parameter is omitted.
            
        timeout:
            Ask to checkpoint jobs on the grid after this much time in minutes. If nan,
            no timeout is asked.
            
        memory:
            Memory to request from SGE in gigabytes.
            
        threads:
            Specify requested thread range on the grid. This is a string in
            the form of 'x:y', where x is the minimal # of threads and y is
            the maximal number. None means the option is omitted.
            
        show_bars:
            If True, show progress bars instead the scheduler log.
            We show two bars: the top one is the number of jobs finished vs. total jobs,
            the bottom one is the average progress of jobs that still need to run (this can move backwards). 
            The top bar updates stats of the jobs:
            
                wait - waiting to start
                loc - running locally
                rem - running remotely on the grid
                end - finished successfully
                err - finished with an error
                cpt - waiting for checkpoint file to appear

            Bars are never shown in debug mode.
    """
    # sanity checks
    
    assert len(inputs) > 0
    assert jobids is None or len(inputs) == len(jobids)
    assert project
    assert log_path
    assert cp_path

    if debug:
        show_bars = False

    if basename is None:
        basename = func.__name__
    
    # find a dirname and an id string
    while True:
        idstr = basename + "__" + ptb.tools.rand_tag()
        outdir = os.path.join(log_path, "parexec__" + idstr )
        if not os.path.isdir(outdir):
            break
    os.makedirs(outdir)
    
    # configure screen + file logging
        
    _log = logging.getLogger(idstr)
    _log.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    fh = logging.FileHandler(os.path.join(outdir, "scheduler.log"), "w+")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    _log.addHandler(fh)

    if not show_bars:
        # log to the screen only if no bars
        sh = logging.StreamHandler()
        sh.setLevel(logging.DEBUG)    
        sh.setFormatter(formatter)
        _log.addHandler(sh)
        
    if num_locals == -1:
        num_locals = multiprocessing.cpu_count()
    
    # generate defaults
    if jobids is None:
        jobids = [ "job%d" % i for i in range(len(inputs)) ]
    else:
        assert len(set(jobids)) == len(jobids), "jobids are not unique"
        
    num_jobs = len(inputs)
    
    # this array stores the status of the jobs:
    # 0: waiting for start (first run or checkpointed),
    # 1: executing in the scheduler,
    # 2: executing locally,
    # 3: executing on the grid,
    # 4: finished successfully,
    # 5: finished with an error
    # 6: waiting for checkpoint file to appear
    status = np.zeros(num_jobs, dtype=int)
        
    # this array stores the number of checkpoints already stored for each job.
    # The scheduling prioritizes jobs higher with the smallest amount of checkpoints done
    num_cps_done = np.zeros(num_jobs)
    
    # this array stores the base name of the last checkpoint file (if any),
    # and the progressrep file
    cp_fname_bases = [ os.path.join(cp_path, "%s__%s" % (idstr, jobids[i])) \
                for i in range(len(inputs)) ]

    log_fname_bases = [ os.path.join(outdir, "%s" % jobids[i]) \
                for i in range(len(inputs)) ]
    
    for cp_fname_base in cp_fname_bases:
        assert not os.path.exists(cp_fname_base + ".checkpoint"), \
            "checkpoint file already exists - clean cp_path: %s" % cp_path
        assert not os.path.exists(cp_fname_base + ".progress"), \
            "progress file already exists - clean pt_path: %s" % cp_path

    # this array stores the return values from the function
    rets = [None] * num_jobs

    # type to store the process and the pipe's this side for a job 
    Job = namedtuple("Job", ["process", "pipe", "idx"])

    # stores the Jobs of running processes
    local_running_jobs = set()

    # stores SGE futures
    remote_futures = set()
    
    options = []
    if priority is not None:
        options.append("-js")
        options.append( str(priority) )
    if threads is not None:
        options.append("-pe")
        options.append("threaded")
        options.append( threads )

#     grid_settings = GridSettings(project=project,
#                           freeze_data=False,
#                           output_dir="/dev/null", # we have our own logging
#                           email=None,
#                           memory=memory * Memory.GIGABYTES,
#                           queue=("default.q", "short.q"),
#                           options=options,
#                           name=basename)
        
    if show_bars:
        
        bar_jobs = tqdm.tqdm(total=num_jobs,desc="",
                             bar_format="    jobs: {percentage:3.0f}%|{bar} {desc} | {elapsed}->{remaining}")
         
        bar_progress = tqdm.tqdm(total=100,desc="",
                            bar_format="progress: {percentage:3.0f}%|{bar} {desc} | {elapsed}->{remaining}")
        
    try:
        
#         with GridExecutor(grid_settings) as pool:    
            
# !!! reindent below -> if a grid scheduler is added again, until reindent end:             
            
        # stop if no more jobs to run
        while any(status < 4):
        
            # check if there is any job waiting
            if not all(status > 0):
    
                # this will just pick the next not running one if no cp is done
                nextidx = np.ma.MaskedArray(num_cps_done, status > 0).argmin()
                        
                if debug:
                    
                    _log.info("starting %s in scheduler" % jobids[nextidx])
                                        
                    status[nextidx] = 1
                    
                    # we have to repeat this part of _pe_wrapper() here, for progressrep to work
                    # not redirecting stdout/stderr, as it messes up with the scheduler
                    global my_cp_fname_base, my_end_time, my_args, my_func
                    
                    my_cp_fname_base = cp_fname_bases[nextidx]
                    my_end_time = np.nan
                    my_args = inputs[nextidx]
                    my_func = func

                    rets[nextidx] = func(None, *inputs[nextidx][0], **inputs[nextidx][1])
                        
                    status[nextidx] = 4
                                    
                # start on local if there is a free slot
                elif len(local_running_jobs) < num_locals:

                    _log.info("starting %s as local process" % jobids[nextidx])
    
                    server, client = Pipe()
                    
                    proc = Process(target=_pe_wrapper,
                                   args=(func,inputs[nextidx],client,
                                         np.nan,cp_fname_bases[nextidx],
                                         log_fname_bases[nextidx]) )
                    local_running_jobs.add( Job(proc, server, nextidx) )
                    proc.start()
                    status[nextidx] = 2
                    
                elif len(remote_futures) < num_remotes:

                    _log.info("starting %s on the grid" % jobids[nextidx])
                    
#                     remote_futures.add( ( nextidx, \
#                         pool.submit(_pe_wrapper,
#                                      func,inputs[nextidx],
#                                      None,
#                                      timeout,
#                                      cp_fname_bases[nextidx],
#                                      log_fname_bases[nextidx]) ) )
                    status[nextidx] = 3
        
            # launch only +1 job per second. This helps with
            # overloading resources
            sleep(1)
                                            
            # check local jobs            
            jobs_to_remove = set()
            for job in local_running_jobs:
                if not job.process.is_alive():
                    jobs_to_remove.add(job)
                    if not job.pipe.poll():
                        # process was terminated without returning value
                        rets[job.idx] = ParexecErrorReturn("terminated")
                        _log.warning("%s was terminated" % jobids[job.idx])
                    else:
                        try:
                            rets[job.idx] = job.pipe.recv()
                        except:
                            _log.error("error while reading pipe of %s" % jobids[job.idx])
                            rets[job.idx] = ParexecErrorReturn(traceback.format_exc())
                        job.pipe.close()
                        status[job.idx] = 4
                        _log.info("%s is finished" % jobids[job.idx])
                    
            local_running_jobs = local_running_jobs.difference(jobs_to_remove)

            # check remote jobs            
            futures_to_remove = set()
            for jobidx, rf in remote_futures:
                if rf.done():
                    futures_to_remove.add( (jobidx,rf) )
                    if rf.cancelled():
                        # process was terminated without returning value
                        rets[jobidx] = ParexecErrorReturn("terminated")
                        _log.warning("%s was terminated" % jobids[jobidx])
                    else:
                        try:
                            rets[jobidx] = rf.result()
                        except:
                            _log.error("error while reading remote result of %s" % jobids[jobidx])
                            rets[jobidx] = ParexecErrorReturn(traceback.format_exc())
                            
                        if isinstance(rets[jobidx], ParexecErrorReturn) and rets[jobidx].msg == "checkpointed": 
                            # start waiting for the checkpoint file. This is necessary
                            # because filesystems are unreliable in presenting files to various hosts.
                            # We take as criterion for re-scheduling that the file appears accessible on
                            # the server.  
                            status[jobidx] = 6
                            rets[jobidx] = None
                            _log.info("%s is checkpointed, waiting for checkpoint file to appear" % jobids[jobidx])
                        else:
                            status[jobidx] = 4
                            _log.info("%s is finished" % jobids[jobidx])

            remote_futures = remote_futures.difference(futures_to_remove)
                
            # test if any previously running jobs have finished with an error
            for jobidx in range(num_jobs):     
                if status[jobidx] < 5 and isinstance(rets[jobidx], ParexecErrorReturn):
                    status[jobidx] = 5
                    _log.warning("%s is marked as error finish" % jobids[jobidx])
                    
                    # dump error message into .stderr so we can check it before the batch finishes
                    
                    with open(log_fname_bases[jobidx] + ".stderr", "a") as errfile:
                        errfile.write(str(rets[jobidx]))
                    
                if status[jobidx] == 6 and os.path.exists(cp_fname_bases[jobidx] + ".checkpoint"):
                    status[jobidx] = 0
                    _log.info("%s checkpoint file is available, re-scheduling" % jobids[jobidx])
                    
            if show_bars:
                
                st = list(status)
                
                bar_jobs.n = st.count(4) + st.count(5)
                bar_jobs.set_description_str( "wait:%d,loc:%d,rem:%d,end:%d,err:%d,cpt:%d" %
                                              (st.count(0), st.count(1) + st.count(2),
                                               st.count(3), st.count(4), st.count(5), st.count(6) )
                                            )
                
                # average progress of running jobs
                                    
                running_jobs_indices = [ idx for idx,x in enumerate(st) if x == 1 or x == 2 or x == 3]
                
                if len(running_jobs_indices) > 0:
                
                    progress = 0.0

                    for idx in running_jobs_indices:                    
                        pfile = cp_fname_bases[idx] + ".progress"
                        if os.path.exists(pfile):
                            with open(pfile, "r") as f:
                                try:
                                    progress += float(f.read())
                                except:
                                    pass
                    
                    bar_progress.n = progress / len(running_jobs_indices)
                    bar_progress.refresh()

# !!! reindent ends             
                            
        if show_bars:              
            bar_jobs.n = num_jobs
            bar_jobs.refresh()
            bar_progress.n = 100
            bar_progress.refresh()
                          
        _log.info("all jobs finished")
        
    finally:

        # clean up all progress / regular checkpoint files
        for cp_file in iter(cp_fname_bases):
            pfile = cp_file + ".progress"
            if os.path.exists(pfile):
                os.remove(pfile)
            pfile = cp_file + ".checkpoint"
            if os.path.exists(pfile):
                os.remove(pfile)
                
        logging.shutdown()
    
    return rets

def _pe_wrapper(func: Callable, args: tuple, pipe, timeout,
                cp_fname_base, log_fname_base):
    """
    Internal function that runs on child instances by start().
    
    If cp_file exists, load it as start state, otherwise use it as dump location
    at timeout.
    
    pipe can be None - in that case just return the return value for SGE, otherwise
    put result into the pipe.
    """

    # save stuff into global space, so we can avoid asking the user to pass around our internal variables
    global my_cp_fname_base, my_end_time, my_args, my_func
    my_cp_fname_base = cp_fname_base
    my_end_time = time.monotonic() + 60*timeout
    my_args = args
    my_func = func
    
    cp_file = cp_fname_base + ".checkpoint"
    
    if os.path.exists(cp_file):
        start_state = load_checkpoint_state(cp_file)
        os.remove(cp_file)
    else:
        start_state = None

    with open(log_fname_base + ".stdout", "a") as stdout, \
         open(log_fname_base + ".stderr", "a") as stderr:
        with redirect_stdout(stdout):
            with redirect_stderr(stderr):

                try:    
                    ret = func(start_state, *args[0], **args[1])
                except:
                    # we have to pass the formatted error string, as exceptions cannot be pickled
                    ret = ParexecErrorReturn(traceback.format_exc())
    
    if pipe is None:
        return ret
    else:
        pipe.send(ret)
        pipe.close()

def checkpoint(state):
    """
    Saves the passed state variable, then calls exit(). The data is passed through
    lightweight compression.
    """
    write_checkpoint(state)
    return ParexecErrorReturn("checkpointed")

def write_checkpoint(state, tag: str=None) -> str:
    """
    Saves the passed state variable into a file tagged by the passed string.
    The tag should be specified when called directly, otherwise the regular
    checkpoint file is overwritten. The data is passed through lightweight lz4
    compression. Does NOT call exit(), so error handling is possible afterwards.
    Returns the saved file location.
    """
    if tag is None:
        cp_file = my_cp_fname_base + ".checkpoint"
    else:
        cp_file = my_cp_fname_base + ".checkpoint" + "_" + tag
        
    with lz4.frame.open(cp_file, mode="w") as cpf:
        cp = Cpdata(state, my_func, my_args)
        pickle.dump(cp, cpf, protocol=pickle.HIGHEST_PROTOCOL)
        
    return cp_file

def load_checkpoint_state(fname : str):
    """
    Restores the state from a checkpoint file.
    """
    with lz4.frame.open(fname, mode="r") as cpf:
        cp = pickle.load(cpf)
        return cp.state

def restore_checkpoint(fname : str):
    """
    Calls the function that generated the checkpoint file from the state and
    parameters stored in the file.
    """
    with lz4.frame.open(fname, mode="r") as cpf:
        cp = pickle.load(cpf)
    return cp.func(cp.state, *cp.args[0], **cp.args[1])

def progressrep(progress: float) -> bool:
    """
    Updates progress of the function. If it returns True, you have to prepare a state
    and call checkpoint(). 
    """
    
    progress_file = my_cp_fname_base + ".progress"
    
    with open(progress_file, "w") as pfile:
        pfile.write(str(np.ceil(100 * progress)))
        
    return time.monotonic() > my_end_time

def _testfunc(state, count_to : int, error_at: int):
    """
    dummy test function
    """
    
    if state is not None:
        start_val = state
    else:
        start_val = 0  
    
    for i in range(start_val, count_to):
        sleep(1)
        print( "iteration %d" % i )
        
        if i == error_at:
            raise ValueError
        
        if ptb.pe.progressrep( i/count_to ):
            return ptb.pe.checkpoint(i+1)

    return count_to

def _testdebug():
    
    print( ptb.pe.start( ptb.pe._testfunc, [ ( (10,None),{} ) ], debug=True ) )
                  
    print( ptb.pe.start( ptb.pe._testfunc, [ ( (10,5),{} ) ], debug=True ) )

def _testlocal():
    
    return ptb.pe.start( ptb.pe._testfunc, [
            ( (10,None),{} ), ( (10,5),{} )
            ], num_locals=5, show_bars=True )

def _testgrid():
    
    return ptb.pe.start( ptb.pe._testfunc, [
            ( (10,None),{} ), ( (10,5),{} )
            ], num_locals=0, num_remotes=10, show_bars=True )

def _testgrid_checkpoint():
    
    return ptb.pe.start( ptb.pe._testfunc, [
            ( (120,None),{} ), ( (120,70),{} )
            ], num_locals=0, num_remotes=10, show_bars=False, timeout=1 )

def _testlocalgrid():
    
    return ptb.pe.start( ptb.pe._testfunc, [
            ( (10,None),{} ), ( (10,5),{} ), ( (20,None),{} ), ( (20,10),{} )
            ], num_locals=2, num_remotes=2, show_bars=True )

def _test_tqdm(num_bars):
        
    pbars = [ tqdm.tqdm(total=100,desc=ptb.tools.rand_tag(int(np.ceil(10*np.random.rand()))),
                        bar_format="{percentage:3.0f}%|{bar} {desc} | {elapsed}->{remaining}") for i in range(num_bars) ]

    for i in range(100):
        
        sleep(1)

        for idx in range(num_bars):
            pbars[idx].n = i
            pbars[idx].refresh()

            if idx % 10 == 0:
                pbars[idx].n = 100
                pbars[idx].refresh()

            pbars[idx].set_description_str( ptb.tools.rand_tag(int(np.ceil(10*np.random.rand()))) )
            
        tqdm.tqdm.write("and %d more" % i)
