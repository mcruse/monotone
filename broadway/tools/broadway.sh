# Sourceable helper functions for ash, bash and ksh.

if echo "$0" | grep -q -e '\.sh$'
then
    # Special handling to handle scary upgrade possibilities.
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

pversion () {
    cat $(proot)/BROADWAY 2>/dev/null
}

pdevdir () {
    local result=$(proot) && dirname $(dirname $result) && return 0
    return 1
}

ps1 () {
    echo -n "[$(pversion || echo \u@\h) \W] "
}

pprompt () {
    case "$1" in
    "default"|"") echo -ne "[\u@\h \W]\$ " ;;
    "version") echo -ne "[$(pversion || echo \u@\h) \W] " ;;
    esac
    return 0
}
#    *)  (echo -ne "$PS1"
#	 echo "pprompt: $1 is an invalid argument, returning PS1." >&2
#	 return 1)
#	;;

pbroadwayrc () {
    local name="$1"
    local default="$2"
    local result=""
    if [ -e ~/.pbroadwayrc ]
    then
	result=$(cat ~/.pbroadwayrc |
		    sed "s/^\W*${name}\W*=\W*\(.*\)\$/\1/g" |
		    tail -n 1)
	[ "$result" == "" ] && echo -ne $default || echo -ne $result
    else
	echo -ne $default
    fi
}

# export PS1='$(pprompt '"$(pbroadwayrc prompt)"')'

PS1="$(pprompt default)"