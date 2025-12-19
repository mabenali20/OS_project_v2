import os
import fs_constants


class VirtualDisk:
    def __init__(self):
        self.file = None
        self.path = ""

    def initialize(self, path):
        self.path = path
        # Create disk if it doesn't exist
        if not os.path.exists(path):
            self._create_disk()

        # Open in read/write binary mode
        self.file = open(path, "r+b")

    def _create_disk(self):
        # Initialize the file with zeros (1MB total)
        total_size = fs_constants.CLUSTERS_NUMBER * fs_constants.CLUSTER_SIZE
        with open(self.path, "wb") as f:
            f.write(b'\x00' * total_size)

    def write_cluster(self, cluster_idx, data):
        # Bounds check
        if not (0 <= cluster_idx < fs_constants.CLUSTERS_NUMBER):
            raise IndexError(f"Cluster index {cluster_idx} out of bounds")

        # Ensure data fits cluster size
        if len(data) > fs_constants.CLUSTER_SIZE:
            raise ValueError(f"Data exceeds cluster size ({fs_constants.CLUSTER_SIZE} bytes)")

        # Pad with zeros if data is smaller than cluster size (Safety feature)
        if len(data) < fs_constants.CLUSTER_SIZE:
            data = data.ljust(fs_constants.CLUSTER_SIZE, b'\x00')
        self.file.seek(cluster_idx * fs_constants.CLUSTER_SIZE)
        self.file.write(data)
        self.file.flush()

    def read_cluster(self, cluster_idx):
        if not (0 <= cluster_idx < fs_constants.CLUSTERS_NUMBER):
            raise IndexError(f"Cluster index {cluster_idx} out of bounds")

        self.file.seek(cluster_idx * fs_constants.CLUSTER_SIZE)
        return self.file.read(fs_constants.CLUSTER_SIZE)

    def close(self):
        if self.file:
            self.file.close()
            self.file = None