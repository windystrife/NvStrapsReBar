# 🐧 Build và chạy NvStrapsReBar trên Linux

> 🇬🇧 English version: xem mục **"Building and running on Linux"** trong [README.md](../README.md).

Công cụ cấu hình `NvStrapsReBar` (thư mục `ReBarState`) **build và chạy được native trên Linux** dưới dạng một file ELF bình thường — bạn không cần Windows để bật Resizable BAR nữa. Trên Linux, tool liệt kê GPU qua `/sys/bus/pci` và đọc/ghi biến EFI cấu hình qua `efivarfs`.

## Yêu cầu (Ubuntu 24.04 / Debian 13, x86-64)

Tool dùng C++23 modules và `import std`, nên cần Clang + libc++ đời mới và CMake đủ mới để hỗ trợ `import std`:

```sh
sudo apt install -y build-essential clang-18 libc++-18-dev libc++abi-18-dev \
                    lld-18 ninja-build libpci-dev pkg-config git
sudo snap install cmake --classic      # CMake 4.x, cho native `import std`
```

`libpci-dev` để hiển thị tên GPU dễ đọc; lúc chạy cần `efivarfs` (mặc định đã mount ở `/sys/firmware/efi/efivars` trên hệ thống UEFI).

> **Lưu ý về phiên bản CMake:** file `ReBarState/CMakeLists.txt` bật tính năng *thử nghiệm* `import std` của CMake bằng một token gắn theo phiên bản (đang đặt cho CMake 4.4). Nếu bước configure báo lỗi *"import std … not enabled when detecting toolchain"*, hãy sửa giá trị `CMAKE_EXPERIMENTAL_CXX_IMPORT_STD` ở đầu file đó cho khớp token mà phiên bản CMake của bạn yêu cầu.

## Build

```sh
cd ReBarState
cmake -G Ninja -B build-linux \
      -DCMAKE_C_COMPILER=clang-18 \
      -DCMAKE_CXX_COMPILER=clang++-18 \
      -DCMAKE_BUILD_TYPE=Release
ninja -C build-linux
```

Kết quả là file `build-linux/NvStrapsReBar`. (Nếu `cmake` trong `PATH` vẫn là bản cũ của distro, gọi trực tiếp bản snap: `/snap/bin/cmake`.)

## Chạy

Chạy với quyền **root**, vì tool đọc/ghi biến EFI và liệt kê thiết bị PCI:

```sh
sudo ./build-linux/NvStrapsReBar
```

Tool hiện menu text giống hệt bản Windows: bấm `E` để bật ReBAR cho GPU Turing, rồi `S` để lưu cấu hình vào biến EFI, sau đó khởi động lại. Mọi lưu ý ở mục **Usage** và **Warning** trong README vẫn áp dụng — đặc biệt: bạn vẫn phải nhúng driver DXE `NvStrapsReBar.ffs` vào UEFI của mainboard; tool này chỉ quản lý biến EFI cấu hình.

## Ghi chú

* Cần hệ thống **UEFI** (không phải BIOS legacy) và `efivarfs` được mount đọc-ghi.
* Điểm còn thiếu (chỉ về mặt hiển thị) trên Linux: cột `VRAM` và `Current BAR size` trong bảng thiết bị để trống (không có nguồn `sysfs` tương đương với truy vấn DXGI của Windows).
* Đã test với Clang 18 + libc++ 18, CMake 4.4 và Ninja trên Ubuntu 24.04, với card RTX 2080 Ti.

---

⚠️ **Cảnh báo an toàn:** Trước khi thay đổi phần cứng (ví dụ lắp thêm card thứ hai), hãy **tắt ReBAR trước**. NvStrapsReBar dựa vào địa chỉ BAR0 của GPU để bật ReBAR, và firmware sẽ đổi địa chỉ này khi phần cứng hoặc thiết lập trong UEFI Setup thay đổi.
