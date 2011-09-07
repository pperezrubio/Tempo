#!/bin/bash

if [ -r novarc ]; then
  . ./novarc
elif [ -r ~/novarc ]; then
  . ~/novarc
elif [ -r /etc/novarc ]; then
  . /etc/novarc
fi

instance_uuid=$1
backup_name=$2
backup_type=$3
rotation=$4

nova --version=1.0 backup $instance_uuid $backup_name $backup_type $rotation
