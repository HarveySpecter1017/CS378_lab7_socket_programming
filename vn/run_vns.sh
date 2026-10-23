ON_IP=192.168.0.102
ON_PORT=5000

MY_IP=192.168.0.110
PORT=5010

mkdir -p outputs
mkdir -p logs
rm outputs/*
rm logs/*

BIN="./bin/vn"
i=$1

if [[ "$2" == "--debug" ]]; then
    BIN="./bin/vn_debug"
fi

while [[ $i -gt 0 ]]; do
    echo $BIN $ON_IP $ON_PORT $MY_IP $((PORT + i))
	$BIN $ON_IP $ON_PORT $MY_IP $((PORT + i)) 2> logs/vn_$i.log 1> outputs/vn_$i.txt&
    i=$((i-1))
done;
