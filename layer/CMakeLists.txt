cmake_minimum_required(VERSION 3.16)
project(gamohud_layer C)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Locate the Vulkan headers (vk_layer.h ships with the loader development files).
find_path(VULKAN_INCLUDE_DIR vulkan/vulkan.h)
if(NOT VULKAN_INCLUDE_DIR)
    message(FATAL_ERROR "Vulkan headers not found (vulkan/vulkan.h). Install vulkan-headers / the Vulkan SDK.")
endif()
find_path(VULKAN_LAYER_INCLUDE_DIR vulkan/vk_layer.h)
if(NOT VULKAN_LAYER_INCLUDE_DIR)
    message(FATAL_ERROR "vk_layer.h not found. Install the Vulkan loader development files.")
endif()

add_library(gamohud_layer SHARED src/gamohud_layer.c)
target_include_directories(gamohud_layer PRIVATE ${VULKAN_INCLUDE_DIR} ${VULKAN_LAYER_INCLUDE_DIR})

set_target_properties(gamohud_layer PROPERTIES
    PREFIX ""
    OUTPUT_NAME "gamohud_layer"
    C_VISIBILITY_PRESET hidden
    POSITION_INDEPENDENT_CODE ON
)

# No dependency on the Vulkan loader itself: layers are loaded by the loader and
# resolve everything through the negotiated next-layer function pointers.
if(WIN32)
    target_compile_definitions(gamohud_layer PRIVATE WIN32_LEAN_AND_MEAN)
endif()
