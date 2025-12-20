import math
import os
import fs_constants
from virtual_disk import VirtualDisk
from fat_table_manager import FatTableManager
from directory import Directory
from directory_entry import DirectoryEntry


class FileSystem:
    def __init__(self, disk_path):
        self.disk = VirtualDisk()
        self.disk.initialize(disk_path)

        self.fat = FatTableManager(self.disk)
        self.fat.load_fat()

        self.dir = Directory(self.disk, self.fat)
        self.current_dir = fs_constants.ROOT_DIR_CLUSTER

        # Check if fresh disk (Root directory cluster is free)
        if self.fat.get_value(self.current_dir) == fs_constants.FREE_CLUSTER:
            self._format_disk()

    def _format_disk(self):
        print("Formatting new disk...")
        # Reserve Clusters 0-4 (Superblock & FAT)
        for i in range(5):
            self.fat.set_value(i, fs_constants.END_OF_CHAIN)

        # Reserve Root Directory (Cluster 5)
        self.fat.set_value(fs_constants.ROOT_DIR_CLUSTER, fs_constants.END_OF_CHAIN)
        self.fat.write_fat()

    def create_file(self, filename, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir

        if self.dir.find_entry(parent, filename):
            print(f"Error: '{filename}' already exists.")
            return

        new_entry = DirectoryEntry(filename, fs_constants.ATTR_FILE, 0, 0)
        self.dir.add_entry(parent, new_entry)

    def write_file(self, filename, content, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        entry = self.dir.find_entry(parent, filename)

        if not entry:
            print(f"Error: '{filename}' not found.")
            return

        size = len(content)
        clusters_needed = math.ceil(size / fs_constants.CLUSTER_SIZE)

        if clusters_needed == 0:
            print("Warning: Writing empty content.")
            return

        # Overwrite: Free old data first
        if entry.first_cluster != 0:
            self.fat.free_chain(entry.first_cluster)

        try:
            start_cluster = self.fat.allocate_chain(clusters_needed)
            chain = self.fat.follow_chain(start_cluster)

            # Write chunks
            for i, cluster_idx in enumerate(chain):
                start = i * fs_constants.CLUSTER_SIZE
                end = min(start + fs_constants.CLUSTER_SIZE, size)
                chunk = content[start:end]

                # Zero padding if needed
                if len(chunk) < fs_constants.CLUSTER_SIZE:
                    chunk = chunk.ljust(fs_constants.CLUSTER_SIZE, b'\x00')

                self.disk.write_cluster(cluster_idx, chunk)

            # Update entry (Remove old -> Add new)
            self.dir.remove_entry(parent, filename)
            updated_entry = DirectoryEntry(filename, fs_constants.ATTR_FILE, start_cluster, size)
            self.dir.add_entry(parent, updated_entry)

        except Exception as e:
            print(f"Write failed: {e}")

    def read_file(self, filename, parent_cluster=None, silent=False):
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        entry = self.dir.find_entry(parent, filename)

        if not entry:
            if not silent:
                print(f"Error: '{filename}' not found.")
            return None

        if entry.first_cluster == 0:
            return b""

        chain = self.fat.follow_chain(entry.first_cluster)
        content = bytearray()

        for cluster_idx in chain:
            content.extend(self.disk.read_cluster(cluster_idx))

        return content[:entry.file_size]

    def append_to_file(self, filename, new_data, parent_cluster=None):
        # Read old -> Concatenate -> Write new
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        old_content = self.read_file(filename, parent, silent=True) or b""
        self.write_file(filename, old_content + new_data, parent)

    def delete_file(self, filename, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        entry = self.dir.find_entry(parent, filename)

        if not entry:
            print(f"Error: '{filename}' not found.")
            return

        if entry.first_cluster != 0:
            self.fat.free_chain(entry.first_cluster)

        self.dir.remove_entry(parent, filename)

    def create_directory(self, dirname, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir

        if self.dir.find_entry(parent, dirname):
            print(f"Error: '{dirname}' already exists.")
            return

        try:
            cluster = self.fat.allocate_chain(1)
            # Clear new cluster
            self.disk.write_cluster(cluster, bytes(fs_constants.CLUSTER_SIZE))

            entry = DirectoryEntry(dirname, fs_constants.ATTR_DIR, cluster, 0)
            self.dir.add_entry(parent, entry)
        except Exception as e:
            print(f"Mkdir failed: {e}")

    def remove_directory(self, dirname, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        entry = self.dir.find_entry(parent, dirname)

        if not entry or entry.attr != fs_constants.ATTR_DIR:
            print(f"Error: Invalid directory '{dirname}'.")
            return

        # Ensure empty
        contents = self.dir.read_directory(entry.first_cluster)
        if contents:
            print(f"Error: Directory '{dirname}' is not empty.")
            return

        self.dir.remove_entry(parent, dirname)
        self.fat.free_chain(entry.first_cluster)

    def list_directory(self, parent_cluster=None):
        parent = parent_cluster if parent_cluster is not None else self.current_dir
        entries = self.dir.read_directory(parent)

        print(f"\nDirectory listing for cluster {parent}:")
        print(f"{'Name':<15} {'Type':<10} {'Size':<10} {'Cluster'}")
        print("-" * 50)
        for e in entries:
            type_str = "<DIR>" if e.attr == fs_constants.ATTR_DIR else "<FILE>"
            print(f"{e.clean_name:<15} {type_str:<10} {e.file_size:<10} {e.first_cluster}")
        print("-" * 50)

    def copy_file(self, src, dst, parent_cluster=None, silent=False):
        if src.upper() == dst.upper():
            print(f"Error: Source and destination cannot be the same.")
            return
        content = self.read_file(src, parent_cluster)
        if content is not None:
            self.create_file(dst, parent_cluster)
            self.write_file(dst, content, parent_cluster)
            if not silent:
                print(f"Copied '{src}' to '{dst}'.")

    def move_file(self, src, dst, parent_cluster=None):
        content = self.read_file(src, parent_cluster)
        if content is not None:
            self.copy_file(src, dst, parent_cluster, silent=True)
            self.delete_file(src, parent_cluster)
            print(f"Moved '{src}' to '{dst}'.")

    def rename_file(self, old, new, parent_cluster=None):
        self.move_file(old, new, parent_cluster)

    def import_file_from_host(self, host_path, virtual_name, parent_cluster=None):
        if not os.path.exists(host_path):
            print("Host file not found.")
            return

        try:
            with open(host_path, 'rb') as f:
                content = f.read()
            self.create_file(virtual_name, parent_cluster)
            self.write_file(virtual_name, content, parent_cluster)
        except Exception as e:
            print(f"Import failed: {e}")

    def export_file_to_host(self, virtual_name, host_path, parent_cluster=None):
        content = self.read_file(virtual_name, parent_cluster)
        if content is None:
            print(f"Error: '{virtual_name}' not found.")
            return

        try:
            with open(host_path, 'wb') as f:
                f.write(content)
            print(f"Exported '{virtual_name}' to '{host_path}'.")
        except Exception as e:
            print(f"Export failed: {e}")

    def get_free_space(self):
        return self.fat.get_free_clusters_count() * fs_constants.CLUSTER_SIZE

    def close(self):
        self.disk.close()

    def cleanup(self):
        """Close disk and delete the virtual disk file for a fresh start."""
        disk_path = self.disk.path
        self.disk.close()
        if os.path.exists(disk_path):
            os.remove(disk_path)
            print(f"Disk '{os.path.basename(disk_path)}' deleted successfully.")