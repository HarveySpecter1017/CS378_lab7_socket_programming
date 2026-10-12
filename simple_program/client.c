#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <arpa/inet.h>


#define LISTEN_BACKLOG 50
#define PORT_SERVER 8001
#define ADDR_SERVER "10.130.154.46"

#define handle_error(msg) \
    do { perror(msg); exit(EXIT_FAILURE); } while (0)

int
main(void)
{
    int                 sfd, cfd;
    struct sockaddr_in  peer_addr;

    sfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sfd == -1)
        handle_error("socket");

    memset(&peer_addr, 0, sizeof(peer_addr));
    peer_addr.sin_family = AF_INET;
    peer_addr.sin_port   = htons(PORT_SERVER);
    peer_addr.sin_addr.s_addr   = inet_addr(ADDR_SERVER);

    cfd = connect(sfd, (struct sockaddr *) &peer_addr, sizeof(peer_addr));
    if (cfd == -1)
        handle_error("connect");
    
    printf("Connected to server at " ); printf(ADDR_SERVER); printf(":%d\n", PORT_SERVER);
    
    char recv_buf[100] = "";
    int size = recv(sfd, recv_buf, sizeof(recv_buf), 0);

    printf("Recieved from "); printf(ADDR_SERVER); printf(" :      ");
    fflush(stdout);
    write(1, recv_buf, size);
    printf("\n");

    return 0;
}