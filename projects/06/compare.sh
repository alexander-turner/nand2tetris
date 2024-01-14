../../tools/Assembler.sh $1

BASENAME=$(basename $1 .asm)
DIRPATH=$(dirname $1)
PATH_BASENAME=$DIRPATH/$BASENAME

mv "$PATH_BASENAME.hack" "$PATH_BASENAME.my.hack"

python3 assembler.py --filepath="$1"

diff "$PATH_BASENAME.my.hack" "$PATH_BASENAME.hack"
