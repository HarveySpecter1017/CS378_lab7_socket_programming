ON_IP=192.168.0.110
ON_PORT=5000

MY_IP=192.168.0.110
PORT=5010

i=$1
while [[ $i -gt 0 ]]; do
    echo "./bin/vn" $ON_IP $ON_PORT $MY_IP $((PORT + i))
	./bin/vn $ON_IP $ON_PORT $MY_IP $((PORT + i)) 2> logs/vn_$i.log 1> outputs/vn_$i.txt&
    i=$((i-1))
done;
