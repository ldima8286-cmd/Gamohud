/*
 * gamohud Vulkan layer
 * --------------------
 * A small implicit Vulkan layer that counts presented frames and publishes the
 * resulting FPS / frametime as JSON so that the gamohud overlay can display
 * real in-game frame rates without MangoHud.
 *
 * It intercepts vkCreateInstance / vkCreateDevice (to capture the next-layer
 * function pointers through the loader's dispatch chain) and then
 * vkQueuePresentKHR at device level, writing stats roughly twice per second to
 * the path in the GAMOHUD_FPS_FILE environment variable.
 *
 * Written against the standard Vulkan loader interfaces (vulkan.h + vk_layer.h).
 * Build it on a machine that has a C compiler and the Vulkan headers; see
 * layer/README.md.
 */

/* For clock_gettime / CLOCK_MONOTONIC under strict C99. */
#if !defined(_WIN32) && !defined(_POSIX_C_SOURCE)
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>

#if defined(_WIN32)
#define GAMOHUD_EXPORT __declspec(dllexport)
#include <windows.h>
#else
#define GAMOHUD_EXPORT __attribute__((visibility("default")))
#include <time.h>
#endif

#define GAMOHUD_LAYER_NAME "VK_LAYER_GAMOHUD_overlay"

/* ------------------------------------------------------------------ state */
static PFN_vkGetInstanceProcAddr g_next_gipa = NULL;
static PFN_vkGetDeviceProcAddr g_next_gdpa = NULL;
static PFN_vkCreateInstance g_next_create_instance = NULL;
static PFN_vkCreateDevice g_next_create_device = NULL;
static PFN_vkQueuePresentKHR g_next_present = NULL;

static uint64_t g_frames = 0;
static double g_last_write = 0.0;
static double g_last_frame = 0.0;
static double g_smoothed_frametime = 0.0; /* seconds */
static char g_fps_file[1024];
static int g_initialized = 0;

/* ------------------------------------------------------------------ timing */
static double now_seconds(void)
{
#if defined(_WIN32)
    LARGE_INTEGER freq, counter;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&counter);
    return (double)counter.QuadPart / (double)freq.QuadPart;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
#endif
}

/* ------------------------------------------------------------------ init */
static void ensure_initialized(void)
{
    const char *path;
    if (g_initialized)
        return;
    g_initialized = 1;
    g_last_write = now_seconds();
    g_last_frame = g_last_write;

    path = getenv("GAMOHUD_FPS_FILE");
    if (path && path[0]) {
        snprintf(g_fps_file, sizeof(g_fps_file), "%s", path);
        return;
    }
#if defined(_WIN32)
    {
        const char *tmp = getenv("TEMP");
        if (!tmp || !tmp[0])
            tmp = ".";
        snprintf(g_fps_file, sizeof(g_fps_file), "%s\\gamohud-fps.json", tmp);
    }
#else
    {
        const char *run = getenv("XDG_RUNTIME_DIR");
        if (run && run[0])
            snprintf(g_fps_file, sizeof(g_fps_file), "%s/gamohud-fps.json", run);
        else
            snprintf(g_fps_file, sizeof(g_fps_file), "/tmp/gamohud-fps.json");
    }
#endif
}

static void write_stats(double fps, double frametime_ms)
{
    char tmp_path[1100];
    FILE *f;
    if (!g_fps_file[0])
        return;
    snprintf(tmp_path, sizeof(tmp_path), "%s.tmp", g_fps_file);
    f = fopen(tmp_path, "w");
    if (!f)
        return;
    fprintf(f, "{\"fps\": %.1f, \"frametime\": %.2f}\n", fps, frametime_ms);
    fclose(f);
    /* Atomic-ish replace so the reader never sees a partial file. */
    remove(g_fps_file);
    rename(tmp_path, g_fps_file);
}

static void present_frame(void)
{
    double now, frame_dt, write_dt;
    ensure_initialized();
    g_frames++;

    now = now_seconds();

    /* Per-frame interval drives the frametime EMA. */
    frame_dt = now - g_last_frame;
    g_last_frame = now;
    if (frame_dt > 0.0) {
        if (g_smoothed_frametime == 0.0)
            g_smoothed_frametime = frame_dt;
        else
            g_smoothed_frametime = g_smoothed_frametime * 0.9 + frame_dt * 0.1;
    }

    write_dt = now - g_last_write;
    if (write_dt >= 0.5) {
        double fps = (double)g_frames / write_dt;
        write_stats(fps, g_smoothed_frametime * 1000.0);
        g_frames = 0;
        g_last_write = now;
    }
}

/* --------------------------------------------------------------- trampolines */
static VKAPI_ATTR VkResult VKAPI_CALL gh_QueuePresentKHR(
    VkQueue queue, const VkPresentInfoKHR *pPresentInfo)
{
    present_frame();
    if (g_next_present)
        return g_next_present(queue, pPresentInfo);
    return VK_SUCCESS;
}

static VKAPI_ATTR VkResult VKAPI_CALL gh_CreateInstance(
    const VkInstanceCreateInfo *pCreateInfo,
    const VkAllocationCallbacks *pAllocator, VkInstance *pInstance)
{
    const VkLayerInstanceCreateInfo *chain = NULL;
    const void *next = pCreateInfo ? pCreateInfo->pNext : NULL;

    while (next) {
        const VkLayerInstanceCreateInfo *info = (const VkLayerInstanceCreateInfo *)next;
        if (info->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO &&
            info->function == VK_LAYER_LINK_INFO) {
            chain = info;
            break;
        }
        next = info->pNext;
    }
    if (chain && chain->u.pLayerInfo) {
        g_next_gipa = chain->u.pLayerInfo->pfnNextGetInstanceProcAddr;
    }

    if (!g_next_gipa)
        return VK_ERROR_INITIALIZATION_FAILED;
    g_next_create_instance =
        (PFN_vkCreateInstance)g_next_gipa(VK_NULL_HANDLE, "vkCreateInstance");
    if (!g_next_create_instance)
        return VK_ERROR_INITIALIZATION_FAILED;
    return g_next_create_instance(pCreateInfo, pAllocator, pInstance);
}

static VKAPI_ATTR VkResult VKAPI_CALL gh_CreateDevice(
    VkPhysicalDevice physicalDevice, const VkDeviceCreateInfo *pCreateInfo,
    const VkAllocationCallbacks *pAllocator, VkDevice *pDevice)
{
    const VkLayerDeviceCreateInfo *chain = NULL;
    const void *next = pCreateInfo ? pCreateInfo->pNext : NULL;

    while (next) {
        const VkLayerDeviceCreateInfo *info = (const VkLayerDeviceCreateInfo *)next;
        if (info->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO &&
            info->function == VK_LAYER_LINK_INFO) {
            chain = info;
            break;
        }
        next = info->pNext;
    }
    if (chain && chain->u.pLayerInfo) {
        g_next_gdpa = chain->u.pLayerInfo->pfnNextGetDeviceProcAddr;
    }

    if (!g_next_gdpa)
        return VK_ERROR_INITIALIZATION_FAILED;
    g_next_create_device =
        (PFN_vkCreateDevice)g_next_gdpa((VkDevice)physicalDevice, "vkCreateDevice");
    if (!g_next_create_device)
        return VK_ERROR_INITIALIZATION_FAILED;

    {
        VkResult res = g_next_create_device(physicalDevice, pCreateInfo,
                                            pAllocator, pDevice);
        if (res == VK_SUCCESS) {
            g_next_present = (PFN_vkQueuePresentKHR)g_next_gdpa(*pDevice,
                                                               "vkQueuePresentKHR");
        }
        return res;
    }
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL gh_GetDeviceProcAddr(
    VkDevice device, const char *pName)
{
    if (!pName)
        return NULL;
    if (strcmp(pName, "vkGetDeviceProcAddr") == 0)
        return (PFN_vkVoidFunction)gh_GetDeviceProcAddr;
    if (strcmp(pName, "vkQueuePresentKHR") == 0)
        return (PFN_vkVoidFunction)gh_QueuePresentKHR;
    if (g_next_gdpa)
        return g_next_gdpa(device, pName);
    return NULL;
}

static VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL gh_GetInstanceProcAddr(
    VkInstance instance, const char *pName)
{
    if (!pName)
        return NULL;
    if (strcmp(pName, "vkGetInstanceProcAddr") == 0)
        return (PFN_vkVoidFunction)gh_GetInstanceProcAddr;
    if (strcmp(pName, "vkCreateInstance") == 0)
        return (PFN_vkVoidFunction)gh_CreateInstance;
    if (strcmp(pName, "vkGetDeviceProcAddr") == 0)
        return (PFN_vkVoidFunction)gh_GetDeviceProcAddr;
    if (strcmp(pName, "vkCreateDevice") == 0)
        return (PFN_vkVoidFunction)gh_CreateDevice;
    if (strcmp(pName, "vkQueuePresentKHR") == 0)
        return (PFN_vkVoidFunction)gh_QueuePresentKHR;
    if (g_next_gipa)
        return g_next_gipa(instance, pName);
    return NULL;
}

GAMOHUD_EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
vkGetInstanceProcAddr_gh(VkInstance instance, const char *pName)
{
    return gh_GetInstanceProcAddr(instance, pName);
}

GAMOHUD_EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
vkGetDeviceProcAddr_gh(VkDevice device, const char *pName)
{
    return gh_GetDeviceProcAddr(device, pName);
}

GAMOHUD_EXPORT VKAPI_ATTR PFN_vkVoidFunction VKAPI_CALL
vkGetPhysicalDeviceProcAddr_gh(VkInstance instance, const char *pName)
{
    (void)instance;
    (void)pName;
    return NULL;
}

/* ------------------------------------------------------------- negotiation */
GAMOHUD_EXPORT VKAPI_ATTR VkResult VKAPI_CALL
vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *pVersionStruct)
{
    if (pVersionStruct == NULL ||
        pVersionStruct->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT) {
        return VK_ERROR_INITIALIZATION_FAILED;
    }

    if (pVersionStruct->loaderLayerInterfaceVersion >= 2) {
        pVersionStruct->loaderLayerInterfaceVersion = 2;
    }

    pVersionStruct->pfnGetInstanceProcAddr = gh_GetInstanceProcAddr;
    pVersionStruct->pfnGetDeviceProcAddr = gh_GetDeviceProcAddr;
    pVersionStruct->pfnGetPhysicalDeviceProcAddr = vkGetPhysicalDeviceProcAddr_gh;

    return VK_SUCCESS;
}
