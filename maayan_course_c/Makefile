CC = clang
CFLAGS = -Wall -Wextra -std=c11 --target=x86_64-w64-mingw32

TARGET = hello

all: $(TARGET)

$(TARGET): main.c
	@$(CC) $(CFLAGS) -o $(TARGET) main.c
	@echo =============================================
	@./$(TARGET)

clean:
	rm -f $(TARGET)
