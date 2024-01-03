from code_generator import CodeGenerator


class Allocator:
    def initialize(self, args, generator: CodeGenerator):
        pass

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        raise NotImplementedError

    def free(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int):
        raise NotImplementedError

    def get_compiler_flags(self) -> [str]:
        return []

    def finalize(self, generator: CodeGenerator):
        pass

    def get_linker_flags(self) -> [str]:
        return []


class StdlibAllocator(Allocator):
    def initialize(self, args, generator: CodeGenerator):
        generator.include("stdlib.h", sys=True)

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        if args.alignment is None:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) malloc(sizeof({pointer_type}) * (long) {element_count});")
            if not args.silent and not silent:
                generator.add_print_statement(f"Generated unaligned buffer of size %ld elements", element_count)
        else:
            generator.add_line(f"buffer = ({pointer_type}*) aligned_alloc({args.alignment}, sizeof({pointer_type}) * (long) {element_count});")
            if not args.silent and not silent:
                generator.add_print_statement("Generated buffer aligned to " + args.s + " of size %ld", element_count)

    def free(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"free({ptr_name});")

    def __repr__(self):
        return "stdlib"


class JemallocAllocator(StdlibAllocator):
    def initialize(self, args, generator: CodeGenerator):
        generator.include("jemalloc/jemalloc.h", sys=False)

    def get_linker_flags(self) -> [str]:
        return "-ljemalloc"

    def __repr__(self):
        return "jemalloc"


class LibNumaAllocator(Allocator):
    def initialize(self, args, generator: CodeGenerator):
        if args.alignment is not None:
            raise AttributeError("Memory alignment not supported for " + repr(self))
        generator.include("numa.h", sys=True)

        # check if numa is available, otherwise fail
        generator.add_multiline_indented("""if (numa_available() == -1) {
  printf(\"err: libnuma not available\\n\");
  return 0;
}""")

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        if args.allocationLocation is None:
            raise AttributeError(f"Allocation Location '{args.allocationLocation}' is invalid. It should be the numeric index of the numa node, for example '--allocation-location 0'")

        if args.allocationLocation.isdigit():
            numa_node = int(args.allocationLocation)
            generator.add_line(f"{ptr_name} = ({pointer_type}*) numa_alloc_onnode(sizeof({pointer_type}) * (long) {element_count}, {numa_node});")
        elif args.allocationLocation == "local":
            generator.add_line(f"{ptr_name} = ({pointer_type}*) numa_alloc_local(sizeof({pointer_type}) * (long) {element_count});")
        elif args.allocationLocation == "interleaved":
            generator.add_line(f"{ptr_name} = ({pointer_type}*) numa_alloc_interleaved(sizeof({pointer_type}) * (long) {element_count});")
        else:
            raise AttributeError(f"Allocation Location '{args.allocationLocation}' is invalid. It should be the numeric index of the numa node, for example '--allocation-location 0'")

        generator.add_line(f"""if({ptr_name} == NULL) {{
  printf(\"err: failed to allocate on numa\\n\");
  return 1;
}}""")
        if not args.silent and not silent:
            generator.add_print_statement(f"Allocated {args.size} array elements using libnuma")

    def free(self, args, generator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"numa_free({ptr_name}, sizeof({pointer_type}) * {element_count});")

    def get_compiler_flags(self):
        return ["-lnuma"]

    def get_linker_flags(self):
        return ["-lnuma"]

    def __repr__(self):
        return "libnuma"


class MemkindNVMAllocator(Allocator):
    def initialize(self, args, generator: CodeGenerator):
        generator.include("memkind.h", sys=True)
        generator.include("errno.h", sys=True)
        if args.allocationLocation is None:
            generator.add_print_statement("Allocating on DRAM using memkind")
            generator.add_line("memkind_t* kind = MEMKIND_REGULAR;")
        else:
            generator.add_print_statement(f"Allocating on NVM({args.allocationLocation}) using memkind")
            generator.add_line("memkind_t* kind = memkind_t{};")
            generator.add_line(f"memkind_create_pmem (\"{args.allocationLocation}\", 0, &kind);")

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        if args.alignment is None:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) memkind_malloc(kind, sizeof({pointer_type}) * (size_t) {element_count});")
            generator.add_multiline_indented(f"""if({ptr_name} == NULL) {{
    printf(\"err: failed to allocate\\n\");
return 1;
}}""")
        else:
            generator.add_line(f"int r = memkind_posix_memalign(kind, &{ptr_name}, sizeof({pointer_type}) * (size_t) {element_count}, {args.alignment});")
            generator.add_multiline_indented("""if(r == EINVAL) {
  printf(\"err: failed to allocate (invalid input val)\\n\");
  return r;
} else if(r == ENOMEM) {
  printf(\"err: failed to allocate (no memory available)\\n\");
  return r;
} else if(r > 0) {
  printf(\"err: allocation failed: %d\\n\", r);
  return r;
}
""")
        if not args.silent and not silent:
            generator.add_print_statement(f"Allocated buffer {ptr_name} of size {element_count}")

    def free(self, args, generator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"memkind_free(kind, {ptr_name});")

    def get_linker_flags(self) -> [str]:
        return ["-lmemkind"]

    def finalize(self, generator:CodeGenerator):
        generator.add_line("memkind_finalize();")

    def __repr__(self):
        return "memkind-nvm"


class MemkindAllocator(Allocator):
    """
    Predefined memkinds: https://pmem.io/memkind/manpages/memkind.3/#kinds
    """
    def initialize(self, args, generator: CodeGenerator):
        generator.include("memkind.h", sys=True)
        generator.include("errno.h", sys=True)
        if args.allocationLocation is None:
            generator.add_print_statement("Allocating on default memkind")
            generator.add_line(f"memkind_t kind = MEMKIND_DEFAULT;")
        else:
            generator.add_line(f"memkind_t kind = {args.allocationLocation};")
            generator.add_print_statement(f"Allocating on memkind '{args.allocationLocation}'")

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        if args.alignment is None:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) memkind_malloc(kind, sizeof({pointer_type}) * (size_t) {element_count});")
            generator.add_multiline_indented(f"""if({ptr_name} == NULL) {{
        printf(\"err: failed to allocate\\n\");
    return 1;
}}""")
        else:
            generator.add_line(f"int r = memkind_posix_memalign(kind, &{ptr_name}, sizeof({pointer_type}) * (size_t) {element_count}, {args.alignment});")
            generator.add_multiline_indented("""if(r == EINVAL) {
        printf(\"err: failed to allocate (invalid input val)\\n\");
  return r;
} else if(r == ENOMEM) {
  printf(\"err: failed to allocate (no memory available)\\n\");
  return r;
} else if(r > 0) {
  printf(\"err: allocation failed: %d\\n\", r);
  return r;
}
""")
        if not args.silent and not silent:
            generator.add_print_statement(f"Allocated buffer {ptr_name} of size {element_count}")

    def free(self, args, generator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"memkind_free(kind, {ptr_name});")

    def get_compiler_flags(self) -> [str]:
        return ["-lmemkind"]

    def get_linker_flags(self) -> [str]:
        return ["-lmemkind"]

    def finalize(self, generator:CodeGenerator):
        generator.add_line("memkind_finalize();")

    def __repr__(self):
        return "memkind"


class MemkindHBWAllocator(Allocator):
    def initialize(self, args, generator: CodeGenerator):
        generator.include("hbwmalloc.h", sys=True)
        generator.include("errno.h", sys=True)

        generator.add_multiline_indented("""if(hbw_check_available() == ENODEV) {
  printf(\"err: HBW is unavailable\\n\");
  return 1;
}""")
        generator.add_line("hbw_set_policy(HBW_POLICY_BIND_ALL);")

        generator.add_print_statement(f"Allocating on MCDRAM using memkind-hbw")

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):

        if args.alignment is None:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) hbw_malloc(sizeof({pointer_type}) * (long) {element_count});")

            # check if allocation succeeded
            generator.add_multiline_indented(f"""if({ptr_name} == NULL) {{
  printf(\"err: failed to allocate '{ptr_name}' on HBW\\n\");
  return 1;
}}""")
        else:
            generator.add_line(f"int r = hbw_posix_memalign(&{pointer_type}, {args.alignment}, sizeof({pointer_type}) * (long) {element_count})")
            generator.add_multiline_indented(f"""if(r != 0) {{
              printf(\"err: failed to aligned allocate '{ptr_name}' on HBW: %d\\n\", r);
              return 1;
            }}""")

        if not args.silent and not silent:
            generator.add_print_statement(f"Allocated buffer {ptr_name} of size {element_count}")

    def free(self, args, generator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"hbw_free({ptr_name});")

    def get_linker_flags(self) -> [str]:
        return ["-lmemkind"]

    def finalize(self, generator:CodeGenerator):
        generator.add_line("memkind_finalize();")

    def __repr__(self):
        return "memkind-hbw"


class OpenMPAllocator(Allocator):
    """
    Requires OpenMP parallelization enabled with --parallelize.

    Choose on of the following allocators, e.g. "-L omp_large_cap_mem_space"
    * omp_default_mem_space The system default storage.
    * omp_large_cap_mem_space Storage with large capacity.
    * omp_const_mem_space Storage optimized for variables with constant values.
    * mp_high_bw_mem_space Storage with high bandwidth.
    * omp_low_lat_mem_space Storage with low latency.
    """
    def initialize(self, args, generator: CodeGenerator):
        generator.include("stdlib.h", sys=True)
        if not args.parallelize:
            raise ValueError("OpenMP Allocator can only be used with the --parallelize parameter")

    def allocate(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int, silent: bool = False):
        if args.alignment is None:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) omp_alloc(sizeof({pointer_type}) * (long) {element_count}, {args.allocationLocation});")
            if not args.silent and not silent:
                generator.add_print_statement(f"Generated unaligned buffer of size %ld elements", element_count)
        else:
            generator.add_line(f"{ptr_name} = ({pointer_type}*) omp_aligned_alloc({args.alignment}, sizeof({pointer_type}) * (long) {element_count}, {args.allocationLocation});")
            if not args.silent and not silent:
                generator.add_print_statement("Generated buffer aligned to " + args.s + " of size %ld", element_count)

    def free(self, args, generator: CodeGenerator, ptr_name: str, pointer_type: str, element_count: int):
        generator.add_line(f"omp_free({ptr_name}, {args.allocationLocation});")

    def __repr__(self):
        return "openmp"


allocators = [StdlibAllocator(), JemallocAllocator(), MemkindNVMAllocator(), MemkindAllocator(), MemkindHBWAllocator(), LibNumaAllocator(), OpenMPAllocator()]


def get_registered(name):
    name = name.lower()
    for allocator in allocators:
        if repr(allocator).lower() == name:
            return allocator
    return None
