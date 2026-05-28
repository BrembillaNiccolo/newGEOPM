cmake_minimum_required(VERSION 3.18)
project(aurora_bandit_agent LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# GEOPM headers + libs. Aurora's libgeopm/3.2.2 module sets GEOPM_ROOT;
# fall back to pkg-config if it's exposed.
find_package(PkgConfig)
if(PkgConfig_FOUND)
    pkg_check_modules(GEOPM IMPORTED_TARGET geopm)
endif()

if(NOT DEFINED GEOPM_PREFIX AND DEFINED ENV{GEOPM_ROOT})
    set(GEOPM_PREFIX $ENV{GEOPM_ROOT})
endif()

set(AGENT_NAME aurora_bandit)
set(AGENT_SO_NAME geopmagent_${AGENT_NAME})

# GEOPM's plugin loader only scans for files with the .so.<MAJOR>.<MINOR>.<PATCH>
# suffix matching the runtime's plugin ABI. libgeopm/3.2.2 uses .so.2.2.0.
set(AGENT_SO_FILENAME lib${AGENT_SO_NAME}.so.2.2.0)

add_library(${AGENT_SO_NAME} SHARED
    src/AuroraBanditAgent.cpp
    src/ActionGrid.cpp
    src/FeatureExtractor.cpp
    src/LinUCB.cpp
    src/MinControlGuard.cpp
)

target_include_directories(${AGENT_SO_NAME}
    PRIVATE
        include
        src
)

if(DEFINED GEOPM_PREFIX)
    target_include_directories(${AGENT_SO_NAME} PRIVATE ${GEOPM_PREFIX}/include)
    target_link_directories(${AGENT_SO_NAME} PRIVATE ${GEOPM_PREFIX}/lib)
endif()

# Do NOT link the plugin back against libgeopm; the loader dlopen()s us and
# linking back creates a circular dependency / wrong-factory issue (lesson
# from the reference power_tree_agent build.sh).
target_compile_options(${AGENT_SO_NAME} PRIVATE -O3 -Wall -Wextra -Wno-unused-parameter)

set_target_properties(${AGENT_SO_NAME} PROPERTIES
    OUTPUT_NAME ${AGENT_SO_NAME}
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
    PREFIX "lib"
    SUFFIX ".so.2.2.0"
)

# Convenience symlink lib<name>.so → lib<name>.so.2.2.0 for dlopen-by-soname users.
add_custom_command(TARGET ${AGENT_SO_NAME} POST_BUILD
    COMMAND ${CMAKE_COMMAND} -E create_symlink
            ${AGENT_SO_FILENAME}
            ${CMAKE_BINARY_DIR}/bin/lib${AGENT_SO_NAME}.so
)

install(TARGETS ${AGENT_SO_NAME} LIBRARY DESTINATION lib)
install(FILES src/action_grid_default.json DESTINATION share/aurora_bandit)
