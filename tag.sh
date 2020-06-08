#!/bin/bash
input="/builds/real2u/asset-manager/__init__.py"
line=`sed "22q;d" $input`

tmp="${line%%(*}"
if [ "$tmp" != "$line" ]; then
  line=$(echo "${line:$((${#tmp}+1))}")
fi
tmp="${line%%,*}"
if [ "$tmp" != "$line" ]; then
  version0=$(echo "${line:0:$((${#tmp}))}")
  line=$(echo "${line:$((${#tmp}+2))}")
fi
tmp="${line%%,*}"
if [ "$tmp" != "$line" ]; then
  version1=$(echo "${line:0:$((${#tmp}))}")
  line=$(echo "${line:$((${#tmp}+2))}")
fi
tmp="${line%%)*}"
if [ "$tmp" != "$line" ]; then
  version2=$(echo "${line:0:$((${#tmp}))}")
fi

version="$version0.$version1.$version2"

curl -X POST --header "PRIVATE-TOKEN: ${GITLAB_TOKEN}" "https://gitlab.com/api/v4/projects/19263001/repository/tags?tag_name=${version}&ref=master&message=${version}&release_description=${version}"