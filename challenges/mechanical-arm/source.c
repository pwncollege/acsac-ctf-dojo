#include <sys/param.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

#define BUF_SIZE 0x200


struct poem_struct {
  char title[24];
  uint32_t width;
  uint32_t length;
  uint64_t content[BUF_SIZE];
};

int main();
void run_mechanical_arm();
struct poem_struct read_poem();
void read_params(struct poem_struct *poem);
void read_title(struct poem_struct* poem);
void read_content(struct poem_struct* poem);
uint64_t print_poem(struct poem_struct* poem);



void read_params(struct poem_struct *poem){
  printf("Give mechanical arm the parameters of your poem!\n");
  printf("Width(min %lu): ", sizeof(poem->title));
  scanf("%u", &poem->width);
  if(poem->width < sizeof(poem->title)){
    printf("Minimum width allowed is %lu!\n", sizeof(poem->title));
    exit(1);
  }
  printf("Length: ");
  scanf("%u", &poem->length);

  uint32_t square_size = poem->width * poem->length;

  // Check if either of values is 0. Allows poem where square_size > sizeof(content)
  // because case might occur where poem_size <= sizeof(content) < square_size
  // Handled later
  if(square_size == 0 || square_size > sizeof(poem->content) + poem->width){
    printf("Are you trying to break my mechanical arm?!\n");
    exit(1);
  }
}
void run_mechanical_arm(){
  struct poem_struct poem = read_poem();

  uint64_t num_chars = print_poem(&poem);

  printf("Character count of %s: %lu\n", poem.title, num_chars);
}

int main(){
  setbuf(stdout, NULL);

  printf("This mechanical ARM will rewrite your poem so its fancy and in its own frame!\n");
  printf("This arm accepts %lu bytes of information from the user; use this information to weave your poetic masterpiece and frame your thoughts beautifully!", sizeof(struct poem_struct));

  run_mechanical_arm();
  return 0;
}

void read_content(struct poem_struct* poem){
  char* buffer = malloc(poem->width+1);
  char* ptr = NULL;
  uint32_t line = 0;
  int32_t bytes_read = 0;

  printf("For security reasons I will read your poem line by line: ");
  for(ptr = poem->content; ptr < poem->content+BUF_SIZE && line < poem->length; line++, ptr=ptr + poem->width){
    memset(buffer, 0, poem->width+1);
    bytes_read = read(0, buffer, poem->width);
    if(((char*)buffer)[MAX(bytes_read-1, 0)] == '\n')
      ((char*)buffer)[MAX(bytes_read-1, 0)] = 0;

    // Abort memcpy if there is even a small chance that the buffer will overflow.
    // To avoid integer division issues, adds 8, ensuring that the result is rounded
    // up and 1 byte is reserved for safety.
    if(poem->content+BUF_SIZE < ptr+((bytes_read+8)/sizeof(uint64_t))){
      printf("I sense a malicious intent in this payload! Ending the process!\n");
      exit(1);
    }
    memcpy(ptr, buffer, bytes_read);
  }
}

void read_title(struct poem_struct* poem){
  int32_t bytes_read = 0;
  printf("Give your poem a title: ");
  bytes_read = read(0, poem->title, sizeof(poem->title));
  poem->title[MAX(bytes_read-1, 0)] = 0;
}

uint64_t print_poem(struct poem_struct* poem){
  uint64_t* ptr = poem->content;
  uint64_t num_chars = 0;
  printf("=");
  for(int i = 0; i < poem->width; i++) printf("-");
  printf("=\n");
  printf("|");
  for(int i = 0; i < (poem->width-strlen(poem->title))/2; i++) printf(" ");
  for(int i = 0; i < strlen(poem->title); i++) printf("%c", poem->title[i]);
  for(int i = 0; i < (poem->width-strlen(poem->title)+1)/2; i++) printf(" ");
  printf("|\n");

  printf("|");
  for(int i = 0; i < poem->width; i++) printf("-");
  printf("|\n");

  for(int i = 0; i < poem->length; i++){
    printf("|");
    uint32_t len = MIN(poem->width, strlen(ptr));
    num_chars += len;
    printf("%.*s", len, ptr);
    if(len < poem->width)
      for(int j = 0; j < poem->width - len; j++) printf("-");
    ptr = (uint64_t*)((char*)ptr + poem->width);

    printf("|\n");
  }
  printf("|");
  for(int i = 0; i < poem->width; i++) printf("_");
  printf("|\n\n");

  return num_chars;
}

// Ultra secure read
struct poem_struct read_poem(){
  struct poem_struct poem;


  read_params(&poem);

  read_title(&poem);

  read_content(&poem);

  return poem;
}









