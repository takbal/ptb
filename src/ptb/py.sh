# automatically select and run ipython in an environment, like "py envname [params]"

find-up () {
  p=$(pwd)
  while [[ "$p" != "" && ! -e "$p/$1" ]]; do
    p=${p%/*}
  done
  echo "$p"
}

py()
{
  if [[ $1 == "--help" ]]; then
    ipython --help
    return
  fi

  if [[ "$#" == "0" ||  $1 == "." ]]; then
          projectdir=$(find-up setup.py)
  elif [ -d $HOME/workspace/$1 ]; then
    projectdir=$HOME/workspace/$1
  # add more directories here if you need them
  else
    echo "cannot find specified environment"
    return 1
  fi

  if [ -f ${projectdir}/.venv/bin/ipython ]; then
    ipy=${projectdir}/.venv/bin/ipython
  else
    ipy=ipython
  fi

  if [ $# != "0" ]; then
    shift
  fi

  if [ -f ${projectdir}/.venv/bin/activate ]; then
    source ${projectdir}/.venv/bin/activate
  fi

  if [ -d ${projectdir}/.ipython_profile ]; then
      ${ipy} --no-confirm-exit --no-banner --HistoryManager.hist_file=$HOME/.ipython/profile_default/history.sqlite --profile-dir=${projectdir}/.ipython_profile $@
  else
      ${ipy} --no-confirm-exit --no-banner --HistoryManager.hist_file=$HOME/.ipython/profile_default/history.sqlite $@
  fi

  if [ -f ${projectdir}/.venv/bin/activate ]; then
    deactivate
  fi

}

# automatic env completion for the py() call in zsh (cut this below for bash)

_py() {
  local state

  _arguments \
    '1: :->python_environment'\
    '*: :->other'

  # add more directories here if you need them
  envs_ls=`ls -1d $HOME/workspace/*/`
  envs_array=("${(f)envs_ls}")
  envs=()
  for i in $envs_array; do envs+=`basename $i`; done

  case $state in
    (python_environment) _arguments '1:environment:($envs)' ;;
    (other) _gnu_generic ;;
  esac
}

compdef _py py
compdef _gnu_generic python
