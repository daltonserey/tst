# check pip is available
pip --version > /dev/null
if [[ "$?" != "0" ]]; then
    echo "pip was not found"
    echo "install pip and try again"
fi

# install tst using pip
pip install tst --user || echo "error during installation" && exit 1

# check whether tst is already in user PATH
which tst > /dev/null
if [[ "$?" != "0" ]]; then
    echo "tst was not found"
    
fi

case "$OSTYPE" in
  darwin*)  echo "OSX" ;;
    DOTFILE=~/.profile
  linux*)   echo "LINUX" ;;
  bsd*)     echo "BSD" ;;
  *)        echo "unknown: $OSTYPE" ;;
esac
