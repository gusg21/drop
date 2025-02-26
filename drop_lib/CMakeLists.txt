cmake_minimum_required(VERSION 3.21)

project(drop LANGUAGES C)

add_library(drop STATIC src/drop.c)
target_include_directories(drop PUBLIC include/)
