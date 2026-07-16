#include "PciNames.h"

extern "C"
{
#include <pci/pci.h>       // this libpci build ships no extern "C" guard of its own
}

#include <string.h>
#include <strings.h>       // strcasecmp
#include <stdio.h>         // popen
#include <stdlib.h>        // strtoull

int pciLookupDeviceName(unsigned vendorID, unsigned deviceID, char *buf, int size)
{
    if (!buf || size <= 0)
        return 0;

    buf[0] = '\0';

    struct pci_access *pacc = pci_alloc();

    if (!pacc)
        return 0;

    pci_init(pacc);

    char *name = pci_lookup_name(pacc, buf, size, PCI_LOOKUP_VENDOR | PCI_LOOKUP_DEVICE, (int)vendorID, (int)deviceID);

    int length = 0;

    if (name)
    {
        // pci_lookup_name may return an internal static string rather than buf.
        if (name != buf)
        {
            strncpy(buf, name, (size_t)size - 1u);
            buf[size - 1] = '\0';
        }

        length = (int)strlen(buf);
    }

    pci_cleanup(pacc);

    return length;
}

// Return the part of a PCI address after the domain, e.g. "0000:82:00.0" -> "82:00.0".
static const char *busSuffix(const char *address)
{
    const char *colon = strchr(address, ':');
    return colon ? colon + 1 : address;
}

unsigned long long nvidiaVramBytes(const char *pciAddress)
{
    if (!pciAddress || !*pciAddress)
        return 0;

    FILE *pipe = popen("nvidia-smi --query-gpu=pci.bus_id,memory.total --format=csv,noheader,nounits 2>/dev/null", "r");

    if (!pipe)
        return 0;

    const char *wantSuffix = busSuffix(pciAddress);     // e.g. "82:00.0"
    char line[256];
    unsigned long long bytes = 0;

    while (fgets(line, sizeof line, pipe))
    {
        char *comma = strchr(line, ',');

        if (!comma)
            continue;

        *comma = '\0';

        // trim trailing whitespace on the bus-id field
        char *end = comma;
        while (end > line && (end[-1] == ' ' || end[-1] == '\t'))
            *--end = '\0';

        if (strcasecmp(busSuffix(line), wantSuffix) == 0)   // nvidia-smi pads the domain to 8 digits
        {
            bytes = strtoull(comma + 1, 0, 10) * 1024ull * 1024ull;   // reported value is in MiB
            break;
        }
    }

    pclose(pipe);

    return bytes;
}
