import os
from file_system import FileSystem
from shell import Shell

if __name__ == "__main__":
    # 1. Setup Disk Path (Current Directory)
    disk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "virtual_disk.bin"))

    print(f"Booting MiniFAT... Disk Image: {os.path.basename(disk_path)}")

    # 2. Initialize File System (The Kernel)
    fs = FileSystem(disk_path)

    # 3. Start Shell (The Interface)
    shell = Shell(fs)

    try:
        shell.run()
    except KeyboardInterrupt:
        print("\nForce Exit (Ctrl+C).")
    except Exception as e:
        print(f"\nCritical System Error: {e}")
    finally:
        # Ensure data is saved and file handles are closed
        fs.close()
        print("System Shutdown Safely.")