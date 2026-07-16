#include "PciNames.h"

extern "C"
{
#include <pci/pci.h>       // this libpci build ships no extern "C" guard of its own
}

#include <string.h>

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
