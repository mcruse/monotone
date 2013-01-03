# Sourceable helper functions for ash, bash and ksh.

if echo "$0" | grep -q -e '\.sh$'
then
    case "$1" in
    install)
	# @fixme May require additional logic to support upgrades.
	;;
    revision) echo '$Revision: 20101 $-dev' |
		sed 's/\$Revision: //g' |
 		sed 's/ \$//g' ;;
    esac
    exit 0
fi

fg_color () {           # Set the character forgound color
    case "$1" in
    -h|--h|--he|--hel|--help) echo "\
fg_color: Set the foreground color to the specified ISO color.

  fg_color color

  Where color is one of:  black, red, green, yellow, blue, magenta, cyan,
                          white or default.

  Each of the colors may prefixed with the 'bright-' to select the bright
  versions of the ISO colors."
    ;;
    black) echo -e "sgr0\nsetaf 0" | tput -S ;;
    red) echo -e "sgr0\nsetaf 1" | tput -S ;;
    green) echo -e "sgr0\nsetaf 2" | tput -S ;;
    yellow) echo -e "sgr0\nsetaf 3" | tput -S ;;
    blue) echo -e "sgr0\nsetaf 4" | tput -S ;;
    magenta) echo -e "sgr0\nsetaf 5" | tput -S ;;
    cyan) echo -e "sgr0\nsetaf 6" | tput -S ;;
    white) echo -e "sgr0\nsetaf 7" | tput -S ;;
    default) echo -e "sgr0" | tput -S ;;
    bright-black) echo -e "sgr0\nbold\nsetaf 0" | tput -S ;;
    bright-red) echo -e "sgr0\nbold\nsetaf 1" | tput -S ;;
    bright-green) echo -e "sgr0\nbold\nsetaf 2" | tput -S ;;
    bright-yellow) echo -e "sgr0\nbold\nsetaf 3" | tput -S ;;
    bright-blue) echo -e "sgr0\nbold\nsetaf 4" | tput -S ;;
    bright-magenta) echo -e "sgr0\nbold\nsetaf 5" | tput -S ;;
    bright-cyan) echo -e "sgr0\nbold\nsetaf 6" | tput -S ;;
    bright-white) echo -e "sgr0\nbold\nsetaf 7" | tput -S ;;
    "") echo "fg_color:  Requires an argument, try --help." >&2 ;;
    *) echo "fg_color:  Unknown argument $1, try --help." >&2 ;;
    esac
}

bg_color () {           # Set the character forgound color
    case "$1" in
    -h|--h|--he|--hel|--help) echo "\
bg_color: Set the foreground color to the specified ISO color.

  bg_color color

  Where color is one of:  black, red, green, yellow, blue, magenta, cyan,
                          white or default.

  Each of the colors may prefixed with the 'bright-' to select the bright
  versions of the ISO colors."
    ;;
    
    black) echo -e "sgr0\nsetab 0" | tput -S ;;
    red) echo -e "sgr0\nsetab 1" | tput -S ;;
    green) echo -e "sgr0\nsetab 2" | tput -S ;;
    yellow) echo -e "sgr0\nsetab 3" | tput -S ;;
    blue) echo -e "sgr0\nsetab 4" | tput -S ;;
    magenta) echo -e "sgr0\nsetab 5" | tput -S ;;
    cyan) echo -e "sgr0\nsetab 6" | tput -S ;;
    white) echo -e "sgr0\nsetab 7" | tput -S ;;
    default) echo -e "sgr0" | tput -S ;;
    bright-black) echo -e "sgr0\nbold\nsetab 0" | tput -S ;;
    bright-red) echo -e "sgr0\nbold\nsetab 1" | tput -S ;;
    bright-green) echo -e "sgr0\nbold\nsetab 2" | tput -S ;;
    bright-yellow) echo -e "sgr0\nbold\nsetab 3" | tput -S ;;
    bright-blue) echo -e "sgr0\nbold\nsetab 4" | tput -S ;;
    bright-magenta) echo -e "sgr0\nbold\nsetab 5" | tput -S ;;
    bright-cyan) echo -e "sgr0\nbold\nsetab 6" | tput -S ;;
    bright-white) echo -e "sgr0\nbold\nsetab 7" | tput -S ;;
    "") echo "bg_color:  Requires an argument, try --help." >&2 ;;
    *) echo "bg_color:  Unknown argument $1, try --help." >&2 ;;
    esac
}
