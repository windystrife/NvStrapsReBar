// Linux type-compatibility shim for the shared NvStrapsReBar DXE/tool sources.
//
// On UEFI these types come from <Uefi.h>; on Windows from <windef.h>.  This
// header provides the same fixed-width aliases in terms of <stdint.h> so the
// shared C code can be built natively on Linux (as part of the ReBarState tool).
#if !defined(NV_STRAPS_REBAR_LINUX_TYPES_H)
#define NV_STRAPS_REBAR_LINUX_TYPES_H

#include <stdint.h>

typedef uint8_t   BYTE;
typedef uint8_t   UINT8;
typedef uint16_t  UINT16;
typedef uint32_t  UINT32;
typedef uint64_t  UINT64;
typedef int8_t    INT8;
typedef int16_t   INT16;
typedef int32_t   INT32;
typedef int64_t   INT64;
typedef uint16_t  CHAR16;    // UEFI CHAR16 is a 16-bit code unit
typedef int       BOOL;

#if defined(__cplusplus)
typedef bool      BOOLEAN;
#else
# include <stdbool.h>
typedef bool      BOOLEAN;
#endif

#endif  // !defined(NV_STRAPS_REBAR_LINUX_TYPES_H)
