#!/bin/bash

failure () {
    echo "$1" >&2
    exit 1
}

export _PATCH_VERSION='2'
export _PATCH_NAME='fsg-patch'
export _PATCH="${_PATCH_NAME}-${_PATCH_VERSION}"

_SELF=$(
python -c "import os
print os.path.normpath(os.path.join('$(pwd)', '$0'))
"
)

if [[ "$1" == "--make-patch" ]] || [[ "$1" == "-m" ]]
then
    case "${_PATCH_VERSION}" in
    2)  _TMPDIR="/tmp/fsg-patch.$$"
	mkdir "${_TMPDIR}"
	tar xzf fsg-patch-1.tgz -C "${_TMPDIR}"
	_WD=$(pwd)
	cd "${_TMPDIR}"
	echo "./fsg-patch-2.manifest" > fsg-patch-2.manifest
	grep -v fsg-patch-1.manifest fsg-patch-1.manifest \
	    >>fsg-patch-2.manifest 
	rm fsg-patch-1.manifest
	tar czf fsg-patch-2.tgz $(cat fsg-patch-2.manifest)
	cp fsg-patch-2.tgz "${_WD}"
	cd "${_WD}"
	rm -rf "${_TMPDIR}"
	;;
    esac
    cat "${_SELF}" "${_PATCH}".tgz >"${_PATCH}"
    chmod a+x "${_PATCH}"
    case "${_PATCH_VERSION}" in
    2)  rm fsg-patch-2.tgz
	;;
    esac
    exit 0
fi

export _PROP_FILE=/tmp/properties.$$

line_number_after () {
    local _file="$1"
    local _marker="$2"
    local _line=""
    local n=1
    cat "${_file}" | while read _line
        do n=$((n+1))
           if [[ "${_line}" == "${_marker}" ]]
           then echo $((n+1))
                exit 0
           fi
        done
}

_SKIP=$(line_number_after ${_SELF} __ARCHIVE_FOLLOWS__)

python2.2 -c "
from sys import stderr
from os import path

from mpx import properties

_PATCH_VERSION='${_PATCH_VERSION}'
_PATCH_NAME='${_PATCH_NAME}'
_PATCH='${_PATCH}'

_PROP_FILE='${_PROP_FILE}'

# Limit patch to 1.4.13 releases.
version = properties.RELEASE_VERSION.split('.')[0:3]
if (len(version) != 3) or (
    version[0] != '1') or (
    version[1] != '4') or (
    version[2] != '13'):
    raise ValueError('Unsupported version %r' % properties.COMPOUND_VERSION)

# Limit patches to builds before 1.4.13.xxx.35.
if int(properties.RELEASE_BUILD) >= 35:
    raise ValueError('Build %s includes changes in %s.',
                     (properties.COMPOUND_VERSION, _PATCH))

build_type = properties.COMPOUND_VERSION.split('.')[3]

# Only allow a patch to be applied once, do not allow older patches to be
# installed on top of newer patches.
for patch in build_type.split(','):
    if patch[0:len(_PATCH_NAME)] == _PATCH_NAME:
	patch_info = patch.split('-')
	if len(patch_info) < 2:
	    continue
        patch_version = patch_info[-1]
	if int(patch_version) >= int(_PATCH_VERSION):
            raise ValueError('Patch %r already applied!' % patch)

new_version = '%s.%s,%s.%s' % (properties.RELEASE_VERSION,
                               build_type,
                               _PATCH,
                               properties.RELEASE_BUILD)
stderr.write('Updating version from %r to %r\n' %
             (properties.COMPOUND_VERSION, new_version))
bf = open(path.join(properties.ROOT, properties.VERSION_FILE), 'r')
hf = open(path.join(properties.ROOT,
                    '%s.patched_versions' % properties.VERSION_FILE), 'a+')
old_version = bf.readline()[0:-1]
hf.write('%s patched with %s\n' % (old_version, _PATCH))
hf.close()

bf.close()
bf = open(path.join(properties.ROOT, properties.VERSION_FILE), 'w+')
bf.seek(0)
bf.truncate()
bf.write('%s\n' % new_version)
bf.close()

pf = open(_PROP_FILE, 'w+')
pf.seek(0)
pf.truncate()

for property,value in properties.as_dictionary().items():
    value = value.replace('\"', '\\\\\"')
    value = value.replace('\$', '\\\\\$')
    value = value.replace('\`', '\\\\\`')
    value = value.replace('\!', '\\\\\!')
    export_command = 'export BROADWAY_%s=\"%s\"' % (property,value)
    pf.write('%s\n' % export_command)

pf.close()
" || failure "
Error:  Could not apply ${_PATCH} current the Framework installation.
"
. $_PROP_FILE
rm $_PROP_FILE

cd ${BROADWAY_ROOT}

# Get the manifest.
_MANIFEST_FILE=./${_PATCH}.manifest
tail +${_SKIP} ${_SELF} | tar xz ./${_PATCH}.manifest

# Save old files, drop bread crumbs for new ones.
cat ${_MANIFEST_FILE} | while read _file
do
    if [ "${_file}" == "${_MANIFEST_FILE}" ] || [ ! -f "${_file}" ]
    then
	_dir=$(python2.2 -c "from os import path
print path.dirname('${_file}')")
	[ ! -d "${_dir}" ] && mkdir -p "${_dir}"
	echo "" >"${_file}"."new=${_PATCH}"
    else
	cp -f "${_file}" "${_file}"."pre=${_PATCH}"
    fi
done

# Now extract the new files.
tail +${_SKIP} ${_SELF} | tar xz

exit 0

__ARCHIVE_FOLLOWS__
