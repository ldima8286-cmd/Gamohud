# Simple makefile for the gamohud Vulkan layer.
#
#   make            build libgamohud_layer.so
#   make install    install into ~/.local/share/vulkan/implicit_layer.d
#   make clean
#
CC      ?= cc
CFLAGS  ?= -O2 -fPIC -Wall -Wextra -std=c99
LDFLAGS ?= -shared

# Use pkg-config for Vulkan headers when available, otherwise include common dirs.
VK_CFLAGS := $(shell pkg-config --cflags vulkan 2>/dev/null)
ifeq ($(VK_CFLAGS),)
VK_CFLAGS := -I/usr/include
endif

TARGET  := libgamohud_layer.so
SRC     := src/gamohud_layer.c
PREFIX  ?= $(HOME)/.local
IMPLDIR := $(PREFIX)/share/vulkan/implicit_layer.d

.PHONY: all install clean

all: $(TARGET) gamohud_layer.json

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(VK_CFLAGS) $(LDFLAGS) -o $@ $<

gamohud_layer.json: gamohud_layer.json
	@true

install: all
	mkdir -p $(IMPLDIR)
	cp $(TARGET) $(IMPLDIR)/
	cp gamohud_layer.json $(IMPLDIR)/
	@echo "Installed layer to $(IMPLDIR)"

clean:
	rm -f $(TARGET)
