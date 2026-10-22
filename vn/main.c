#include <stddef.h>
#include <stdint.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include <time.h>

#ifdef DEBUG
#define LOG(fmt, ...) \
    fprintf(stderr, fmt, ##__VA_ARGS__);
#else
#define LOG(fmt, ...) ((void)0)
#endif

struct VN {
    char id;
    unsigned char dist;
    struct sockaddr_in addr;
};


unsigned char buf[(1 << 16)];

struct VN me;
struct VN neighbours[26];
size_t num_neighbours;

uint16_t latest_seqno[26] = {}; 
int adj[26][26] = {};
unsigned seq_no = 1;

int udp_fd;
int tcp_fd;

void print_neighbours(void) {
    printf("Update from Oracle -> %c : ", me.id + 'A');
    for (int i = 0; i < num_neighbours; i++) {
        printf("(%c : %u) ",
               neighbours[i].id + 'A',
               (unsigned int)neighbours[i].dist);
    }
    printf("\n");
    fflush(stdout);
}

void send_connect(const struct sockaddr_in* my_addr) {
    buf[0] = 1;             // type
    buf[1] = 0; buf[2] = 6; // length
    memcpy(buf + 3, &(my_addr->sin_addr.s_addr), 4);
    memcpy(buf + 7, &my_addr->sin_port, 2);
    send(tcp_fd, buf, 9, 0);
}

void recieve_link_state(){
    struct sockaddr_in addr;
    socklen_t addr_len;
    int msg_len = recvfrom(udp_fd, buf, sizeof(buf), 0, (struct sockaddr*)&addr, &addr_len);
    buf[msg_len] = 0;
    
    char id = buf[0];
    int size = buf[1];
    unsigned seq_no = ntohl(*(int*)(&buf[2]));

    LOG("Recieved Packet : %c : %u : %lu :", id + 'A', size, seq_no);
    for(int i = 0; i < size; i++) {LOG(" (%c, %d)", buf[6 + 2*i] + 'A', buf[7 + 2*i]);}
    LOG("\n");
    
    if(latest_seqno[id] >= seq_no || id == me.id)  
        return;

    latest_seqno[id] = seq_no;
    int j = 6;

    memset(&adj[id], 0, sizeof(adj[id]));
    for(int i = 0; i < size; i++){
        adj[id][buf[j]] = buf[j+1];
        j += 2;
    }

    for(int i = 0; i < num_neighbours; i++) {
        if(addr.sin_addr.s_addr != neighbours[i].addr.sin_addr.s_addr || addr.sin_port != neighbours[i].addr.sin_port) {
            sendto(udp_fd, buf, size * 2 + 6, 0, (struct sockaddr*)&neighbours[i].addr, sizeof(neighbours[i].addr));
        }
    }
}

size_t create_link_state_msg() {
    buf[0] = me.id;
    *(int*)(buf+2) = htonl(seq_no);
    unsigned char size = 6;
    
    for(int i = 0; i < num_neighbours; i++) {
        buf[size++] = neighbours[i].id;
        buf[size++] = neighbours[i].dist;
    }
    
    buf[1] = num_neighbours;
    seq_no++;
    return size;
}

void print_graph() {
    printf("[Periodic] Known Topology:\n");
    int visited[26] = {};
    int q[27], front = 0, rear = 0;

    visited[me.id] = 1;
    q[rear++] = me.id;

    while(front < rear) {
        int u = q[front++];
        printf("%c -> [", 'A' + u);
        for(int v = 0; v < 26; v++) if (adj[u][v]){
            printf("(%c, %d), ", 'A' + v, adj[u][v]);
            if(!visited[v]) {
                visited[v] = 1;
                q[rear++] = v;
            }
        }
        printf("]\n");
    }

    for(int i = 0; i < 26; i++){
        if(visited[i] == 0)
            memset(&adj[i], 0, sizeof(adj[i]));
    }
}

void update_state(){
    int read = recv(tcp_fd, buf, sizeof(buf), 0);
    if(read == 0) {
        close(tcp_fd);
        close(udp_fd);
        exit(0);
    }
    
    if(buf[0] != 2) LOG("[Error] Wrong Type Recieved\n");
    size_t length = buf[1] * 256 + buf[2];

    if(length%8 != 0) LOG("[Error] length not multiple of 8\n");
    int to_read = length - (read - 3);

    while(to_read > 0) {
        int par_read = recv(tcp_fd, buf + read, to_read, 0);

        read += par_read;
        to_read -= par_read;
    }

    unsigned char* entry = &buf[3];
    num_neighbours = 0;
    memset(&adj[me.id], 0, sizeof(adj[me.id]));
    for(int i = 0; i < length/8; i++) {
        memcpy(&neighbours[num_neighbours].addr.sin_addr.s_addr, entry, 4);
        neighbours[num_neighbours].addr.sin_port = htons(entry[4] * 256 + entry[5]);
        neighbours[num_neighbours].id = entry[6];
        neighbours[num_neighbours].dist = entry[7];

        if(entry[7] == 0) {
            memcpy(&me, &neighbours[num_neighbours], sizeof(me));
        } else {
            adj[me.id][neighbours[num_neighbours].id] = neighbours[num_neighbours].dist;
            num_neighbours++;
        }

        entry += 8;
    }
    print_neighbours();
}

void broadcast_state(){
    size_t size = create_link_state_msg();
    LOG("Broadcasting my state...\n");
    for(int i = 0; i < num_neighbours; i++) {
        sendto(udp_fd, buf, size, 0, (struct sockaddr*)&neighbours[i].addr, sizeof(neighbours[i].addr));
    }
}


int main(int argc, char** argv){
    if (argc != 5) {
        perror("Usage: ./vn oracle_ip oracle_port vn_ip vn_port\n");
        return 1;
    }
    
    struct sockaddr_in node_addr;
    
    {
        node_addr.sin_family = AF_INET;
        if(inet_pton(AF_INET, argv[3], &(node_addr.sin_addr)) != 1)
            perror("inet_pton");
        node_addr.sin_port = htons(atoi(argv[4]));
        LOG("[Info] My addr  %s:%u\n", argv[3], atoi(argv[4]));
        udp_fd = socket(AF_INET, SOCK_DGRAM, 0);
        LOG("[Info] Opening UDP socket fd=%d\n", udp_fd);
        int ret = bind(udp_fd, (struct sockaddr*) &node_addr, sizeof(node_addr));
        LOG("[Info] Binded udp socket return=%d\n", ret);
        if(ret != 0) perror("bind");
    }

    struct sockaddr_in oracle_addr;
    {
        oracle_addr.sin_family = AF_INET;
        if(inet_pton(AF_INET, argv[1], &(oracle_addr.sin_addr)) != 1)
            perror("inet_pton");
        LOG("[Info] Oracle addr  %s:%u\n", argv[1], atoi(argv[2]));
        oracle_addr.sin_port = htons(atoi(argv[2]));
        tcp_fd = socket(AF_INET, SOCK_STREAM, 0);
        LOG("[Info] Opening UDP socket fd=%d\n", udp_fd);
        LOG("[Info] Connecting to Oracle...\n");
        int ret  = connect(tcp_fd, (struct sockaddr*) &oracle_addr, sizeof(oracle_addr));
        LOG("[Info] Connection returned %d\n", ret);
        if(ret != 0) perror("connect");
    }

    send_connect(&node_addr);
    update_state();
    broadcast_state();

    
    struct timeval timeout;
    
    fd_set readfds;
    int nfds = 1 + (tcp_fd > udp_fd ? tcp_fd : udp_fd);
    while(1) {
        fflush(stdout);
        FD_ZERO(&readfds);
        FD_SET(tcp_fd, &readfds);
        FD_SET(udp_fd, &readfds);

        int active = select(nfds, &readfds, NULL, NULL, &timeout);
        if(active <= 0){
            timeout.tv_sec = 10;
            timeout.tv_usec = 10000000;
            broadcast_state();
            print_graph();
        }

        if(FD_ISSET(tcp_fd, &readfds)) {
            update_state();
            broadcast_state();
        }

        if(FD_ISSET(udp_fd, &readfds)) {
            recieve_link_state();
        }
    }
}