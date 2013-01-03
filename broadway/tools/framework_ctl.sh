#!/bin/bash

[ -x /etc/rc.d/init.d/broadway ] || {
        exit 1
}

case `basename $0` in
	startframe)
		/etc/rc.d/init.d/broadway start
		;;

	stopframe)
		/etc/rc.d/init.d/broadway stop
		;;

	restartframe)
		/etc/rc.d/init.d/broadway restart
		;;

	*)
		exit 1
		;;
esac

exit 0
