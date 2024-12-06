#!/usr/bin/env bash

#set -eu
#set -x

function test() {

  mv_cmd="$1"

  if [ -z "$mv_cmd" ]; then
    echo "error: empty mv_cmd"
    return
  fi

  mkdir -p d1 d2

  sudo umount d2

  sudo mount -o bind d1 d2

  [ -e d1/f2 ] && mv d1/f2 d1/f1

  [ -e d1/f1 ] || touch d1/f1
  [ -e d1/s1/s2/f1 ] || {
    mkdir -p d1/s1/s2
    touch d1/s1/s2/f1
  }

  # %d     device number in decimal (st_dev)
  # %D     device number in hex (st_dev)
  # %Hd    major device number in decimal
  # %Ld    minor device number in decimal
  # %i     inode number

  function get_inode() {
    stat -c'%Hd:%Ld %i' "$1"
  }

  for subdir in . s1/s2; do

    path_1="d1/$subdir/f1"
    path_2="d2/$subdir/f2"

    inode_1=$(get_inode "$path_1")

    "$mv_cmd" "$path_1" "$path_2"

    inode_2=$(get_inode "$path_2")

    if [ "$inode_1" = "$inode_2" ]; then
      echo "ok: $mv_cmd $path_1 $path_2"
    else
      echo "fail: $mv_cmd $path_1 $path_2"
      echo "  inode_1: $inode_1"
      echo "  inode_2: $inode_2"
    fi

  done

  sudo umount d2

  mv d1/f2 d1/f1
}

test mv
test ./mv.py
