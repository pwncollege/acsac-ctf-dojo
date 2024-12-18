## Moloka'i
- Category: `pwn`, `arm64`
- Author: `฿Ɇ₦₳`

An island known for its hunters and strength: Moloka'i, a place of power 🦾! 

Mechanical Arm is a program designed to simplify and automate time-consuming tasks, making life more efficient.

In its current alpha stage, it includes a feature to frame poems, with plans to expand its functionality in future updates.

While this is an early release, we are confident in its stability and ready to move it into beta testing!

Challenge items are located in `/challenge/` directory.

To debug the binary run it with: `qemu-aarch64-static -g 1234 /challenge/chal` ("1234" is port) and attach `gdb-multiarch` using `target remote :1234`.
