echo 'scrttv --streams.codes="*.MG01.*.*" --buffer-size=600 --debug --end-time "2023-10-07 23:59:59"'
echo 'scrttv --streams.codes="$1" --buffer-size=600 --debug --end-time "$2"'
source ~/sc3env
scrttv --streams.codes="$1" --buffer-size=600 --debug --end-time "$2" --offline
