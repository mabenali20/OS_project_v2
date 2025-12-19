import fs_constants


class SuperblockManager:
    def __init__(self, disk):
        self.disk = disk

    def write_superblock(self, data):
        # Validate exact cluster size before writing
        if len(data) != fs_constants.CLUSTER_SIZE:
            raise ValueError(f"Data size mismatch: {len(data)} != {fs_constants.CLUSTER_SIZE}")

        self.disk.write_cluster(fs_constants.SUPERBLOCK_CLUSTER, data)

    def read_superblock(self):
        return self.disk.read_cluster(fs_constants.SUPERBLOCK_CLUSTER)