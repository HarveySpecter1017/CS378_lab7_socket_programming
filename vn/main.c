#include <stdio.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <arpa/inet.h>

#define ORACLE_PORT 5000

int extract_ip_addr(struct sockaddr_in* addr, char* ip_addr){
    if (inet_pton(AF_INET, ip_addr, &(addr->sin_addr)) == 1) {
        addr->sin_port = htons(ORACLE_PORT);
        return 0;
    }

    return 1;
}

int connect_to_oracle(struct sockaddr_in* addr){
    int sfd = socket(SOCK_STREAM, AF_INET, 0);
    int cfd = connect(sfd, (struct sockaddr*)addr, sizeof(struct sockaddr_in));
    return cfd;
}

int create_udp(struct sockaddr_in* addr) {
    int sfd = socket(SOCK_DGRAM, AF_INET, 0);
    if(bind(sfd, (struct sockaddr*) addr, sizeof(struct sockaddr_in)) != 0)
        return -1;
    return 0;
}

int main(int argc, char** argv){
    if (argc != 2) {
        perror("Usage: ./vn oracle_ip udp_port_vn\n");
        return 1;
    }

    struct sockaddr_in oracle_addr;
    struct sockaddr_in node_addr;

    if( extract_ip_addr(&oracle_addr, argv[1]) != 0 ){
        perror("Usage: ./vn oracle_ip udp_port_vn\n");
        return 1;
    };

    node_addr.sin_port = atoi(argv[2]);
    int fd = create_udp(&node_addr);

    if(connect_to_oracle(&oracle_addr) == 0) {
        perror("Unable to connect to Oracle.\n");
        return 1;
    };
}