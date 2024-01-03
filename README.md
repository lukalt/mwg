# Memory Workload Generator (MWG) v1.0.1
`mwg` is a command-line tool to generate sample code for profiling memory accesses on unix-based systems.
Based on specified arguments, the tool generates a `C` code file with corresponding `Makefile`.

The following features are supported:
* Different memory access patterns (sequential, strided, random, mixed reads/writes)
* A large variety of memory allocators (stdlib, jemalloc, libnuma, memkind-hbw, memkind-nvm, memkind (hbm,pmem,dram,numa-aware allocations etc.))
* Profiling only actual memory accesses using code instrumentation (`PAPI 7.0.0+` and `likwid` currently supported) and collection of (hardware) performance counters.
* Configurable stride, alignment, allocation size, and chunk size
* Parallelization using OpenMP and first-touch initialization
* Configuration of compiler flags (e.g., optimization level, native compilation, include and linker paths, different compilers)

## Example usages
The folder `examples` contains a set of example command-line usages with corresponding output.

## Requirements
`mwg` requires Python 3. Install requirements using `pip3 -r requirements.txt`:

## Usage
usage: Memory Benchmark Generator [-h] [-o <output folder>] [-v] [-V] [-I {papi,likwid}] [-0] [-nW] [-E <ENV_NAME>=<ENV_VALUE>] [--idle-phase <time in ms>] [-P {strided-copy,strided-scale,strided-add,strided-triad,strided-load,strided-store,random-load,random-store,random-sum,gather,scatter}] [-S SIZE]
                                  [-c CHUNKSIZE] [-s STRIDE] [-X ARITHMETICINTENSITY] [-T {float,double,int}] [-A {stdlib,jemalloc,memkind-nvm,memkind,memkind-hbw,libnuma,openmp}] [-L <allocation location>] [-a ALIGNMENT] [-p] [-nF] [--membind <node1[,node2]..>] [--cpunodebind <node1[,node2]..>] [-nM]
                                  [-O {0,1,2,3}] [--native] [--compiler COMPILER] [--include-path INCLUDEPATH] [--library-path LIBRARYPATH]

Generates C/C++ workload for various memory access patterns and parameter configurations

**options:**
  
``-h, --help ``           show this help message and exit
  
``-o <output folder>, --output-folder <output folder>``
                        Output folder the workload will be generated to
  
``-v, --version ``        show program's version number and exit
  
``-V, --verbose``         Enables verbose logging
  
``-I {papi,likwid}, --instrumentation {papi,likwid}``
                        Select instrumentation library to use
  
``-0, --silent ``         Disables all std output in the generator workload
  
``-nW, --no-wtime-measurement``
                        Does not measure the wall time of the execution
  
``-E <ENV_NAME>=<ENV_VALUE>, --env <ENV_NAME>=<ENV_VALUE>``
                        Specify environment variables that will be added to the run goal of the Makefile, format as ENV_NAME=ENV_VALUE
  
``--idle-phase <time in ms>``
                        Add an idle kernel before and after the actual compute kernel. This parameter specifies the duration of this idle phase in milliseconds

**Memory access settings:**

  ``-P {strided-copy,strided-scale,strided-add,strided-triad,strided-load,strided-store,random-load,random-store,random-sum,gather,scatter}``
                        The access pattern to generate

  ``-S SIZE``, ``--size SIZE``  The size of the total memory access

  ``-c CHUNKSIZE``, ``--chunk-size CHUNKSIZE`` The chunk size of memory accesses, i.e. the number of elements accessed between a stride.
 
 ``-s STRIDE``, ``--stride STRIDE`` Stride (in elements) between consecutive chunks
  -X ARITHMETICINTENSITY
                        Control number of floating-point operations per memory access

  ``-T {float,double,int}``, ``--type {float,double,int}`` Select the data type for all operations

**Allocation options:**

 ``-A {stdlib,jemalloc,memkind-nvm,memkind,memkind-hbw,libnuma,openmp}``, ``--allocator {stdlib,jemalloc,memkind-nvm,memkind,memkind-hbw,libnuma,openmp}`` Allocator used to allocate buffer
 
 ``-L <allocation location>``, ``--allocation-location <allocation location>`` Depending on --allocator, the allocation location can be specified. For --allocator memekind, a memkind (e.g. MEMKIND_REGULAR) can be specified. For --allocator libnuma, the id of the NUMA node is used.
  
``-a ALIGNMENT``, ``--alignment ALIGNMENT`` Optional, memory alignment (multiple of 8)

**Parallelization options:**

  ``-p, --parallelize``     Whether to parallelize the access using OpenMP

  ``-nF, --disable-first-touch``
                        Disables first touch initialization

  ``--membind <node1[,node2]..>``
                        Bind allocations to a comma-seperated list of numa nodes

  ``--cpunodebind <node1[,node2]..>``
                        Bind allocations to CPUs of speciofied NUMA nodes

**Compiler options:**

  ``-nM, --no-make-file``   Whether to generate a default make file

  ``-O {0,1,2,3}, --optimizationLevel {0,1,2,3}``
                        Sets the optimization level for the compiler

  ``--native ``             Enabled native compilation in the Makefile (i.e., ``-march=native``)

  ``--compiler COMPILER``   Name of the compiler executable (default: ``gcc``)

  ``--include-path INCLUDEPATH``
                        Add a location to search for headers

  ``--library-path LIBRARYPATH``
                        Add a location to search for libraries
