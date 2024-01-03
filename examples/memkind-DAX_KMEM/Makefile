OBJS	= main.o
SOURCE	= main.c
HEADER	=
OUT	= main.out
CC	 = gcc
LIB      = 
INC      = 
FLAGS	 = -g -c -Wall -lm -m64 -lmemkind -O2
LFLAGS	 = -lm -lmemkind

all: $(OBJS)
	$(CC) -g $(OBJS) $(LIB) $(INC) -o $(OUT) $(LFLAGS)

main.o: main.c
	$(CC) $(FLAGS) $(LIB) $(INC) main.c -std=c11

clean:
	rm -f $(OBJS) $(OUT)

run: $(OUT)
	./$(OUT)