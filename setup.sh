echo Make sure AWS CLI is installed before running this script...
mkdir -p ./export/js/aws
mkdir -p ./export/ts/aws

aws configure set plugins.fig fig
export PYTHONPATH=$(pwd):$PYTHONPATH


aws configure set plugins.aws_cli_plugin aws_cli_plugin
