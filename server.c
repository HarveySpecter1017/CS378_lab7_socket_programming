#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>

#define LISTEN_BACKLOG 50
#define MY_PORT (8001)
#define MY_ADDR ("10.130.154.45")

#define handle_error(msg) \
    do { perror(msg); exit(EXIT_FAILURE); } while (0)

int
main(void)
{
    int                 sfd, cfd;
    socklen_t           peer_addr_size;
    struct sockaddr_in  my_addr, peer_addr;

    sfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sfd == -1)
        handle_error("socket");

    memset(&my_addr, 0, sizeof(my_addr));
    my_addr.sin_family = AF_INET;
    my_addr.sin_port   = htons(MY_PORT);
    my_addr.sin_addr.s_addr = inet_addr(MY_ADDR);

    if (bind(sfd, (struct sockaddr *) &my_addr,
            sizeof(my_addr)) == -1)
        handle_error("bind");

    if (listen(sfd, LISTEN_BACKLOG) == -1)
        handle_error("listen");

    peer_addr_size = sizeof(peer_addr);
    cfd = accept(sfd, (struct sockaddr *) &peer_addr,
                &peer_addr_size);
    if (cfd == -1)
        handle_error("accept");

        
    char msg[100] = "Hello, ";
    char* ip_str = inet_ntoa(peer_addr.sin_addr);
    
    printf("Client connected : %s\n", ip_str);
    memcpy(msg + 7, ip_str, strlen(ip_str) + 1);

    printf("Sending Greetings to %s\n", ip_str);
    send(cfd, msg, strlen(msg),0);

    if (close(sfd) == -1)
        handle_error("close");
}