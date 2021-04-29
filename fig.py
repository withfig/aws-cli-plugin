import json
import re
import os
from awscli.customizations.commands import BasicCommand
from awscli.clidriver import (
    CLIDriver, ServiceCommand, ServiceOperation, CLICommand)

exportDirectory = '/Users/mschrage/fig/research/aws-cli-plugin/'
exportTypescript = True

def awscli_initialize(cli):
    cli.register("building-command-table", read_commands)
    # cli.register("building-command-table.s3", read_commands)

    # cli.register("building-command-table", read_commands)

def print_args(args):
	for argName in args:
		arg = args[argName]
		argJSON = { "name": arg.cli_name, "type": arg.cli_type_name, "nargs": arg.nargs, "required":  arg.required, "documentation": arg.documentation, "suggestions": arg.choices}

		# print(arg.cli_name, arg.cli_type_name, arg.nargs, arg.required, arg.documentation, arg.choices)

def stripHTML(text):
	return re.sub('<[^<]+?>', '', text).strip()

def argumentsDictionary(args): 
	flags = []
	positional = []
	for argName in args:
		arg = args[argName]
		choices = arg.choices if arg.choices == None or isinstance(arg.choices, list) else list(arg.choices)
		description = stripHTML(arg.documentation)
		variadic = arg.nargs != None and arg.nargs == "+"
		# print(arg.cli_name, arg.nargs, arg.required)
		# js = { "name": arg.cli_name, "type": arg.cli_type_name, "nargs": arg.nargs, "required":  arg.required, "documentation": arg.documentation, "suggestions": arg.choices}
		raw = {"name": arg.cli_name }

		if description != None and len(description) > 0:
			raw["description"] = description

		if arg.positional_arg:
			if choices != None and len(choices) > 0:
				raw["suggestions"] = choices
			# raw["isOptional"] = not arg.required 
			if variadic:
				raw["variadic"] = variadic

			positional.append(raw)
		elif arg.cli_type_name == "boolean":
			flags.append(raw)
		else:
			raw["args"] = { "name": arg.cli_type_name }
			if choices != None and len(choices) > 0:
				 raw["args"]["suggestions"] = choices
			# raw["isOptional"] = not arg.required

			if variadic:
				raw["args"]["variadic"] = variadic
			flags.append(raw)

	return (flags, positional)


def generateCompletionSpecSkeleton(name, command):


	command_table = command._create_command_table()
	subcommands = []
	for operation_name in command_table:
		# print(operation_name)
		operation = command_table[operation_name]
		if isinstance(operation, ServiceOperation):
			(flags, args) = argumentsDictionary(operation.arg_table)
			description = stripHTML(operation._operation_model.documentation)

			subcommand = { "name": operation_name} 
			
			if description != None and len(description) > 0:
				subcommand["description"] = description

			if flags != None and len(flags) > 0:
				subcommand["options"] = flags

			if args != None and len(args) > 0:
				subcommand["args"] = args

			subcommands.append(subcommand)

		elif isinstance(operation, BasicCommand):
			print("Basic Command:", operation_name)
			subcommands.append(parseBasicCommand(operation))

		else:
			print("Unknown command!")

	spec = { "name": name, "description": stripHTML(command.service_model.documentation), "subcommands": subcommands}

	# write spec to file
	return spec

def getDescription(name, description):
    value = description
    if isinstance(value, BasicCommand.FROM_FILE):
        if value.filename is not None:
            trailing_path = value.filename
        else:
            trailing_path = os.path.join(name, "_description" + '.rst')
        root_module = value.root_module
        doc_path = os.path.join(
            os.path.abspath(os.path.dirname(root_module.__file__)),
            'examples', trailing_path)
        with open(doc_path) as f:
            return f.read()
    else:
        return value

def parseBasicCommand(command):
	print("Parsing BasicCommand: ", command.name)
	# print(command.DESCRIPTION)
	subcommands = []
	(flags, args) = argumentsDictionary(command.arg_table)

	raw_subcommands = []
	try:
		raw_subcommands = command._build_subcommand_table()
	except:
		print("Error creating subcommand table!", command.name)
	for subcommand_name in raw_subcommands:
		subcommand = raw_subcommands[subcommand_name]
		# invariant: subcommands must conform to BasicCommand
		subcommands.append(parseBasicCommand(subcommand))


	description = getDescription(command.name, command.DESCRIPTION)

	spec = { "name": command.name }

	if description != None and len(description) > 0:
		spec["description"] = description

	if flags != None and len(flags) > 0:
		spec["options"] = flags

	if args != None and len(args) > 0:
		spec["args"] = args

	if subcommands != None and len(subcommands) > 0:
		spec["subcommands"] = subcommands
	return spec


def saveJsonAsSpec(d, path):
	prefix = 'export const completionSpec: Fig.Spec =' if exportTypescript else 'var completionSpec ='
	extension = '.ts' if exportTypescript else '.js'
	directory = "{}/export/{}/".format(exportDirectory, 'ts' if exportTypescript else 'js')
	final = "{} {}".format(prefix, json.dumps(d, indent=4))
	
	f = open(directory + path + extension, "w")
	f.write(final)
	f.close()

root = { "name": "aws", "subcommands": []}

def read_commands(command_table, session, **kwargs):
	# Confusingly, we need to subcribe to all `building-command-table` events
	# in order to get full listed of services (included customized ones like S3)
	# But we only want to actually handle "building-command-table.main" 
	if kwargs["event_name"] != "building-command-table.main":
		return

	for command_name in command_table:
		command = command_table[command_name]
		if isinstance(command, ServiceCommand):
			print("ServiceCommand:", command_name)

			spec = generateCompletionSpecSkeleton(command_name, command)
			path = "aws/{}".format(spec["name"])
			saveJsonAsSpec(spec, path)

			root["subcommands"].append({ "name": spec["name"], "description": spec["description"], "loadSpec": path})

		elif isinstance(command, ServiceOperation):
			print("ServiceOperation:", command._parent_name, command_name)
		elif isinstance(command, BasicCommand):
			spec = parseBasicCommand(command)
			path = "aws/{}".format(spec["name"])
			# save spec file to disk
			saveJsonAsSpec(spec, path)

			root["subcommands"].append({ "name": spec["name"], "description": spec["description"], "loadSpec": path})

		else:
			print(type(command), command_name)

	print("Done!")
	saveJsonAsSpec(root, 'aws')




