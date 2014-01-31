# Provided by cdist __cbrg_local_home
# This file is only deployed if it doesn't already exist.
# Feel free to change. Your changes will _not_ be overwritten.

# Prepend PATH with ~/bin if it exists
[ -d ~/bin ] && export PATH=~/bin:$PATH

# Source ~/.bashrc if any
[ -f ~/.bashrc ] && . ~/.bashrc
