cmake_minimum_required(VERSION 3.20)
project(SoftRenderer LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# 设置变量
set(PROJ_SRC_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src")
set(OpenCV_DIR "O:/Person/Projects/CompiledProjects/opencv-4.10.0/install")
set(OpenCV_BIN_DIR "O:/Person/Projects/CompiledProjects/opencv-4.10.0/install/x64/vc17/bin")
set(EIGEN3_INCLUDE_DIR "O:/Person/Projects/CompiledProjects/eigen-3.4.0")

# 打印 opencv info
find_package(OpenCV REQUIRED)
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV include dirs: ${OpenCV_INCLUDE_DIRS}")
message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
message(STATUS "OpenCV_DIR: ${OpenCV_DIR}")

# 递归收集源与头（仅为 IDE 可见以及构建）
file(GLOB_RECURSE SRCS CONFIGURE_DEPENDS
"${PROJ_SRC_DIR}/*.cpp"
)
file(GLOB_RECURSE HDRS CONFIGURE_DEPENDS
"${PROJ_SRC_DIR}/*.h"
"${PROJ_SRC_DIR}/*.hpp"
)

# 在配置阶段检测头文件的“基名”是否唯一（不含路径）如 src/math/Vec3.hpp 与 src/geo/Vec3.hpp 会冲突
set(_name_list)
set(_dups)
function(_record_and_check files_list_var)
foreach(f IN LISTS ${files_list_var})
if(NOT EXISTS "${f}")
continue()
endif()
get_filename_component(_base "${f}" NAME) # 文件名+扩展
# 首次出现
list(FIND _name_list "${_base}" _idx)
if(_idx EQUAL -1)
list(APPEND _name_list "${_base}")
set("paths${_base}" "${f}" PARENT_SCOPE)
else()
# 冲突：累积路径并标记重复
set("paths${_base}" "${paths${_base}};${f}" PARENT_SCOPE)
list(FIND _dups "${_base}" _dup_idx)
if(_dup_idx EQUAL -1)
list(APPEND _dups "${_base}")
endif()
set(_dups "${_dups}" PARENT_SCOPE)
endif()
endforeach()
set(_name_list "${_name_list}" PARENT_SCOPE)
endfunction()

_record_and_check(SRCS)
_record_and_check(HDRS)

if(_dups)
message(STATUS "Detected duplicate file names (must be globally unique):")
foreach(n IN LISTS _dups)
message(STATUS " ${n} -> ${paths${n}}")
endforeach()
message(FATAL_ERROR "Duplicate file names detected. Please rename the conflicting files.")
endif()

if(NOT SRCS)
message(FATAL_ERROR "No source files found in ${PROJ_SRC_DIR}. Ensure your .cpp files are under this directory.")
endif()

# 收集所有包含头文件的目录，并去重
set(ALL_INCLUDE_DIRS)
foreach(h IN LISTS HDRS)
get_filename_component(h_dir "${h}" DIRECTORY)
list(APPEND ALL_INCLUDE_DIRS "${h_dir}")
endforeach()

# 加上源码根
list(APPEND ALL_INCLUDE_DIRS "${PROJ_SRC_DIR}")

# 去重
if(ALL_INCLUDE_DIRS)
list(REMOVE_DUPLICATES ALL_INCLUDE_DIRS)
endif()

# 定义可执行目标并添加文件
add_executable(SoftRenderer ${SRCS} ${HDRS})

# 将“所有头文件所在目录”加入 include 路径
target_include_directories(SoftRenderer PRIVATE ${ALL_INCLUDE_DIRS})

# 额外的库
target_include_directories(SoftRenderer PRIVATE ${OpenCV_INCLUDE_DIRS})
target_include_directories(SoftRenderer PRIVATE ${EIGEN3_INCLUDE_DIR})
target_link_libraries(SoftRenderer PRIVATE ${OpenCV_LIBS})


# 处理 opencv 的 dll 拷贝
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


# 设置 visual studio 默认启动项目
if(MSVC)
set_property(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}" PROPERTY VS_STARTUP_PROJECT SoftRenderer)
endif()