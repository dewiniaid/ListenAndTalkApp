"""
Handles building the project and deploying to AWS via awsebcli
"""
import operator
import sys
import functools
import re

BUILD_INCLUDES = (
    "/application.py;/requirements.txt;+/latci/;+/client/;"
    "-__pycache__;-.*;-*.py[cod];-server.ini;+/.ebextensions/"
)

# Setup defaults
def which(executable):
    """Cheap imitation version of 'which', based off of distutils.spawn.find_executable."""
    import distutils.spawn
    return distutils.spawn.find_executable(executable)


def cmd_build(file, ini_override='deploy/server.ini', verbose=False):
    import pathlib
    import zipfile
    root = pathlib.Path('.')
    files = set()

    server_ini = root.joinpath(ini_override)
    if not server_ini.exists():
        raise RuntimeError("*** server.ini override located at {} does not exist.".format(server_ini))

    print("Building list of files to include...")

    def compile_pattern(pattern, allow_custom_op=True, default_op=operator.ior):
        if ';' in pattern:
            for subpattern in pattern.split(';'):
                yield from compile_pattern(subpattern, allow_custom_op, default_op)
            return

        if allow_custom_op and pattern[0] in '-+':
            mode, pattern = pattern[0], pattern[1:]
            op = operator.ior if mode == '+' else operator.isub
        else:
            op = default_op

        if pattern[0] != '/':
            pattern = '**/' + pattern
        else:
            pattern = pattern[1:]

        yield op, pattern
        if pattern[-1] != '/':
            pattern += '/'
        yield op, pattern + '**/*'

    for op, pattern in compile_pattern(BUILD_INCLUDES):
        files = op(files, set(root.glob(pattern)))

    print("Adding {} files to {}".format(len(files), file))
    with zipfile.ZipFile(file, mode='w', compression=zipfile.ZIP_DEFLATED) as zip:
        for path in sorted(files):
            relname = path.relative_to(root).as_posix()
            if verbose: print(relname)
            zip.write(path.as_posix(), arcname=relname)
        zip.write(server_ini.as_posix(), arcname='server.ini')
        print("Added server.ini to {} (from {})".format(file, server_ini.as_posix()))


def cmd_deploy(eb, environment, label, message):
    import datetime
    import subprocess

    now = datetime.datetime.utcnow()
    if label is None:
        label = "autobuild-" + now.strftime("%Y%m%d-%H%M%S")
        print("label is '{}'".format(label))

    if message is None:
        git = which('git')
        if git:
            git_version = subprocess.check_output(
                [git, 'describe', '--long', '--all', '--dirty'],
                universal_newlines=True
            ).strip()
            message = "Built from git {} on {}".format(git_version, now.isoformat())
        else:
            message = "Built from unknown version on {}".format(git_version, now.isoformat())
        print("message is '{}'".format(message))

    args = [eb, 'deploy']
    if environment: args.append(environment)
    args += ['-l', label, '-m', message]

    subprocess.check_call(args, stdout=sys.stdout, stderr=sys.stderr)


# build_zip('test.zip')

ebcli_path = which('eb')
#
# import sys
# argv = sys.argv[1:]
#
# if 'build' in argv:
#     cmd_build("deploy/artifact.zip", "deploy/server.ini")
#
# if 'deploy' in argv:
#


import argparse
parser = argparse.ArgumentParser(
    description='Manages latci Elastic Beanstalk deployment and builds',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    epilog=(
        "--label and --message choose defaults based on the current time and other states."
        "  At least one of the -B, -D, and -C parameters is required."
    )
)

group = parser.add_argument_group(title='Actions')
group.add_argument(
    '-B, --build', action='append_const', const='build', dest='actions',
    help='Build new artifact.'
)
group.add_argument(
    '-D, --deploy', action='append_const', const='deploy', dest='actions',
    help='Deploy an artifact.'
)
group.add_argument(
    '-C, --configure', nargs=1, metavar='FILE', dest='configure',
    help='Configures environment variables on an existing EBS instance using the [environment] section of FILE'
)

group = parser.add_argument_group(title='Settings for use with --build')
group.add_argument(
    '--artifact', nargs=1, default='deploy/artifact.zip', metavar='FILE', dest='artifact',
    help=(
        "Where the build artifact should be located.  WARNING: If changing this, it will be necessary to change"
        " settings in .elasticbeanstalk\config.yml to match."
    )
)
group.add_argument(
    '-c, --server-ini', nargs=1, default=['deploy/server.ini'], metavar='FILE', dest='server_ini',
    help="Location of server INI file to include in the build artifact."
)
group.add_argument(
    '--list-files', action='store_const', const=True, default=False, dest='list_files',
    help="List files included in build."
)
group = parser.add_argument_group(title='Settings for use with --deploy and --configure')
group.add_argument(
    '-e, --environment', nargs=1, metavar='ENVIRONMENT', dest='environment',
    help="Name of the Elastic Beanstalk environment to use.  If omitted, uses the default as determined by 'eb use'."
)
group.add_argument(
    '--eb-cli', nargs=1, metavar='PATH', dest='eb',
    help="Path to eb client", default=which('eb')
)
group = parser.add_argument_group(title='Settings for use with --deploy')
group.add_argument(
    '--label', nargs=1, metavar='LABEL', dest='label',
    help="Label name for the newly deployed version."
)
group.add_argument(
    '--message', nargs=1, metavar='MESSAGE', dest='message',
    help="Message for the newly deployed version."
)
group.add_argument(
    '--skip-build', action='store_const', const=True, default=False, dest='skip_build',
    help="Don't force a new build when deploying."
)
args = parser.parse_args()
if args.actions is None:
    args.actions = []
if args.configure:
    args.actions.append('configure')
args.actions = set(args.actions)

if not args.actions:
    print("You must specify at least one of the -B, -D and -C options.")
    sys.exit(1)

if 'deploy' in args.actions:
    if not args.skip_build:
        args.actions.add('build')

if 'build' in args.actions:
    cmd_build(args.artifact, args.server_ini[0], verbose=args.list_files)

if 'deploy' in args.actions:
    cmd_deploy(args.eb, args.environment, args.label, args.message)
