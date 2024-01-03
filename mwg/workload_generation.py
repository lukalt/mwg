from code_generator import CodeGenerator


def write_idle_kernel(args, generator: CodeGenerator, region_name: str):
    args.instrumentation.start_region(generator, region_name=region_name)
    generator.add_line(f"msleep({args.idlePhase});")
    args.instrumentation.end_region(generator, region_name=region_name)


def generate_code(args) -> dict:
    output = {}
    includes = ["<time.h>", "<errno.h>", "<stdio.h>", "<unistd.h>"]  # default imports

    header_generator = CodeGenerator(includes=includes)
    args.pattern.write_definitions(args, header_generator)
    output["HEADER"] = header_generator.get_code()

    init_generator = CodeGenerator(includes=includes)
    _write_initialization(args, generator=init_generator)
    output["BODY_initialization"] = init_generator.get_code()

    body_generator = CodeGenerator(includes=includes)
    _write_main_body(args, generator=body_generator)
    output["BODY_kernel"] = body_generator.get_code()

    finalization_generator = CodeGenerator(includes=includes)
    _write_finalization(args, generator=finalization_generator)
    output["BODY_finalization"] = finalization_generator.get_code()

    output["INCLUDES"] = includes
    return output


def write_array_initialization(args, generator, pointer_name: str, element_count: str, value: str):
    if args.parallelize and args.firstTouch:
        generator.add_line("#pragma omp parallel for")
    generator.add_line(f"for (int i = 0; i < {element_count}; i++) {{")
    generator.new_intended_block(lambda: generator.add_line(f"{pointer_name}[i] = {value};"))
    generator.add_line("}")
    if not args.silent:
        generator.add_print_statement(f"Initialization of {pointer_name} completed")


def _write_initialization(args, generator):
    if args.parallelize:
        generator.include("omp.h", sys=True)
        generator.add_line("printf(\"Using OpenMP parallel implementation with %d threads\\n\", omp_get_max_threads());")
    if not args.silent:
        generator.include("stdio.h", sys=True)

    args.allocator.initialize(args, generator)
    args.instrumentation.initialize(generator)

    if args.idlePhase > 0:
        write_idle_kernel(args, generator=generator, region_name="idle_start")
    args.pattern.write_header(args, generator)


def _write_main_body(args, generator):
    args.instrumentation.start_region(generator, region_name="main")
    generator.add_line("double result = 0.0;")
    if args.wallTimeMeasure:
        if args.parallelize:
            generator.add_line("double begin = omp_get_wtime();")
        else:
            generator.include("time.h", sys=True)
            generator.add_line("time_t begin = time(NULL);")

    args.pattern.write_body(args=args, generator=generator)

    if args.wallTimeMeasure:
        generator.add_line("double time_spent = omp_get_wtime() - begin;" if args.parallelize else "double time_spent = (double)(time(NULL) - begin);")
    args.instrumentation.end_region(generator, region_name="main")
    if args.wallTimeMeasure and not args.silent:
        generator.add_line("printf(\"Computation took: %.3fs\\n\", time_spent);")
    generator.add_print_statement("Result: %f", "result")
    if not args.silent:
        generator.add_print_statement("Workload has been completed. Cleaning up...")


def _write_finalization(args, generator):
    args.pattern.write_footer(args, generator)
    args.instrumentation.finalize(generator)
    if args.idlePhase > 0:
        write_idle_kernel(args, generator=generator, region_name="idle_end")
