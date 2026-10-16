# gamohud Vulkan layer

A tiny implicit Vulkan layer that measures real in-game FPS without MangoHud.

It intercepts `vkQueuePresentKHR`, counts presented frames, computes a smoothed
frametime and writes the result roughly twice per second as JSON:

```json
{"fps": 143.7, "frametime": 6.96}
```

The destination file is taken from `GAMOHUD_FPS_FILE`, defaulting to
`$XDG_RUNTIME_DIR/gamohud-fps.json` (Unix) or `%TEMP%\gamohud-fps.json`
(Windows). The gamohud overlay reads that file via the `vulkan_layer` FPS
backend.

## Building

Requirements: a C compiler and the Vulkan headers (`vulkan/vulkan.h` and
`vulkan/vk_layer.h`).

Linux:
```
./build_layer.sh            # builds layer/build/libgamohud_layer.so
./build_layer.sh --install  # installs to ~/.local/share/vulkan/implicit_layer.d
```

Windows (Vulkan SDK required, `VULKAN_SDK` set):
```
build_layer.bat             # builds build\gamohud_layer.dll + manifest
```

CMake is also supported:
```
cmake -S . -B build && cmake --build build
```

## How the overlay uses it

When `vulkan_layer` is the selected FPS backend, `gamohud-run` / the GUI set:

```
VK_INSTANCE_LAYERS=VK_LAYER_GAMOHUD_overlay
VK_LAYER_PATH=<dir containing gamohud_layer.json>
GAMOHUD_ENABLE=1
GAMOHUD_FPS_FILE=<runtime path>
```

so only processes launched through gamohud load the layer. Applications not
launched through gamohud are unaffected (the layer's `enable_environment` gate).

## Limitations

- Measures Vulkan (and DXVK/VKD3D, which present through Vulkan) applications.
  Pure OpenGL games are not covered; use the `mesa_gallium` backend for those.
- The plugin is only active when launched through gamohud (`GAMOHUD_ENABLE=1`).
- Written against the standard loader interfaces; builds are done on a machine
  with the Vulkan SDK.
