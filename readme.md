### AWS Plugin Scraper

This is an `aws` plugin that will generate completion specs directly from the internal represention in the AWS CLI.

1. Make sure to install the AWS CLI

2. Run `setup.sh`

3. Update variables in `fig.py`
   - `exportDirectory` should be the project directory
   - `exportTypescript` bool whether to export Typescript or Javascript

Output will be in `exports` folder, once you run any `aws` command.

### Todo

[] nargs to variadic flag
[] service descriptions
