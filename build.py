"""
Handles building the project and deploying to AWS via awsebcli
"""
import operator
import sys
import functools
import re
import subprocess
import os
import shlex


# Setup defaults
BUILD_INCLUDES = (
    "/application.py;/requirements.txt;+/latci/;+/client/;"
    "-__pycache__;-.*;-*.py[cod];-server.ini;+/.ebextensions/"
)

def _verbose_exec(cmd, *a, _fn, **kw):
    import shlex
    print("# running: ", " ".join(shlex.quote(arg) for arg in cmd))
    _fn(cmd, *a, **kw)
check_call = functools.partial(_verbose_exec, _fn=subprocess.check_call)
check_output = functools.partial(_verbose_exec, _fn=subprocess.check_output)

std_passthru = {"stdout": sys.stdout, "stderr": sys.stderr}


def which(name, _paths=os.environ["PATH"].split(os.pathsep), _exts=os.environ.get("PATHEXT", "").split(os.pathsep)):
    """Cheap imitation version of 'which'"""
    names = [name + x for x in _exts]
    for path in _paths:
        try:
            if not os.path.exists(path):
                continue
            for name in [os.path.join(path, name) for name in names]:
                try:
                    if os.access(name, os.X_OK):
                        return name
                except:
                    pass
        except:
            pass
    return None


def cmd_setup_client(npm=None, grunt=None, bower=None):
    npm = npm or which('npm')
    grunt = grunt or which('grunt')
    bower = bower or which('bower')

    if not npm:
        print("*** Couldn't determine path to npm.")
        sys.exit(1)
    else:
        if not grunt:
            check_call([npm, 'install', '-g', 'grunt-cli'], **std_passthru)
        if not bower:
            check_call([npm, 'install', '-g', 'bower'], **std_passthru)
        check_call([npm, 'install'], **std_passthru)


def cmd_setup_server(path='venv', use_current=False):
    import pathlib

    clear_env_var = False
    try:
        # Check to see if we're in a virtual environment already
        if sys.base_prefix != sys.prefix or sys.exec_prefix != sys.base_exec_prefix or os.environ.get('VIRTUAL_ENV'):
            # Yes.
            if not use_current:
                print("I won't install packages while running within a virtual environment without the --use-current"
                      " option.")
                sys.exit(1)
            pip = which('pip')
            easy_install = which('easy_install')
            if not pip:
                print("*** Couldn't determine path to pip.")
                sys.exit(1)
            if not easy_install:
                print("*** Couldn't determine path to easy_install.")
                sys.exit(1)
        else:
            # Check to see if a venv exists
            pathobj = pathlib.Path(path)

            create = True
            if pathobj.exists():
                if len(list(pathobj.glob("**/site-packages"))):
                    print("Virtual environment appears to already exist, not creating a new one.")
                    create = False
                elif len(list(pathobj.glob("*"))):
                    print("Won't create virtual environment at {path}: Directory exists and is not empty"
                          .format(path))
                    sys.exit(1)

            import venv
            builder = venv.EnvBuilder(with_pip=True)
            if create:
                print("Creating virtual environment '{}'".format(path))
                builder.create(path)
            context = builder.ensure_directories(path)
            clear_env_var = True
            os.environ['VIRTUAL_ENV'] = context.env_dir
            pip = os.path.join(context.bin_path, 'pip')
            easy_install = os.path.join(context.bin_path, 'easy_install')
    finally:
        if clear_env_var:
            del os.environ['VIRTUAL_ENV']

    # Package installation.
    if sys.platform == 'win32':  # Yes, even on x64 it's called win32.
        print("*** You appear to be running on Windows.  Thus, it's highly likely this next\n"
              "*** command will fail.  Don't worry if it does, we'll take care of it.")
        try:
            check_call([pip, 'install', 'psycopg2'])
        except subprocess.CalledProcessError:
            url = "http://www.stickpeople.com/projects/python/win-psycopg/2.6.1/psycopg2-2.6.1.{arch}-py{major}.{minor}-pg9.4.4-release.exe"
            # Seriously, the docs suggest this to see if we're on a 64-bit platform.
            # https://docs.python.org/3/library/platform.html#module-platform
            arch = 'win-amd64' if sys.maxsize > 2**32 else 'win32'
            major, minor = sys.version_info[:2]
            if (major, minor) not in ((2,6), (2,7), (3,2), (3,3), (3,4)):
                print("*** I don't think there's a prebuilt psycopg2 package for this Python version.\n"
                      "*** Trying anyways...")
            check_call([easy_install, url.format(arch=arch, major=major, minor=minor)], **std_passthru)
    check_call([pip, 'install', '-r', 'requirements.txt'])


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

    subprocess.check_call(args, **std_passthru)


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
    '-S', '--setup', action='append_const', const='setup', dest='actions',
    help='Initialize development environment and report any problems.  Builds a virtual environment and sets up packages.'
)
group.add_argument(
    '-B', '--build', action='append_const', const='build', dest='actions',
    help='Build new artifact.'
)
group.add_argument(
    '-D', '--deploy', action='append_const', const='deploy', dest='actions',
    help='Deploy an artifact.'
)
group.add_argument(
    '-C', '--configure', nargs=1, metavar='FILE', dest='configure',
    help='Configures environment variables on an existing EBS instance using the [environment] section of FILE'
)

group = parser.add_argument_group(title='Settings for use with --setup')
mex = group.add_mutually_exclusive_group()
mex.add_argument(
    '--client-only', action='store_const', const=True, dest='skip_server', help='Skip server-side setup actions.'
)
mex.add_argument(
    '--server-only', action='store_const', const=True, dest='skip_client', help='Skip client-side setup actions.'
)
group.add_argument(
    '--with-npm', nargs=1, metavar='NPM', dest='with_npm', help='Specifies location of npm.'
)
group.add_argument(
    '--with-grunt', nargs=1, metavar='GRUNT', dest='with_grunt', help='Specifies location of grunt.'
)
group.add_argument(
    '--with-bower', nargs=1, metavar='BOWER', dest='with_bower', help='Specifies location of bower.'
)
group.add_argument(
    '--venv-path', nargs=1, metavar='VENV', dest='venv_path', help='Path to virtual environment to build.',
    default=['venv']
)
group.add_argument(
    '--use-current', action='store_const', const=True, dest='venv_use_current',
    help="Install to the current virtual environment (if we're in one)"
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
    '-c', '--server-ini', nargs=1, default=['deploy/server.ini'], metavar='FILE', dest='server_ini',
    help="Location of server INI file to include in the build artifact."
)
group.add_argument(
    '--list-files', action='store_const', const=True, default=False, dest='list_files',
    help="List files included in build."
)
group = parser.add_argument_group(title='Settings for use with --deploy and --configure')
group.add_argument(
    '-e', '--environment', nargs=1, metavar='ENVIRONMENT', dest='environment',
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
    print("You must specify at least one of the [-B, -C, -D, -S] options.")
    sys.exit(1)

def delist(arg):
    return arg[0] if arg else None

if 'setup' in args.actions:
    if not args.skip_client:
        cmd_setup_client(npm=delist(args.with_npm), bower=delist(args.with_bower), grunt=delist(args.with_grunt))
    if not args.skip_server:
        cmd_setup_server(path=delist(args.venv_path), use_current=args.venv_use_current)

if 'deploy' in args.actions:
    if not args.skip_build:
        args.actions.add('build')

if 'build' in args.actions:
    cmd_build(delist(args.artifact), delist(args.server_ini), verbose=args.list_files)

if 'deploy' in args.actions:
    cmd_deploy(delist(args.eb), delist(args.environment), delist(args.label), delist(args.message))
