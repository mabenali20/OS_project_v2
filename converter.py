import struct

class Converter:
    @staticmethod
    def int_to_bytes(value):
        # Pack int into 4 bytes (Little Endian)
        return struct.pack('<i', value)

    @staticmethod
    def bytes_to_int(data):
        return struct.unpack('<i', data)[0]

    @staticmethod
    def int_list_to_bytes(values):
        buffer = bytearray()
        for val in values:
            buffer.extend(Converter.int_to_bytes(val))
        return bytes(buffer)

    @staticmethod
    def bytes_to_int_list(data):
        values = []
        # Iterate every 4 bytes (size of int)
        for i in range(0, len(data), 4):
            chunk = data[i:i+4]
            if len(chunk) < 4:
                break
            values.append(Converter.bytes_to_int(chunk))
        return values
