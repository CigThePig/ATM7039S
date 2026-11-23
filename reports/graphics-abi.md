# Graphics stack: released artifacts and source ABI

Evidence: GPU-008 and GPU-009. The existing SGX544/reMESA investigation remains applicable within its original limits. This phase adds a concrete release artifact set, not a new renderer or complete command-stream specification.

## Identified release pair

The nested ext4 `/BOOT/BATOCERA` filesystem contains `pvrsrvkm.ko` and selected ARM ELF32 graphics libraries. [The rootfs manifest](../evidence/firmware/koriki-v1.0-rootfs.json) records container hash, paths, inode numbers, component sizes/hashes, module metadata and dynamic dependencies.

| Artifact | Evidence | Development implication |
|---|---|---|
| `pvrsrvkm.ko` | vermagic 3.10.37 SMP/preempt; DRM dependency; `actions,atm7039c-gpu` alias | Candidate legacy DRM services integration, not proof of fitted GPU variant |
| `libEGL.so.1.14.3625561` | Needs libIMGegl and libc | Front-end wrapper alone is insufficient |
| `libGLESv2.so.1.14.3625561` | Needs services, IMGegl, libm, pthread, libc | Recover matching services/display dependencies before transplanting |
| `libsrv_um.so.1.14.3625561` | Needs libdrm and other system libraries | Concrete kernel/userspace services candidate |
| `libglslcompiler` / `libusc` | Versioned compiler libraries present | Open shader compilation remains a separate replacement problem |
| DDK install log | Identifies sgxddk MAIN build 3625561 | Agrees with pinned source build number; does not prove complete source identity |

GNU readelf independently reproduced module metadata and selected DT_NEEDED entries. No library was loaded, no GPU device opened, and no renderer test ran.

## Source interface map

Source locations below are all in `drivers/gpu/pvr/eurasia_km_linux`, pinned at the vendor-kernel revision and individually hashed:

| Layer | Location | Observed role |
|---|---|---|
| Transport selection | `config_kernel.h:41` | SUPPORT_DRI_DRM defined |
| DRM command wrapper | `services4/include/env/linux/pvr_drm_shared.h:47–67`; `services4/srvkm/env/linux/pvr_drm.h:130–155` | Services command identity and ioctl wrapper; configuration branches change values |
| Bridge envelope | `services4/include/pvr_bridge.h:312–322` | Bridge ID, package size, input/output pointers and lengths, services handle |
| Dispatch/access state | `services4/srvkm/env/linux/pvr_bridge_k.c:242–324` | DRM versus standalone argument path; services connection and per-process handle checks |
| SGX operations | `services4/include/sgx_bridge.h:67–98` | Kick, transfer and context operations; names alone do not define GPU packets |

The envelope's pointer/handle representation and conditional build options matter. Do not publish a universal ioctl number or a 64-bit host struct as the target ABI without compiling/checking the precise configuration. This phase does not claim a fully decoded kick structure, synchronization protocol, GPU virtual-address model, microcode image or shader ISA.

## Display is a separate dependency

Existing LCD/DE sources and DT evidence describe scanout independently of the GPU services stack. A loaded GPU driver does not establish panel power/reset, correct stride/pixel format, ownership of scanout buffers, or usable KMS support. The next useful work is to follow display buffer allocation and release lifetimes in the exact stack, then compare panel initialization and reserved memory with final boot handoff.

An independent open graphics stack still needs command/firmware/ISA/compiler understanding, tested allocation/synchronization, display integration and target observations. reMESA's SGX544 research should be compared at the specific core/DDK/platform level; support for a different PowerVR generation is not transferable by name alone.
