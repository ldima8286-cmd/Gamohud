/*
 * gamohud Vulkan layer
 * --------------------
 * A small implicit Vulkan layer that counts presented frames and publishes the
 * resulting FPS / frametime as JSON to a file, so that the gamohud overlay can
 * display real in-game frame rates without MangoHud.
 *
 * It intercepts vkQueuePresentKHR (device level) and writes stats roughly twice
 * per second to the path in the GAMOHUD_FPS_FILE environment variable (default
 * "$XDG_RUNTIME_DIR/gamohud-fps.json" on Unix, "%TEMP%\gamohud-fps.json" on
 * Windows).
 *
 * This file has been written against the standard Vulkan loader interfaces
 * (vulkan.h + vk_layer.h). It must be compiled on a machine that has a C
 * compiler and the Vulkan headers; see layer/README.md.
 */

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
static PFN_vkCreateDevice g_next_create_device = NULL;
static PFN_vkQueuePresentKHR g_next_present = NULL;

static uint64_t g_frames = 0;
static double g_last_write = 0.0;
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
    double now, dt;
    ensure_initialized();
    g_frames++;

    now = now_seconds();
    dt = now - g_last_write;
    if (dt <= 0.0)
        return;

    /* Exponential moving average of the frame time. */
    if (g_smoothed_frametime == 0.0)
        g_smoothed_frametime = dt;
    else
        g_smoothed_frametime = g_smoothed_frametime * 0.9 + dt * 0.1;

    if (dt >= 0.5) {
        double fps = (double)g_frames / dt;
        write_stats(fps, g_smoothed_frametime * 1000.0);
        g_frames = 0;
        g_last_write = now;
    }
}

/* --------------------------------------------------------------- trampolines */
GAMOHUD_EXPORT VkResult vkQueuePresentKHR_gh(VkQueue queue,
                                             const VkPresentInfoKHR *pPresentInfo)
{
    present_frame();
    if (g_next_present)
        return g_next_present(queue, pPresentInfo);
    return VK_SUCCESS;
}

static VkResult gh_CreateDevice(VkPhysicalDevice physicalDevice,
                                const VkDeviceCreateInfo *pCreateInfo,
                                const VkAllocationCallbacks *pAllocator,
                                VkDevice *pDevice)
{
    VkResult res;
    if (!g_next_create_device)
        return VK_ERROR_INITIALIZATION_FAILED;
    res = g_next_create_device(physicalDevice, pCreateInfo, pAllocator, pDevice);
    if (res == VK_SUCCESS && g_next_gdpa) {
        PFN_vkVoidFunction fn = g_next_gdpa(*pDevice, "vkQueuePresentKHR");
        g_next_present = (PFN_vkQueuePresentKHR)fn;
    }
    return res;
}

GAMOHUD_EXPORT PFN_vkVoidFunction vkGetDeviceProcAddr_gh(VkDevice device,
                                                         const char *pName)
{
    if (!pName)
        return NULL;
    if (strcmp(pName, "vkGetDeviceProcAddr") == 0)
        return (PFN_vkVoidFunction)vkGetDeviceProcAddr_gh;
    if (strcmp(pName, "vkQueuePresentKHR") == 0)
        return (PFN_vkVoidFunction)vkQueuePresentKHR_gh;
    if (g_next_gdpa)
        return g_next_gdpa(device, pName);
    return NULL;
}

GAMOHUD_EXPORT PFN_vkVoidFunction vkGetInstanceProcAddr_gh(VkInstance instance,
                                                           const char *pName)
{
    if (!pName)
        return NULL;
    if (strcmp(pName, "vkGetInstanceProcAddr") == 0)
        return (PFN_vkVoidFunction)vkGetInstanceProcAddr_gh;
    if (strcmp(pName, "vkGetDeviceProcAddr") == 0)
        return (PFN_vkVoidFunction)vkGetDeviceProcAddr_gh;
    if (strcmp(pName, "vkQueuePresentKHR") == 0)
        return (PFN_vkVoidFunction)vkQueuePresentKHR_gh;
    if (strcmp(pName, "vkCreateDevice") == 0) {
        if (g_next_gipa)
            g_next_create_device =
                (PFN_vkCreateDevice)g_next_gipa(instance, "vkCreateDevice");
        return (PFN_vkVoidFunction)gh_CreateDevice;
    }
    if (g_next_gipa)
        return g_next_gipa(instance, pName);
    return NULL;
}

GAMOHUD_EXPORT PFN_vkVoidFunction vkGetPhysicalDeviceProcAddr_gh(
    VkInstance instance, const char *pName)
{
    (void)instance;
    (void)pName;
    return NULL;
}

/* ------------------------------------------------------------- negotiation */
GAMOHUD_EXPORT VkResult vkNegotiateLoaderLayerInterfaceVersion(
    VkNegotiateLayerInterface *pVersionStruct)
{
    if (pVersionStruct == NULL ||
        pVersionStruct->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT) {
        return VK_ERROR_INITIALIZATION_FAILED;
    }

    if (pVersionStruct->loaderLayerInterfaceVersion >= 2) {
        pVersionStruct->loaderLayerInterfaceVersion = 2;
    }

    g_next_gipa = pVersionStruct->pfnNextGetInstanceProcAddr;
    g_next_gdpa = pVersionStruct->pfnNextGetDeviceProcAddr;

    pVersionStruct->pfnGetInstanceProcAddr = vkGetInstanceProcAddr_gh;
    pVersionStruct->pfnGetDeviceProcAddr = vkGetDeviceProcAddr_gh;
    pVersionStruct->pfnGetPhysicalDeviceProcAddr = vkGetPhysicalDeviceProcAddr_gh;

    return VK_SUCCESS;
}
