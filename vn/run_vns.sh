ON_IP=10.51.8.215
ON_PORT=5000

MY_IP=10.51.23.153
PORT=5010

i=$1
while [[ $i -gt 0 ]]; do
    echo "./bin/vn" $ON_IP $ON_PORT $MY_IP $((PORT + i))
	./bin/vn $ON_IP $ON_PORT $MY_IP $((PORT + i)) > logs/output_$i.log &
    i=$((i-1))
done;