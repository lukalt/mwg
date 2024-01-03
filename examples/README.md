This folder includes several example usages of `mwg` with the corresponding output in the respective subfolders.

* `default`: `python3 mwg/main.py -o examples/default`
* `default-likwid`: `python3 mwg/main.py -o examples/likwid`
* `default-papi`: `python3 mwg/main.py -o examples/default-papi -I papi`
* `strided-triad-8`: `python3 mwg/main.py -o examples/strided-triad-8 --pattern strided-triad --stride 8`
* `openmp-parallel`: `python3 mwg/main.py -o examples/openmp-parallel --parallelize`
* `libnuma-node-2`: `python3 mwg/main.py -o examples/libnuma-node-2 --allocator libnuma -L 2`
* `memkind-DAX-KMEM`: `python3 mwg/main.py -o examples/memkind-DAX_KMEM --allocator memkind -L MEMKIND_DAX_KMEM`
* `memkind-LOWEST_LATENCY_LOCAL`: `python3 mwg/main.py -o examples/memkind-LOWEST_LATENCY_LOCAL --allocator memkind -L MEMKIND_LOWEST_LATENCY_LOCAL`
* `complex-example`: `$ python3 mwg/main.py -o examples/complex-example --allocator memkind -L MEMKIND_DAX_KMEM -T float --stride 8 -c 16 -a 16  --pattern strided-triad --parallelize --cpunodebind 1 --compiler clang -E OMP_NUM_THREADS=8 -E OMP_PROC_BIND=spread -E OMP_PLACES=cores -I papi`