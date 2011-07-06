#!/bin/bash

if [ -r novarc ]; then
  . ./novarc
elif [ -r ~/novarc ]; then
  . ~/novarc
elif [ -r /etc/novarc ]; then
  . /etc/novarc
fi

tempo-task-wrapper $1 "nova image-create $2 $3"

