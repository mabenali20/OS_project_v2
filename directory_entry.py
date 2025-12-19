import struct
import fs_constants


class DirectoryEntry:
    def __init__(self, name, attr=fs_constants.ATTR_FILE, first_cluster=0, size=0):
        self.attr = attr
        self.first_cluster = first_cluster
        self.file_size = size

        # Logic: If name is already 11 chars (read from disk), keep it.
        # Otherwise, apply 8.3 formatting (user input).
        if len(name) == 11:
            self.name = name
        else:
            self.name = self._format_8_3(name)

    def _format_8_3(self, name):
        # Convert "file.txt" to "FILE    TXT"
        name = name.upper()
        if "." in name:
            parts = name.rsplit(".", 1)
            base = parts[0][:8].ljust(8)
            ext = parts[1][:3].ljust(3)
            return base + ext
        else:
            return name[:11].ljust(11)

    def to_bytes(self):
        # Struct: 11s(Name) + B(Attr) + I(Cluster) + I(Size) + 12x(Padding) = 32 bytes
        return struct.pack(
            '<11sBII12x',
            self.name.encode('utf-8'),
            self.attr,
            self.first_cluster,
            self.file_size
        )

    @classmethod
    def from_bytes(cls, data):
        if len(data) != fs_constants.DIR_ENTRY_SIZE:
            raise ValueError(f"Invalid entry size: {len(data)}")

        unpacked = struct.unpack('<11sBII12x', data)
        # unpacked = (name_bytes, attr, cluster, size)
        return cls(unpacked[0].decode('utf-8'), unpacked[1], unpacked[2], unpacked[3])

    @property
    def clean_name(self):
        # Convert "FILE    TXT" back to "FILE.TXT"
        base = self.name[:8].strip()
        ext = self.name[8:].strip()
        if ext:
            return f"{base}.{ext}"
        return base