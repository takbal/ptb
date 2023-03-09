# INSTALL

You will need 'git', 'python3', 'pip' binaries, and 'glab' in case you need GitLab.

You will also need the 'auto-changelog', 'virtualenv', 'black' and 'flake8' python
packages installed for full functionality, working from any prompt.

The 'mkp' tool assumes the following directory format for you projects:

```
workspace/
    ptb/ # repo of this project
    project1/ # your projects come here
    project2/
    ...
    templates/python/ # the project template is copied here
```

1. Copy the 'template' folder to ../../templates/python, and edit it there to your liking.
If you want to use ipython and the autoimport support, you may want to add it to master
setup.cfg like:

[options.extras_require]
test = 
    pytest
dev =
    ipython

2. Add the contents of py.sh to your .zshrc (with completion) or .bashrc to allow
easy switch between project environments, as in 'py projectname' issued from anywhere.
