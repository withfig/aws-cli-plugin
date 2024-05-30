import json
import re
import os.path as path
from pathlib import Path
from awscli.customizations.commands import BasicCommand
from awscli.clidriver import ServiceCommand, ServiceOperation

exportDirectory = Path("export")
exportTypescript = True


def awscli_initialize(cli):
    cli.register("building-command-table", read_commands)


def cleanDescription(text):
    # replace the final '.'
    text = re.sub("<[^<]+?>", "", text).strip().rstrip(".").strip()
    if len(text) > 0:
        # make the first char upper case
        text = text[0].upper() + text[1:]
        return text
    return None


def argumentsDictionary(args):
    flags = []
    positional = []
    for argName in args:
        arg = args[argName]
        choices = (
            arg.choices
            if arg.choices is None or isinstance(arg.choices, list)
            else list(arg.choices)
        )
        description = cleanDescription(arg.documentation)
        variadic = arg.nargs is not None and arg.nargs == "+"
        # print(arg.cli_name, arg.nargs, arg.required)
        # js = { "name": arg.cli_name, "type": arg.cli_type_name, "nargs": arg.nargs, "required":  arg.required, "documentation": arg.documentation, "suggestions": arg.choices}
        raw = {"name": arg.cli_name}

        if description is not None and len(description) > 0:
            raw["description"] = description

        if arg.positional_arg:
            if choices is not None and len(choices) > 0:
                raw["suggestions"] = choices
            # raw["isOptional"] = not arg.required
            if variadic:
                raw["isVariadic"] = variadic

            positional.append(raw)
        elif arg.cli_type_name == "boolean":
            flags.append(raw)
        else:
            raw["args"] = {"name": arg.cli_type_name}
            if choices is not None and len(choices) > 0:
                raw["args"]["suggestions"] = choices
            # raw["isOptional"] = not arg.required

            if variadic:
                raw["args"]["isVariadic"] = variadic
            flags.append(raw)

    return (flags, positional)


def generateCompletionSpecSkeleton(name, command):
    command_table = command._create_command_table()
    subcommands = []
    for operation_name in command_table:
        operation = command_table[operation_name]
        if isinstance(operation, ServiceOperation):
            (flags, args) = argumentsDictionary(operation.arg_table)
            description = cleanDescription(operation._operation_model.documentation)

            subcommand = {"name": operation_name}

            if description is not None and len(description) > 0:
                subcommand["description"] = description

            if flags is not None and len(flags) > 0:
                subcommand["options"] = flags

            if args is not None and len(args) > 0:
                subcommand["args"] = args

            subcommands.append(subcommand)

        elif isinstance(operation, BasicCommand):
            print("Basic Command:", operation_name)
            subcommands.append(parseBasicCommand(operation))

        else:
            print("Unknown command!")

    spec = {
        "name": name,
        "description": cleanDescription(command.service_model.documentation),
        "subcommands": subcommands,
    }

    return spec


def getDescription(name, description):
    value = description
    if isinstance(value, BasicCommand.FROM_FILE):
        if value.filename is not None:
            trailing_path = value.filename
        else:
            trailing_path = path.join(name, "_description" + ".rst")
        root_module = value.root_module
        doc_path = path.join(
            path.abspath(path.dirname(root_module.__file__)),
            "examples",
            trailing_path,
        )
        with open(doc_path) as f:
            return f.read()
    else:
        return value


def parseBasicCommand(command):
    print("Parsing BasicCommand: ", command.name)
    subcommands = []
    (flags, args) = argumentsDictionary(command.arg_table)

    raw_subcommands = []
    try:
        raw_subcommands = command._build_subcommand_table()
    except:  # noqa: E722
        print("Error creating subcommand table!", command.name)
    for subcommand_name in raw_subcommands:
        subcommand = raw_subcommands[subcommand_name]
        # invariant: subcommands must conform to BasicCommand
        subcommands.append(parseBasicCommand(subcommand))

    description = getDescription(command.name, command.DESCRIPTION)

    spec = {"name": command.name}

    if description is not None and len(description) > 0:
        spec["description"] = description

    if flags is not None and len(flags) > 0:
        spec["options"] = flags

    if args is not None and len(args) > 0:
        spec["args"] = args

    if subcommands is not None and len(subcommands) > 0:
        spec["subcommands"] = subcommands
    return spec


def saveJsonAsSpec(d, path):
    prefix = (
        "const completionSpec: Fig.Spec = "
        if exportTypescript
        else "var completionSpec = "
    )
    extension = ".ts" if exportTypescript else ".js"

    file_path = exportDirectory.joinpath("ts" if exportTypescript else "js").joinpath(
        f"{path}{extension}"
    )
    file_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = (
        ";\n\nexport default completionSpec;"
        if exportTypescript
        else ";\n\nmodule.exports = completionSpec;"
    )

    final = f"{prefix}{json.dumps(d, indent=4)}{suffix}"
    file_path.write_text(final)


def read_commands(command_table, session, **kwargs):
    # Confusingly, we need to subcribe to all `building-command-table` events
    # in order to get full listed of services (included customized ones like S3)
    # But we only want to actually handle "building-command-table.main"
    if kwargs["event_name"] != "building-command-table.main":
        return

    root = {"name": "aws", "subcommands": []}

    for command_name in command_table:
        command = command_table[command_name]
        if isinstance(command, ServiceCommand):
            print("ServiceCommand:", command_name)
            spec = generateCompletionSpecSkeleton(command_name, command)
            path = f"aws/{spec["name"]}"

            saveJsonAsSpec(spec, path)
            root["subcommands"].append(
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "loadSpec": path,
                }
            )
        elif isinstance(command, ServiceOperation):
            print("ServiceOperation:", command._parent_name, command_name)
        elif isinstance(command, BasicCommand):
            spec = parseBasicCommand(command)
            path = f"aws/{spec["name"]}"

            saveJsonAsSpec(spec, path)
            root["subcommands"].append(
                {
                    "name": spec["name"],
                    "description": spec["description"],
                    "loadSpec": path,
                }
            )
        else:
            print(type(command), command_name)

    print("Done!")
    saveJsonAsSpec(root, "aws")
