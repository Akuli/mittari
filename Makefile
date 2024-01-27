CFLAGS += -g -Wall -Wextra -Wpedantic -std=c99
LDFLAGS += -lm

all: mittari

mittari: mittari.c
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)
