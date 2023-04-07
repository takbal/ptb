The 'mkp' tool is a command line utility to help with creating new projects, venvs, releases and more.

It assumes the following directory layout for your projects:

```
workspace/              # name does not matter (but change it in py.sh as well)
    ptb/                # repo of this project
    project1/           # your projects come here
    project2/
    ...
    templates/python/   # the project template is copied here
```

# INSTALL

1. install the required binaries. You will need 'git', 'python3', 'pip' at least,
and 'glab' in case you need GitLab. For full functionality, you will also need
the 'auto-changelog', 'virtualenv', 'black' and 'flake8' python packages installed
and working from any prompt.

2. from the ptb/ directory, copy the 'template' folder to ../templates/python, and
edit it there to your liking. If you want to use ipython and the autoimport support,
you may want to add it to the master setup.cfg in the template like:

```
[options.extras_require]
test = 
    pytest
dev =
    ipython
```

3. Add the contents of py.sh to your .zshrc (with completion) or .bashrc to allow
easy switch between project environments, as in 'py projectname', issued from anywhere.
If you use a different project root directory name (defaults to '$HOME/workspace'), then
change it in this script.