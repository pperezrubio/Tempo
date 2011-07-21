#!/bin/bash

if [ -r novarc ]; then
  . ./novarc
elif [ -r ~/novarc ]; then
  . ~/novarc
elif [ -r /etc/novarc ]; then
  . /etc/novarc
fi

nova image-create $1 $2

