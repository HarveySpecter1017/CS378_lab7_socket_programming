run: bin/vn
	./run_vns.sh $(NUM_PROCS)

run-debug: bin/vn_debug
	./run_vns.sh $(NUM_PROCS) --debug

bin/vn: main.c
	gcc main.c -o bin/vn

bin/vn_debug: main.c
	gcc -DDEBUG main.c -o bin/vn_debug

clean:
	rm bin/*

.PHONY:
	clean
