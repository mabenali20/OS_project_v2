import fs_constants
import virtual_disk

class SuperblockManager:
    def __init__(self, disk):
        self.disk = disk

        if virtual_disk is None:
            raise ValueError("VirtualDisk object cannot be None")
        
        if not isinstance(virtual_disk, disk):
            raise ValueError("Parameter must be a VirtualDisk instance")

    def write_superblock(self, data):
        # Validate exact cluster size before writing
        if len(data) != fs_constants.CLUSTER_SIZE:
            raise ValueError(f"Data size mismatch: {len(data)} != {fs_constants.CLUSTER_SIZE}")

        self.disk.write_cluster(fs_constants.SUPERBLOCK_CLUSTER, data)

    def read_superblock(self):
        try:
           return self.disk.read_cluster(fs_constants.SUPERBLOCK_CLUSTER)
        except Exception as ex:
            raise IOError(f"Failed to read superblock: {ex}") from ex