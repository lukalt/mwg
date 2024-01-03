import argparse
import json
import pathlib
import os

import allocators
from utils import parse_size
from jinja2 import Environment, FileSystemLoader
from itertools import chain

import workload_generation
import access_patterns
import utils
import instrumentation

parser = argparse.ArgumentParser(
    prog='Memory Benchmark Generator',
    description='Generate C/C++ workload for various memory access patterns and parameter configurations'
)
parser.add_argument("-o", "--output-folder",
                    default="output",
                    dest="outputFolder",
                    metavar="<output folder>",
                    type=str,
                    required=False,
                    help="Output folder the workload will be generated to")
parser.add_argument("-v", "--version", action="version", version='%(prog)s 1.0.1')
parser.add_argument("-V", "--verbose",
                    action="store_true",
                    dest="verbose",
                    help="Enables verbose logging")
parser.add_argument("-I", "--instrumentation",
                    choices=instrumentation.registered_instrumentation_methods.values(),
                    default=instrumentation.NoInstrumentation(),
                    type=instrumentation.get_registered,
                    dest="instrumentation",
                    help="Select instrumentation library to use")
parser.add_argument("-0", "--silent",
                    action="store_true",
                    dest="silent",
                    help="Disables all std output in the generator workload")
parser.add_argument("-nW", "--no-wtime-measurement",
                    action="store_false",
                    dest="wallTimeMeasure",
                    help="Does not measure the wall time of the execution")
parser.add_argument("-E", "--env", action="append",
                    metavar="<ENV_NAME>=<ENV_VALUE>",
                    dest="environmentVariables",
                    help="Specify environment variables that will be added to the run goal of the Makefile, format as ENV_NAME=ENV_VALUE")
parser.add_argument("--idle-phase", action="store", dest="idlePhase", type=int, default=-1,
                    metavar="<time in ms>",
                    help="Add an idle kernel before and after the actual compute kernel. This parameter specifies the duration of this idle phase in milliseconds")

access_args = parser.add_argument_group('Memory access settings')
access_args.add_argument("-P", "--pattern",
                         choices=access_patterns.patterns,
                         default=access_patterns.get_registered("strided-copy"),
                         type=access_patterns.get_registered,
                         dest="pattern",
                         help="The access pattern to generate")
access_args.add_argument("-S", "--size",
                         type=parse_size,
                         default="512MiB",
                         dest="size",
                         help="The size of the total memory access")
access_args.add_argument("-c", "--chunk-size",
                         type=parse_size,
                         default="1",
                         dest="chunkSize",
                         help="The chunk size of memory accesses, i.e. the number of elements accessed between a stride.")
access_args.add_argument("-s", "--stride",
                         default=1,
                         type=int,
                         dest="stride",
                         help="Stride (in elements) between consecutive chunks")
access_args.add_argument("-X", default=0, type=int, dest="arithmeticIntensity", help="Control number of floating-point operations per memory access"),
access_args.add_argument("-T", "--type",
                         choices=["float", "double", "int"],
                         default="double",
                         type=str,
                         dest="dataType",
                         help="Select the data type for all operations")

allocation_args = parser.add_argument_group("Allocation options")
allocation_args.add_argument("-A", "--allocator",
                             choices=allocators.allocators,
                             default=allocators.get_registered("stdlib"),
                             type=allocators.get_registered,
                             dest="allocator",
                             help="Allocator used to allocate buffer")
allocation_args.add_argument("-L", "--allocation-location",
                             type=str,
                             required=False,
                             dest="allocationLocation",
                             metavar="<allocation location>",
                             help="Depending on --allocator, the allocation location can be specified. For --allocator memekind, a memkind (e.g. MEMKIND_REGULAR) can be specified. For --allocator libnuma, the id of the NUMA node is used.")
allocation_args.add_argument("-a", "--alignment",
                             default=None,
                             type=utils.parse_and_assert(int, lambda x: x % 8 == 0 and x > 0),
                             dest="alignment",
                             help="Optional, memory alignment (multiple of 8)")

parallelization_args = parser.add_argument_group("Parallelization options")
parallelization_args.add_argument("-p", "--parallelize",
                                  action="store_true",
                                  required=False,
                                  dest="parallelize",
                                  help="Whether to parallelize the access using OpenMP")
parallelization_args.add_argument("-nF", "--disable-first-touch",
                                  action="store_false",
                                  dest="firstTouch",
                                  help="Disables first touch initialization")
parallelization_args.add_argument("--membind", action="store", type=str, dest="membind", metavar="<node1[,node2]..>", help="Bind allocations to a comma-seperated list of numa nodes")
parallelization_args.add_argument("--cpunodebind", action="store", type=str, dest="cpunodebind", metavar="<node1[,node2]..>", help="Bind allocations to CPUs of speciofied NUMA nodes")

compiler_args = parser.add_argument_group("Compiler options")
compiler_args.add_argument("-nM", "--no-make-file",
                           action="store_false",
                           required=False,
                           dest="createMakeFile",
                           help="Whether to generate a default make file")
compiler_args.add_argument("-O", "--optimizationLevel",
                           type=str,
                           default="2",
                           dest="optimizationLevel",
                           choices=["0", "1", "2", "3"],
                           help="Sets the optimization level for the compiler")
compiler_args.add_argument("--native",
                           action="store_true",
                           required=False,
                           dest="native",
                           help="Enabled native compilation in the Makefile (i.e., -march=native)")
compiler_args.add_argument("--compiler", dest="compiler", action="store", type=str, help="Name of the compiler executable (default: gcc)", default="gcc")
compiler_args.add_argument("--include-path", dest="includePath", action="append", type=pathlib.Path, help="Add a location to search for headers")
compiler_args.add_argument("--library-path", dest="libraryPath", action="append", type=pathlib.Path, help="Add a location to search for libraries")
args = parser.parse_args()

outputFolder = pathlib.Path(args.outputFolder)
if not outputFolder.exists() or not outputFolder.is_dir():
    outputFolder.mkdir(exist_ok=True)

config_args = dict(vars(args))
for to_remove in ["verbose", "instrumentation", "silent", "wallTimeMeasure", "createMakeFile", "includePath", "libraryPath", "outputFolder"]:
    if to_remove in config_args:
        config_args.pop(to_remove)
print("Configuration:", json.dumps(config_args, cls=utils.CustomEncoder))

base_dir = os.path.dirname(__file__)
if base_dir != "":
    base_dir = base_dir + "/"
TemplateLoader = FileSystemLoader(os.path.abspath(base_dir + "templates"))
env = Environment(loader=TemplateLoader)
print("Generating benchmark...")
template = env.get_template("main.c.j2")
with open(pathlib.Path(outputFolder, "main.c"), "w") as f:
    generatedVars = workload_generation.generate_code(args)
    f.write(template.render(generatedVars))
print("Benchmark has been written to '" + str(outputFolder) + "/main.c'")

if args.createMakeFile:
    template = env.get_template("Makefile.j2")
    print("Generating Makefile")
    make_opts = {}

    flags = []
    linkerFlags = []
    flags.append("-lm")
    flags.append("-m64")
    linkerFlags.append("-lm")
    if args.parallelize:
        flags.append("-fopenmp")
        linkerFlags.append("-fopenmp")

    for x in chain(args.allocator.get_compiler_flags(), args.instrumentation.get_linker_flags()):
        flags.append(x)
    for x in chain(args.allocator.get_linker_flags(), args.instrumentation.get_linker_flags()):
        linkerFlags.append(x)

    flags.append("-O" + args.optimizationLevel)
    if args.native:
        flags.append("-march=native")

    execPrefix = []
    if args.libraryPath is not None:
        for libPath in args.libraryPath:
            execPrefix.append(f"LD_LIBRARY_PATH={libPath}:${{LD_LIBRARY_PATH}}")
    if args.environmentVariables is not None:
        for env in args.environmentVariables:
            execPrefix.append(env)
    execPrefix = " ".join(execPrefix)
    if len(execPrefix) > 0:
        execPrefix = execPrefix + " "

    if (args.membind is not None and args.membind != "") or (args.cpunodebind is not None and args.cpunodebind != ""):
        execPrefix = execPrefix + "numactl "
        if args.membind is not None and args.membind != "":
            execPrefix = execPrefix + "-m " + args.membind + " "
        if args.cpunodebind is not None and args.cpunodebind != "":
            execPrefix = execPrefix + "-N " + args.cpunodebind + " "

    makefile_vars = {
        "FLAGS": " ".join(flags),
        "COMPILER": args.compiler,
        "LINKER_FLAGS": " ".join(linkerFlags),
        "LIBRARY_PATH": "" if args.libraryPath is None else " ".join(["-L" + str(s) for s in args.libraryPath]),
        "INCLUDE_PATH": "" if args.includePath is None else " ".join(["-I" + str(s) for s in args.includePath]),
        "EXEC_PREFIX": execPrefix
    }
    with open(pathlib.Path(outputFolder, "Makefile"), "w") as f:
        f.write(template.render(makefile_vars))
    print("Makefile has been written to '" + str(outputFolder) + "/Makefile'")
