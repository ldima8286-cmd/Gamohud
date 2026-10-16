import ctypes as C
import json
import os
import sys
import time

LAYER = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ghlayer/libgamohud_layer.so"
FPS_FILE = "/tmp/gh_fps.json"

VK_SUCCESS = 0
ST_INSTANCE_CREATE_INFO = 1
ST_DEVICE_CREATE_INFO = 3
ST_LOADER_INSTANCE_CREATE_INFO = 47
ST_LOADER_DEVICE_CREATE_INFO = 48
LAYER_NEGOTIATE_INTERFACE_STRUCT = 1
VK_LAYER_LINK_INFO = 0

GIPA_t = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_char_p)
GDPA_t = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_char_p)
Present_t = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p)


class VkNegotiateLayerInterface(C.Structure):
    _fields_ = [
        ("sType", C.c_int),
        ("pNext", C.c_void_p),
        ("loaderLayerInterfaceVersion", C.c_uint32),
        ("pfnGetInstanceProcAddr", C.c_void_p),
        ("pfnGetDeviceProcAddr", C.c_void_p),
        ("pfnGetPhysicalDeviceProcAddr", C.c_void_p),
    ]


class VkInstanceCreateInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_int),
        ("pNext", C.c_void_p),
        ("flags", C.c_uint32),
        ("pApplicationInfo", C.c_void_p),
        ("enabledLayerCount", C.c_uint32),
        ("ppEnabledLayerNames", C.c_void_p),
        ("enabledExtensionCount", C.c_uint32),
        ("ppEnabledExtensionNames", C.c_void_p),
    ]


class VkDeviceCreateInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_int),
        ("pNext", C.c_void_p),
        ("flags", C.c_uint32),
        ("queueCreateInfoCount", C.c_uint32),
        ("pQueueCreateInfos", C.c_void_p),
        ("enabledLayerCount", C.c_uint32),
        ("ppEnabledLayerNames", C.c_void_p),
        ("enabledExtensionCount", C.c_uint32),
        ("ppEnabledExtensionNames", C.c_void_p),
        ("pEnabledFeatures", C.c_void_p),
    ]


class VkLayerInstanceLink(C.Structure):
    _fields_ = [
        ("pNext", C.c_void_p),
        ("pfnNextGetInstanceProcAddr", C.c_void_p),
        ("pfnNextGetPhysicalDeviceProcAddr", C.c_void_p),
    ]


class VkLayerDeviceLink(C.Structure):
    _fields_ = [
        ("pNext", C.c_void_p),
        ("pfnNextGetInstanceProcAddr", C.c_void_p),
        ("pfnNextGetDeviceProcAddr", C.c_void_p),
    ]


class VkLayerInstanceCreateInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_int),
        ("pNext", C.c_void_p),
        ("function", C.c_int),
        ("u", C.c_void_p),
    ]


class VkLayerDeviceCreateInfo(C.Structure):
    _fields_ = [
        ("sType", C.c_int),
        ("pNext", C.c_void_p),
        ("function", C.c_int),
        ("u", C.c_void_p),
    ]


CreateInstance_t = C.CFUNCTYPE(C.c_int, C.POINTER(VkInstanceCreateInfo), C.c_void_p, C.POINTER(C.c_void_p))
CreateDevice_t = C.CFUNCTYPE(C.c_int, C.c_void_p, C.POINTER(VkDeviceCreateInfo), C.c_void_p, C.POINTER(C.c_void_p))

# ---- fake "next layer" / driver ------------------------------------------
present_count = [0]


@CreateInstance_t
def fake_next_create_instance(ci, alloc, out):
    out[0] = 0x1234
    return VK_SUCCESS


@CreateDevice_t
def fake_next_create_device(pdev, ci, alloc, out):
    out[0] = 0x5678
    return VK_SUCCESS


@Present_t
def fake_next_present(queue, pi):
    present_count[0] += 1
    return VK_SUCCESS


@GIPA_t
def fake_gipa(instance, name):
    if name == b"vkCreateInstance":
        return C.cast(fake_next_create_instance, C.c_void_p).value
    return None


@GDPA_t
def fake_gdpa(device, name):
    if name == b"vkCreateDevice":
        return C.cast(fake_next_create_device, C.c_void_p).value
    if name == b"vkQueuePresentKHR":
        return C.cast(fake_next_present, C.c_void_p).value
    return None


def main():
    if os.path.exists(FPS_FILE):
        os.remove(FPS_FILE)
    os.environ["GAMOHUD_FPS_FILE"] = FPS_FILE

    lib = C.CDLL(LAYER)
    negotiate = C.CFUNCTYPE(C.c_int, C.POINTER(VkNegotiateLayerInterface))(
        lib.vkNegotiateLoaderLayerInterfaceVersion
    )

    ni = VkNegotiateLayerInterface()
    ni.sType = LAYER_NEGOTIATE_INTERFACE_STRUCT
    ni.loaderLayerInterfaceVersion = 2
    rc = negotiate(C.byref(ni))
    assert rc == VK_SUCCESS, f"negotiate rc={rc}"
    assert ni.loaderLayerInterfaceVersion == 2, ni.loaderLayerInterfaceVersion
    assert ni.pfnGetInstanceProcAddr and ni.pfnGetDeviceProcAddr
    print("[ok] negotiate -> version 2, GIPA/GDPA set")

    gipa = GIPA_t(ni.pfnGetInstanceProcAddr)
    gdpa = GDPA_t(ni.pfnGetDeviceProcAddr)

    ci_addr = gipa(None, b"vkCreateInstance")
    assert ci_addr, "no vkCreateInstance"
    create_instance = C.cast(ci_addr, CreateInstance_t)

    # instance create with a loader link to our fake driver
    link = VkLayerInstanceLink()
    link.pfnNextGetInstanceProcAddr = C.cast(fake_gipa, C.c_void_p)
    lici = VkLayerInstanceCreateInfo()
    lici.sType = ST_LOADER_INSTANCE_CREATE_INFO
    lici.function = VK_LAYER_LINK_INFO
    lici.u = C.cast(C.pointer(link), C.c_void_p)
    ci = VkInstanceCreateInfo()
    ci.sType = ST_INSTANCE_CREATE_INFO
    ci.pNext = C.cast(C.pointer(lici), C.c_void_p)

    inst = C.c_void_p(0)
    rc = create_instance(C.byref(ci), None, C.byref(inst))
    assert rc == VK_SUCCESS and inst.value == 0x1234, (rc, inst.value)
    print("[ok] vkCreateInstance chained -> instance 0x1234")

    cd_addr = gipa(None, b"vkCreateDevice")
    assert cd_addr, "no vkCreateDevice"
    create_device = C.cast(cd_addr, CreateDevice_t)

    dlink = VkLayerDeviceLink()
    dlink.pfnNextGetInstanceProcAddr = C.cast(fake_gipa, C.c_void_p)
    dlink.pfnNextGetDeviceProcAddr = C.cast(fake_gdpa, C.c_void_p)
    ldci = VkLayerDeviceCreateInfo()
    ldci.sType = ST_LOADER_DEVICE_CREATE_INFO
    ldci.function = VK_LAYER_LINK_INFO
    ldci.u = C.cast(C.pointer(dlink), C.c_void_p)
    dci = VkDeviceCreateInfo()
    dci.sType = ST_DEVICE_CREATE_INFO
    dci.pNext = C.cast(C.pointer(ldci), C.c_void_p)

    dev = C.c_void_p(0)
    rc = create_device(C.c_void_p(0x1), C.byref(dci), None, C.byref(dev))
    assert rc == VK_SUCCESS and dev.value == 0x5678, (rc, dev.value)
    print("[ok] vkCreateDevice chained -> device 0x5678")

    p_addr = gdpa(dev, b"vkQueuePresentKHR")
    assert p_addr, "no vkQueuePresentKHR"
    present = Present_t(p_addr)

    n = 40
    for _ in range(n):
        present(None, None)
        time.sleep(0.02)

    assert present_count[0] == n, f"next present not chained ({present_count[0]})"
    print(f"[ok] vkQueuePresentKHR intercepted & chained ({present_count[0]} calls)")

    deadline = time.time() + 2.0
    while not os.path.exists(FPS_FILE) and time.time() < deadline:
        time.sleep(0.05)
    assert os.path.exists(FPS_FILE), "no FPS file written"
    with open(FPS_FILE) as f:
        data = json.load(f)
    print(f"[ok] FPS file: {data}")
    assert 30 <= data["fps"] <= 70, f"unexpected fps {data['fps']}"
    assert data["frametime"] > 0
    print("\nALL LAYER TESTS PASSED")


if __name__ == "__main__":
    main()
