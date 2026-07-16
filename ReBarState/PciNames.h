// Thin C wrapper around libpci name lookup, kept in a non-module translation
// unit so <pci/pci.h> never has to be pulled into a C++ module purview.
#if !defined(NV_STRAPS_REBAR_PCI_NAMES_H)
#define NV_STRAPS_REBAR_PCI_NAMES_H

#if defined(__cplusplus)
extern "C"
{
#endif

// Look up the human-readable "<vendor> <device>" name for a PCI id pair and
// write it (NUL-terminated ASCII) into buf.  Returns the string length, or 0
// if the id is unknown / on any failure (buf is set to an empty string then).
int pciLookupDeviceName(unsigned vendorID, unsigned deviceID, char *buf, int size);

// Total VRAM in bytes for the GPU at the given PCI address ("DDDD:BB:DD.F"),
// obtained from nvidia-smi.  Returns 0 if nvidia-smi is missing or the device
// is not found (e.g. non-NVIDIA GPU, or the driver is not loaded).
unsigned long long nvidiaVramBytes(const char *pciAddress);

#if defined(__cplusplus)
}   // extern "C"
#endif

#endif  // !defined(NV_STRAPS_REBAR_PCI_NAMES_H)
