import utils
from code_generator import CodeGenerator
import workload_generation


class AccessPattern:
    def write_definitions(self, args, generator: CodeGenerator):
        pass

    def write_header(self, args, generator: CodeGenerator):
        pass

    def write_body(self, args, generator: CodeGenerator):
        raise NotImplementedError

    def write_footer(self, args, generator: CodeGenerator):
        pass


class StridedPattern(AccessPattern):
    def __init__(self, id):
        self.id = id.lower()
        self.unary = self.id == "copy" or self.id == "scale"

    def get_num_arrays(self):
        if self.id == "add" or self.id == "triad":
            return 3
        if self.id == "copy" or self.id == "scale":
            return 2
        return 1

    def get_output_array_names(self):
        if self.id == "add" or self.id == "triad":
            return ["C"]
        if self.id == "copy" or self.id == "scale":
            return ["B"]
        if self.id == "store":
            return ["A"]
        return []

    def get_variable_names(self):
        return ["A", "B", "C"][:self.get_num_arrays()]

    def write_header(self, args, generator: CodeGenerator):
        per_array_size = args.size // self.get_num_arrays()
        generator.add_line(
            f"long N = ((long) {args.stride}*{per_array_size})/sizeof({args.dataType});")  # compute number of elements in each array

        for var in self.get_variable_names():  # allocate all required arrays
            generator.add_line(f"{args.dataType}* {var};")
            args.allocator.allocate(args, generator, var, args.dataType, "N")
            if var not in self.get_output_array_names():
                workload_generation.write_array_initialization(args, generator, var, "N",
                                                               utils.get_number_literal(args, 0))
        generator.add_line(f"{args.dataType} temp = 0;")
        generator.add_line("temp = 1;")
        generator.include("math.h", sys=True)

    def _write_kernel_line(self, args, generator: CodeGenerator, offset: str):
        if offset != "0":
            offset = " + " + offset
        else:
            offset = ""
        if self.id == "copy":
            generator.add_line(f"B[i{offset}] = A[i{offset}];")
        elif self.id == "scale":
            generator.add_line(f"B[i{offset}] = 3 * A[i{offset}];")
        elif self.id == "add":
            generator.add_line(f"C[i{offset}] = A[i{offset}] + B[i{offset}];")
        elif self.id == "triad":
            generator.add_line(f"C[i{offset}] = A[i{offset}] + 3 * B[i{offset}];")
        elif self.id == "store":
            generator.add_line(f"A[i{offset}] = {utils.get_number_literal(args, 1)};")
        elif self.id == "load":
            generator.add_line(f"index = i{offset};")
            generator.add_line("__asm__ volatile (")
            generator.add_line("\"movq (%[array], %[index], 8), %[out]\\n\"")
            for i in range(args.arithmeticIntensity):
                generator.add_line("\"add $3, %[out]\\n\"")
            generator.add_line(": [out]\"=r\"(temp)")
            generator.add_line(": [array]\"r\"(A), [index]\"r\"(index)")
            generator.add_line(");")
        else:
            raise ValueError("Invalid operation id: " + self.id)

    def write_body(self, args, generator: CodeGenerator):
        stride = args.stride
        if args.parallelize:
            omp_flags = ""
            input_array_names = list(set(self.get_variable_names()) - set(self.get_output_array_names()))
            if len(input_array_names) > 0:
                omp_flags = f" firstprivate({', '.join(input_array_names)})"
            generator.add_line(f"#pragma omp parallel for{omp_flags} lastprivate(temp)")
        generator.add_line(f"for (int i = 0; i < N - {stride + args.chunkSize}; i += {stride + args.chunkSize - 1}) {{")
        generator.start_indent()

        if self.id == "load":
            generator.add_line("size_t index;")
        if args.chunkSize < 4:
            for i in range(args.chunkSize):
                self._write_kernel_line(args, generator, offset=str(i))
        else:
            generator.add_line(f"for (int j = 0; j < {args.chunkSize}; j += 1) {{")
            generator.start_indent()
            self._write_kernel_line(args, generator, "j")
            generator.close_indent()
            generator.add_line("}")

        generator.close_indent()
        generator.add_line("}")
        generator.add_print_statement("Temp: %f", "temp")
        generator.add_line("result = A[0]; // do not optimize away loop")

    def write_footer(self, args, generator: CodeGenerator):
        for array in self.get_variable_names():
            args.allocator.free(args, generator, array, args.dataType, "N")

    def __repr__(self):
        return f"strided-{self.id}"


class CRSSumAccessPattern(AccessPattern):

    def write_header(self, args, generator: CodeGenerator):
        generator.include("stdlib.h", sys=True)

        # three array: vals, col_index, row_index
        generator.add_line(f"int NNZ = {args.size}/sizeof({args.dataType});")  # compute number of non-zero values
        generator.add_line(f"int row_count = 64;")
        generator.add_line(f"int nnz_per_row = NNZ / row_count;")
        generator.add_line(f"int row_factor = 64;")
        generator.add_line(f"int col_count = row_factor * nnz_per_row;")  # 1/32 row utilization
        generator.add_print_statement("%d %d %d %d", "NNZ", "row_count", "nnz_per_row", "col_count")
        generator.add_line(f"{args.dataType}* vals;")
        generator.add_line(f"int* col_index;")
        generator.add_line(f"int* row_index;")

        args.allocator.allocate(args, generator, "vals", args.dataType, "NNZ")
        args.allocator.allocate(args, generator, "col_index", "int", "NNZ")
        args.allocator.allocate(args, generator, "row_index", "int", "row_count + 1")

        generator.include("time.h", sys=True)
        generator.add_multiline_indented(f"""srand(37);
for (int i = 0; i < row_count; i++) {{
    row_index[i] = i * nnz_per_row;
    int offset = 1 + (rand() % (row_factor - 1));
    for(int j = 0; j < nnz_per_row; j++) {{
        vals[i * nnz_per_row + j] = 1.337;
        col_index[i * nnz_per_row + j] = offset;
        offset += 1 + (rand() % (row_factor - 1));
    }}
}}""")
        generator.add_line("row_index[row_count] = NNZ;")
        generator.add_print_statement("Init completed")

    def write_body(self, args, generator: CodeGenerator):
        generator.add_line(f"{args.dataType} sum = 0.0;")
        if args.parallelize:
            generator.add_line("#pragma omp parallel for reduction(+:sum)")
        generator.add_multiline_indented("""for(int i = 0; i < row_count; i++) {
    for(int j = row_index[i]; j < row_index[i + 1]; j++) {
        sum += vals[col_index[j]];
    }
}""")
        generator.add_line("result = sum; // do not optimize away loop")

    def write_footer(self, args, generator: CodeGenerator):
        args.allocator.free(args, generator, "vals", args.dataType, "NNZ")
        args.allocator.free(args, generator, "col_index", "int", "NNZ")
        args.allocator.free(args, generator, "row_index", "int", "row_count + 1")

    def __repr__(self):
        return "crs-sum"


class RandomAccessPattern(AccessPattern):
    def __init__(self, sid: str):
        self.sid = sid


    def write_definitions(self, args, generator: CodeGenerator):
        generator.include("stdlib.h", sys=True)

        if args.stride != 1:
            print("warning: The stride parameter will be ignored for pointer-chasing access pattern")
        generator.add_multiline_indented("""void fisher_yates_shuffle(size_t n, size_t* a) {
    for (size_t i = n - 1; i > 0; i--) {
        size_t j = rand() % (i + 1);
        size_t tmp = a[j];
        a[j] = a[i];
        a[i] = tmp;
    }
}       
""")

    def write_header(self, args, generator: CodeGenerator):
        generator.add_line(f"size_t size = {args.size} / ({args.chunkSize} * sizeof({args.dataType}));")
        generator.add_line(f"size_t chunkSize = {args.chunkSize};")
        generator.add_line(f"size_t dataSize = size + chunkSize;")
        generator.add_line("size_t* next_indices;")
        args.allocator.allocate(args, generator, "next_indices", "size_t", "size", silent=True)
        generator.add_multiline_indented("""for(size_t i = 0; i < size; i++) {
    next_indices[i] = i;
}
fisher_yates_shuffle(size, next_indices);
""")
        generator.add_line(f"{args.dataType}* data;")
        args.allocator.allocate(args, generator, "data", args.dataType, "dataSize")
        workload_generation.write_array_initialization(args, generator, "data", "dataSize",
                                                       utils.get_number_literal(args, 1))

    def write_body(self, args, generator: CodeGenerator):
        if self.sid == "store":
            if args.parallelize:
                generator.add_multiline_indented("""#pragma omp parallel firstprivate(data, next_indices)
{
    size_t per_thread = (size / omp_get_num_threads());
    size_t offset = per_thread * omp_get_thread_num();
    for (int i = 0; i < per_thread; i++) {
        for(int j = 0; j < chunkSize; j++) {
            data[offset + j] = 3.0;
        }
        offset = next_indices[offset];
    }
}
""")
            else:
                generator.add_multiline_indented("""size_t offset = 0;
for (int i = 0; i < size; i++) {
    for(int j = 0; j < chunkSize; j++) {
        data[offset + j] = 3.0;
    }
    offset = next_indices[offset];
}
""")
        elif self.sid == "load":
            if args.parallelize:
                generator.add_multiline_indented("""#pragma omp parallel firstprivate(data, next_indices)
{
    size_t per_thread = (size / omp_get_num_threads());
    size_t offset = per_thread * omp_get_thread_num();
    for (int i = 0; i < per_thread; i++) {
        size_t index;
        for(int j = 0; j < chunkSize; j++) {
            index = offset + j;
            double val;
            __asm__ volatile (
                "movq (%[array], %[index], 8), %[out]\\n"
                : [out]"=r"(val)
                : [array]"r"(data), [index]"r"(index)
            );
        }
        offset = next_indices[offset];
    }
}
""")
            else:
                generator.add_multiline_indented("""size_t offset = 0;
for (int i = 0; i < size; i++) {
    size_t index;
    for(int j = 0; j < chunkSize; j++) {
        index = offset + j;
        double val;
        __asm__ volatile (
            "movq (%[array], %[index], 8), %[out]\\n"
            : [out]"=r"(val)
            : [array]"r"(data), [index]"r"(index)
        );
    }
    offset = next_indices[offset];
}
""")
        elif self.sid == "sum":
            generator.add_line("double sum = 0.0;")
            if args.parallelize:
                generator.add_multiline_indented("""#pragma omp parallel reduction(+:sum) firstprivate(data, next_indices)
{
    size_t per_thread = (size / omp_get_num_threads());
    size_t offset = per_thread * omp_get_thread_num();
    for (int i = 0; i < per_thread; i++) {
        for(int j = 0; j < chunkSize; j++) {
            sum += data[offset + j];
        }
        offset = next_indices[offset];
    }
}
""")
            else:
                generator.add_multiline_indented("""size_t offset = 0;
for (int i = 0; i < size; i++) {
    for(int j = 0; j < chunkSize; j++) {
        sum += data[offset + j];
    }
    offset = next_indices[offset];
}
""")
        else:
            print("err: invalid pattern", self.sid)

    def write_footer(self, args, generator: CodeGenerator):
        args.allocator.free(args, generator, "next_indices", "size_t", "size")
        args.allocator.free(args, generator, "data", args.dataType, "dataSize")

    def __repr__(self):
        return "random-" + self.sid


class GatherPattern(AccessPattern):
    def write_header(self, args, generator: CodeGenerator):
        generator.include("time.h", sys=True)
        generator.include("stdlib.h", sys=True)
        generator.add_multiline_indented("srand(37);")

        generator.add_line(
            f"long N = ((long) {args.stride}*{args.size})/sizeof({args.dataType});")  # compute number of elements in each array
        generator.add_line("long F = 1024;")
        generator.add_line("long NF = N * F;")
        generator.add_line(f"{args.dataType}* x;")
        generator.add_line(f"{args.dataType}* y;")
        generator.add_line("int* idx;")
        args.allocator.allocate(args, generator, "y", args.dataType, "NF")
        args.allocator.allocate(args, generator, "x", args.dataType, "N")
        args.allocator.allocate(args, generator, "idx", "int", "N")
        workload_generation.write_array_initialization(args, generator, "y", "NF",
                                                       utils.get_number_literal(args, 3))

        if args.parallelize:
            generator.add_line("#pragma omp parallel for shared(idx) firstprivate(N, NF)")
        generator.add_multiline_indented(f"""
for(long i = 0; i < N; i++) {{
    idx[i] = (double) (rand() % NF);
}}
""")

    def write_body(self, args, generator: CodeGenerator):
        if args.parallelize:
            generator.add_line("#pragma omp parallel for shared(x) firstprivate(y,idx, N)")
            generator.add_multiline_indented("""
for(long i = 0; i < N; i++) {
    x[i] = y[idx[i]];
}
result = x[N - 1];""")
    
    def write_footer(self, args, generator: CodeGenerator):
        args.allocator.free(args, generator, "y", args.dataType, "NF")
        args.allocator.free(args, generator, "x", args.dataType, "N")
        args.allocator.free(args, generator, "idx", "int", "N")

    def __repr__(self):
        return "gather"


class ScatterPattern(AccessPattern):
    def write_header(self, args, generator: CodeGenerator):
        generator.include("time.h", sys=True)
        generator.include("stdlib.h", sys=True)
        generator.add_multiline_indented("srand(37);")

        generator.add_line(
            f"long N = ((long) {args.stride}*{args.size})/sizeof({args.dataType});")  # compute number of elements in each array
        generator.add_line("long F = 1024;")
        generator.add_line("long NF = N * F;")

        generator.add_line(f"{args.dataType}* x;")
        generator.add_line(f"{args.dataType}* y;")
        generator.add_line("int* idx;")
        args.allocator.allocate(args, generator, "y", args.dataType, "NF")
        args.allocator.allocate(args, generator, "x", args.dataType, "N")
        args.allocator.allocate(args, generator, "idx", "int", "N")
        workload_generation.write_array_initialization(args, generator, "x", "N",
                                                       utils.get_number_literal(args, 3))
        if args.parallelize:
            generator.add_line("#pragma omp parallel for firstprivate(N, NF) shared(idx)")
        generator.add_multiline_indented(f"""for(long i = 0; i < N; i++) {{
    idx[i] = (double) (rand() % NF);
}}
""")

    def write_body(self, args, generator: CodeGenerator):
        if args.parallelize:
            generator.add_line("#pragma omp parallel for firstprivate(x,idx,N) shared(y)")
            generator.add_multiline_indented("""for(long i = 0; i < N; i++) {
    y[idx[i]] = x[i];
}
result = y[NF - 1];""")

    def write_footer(self, args, generator: CodeGenerator):
        args.allocator.free(args, generator, "y", args.dataType, "NF")
        args.allocator.free(args, generator, "x", args.dataType, "N")
        args.allocator.free(args, generator, "idx", "int", "N")

    def __repr__(self):
        return "scatter"


patterns = [
    StridedPattern(id="copy"),
    StridedPattern(id="scale"),
    StridedPattern(id="add"),
    StridedPattern(id="triad"),
    StridedPattern(id="load"),
    StridedPattern(id="store"),
    RandomAccessPattern("load"),
    RandomAccessPattern("store"),
    RandomAccessPattern("sum"),
    GatherPattern(),
    ScatterPattern()
]


def get_registered(name):
    name = name.lower()
    for pattern in patterns:
        if repr(pattern).lower() == name:
            return pattern
    return None
