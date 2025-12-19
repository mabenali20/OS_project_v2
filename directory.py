import fs_constants
from directory_entry import DirectoryEntry


class Directory:
    def __init__(self, disk, fat_manager):
        self.disk = disk
        self.fat = fat_manager

    def read_directory(self, start_cluster):
        entries = []
        chain = self.fat.follow_chain(start_cluster)

        for cluster_idx in chain:
            data = self.disk.read_cluster(cluster_idx)

            # Iterate over 32-byte chunks
            for i in range(0, len(data), fs_constants.DIR_ENTRY_SIZE):
                chunk = data[i: i + fs_constants.DIR_ENTRY_SIZE]

                # Skip empty entries (marked with 0x00)
                if chunk[0] == fs_constants.EMPTY_ENTRY:
                    continue

                entries.append(DirectoryEntry.from_bytes(chunk))
        return entries

    def find_entry(self, start_cluster, filename):
        # We construct a dummy entry to get the hashed 8.3 name (e.g., "FILE.TXT" -> "FILE    TXT")
        target_name = DirectoryEntry(filename).name

        # Read all entries and search (Simple Linear Search)
        entries = self.read_directory(start_cluster)
        for entry in entries:
            if entry.name == target_name:
                return entry
        return None

    def add_entry(self, start_cluster, entry):
        chain = self.fat.follow_chain(start_cluster)
        entry_bytes = entry.to_bytes()

        # 1. Try to find an empty slot in existing clusters
        for cluster_idx in chain:
            data = bytearray(self.disk.read_cluster(cluster_idx))

            for i in range(0, len(data), fs_constants.DIR_ENTRY_SIZE):
                # Check first byte for empty marker
                if data[i] == fs_constants.EMPTY_ENTRY:
                    # Found slot -> Write entry -> Save to disk
                    data[i: i + fs_constants.DIR_ENTRY_SIZE] = entry_bytes
                    self.disk.write_cluster(cluster_idx, data)
                    return

        # 2. No space found? Extend the directory chain.
        new_cluster = self.fat.allocate_chain(1)

        # Link the last cluster of the current directory to the new cluster
        last_cluster = chain[-1]
        self.fat.set_value(last_cluster, new_cluster)
        self.fat.write_fat()  # Persist FAT changes immediately

        # Write the entry at the beginning of the new cluster
        new_data = bytearray(fs_constants.CLUSTER_SIZE)
        new_data[0: fs_constants.DIR_ENTRY_SIZE] = entry_bytes
        self.disk.write_cluster(new_cluster, new_data)

    def remove_entry(self, start_cluster, filename):
        target_name = DirectoryEntry(filename).name
        chain = self.fat.follow_chain(start_cluster)

        for cluster_idx in chain:
            data = bytearray(self.disk.read_cluster(cluster_idx))
            dirty = False

            for i in range(0, len(data), fs_constants.DIR_ENTRY_SIZE):
                chunk = data[i: i + fs_constants.DIR_ENTRY_SIZE]

                if chunk[0] == fs_constants.EMPTY_ENTRY:
                    continue

                # Check if this is the file we want to delete
                entry = DirectoryEntry.from_bytes(chunk)
                if entry.name == target_name:
                    # Mark as empty (write 0x00 to first byte)
                    data[i] = fs_constants.EMPTY_ENTRY
                    dirty = True
                    # Found and deleted, break inner loop
                    break

            if dirty:
                self.disk.write_cluster(cluster_idx, data)
                return True

        return False