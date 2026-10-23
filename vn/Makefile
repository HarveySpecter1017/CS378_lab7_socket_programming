bin/vn: main.c
	gcc main.c -o bin/vn

run: bin/vn
	./run_vns $(NUM_PROCS)

debug: main.c
	gcc -DDEBUG main.c -o bin/vn_debug

clean:
	rm bin/*

.PHONY:
	clean
