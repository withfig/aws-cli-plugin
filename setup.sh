echo Make sure AWS CLI is installed before running this script...
mkdir -p ./export/js/aws
mkdir -p ./export/ts/aws

aws configure set plugins.fig fig
export PYTHONPATH=$(pwd):$PYTHONPATH
