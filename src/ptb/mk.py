#!/usr/bin/env python3

"""
simple tool to perform usual tasks on a Python project

Due to likely being called from command-line and ptb not installed,
this must work stand-alone, and only with system libraries.

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

epilog = """
    Usage: mk TASK
    
    Where task is one of:
    
        new           : create a new project (guided: enter package, module and location)
        build         : build project with setup.py build
        install       : install project with setup.py install
        major         : generate a major release
        minor         : generate a minor release
        patch         : generate a patch release
        venv          : re-create the editable venv for the project (also called if new project is made)
        dist          : create packages with setup.py sdist bdist_wheel (also called if a release is made)
        changelog     : auto-generate changelog (also called if a release is made)
        
    Creating a new project is going to automatically create a venv, and install 'ptb' and the project in
    editable mode. 
    
    Generating a release will first check if repo is clean, and the tests run without failure.
    Then it is going to create the changelog, and checks it in.
    Finally, it creates the packages automatically.
    """

import subprocess
import sys
import os
import contextlib
from importlib.metadata import version as importlib_version, PackageNotFoundError

# import pkg_resources

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from pathlib import Path
from inspect import getsourcefile

def main(args, ptb_location: str):
        
    def_project_location = ptb_location.parent
    template_location = def_project_location / 'templates' / 'python' 
    
    try:

        if args.task == 'new':
            
            # create new project
            
            assert template_location.exists(), 'cannot find template location'
            assert ptb_location.exists(), 'cannot find ptb'
            
            project_name = input("new project (package) name: ")
            assert project_name, 'you must supply a project name'
            module_name = input("main module name [%s]: " % project_name)
            if not module_name:
                module_name = project_name
            project_location = input("parent directory of the project [%s]: " % def_project_location)
            if not project_location:
                project_location = def_project_location
            project_location /= project_name
            
            assert not project_location.exists(), 'project already exists'

            print('copying template ...')            
            run_script('cp -a ' + str(template_location) + ' ' + str(project_location))
            run_script('mv ' + str(project_location / 'src' / 'python') + ' ' +
                       str(project_location / 'src' / project_name))
            if module_name != 'main':
                run_script('mv ' + str(project_location / 'src' / project_name / 'main.py') + ' ' +
                           str(project_location / 'src' / project_name / (module_name + '.py') ))
            
            with working_directory(project_location):
                print('adding git repository ...')
                run_script('git init')
                run_script('git add .')
                run_script('git commit -m "[AUTO] initial check-in"')

                print('generating venv ...')
                generate_venv(ptb_location)
                        
        else:
                    
                if args.task == 'venv':
                    assert ptb_location.exists(), 'cannot find ptb'
                    with working_directory(get_basedir()):
                        generate_venv(ptb_location)
            
                elif args.task == 'dist':
                    with working_directory(get_basedir()):
                        generate_dist()
                        
                elif args.task == 'build':
                    with working_directory(get_basedir()):
                        run_script('python3 setup.py build')
                    
                elif args.task == 'install':
                    with working_directory(get_basedir()):
                        run_script('python3 setup.py install')
            
                elif args.task == 'changelog':
                    with working_directory(get_basedir()):
                        generate_changelog()
                    
                elif args.task == 'major':
                    with working_directory(get_basedir()):
                        generate_new_version(0)
                    
                elif args.task == 'minor':
                    with working_directory(get_basedir()):
                        generate_new_version(1)
                    
                elif args.task == 'patch':
                    with working_directory(get_basedir()):
                        generate_new_version(2)
                    
                else:
                    raise ValueError('unknown task')
                
    except ScriptException as se:
        print("*** got return code %d while executing:\n\n%s" % (se.returncode, se.script) )       
        print("\n*** output:\n%s" % se.output )       

def get_basedir() -> Path:
    """determine by guesswork the actual project path, by looking for canonical files/dirs
       of the template from child directories"""
    
    actdir = Path.cwd().resolve()
    init_dir = actdir
    firstdir = Path(actdir.parts[0]) # .root is stupid in Windows
    
    def likely_project_dir(actdir) -> bool:
        filelist = ['src','tests','.autoenv.zsh','setup.py','version']
        return all ([ (actdir / f).exists() for f in filelist ])
    
    while not likely_project_dir(actdir) and actdir != firstdir:
        actdir = actdir.parent
    
    if actdir == firstdir:
        raise RuntimeError("cannot determine project directory")
    
    if actdir != init_dir:
        print('guessed project directory as: %s' % actdir)
    
    return actdir

def test_repo_clean() -> bool:
    output = subprocess.check_output(['git', 'status', '--porcelain']).strip()
    return len(output) == 0

def generate_changelog():
    # --ignore-commit-pattern ignores the entire release string
    run_script("""
        auto-changelog --commit-limit false -o CHANGELOG.md.orig
        sed '/^-\ \[AUTO\]/d' < CHANGELOG.md.orig > CHANGELOG.md 
        rm CHANGELOG.md.orig
        git add CHANGELOG.md
        """)

def generate_dist():
    run_script('python3 setup.py sdist bdist_wheel')

def generate_venv(ptb_location: Path):
    run_script("""
        rm -rf .venv
        virtualenv .venv --system-site-packages
        . .venv/bin/activate
        pip install -I ipython
        pip install -e """ + str(ptb_location) + """
        pip install -e .
        hash -r
        """)
    
def generate_new_version(version_index_to_increase: int):
        
    assert test_repo_clean(), '*** repository is not clean, aborting'
    
    try:
        run_script('pytest')
    except ScriptException as se:
        if se.returncode != 5:
            print('*** tests failed to run, aborting. Check pytest')
            exit()
            
    if input("are you sure? [y/n] ") != "y":
        exit()
                
    with open('version') as f:
        old_version = f.read().strip()
    new_version = increment_version(old_version, version_index_to_increase)
    print('incremented version ' + old_version + ' to ' + new_version)
    with open('version', 'w') as f:
        f.write(new_version)

    # a bit stupid to check in the changelog post-release, but auto-changelog
    # needs the new release tag first to generate an entry for it

    print('tagging release in git ...')

    run_script('git tag -a ' + new_version + ' -m "RELEASE ' + new_version + '"')        

    print('creating changelog ...')
    
    generate_changelog()

    print('committing changelog ...')
    
    run_script('git commit -a -m "[AUTO] post-release ' + new_version + '"')

    print('creating packages ...')
        
    generate_dist()        

def increment_version(version: str, pos: int) -> str:
    """
    Increases X.Y.Z version number stored in a string.
    Specify index of position to choose which one to increment
    """
    parts = version.split(sep='.')
    assert len(parts) == 3, 'cannot parse version numbers'
    assert pos < 3, 'position number must be 0,1 or 2'
    nums = [ int(p) for p in parts ]
    nums[pos] += 1
    nums[pos+1:] = (2-pos)*[0]
    parts = [ str(p) for p in nums ]
    return ".".join(parts)

#### stuff from here are repeated in tools.py, please keep in syncro ####

@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

def run_script(script, print_output=False) -> str:
    output = ''
    with subprocess.Popen(['bash', '-c', script],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL, bufsize=1, universal_newlines=True) as proc:
        
        for line in proc.stdout:
            if print_output:
                print(line, end='')
            output += line

    if proc.returncode:
        raise ScriptException(proc.returncode, output, script)
    
    return output

class ScriptException(Exception):
    def __init__(self, returncode, output, script):
        self.returncode = returncode
        self.output = output
        self.script = script
        super().__init__('Error in script')

#### repeated code ends ####

if __name__ == '__main__':

    # no error dumps
    sys.tracebacklimit = 0

    project_dir = Path(getsourcefile(lambda:0)).resolve().parent.parent.parent

    if (project_dir / 'version').exists():
        with open(project_dir / 'version', "r") as f:
            version = f.read()
    else:
        version = 'UNKNOWN'

    parser = ArgumentParser( description=__import__('__main__').__doc__.split("\n")[1],
        formatter_class=RawDescriptionHelpFormatter,
        epilog=dedent(epilog) )
    
    parser.add_argument('-V', '--version', action='version', version=version)
    parser.add_argument('task', type=str, default=None, help="the task to perform")

    main(parser.parse_args(), project_dir)
