import fs_constants
from utils import Converter


class FatTableManager:
    def __init__(self, disk):
        self.disk = disk
        self.fat = [0] * fs_constants.CLUSTERS_NUMBER

    def load_fat(self):
        # Read FAT clusters into memory
        buffer = bytearray()
        for i in range(fs_constants.FAT_START, fs_constants.FAT_END + 1):
            buffer.extend(self.disk.read_cluster(i))

        self.fat = Converter.bytes_to_int_list(buffer)

    def write_fat(self):
        # Serialize FAT to bytes
        data = Converter.int_list_to_bytes(self.fat)

        # Write split chunks to FAT clusters
        offset = 0
        for i in range(fs_constants.FAT_START, fs_constants.FAT_END + 1):
            chunk = data[offset: offset + fs_constants.CLUSTER_SIZE]
            self.disk.write_cluster(i, chunk)
            offset += fs_constants.CLUSTER_SIZE

    def get_value(self, cluster_idx):
        if 0 <= cluster_idx < fs_constants.CLUSTERS_NUMBER:
            return self.fat[cluster_idx]
        raise IndexError(f"Cluster index {cluster_idx} out of bounds")

    def set_value(self, cluster_idx, value):
        if 0 <= cluster_idx < fs_constants.CLUSTERS_NUMBER:
            self.fat[cluster_idx] = value
        else:
            raise IndexError(f"Cluster index {cluster_idx} out of bounds")

    def get_free_clusters_count(self):
        # Count 0s starting from Root Directory onwards
        return self.fat[fs_constants.ROOT_DIR_CLUSTER:].count(fs_constants.FREE_CLUSTER)

    def allocate_chain(self, n_clusters):
        if n_clusters == 0:
            return -1

        # Search for free slots
        free_indices = []
        for i in range(fs_constants.ROOT_DIR_CLUSTER, fs_constants.CLUSTERS_NUMBER):
            if self.fat[i] == fs_constants.FREE_CLUSTER:
                free_indices.append(i)
                if len(free_indices) == n_clusters:
                    break

        if len(free_indices) < n_clusters:
            raise Exception("Disk Full: Not enough free clusters")

        # Link the chain
        for i in range(len(free_indices) - 1):
            self.fat[free_indices[i]] = free_indices[i + 1]

        # Mark end of chain
        self.fat[free_indices[-1]] = fs_constants.END_OF_CHAIN

        # Persist changes
        self.write_fat()
        return free_indices[0]

    def follow_chain(self, start_cluster):
        chain = []
        curr = start_cluster

        while curr != fs_constants.END_OF_CHAIN:
            chain.append(curr)
            curr = self.get_value(curr)

            # Simple guard against infinite loops
            if len(chain) > fs_constants.CLUSTERS_NUMBER:
                raise Exception("Corrupted FAT: Infinite loop detected")

        return chain

    def free_chain(self, start_cluster):
        curr = start_cluster
        while curr != fs_constants.END_OF_CHAIN:
            next_cluster = self.get_value(curr)
            self.fat[curr] = fs_constants.FREE_CLUSTER
            curr = next_cluster

        self.write_fat()