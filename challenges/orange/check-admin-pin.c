#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

void grant_access() {
    printf("Access granted\n");
    exit(EXIT_SUCCESS);
}

int main(int argc, char **argv, char **envp) {
    char *admin_pin_path = getenv("ADMIN_PIN_PATH");
    if (admin_pin_path == NULL) {
        fprintf(stderr, "ADMIN_PIN_PATH not set\n");
        return EXIT_FAILURE;
    }

    int admin_pin_fd = open(admin_pin_path, O_RDONLY);
    if (admin_pin_fd == -1) {
        fprintf(stderr, "Failed to open admin pin file\n");
        return EXIT_FAILURE;
    }

    char admin_pin[64];
    ssize_t bytes_read = read(admin_pin_fd, admin_pin, 32);
    if (bytes_read <= 0) {
        fprintf(stderr, "Failed to read admin pin file\n");
        return EXIT_FAILURE;
    }
    admin_pin[bytes_read] = '\0';

    char input_pin[64];
    gets(input_pin);

    if (strcmp(input_pin, admin_pin)) {
        fprintf(stderr, "Incorrect admin pin\n");
        return EXIT_FAILURE;
    }

    grant_access();
}
