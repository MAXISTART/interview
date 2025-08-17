cmake_minimum_required(VERSION 3.20)
project(SoftRenderer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)


set(OpenCV_DIR "H:/workArea/CompileProjects/opencv/install")
set(OpenCV_BIN_DIR "H:/workArea/CompileProjects/opencv/install/x64/vc17/bin")
set(EIGEN3_INCLUDE_DIR "H:/workArea/CompileProjects/eigen-3.4.0")

find_package(OpenCV REQUIRED)
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")
message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
message(STATUS "OpenCV_DIR: ${OpenCV_DIR}")


add_executable(SoftRenderer
src/main.cpp
)

target_include_directories(SoftRenderer PRIVATE ${OpenCV_INCLUDE_DIRS})
target_include_directories(SoftRenderer PRIVATE ${EIGEN3_INCLUDE_DIR})

target_link_libraries(SoftRenderer PRIVATE ${OpenCV_LIBS})

if(WIN32)

if(NOT DEFINED OpenCV_BIN_DIR OR OpenCV_BIN_DIR STREQUAL "")
message(FATAL_ERROR "Please configure with -DOpenCV_BIN_DIR=path/to/opencv/bin")
endif()

set(_fix_script "${CMAKE_CURRENT_BINARY_DIR}/_fixup_run.cmake")
file(WRITE "${_fix_script}" [=[

include(BundleUtilities)

if(NOT EXISTS ${APP_PATH})
  message(FATAL_ERROR "fixup_bundle: APP_PATH does not exist: ${APP_PATH}")
endif()

# 只使用用户显式提供的 OpenCV bin 目录
if(NOT EXISTS "${OpenCV_BIN_DIR_HINT}")
  message(FATAL_ERROR "fixup_bundle: OpenCV_BIN_DIR_HINT does not exist: ${OpenCV_BIN_DIR_HINT}")
endif()
set(dirs "${OpenCV_BIN_DIR_HINT}")

message(STATUS "fixup_bundle: app=${APP_PATH}")
message(STATUS "fixup_bundle: dirs='${dirs}'")

# 按需复制 DLL 到可执行目录
fixup_bundle(${APP_PATH} "" "${dirs}")

]=])

add_custom_command(TARGET SoftRenderer POST_BUILD
COMMAND ${CMAKE_COMMAND}
-DAPP_PATH=$<TARGET_FILE:SoftRenderer>
-DOpenCV_BIN_DIR_HINT=${OpenCV_BIN_DIR}
-P "${_fix_script}"
COMMENT "Fixing up runtime DLLs for $<TARGET_FILE_NAME:SoftRenderer>"
VERBATIM
)
endif()