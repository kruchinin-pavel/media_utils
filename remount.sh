#!/bin/bash
check(){
  local cnt=`ls $1|wc -l`
  if [ "$cnt" -gt 0 ]; then
          echo $1 exist $cnt
          return 1
  fi
  return 0
}

remount(){
  echo args  "${*:2}"
  if check $1; then
          mkdir -p $1
          umount $1
          mount -t cifs $2 $1  -o username=krucpav,password=$3,noperm
  fi
}

remount_sftp(){
  if check $1; then
        mkdir -p $1
        umount $1
        sshfs -o password_stdin,allow_other,default_permissions $2 $1  <<< $3
  fi
}

date
remount_sftp "/mnt/myt_black" "krucpav@192.168.2.1:/tmp/mnt/BLACK_HDD/" pwd
