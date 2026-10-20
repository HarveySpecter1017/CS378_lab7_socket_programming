bin/vn: main.c
	gcc -DDEBUG main.c -o bin/vn

run: bin/vn
	./run_vns $(NUM_PROCS)

.PHONY : debug
