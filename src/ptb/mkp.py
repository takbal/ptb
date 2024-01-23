#!/usr/bin/env python3

"""
simple tool to perform usual tasks on a Python project

Due to likely being called with ptb not installed,
this script must work stand-alone, and only with system libraries.

@author:  Balint Takacs
@contact: takbal@gmail.com
"""

epilog = """
    Usage: mkp TASK
    
    Where task is one of:
    
        new           : create a new project (guided: enter package, module and location, optionally gitlab)
        build         : build project with setup.py build
        install       : install project with setup.py install
        major         : generate a major release
        minor         : generate a minor release
        patch         : generate a patch release
        venv          : re-create the editable venv for the project (also called if new project is made)
        dist          : create packages with setup.py sdist bdist_wheel (also called if a release is made)
        changelog     : auto-generate changelog (also called if a release is made)
        format        : run 'black' then 'flake8' on the src/ and tests/ directory
        autoimport    : add import statements to .ipython_profile/startup/75-mkp.py from the current deps
        
    For auto-changelogs to work, you need to use https://www.conventionalcommits.org/en/v1.0.0/#specification
    Generally, use feat: fix:, feat!:, fix!: docs:  prefixes with optional () scope in a commit if you want
    it to appear in changelog.
    
    Creating a new project is going to automatically create a venv, and install the project in editable mode. 
    You need to setup and edit the project template before doing it first.
    
    Generating a release will:

     - run black
     - check if repo is clean
     - run the tests
     - change version
     - auto-generate the changelog and check it in
     - create distribution packages
     - push the release

    You need the following tools to be installed and accessible on path:

    binaries: git, python3, pip
    python packages: auto-changelog, virtualenv, black, flake8

    If you are using gitlab, 'glab' also needs to be installed.
    """

import subprocess
import sys
import os
import contextlib
import configparser
from importlib.metadata import version as importlib_version, PackageNotFoundError

# import pkg_resources

from argparse import ArgumentParser, RawDescriptionHelpFormatter
from textwrap import dedent
from pathlib import Path
from inspect import getsourcefile

autoimport_statements = {
    "numpy": "import numpy as np",
    "pandas": "import pandas as pd",
    "bottleneck": "import bottleneck as bn",
    "plotly": "import plotly.express as px",
}


def main(args, def_project_location: str):
    template_location = def_project_location / "templates" / "python"

    try:
        if args.task == "new":
            # create new project

            assert template_location.exists(), "cannot find template location"

            project_name = input("new project (package) name: ")
            assert project_name, "you must supply a project name"
            module_name = input("main module name [%s]: " % project_name)
            if not module_name:
                module_name = project_name
            project_location = input(
                "parent directory of the project [%s]: " % def_project_location
            )
            if not project_location:
                project_location = def_project_location
            project_location /= project_name

            assert not project_location.exists(), "project already exists"

            print("copying template ...")
            run_script("cp -a " + str(template_location) + " " + str(project_location))
            run_script(
                "mv "
                + str(project_location / "src" / "python")
                + " "
                + str(project_location / "src" / project_name)
            )
            if module_name != "main":
                run_script(
                    "mv "
                    + str(project_location / "src" / project_name / "main.py")
                    + " "
                    + str(
                        project_location / "src" / project_name / (module_name + ".py")
                    )
                )

            with working_directory(project_location):
                config = configparser.ConfigParser()
                config.read("setup.cfg")
                config["metadata"]["name"] = project_name
                with open("setup.cfg", "w") as f:
                    config.write(f)

                print("adding git repository ...")
                run_script("git init")
                run_script("git add .")
                run_script('git commit -m "[AUTO] initial check-in"')

                print("generating venv ...")
                generate_venv()

                need_gitlab = input("do you need a gitlab repo? [y/N]: ")
                if need_gitlab == "y":
                    tmp = run_script("glab auth status")
                    if "401" in tmp:
                        token = input("gitlab needs login, enter your token: ")
                        run_script(f"glab auth login --token {token}")
                    run_script(f'glab repo create --group {config["gitlab"]["group"]}')
                    run_script("git push --set-upstream origin master")

        else:
            project_dir = get_project_dir()

            with working_directory(project_dir):
                print("guessed project directory as: %s" % project_dir)

                if args.task == "venv":
                    generate_venv()

                elif args.task == "dist":
                    generate_dist()

                elif args.task == "build":
                    run_script("python3 setup.py build")

                elif args.task == "install":
                    run_script("python3 setup.py install")

                elif args.task == "changelog":
                    generate_changelog()

                elif args.task == "major":
                    generate_new_version(0)

                elif args.task == "minor":
                    generate_new_version(1)

                elif args.task == "patch":
                    generate_new_version(2)

                elif args.task == "format":
                    run_script("black src tests")
                    run_script("flake8 src tests")

                elif args.task == "autoimport":
                    generate_autoimport()

                else:
                    raise ValueError("unknown task")

    except ScriptException as se:
        print(
            "*** got return code %d while executing:\n\n%s" % (se.returncode, se.script)
        )
        print("\n*** output:\n%s" % se.output)


def get_project_dir(actdir=None) -> Path:
    """guess the parent project path"""

    if actdir is None:
        actdir = Path.cwd().resolve()

    init_dir = actdir
    firstdir = Path(actdir.parts[0])  # .root is stupid in Windows

    def likely_project_dir(actdir) -> bool:
        filelist = ["src", "tests", "setup.py"]
        return all([(actdir / f).exists() for f in filelist])

    while not likely_project_dir(actdir) and actdir != firstdir:
        actdir = actdir.parent

    if actdir == firstdir:
        raise RuntimeError("cannot determine project directory")

    return actdir


def test_repo_clean() -> bool:
    output = subprocess.check_output(["git", "status", "--porcelain"]).strip()
    return len(output) == 0


def test_has_remote() -> bool:
    output = subprocess.check_output(["git", "remote", "-v"]).strip()
    return len(output) != 0


def generate_changelog():
    run_script(
        """
        auto-changelog --gitlab
        git add CHANGELOG.md
        """
    )


def generate_dist():
    run_script("python3 setup.py sdist bdist_wheel")


def generate_venv():
    run_script(
        """
        rm -rf .venv
        virtualenv .venv
        . .venv/bin/activate
        pip install -e .[dev,test]
        hash -r
        """
    )


def generate_autoimport():
    os.makedirs(Path(".ipython_profile") / "startup", exist_ok=True)

    config = configparser.ConfigParser()
    config.read("setup.cfg")
    packages = config["options"]["install_requires"]

    with open(Path(".ipython_profile") / "startup" / "75-mkp.py", "w") as file:
        for key in autoimport_statements:
            if key in packages:
                file.write(f"{autoimport_statements[key]}\n")


def generate_new_version(version_index_to_increase: int):
    run_script("black src tests")

    assert test_repo_clean(), "*** repository is not clean, aborting"

    try:
        run_script("pytest")
    except ScriptException as se:
        if se.returncode != 5:
            print("*** tests failed to run, aborting. Check pytest")
            exit()

    if input("are you sure? [y/n] ") != "y":
        exit()

    config = configparser.ConfigParser()
    config.read("setup.cfg")

    old_version = config["metadata"]["version"]
    new_version = increment_version(old_version, version_index_to_increase)
    config["metadata"]["version"] = new_version
    print("incremented version " + old_version + " to " + new_version)

    with open("setup.cfg", "w") as f:
        config.write(f)

    # a bit stupid to check in the changelog post-release, but auto-changelog
    # needs the new release tag first to generate an entry for it

    print("tagging release for auto-changelog ...")

    run_script("git tag -a " + new_version + ' -m "RELEASE ' + new_version + '"')

    print("creating changelog ...")

    generate_changelog()

    print("creating packages ...")

    generate_dist()

    print("committing pre-release changes ...")

    run_script('git commit -a -m "[AUTO] pre-release ' + new_version + '"')

    print("tagging ...")

    run_script("git tag -a -f " + new_version + ' -m "RELEASE ' + new_version + '"')

    if test_has_remote():
        print("pushing ...")
        run_script("git push")
        # push tag
        run_script("git push origin " + new_version)


def increment_version(version: str, pos: int) -> str:
    """
    Increases X.Y.Z version number stored in a string.
    Specify index of position to choose which one to increment
    """
    parts = version.split(sep=".")
    assert len(parts) == 3, "cannot parse version numbers"
    assert pos < 3, "position number must be 0,1 or 2"
    nums = [int(p) for p in parts]
    nums[pos] += 1
    nums[pos + 1 :] = (2 - pos) * [0]
    parts = [str(p) for p in nums]
    return ".".join(parts)


#### stuff from here are repeated in tools.py so this works standalone, please keep in sync ####


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
    output = ""
    with subprocess.Popen(
        ["bash", "-c", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        bufsize=1,
        universal_newlines=True,
    ) as proc:
        for line in proc.stdout:
            if print_output:
                print(line, end="")
            output += line

    if proc.returncode:
        raise ScriptException(proc.returncode, output, script)

    return output


class ScriptException(Exception):
    def __init__(self, returncode, output, script):
        self.returncode = returncode
        self.output = output
        self.script = script
        super().__init__("Error in script")


#### repeated code ends ####

if __name__ == "__main__":
    # no error dumps
    sys.tracebacklimit = 0

    my_project_dir = get_project_dir(Path(getsourcefile(lambda: 0)).resolve())

    if (my_project_dir / "setup.cfg").exists():
        with working_directory(my_project_dir):
            config = configparser.ConfigParser()
            config.read("setup.cfg")
            version = config["metadata"]["version"]
    else:
        version = "UNKNOWN"

    parser = ArgumentParser(
        description=__import__("__main__").__doc__.split("\n")[1],
        formatter_class=RawDescriptionHelpFormatter,
        epilog=dedent(epilog),
    )

    parser.add_argument("-V", "--version", action="version", version=version)
    parser.add_argument(
        "task",
        type=str,
        help="the task to perform",
        choices=[
            "new",
            "build",
            "install",
            "major",
            "minor",
            "patch",
            "venv",
            "dist",
            "changelog",
            "format",
            "autoimport",
        ],
    )

    main(parser.parse_args(), my_project_dir.parent)
