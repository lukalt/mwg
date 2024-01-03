OBJS	= main.o
SOURCE	= main.c
HEADER	=
OUT	= main.out
CC	 = clang
LIB      = 
INC      = 
FLAGS	 = -g -c -Wall -lm -m64 -fopenmp -lmemkind -lpapi -O2
LFLAGS	 = -lm -fopenmp -lmemkind -lpapi

all: $(OBJS)
	$(CC) -g $(OBJS) $(LIB) $(INC) -o $(OUT) $(LFLAGS)

main.o: main.c
	$(CC) $(FLAGS) $(LIB) $(INC) main.c -std=c11

clean:
	rm -f $(OBJS) $(OUT)

run: $(OUT)
	OMP_NUM_THREADS=8 OMP_PROC_BIND=spread OMP_PLACES=cores numactl -N 1 ./$(OUT)