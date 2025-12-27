#include <iostream>
#include <cstring>
#include <thread>

// [HIGH-1] Global variable
int global_counter = 0;

void process_string(char* input) {
    char buffer[10];
    // [CRITICAL-7] Unsafe function (strcpy buffer overflow)
    strcpy(buffer, input);
}

void memory_issue() {
    // [CRITICAL-1] Memory Management (no check, no free)
    int* ptr = (int*)malloc(100 * sizeof(int));
    ptr[0] = 10;
    // Missing free(ptr)
}

void race_condition() {
    // [CRITICAL-3] Race condition (no mutex)
    global_counter++;
}

// [LOW-1] Bad Naming (should be CamelCase or similar standard, usually functions are verbs)
void BAD_FUNCTION_NAME() {
    // [MEDIUM-2] Magic Number
    int timeout = 3600; 
    
    // [HIGH-4] Uninitialized variable
    int x;
    if (x > 0) {
        printf("Undefined behavior");
    }
}
