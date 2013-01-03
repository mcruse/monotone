all: utest

LDFLAGS=-lmd5

utest: sysdep.o utest.o uuid.o namespace.o

clean:
	rm -rf *.o
	rm -rf *~
	rm -rf utest
	rm -rf nodeid # Save somewhere to ensure sequences?
	rm -rf state  # Save somewhere to ensure correctness?
