# INSTALL

The 'mkp' tool assumes the following directory format for you projects:

```
workspace/
    ptb/ # repo of this project
    templates/python/
    project1/ # your projects come here
    project2/
    ...
```

1. Copy the 'template' folder to ../../templates/python, and edit it there to your liking.

2. Add the contents of py.sh to your .zshrc (with completion) or .bashrc.

You will need 'git', 'python3', 'pip' binaries, and 'glab' in case you need GitLab.

You will also need the 'auto-changelog', 'virtualenv', 'black' and 'flake8' python
packages installed, with their CLI working.
