import struct
import os
import sys

# 定义文件头和ChunkItem的结构体格式
# '<' 表示小端字节序
# 'I' 表示无符号整数 (4字节)
# '32s' 表示32字节的字符串
# 'Q' 表示无符号长长整数 (8字节), 但C++代码用的是DWORD (4字节), 所以这里用 'I'
# 注意：C++代码中的DWORD是4字节，Python的struct.pack/unpack默认是平台相关，
# 但通常'I'是4字节无符号int。为确保跨平台一致性，最好指定字节序。

# C++ Header:
# DWORD Magic;      -> I (unsigned int)
# DWORD ChunkSize;  -> I
# DWORD ChunkCount; -> I
HEADER_FORMAT = '<III' # < for little-endian, I for unsigned int (4 bytes)
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# C++ ChunkItem:
# CHAR FileName[0x20]; -> 32s (32 bytes string/bytes)
# DWORD Offset;        -> I
# DWORD Size;          -> I
CHUNK_ITEM_FORMAT = '<32sII' # < for little-endian, 32s for 32-byte string, I for unsigned int (4 bytes)
CHUNK_ITEM_SIZE = struct.calcsize(CHUNK_ITEM_FORMAT)

MAGIC_NUMBER = 0x0001424c # C++中的UL表示unsigned long，Python中直接用整数即可

def unpack_archive(archive_path):
    """
    解包自定义格式的归档文件。
    """
    try:
        with open(archive_path, 'rb') as fin:
            # 1. 读取文件头
            header_data = fin.read(HEADER_SIZE)
            if len(header_data) < HEADER_SIZE:
                print(f"错误: 文件过小，无法读取文件头: {archive_path}")
                return

            magic, chunk_size, chunk_count = struct.unpack(HEADER_FORMAT, header_data)

            # 2. 检查魔术数字
            # if magic != MAGIC_NUMBER:
            #     print(f"错误: 文件魔术数字不匹配。预期: {hex(MAGIC_NUMBER)}, 实际: {hex(magic)}")
            #     print(chunk_size, chunk_count)
            #     return

            print(f"文件头信息: Magic={hex(magic)}, ChunkSize={chunk_size} bytes, ChunkCount={chunk_count} files")

            # 3. 读取块数据 (ChunkData)
            chunk_data_raw = fin.read(chunk_size)
            if len(chunk_data_raw) < chunk_size:
                print(f"错误: 无法读取完整的块数据。预期: {chunk_size} bytes, 实际: {len(chunk_data_raw)} bytes")
                return

            # 计算文件数据起始偏移 (PostOffset)
            # Python的tell()可以获取当前文件指针位置，所以不一定需要显式计算PostOffset
            # 但为了与C++代码逻辑对应，我们还是计算一下。
            # C++的PostOffset是 HeaderSize + ChunkSize
            post_offset = HEADER_SIZE + chunk_size

            # 4. 遍历ChunkItem并提取文件
            print("正在提取文件...")
            for i in range(chunk_count):
                # 从原始块数据中解析ChunkItem
                start_index = i * CHUNK_ITEM_SIZE
                end_index = start_index + CHUNK_ITEM_SIZE
                
                if end_index > len(chunk_data_raw):
                    print(f"警告: 块数据不完整或ChunkItem数量有误。无法解析第 {i+1} 个ChunkItem。")
                    print(end_index, len(chunk_data_raw))
                    break

                item_data = chunk_data_raw[start_index:end_index]
                
                # 解包ChunkItem
                file_name_bytes, offset, size = struct.unpack(CHUNK_ITEM_FORMAT, item_data)

                # 处理文件名：移除末尾的空字节，并尝试解码
                # C++的CHAR数组通常是null-terminated
                file_name = file_name_bytes.decode('ascii').rstrip('\0')
                # 也可以尝试其他编码，如 'utf-8' 或 'cp936' (GBK)
                # file_name = file_name_bytes.split(b'\0', 1)[0].decode('utf-8', errors='ignore')

                print(f"  - 提取文件: {file_name} (偏移: {offset}, 大小: {size} bytes)")

                # 5. 定位到子文件数据并读取
                current_pos = fin.tell() # 记录当前文件指针，以便后续跳回
                fin.seek(post_offset + offset, os.SEEK_SET) # 移动到子文件数据开始处

                file_content = fin.read(size)
                if len(file_content) < size:
                    print(f"    警告: 无法读取完整的文件内容。预期: {size} bytes, 实际: {len(file_content)} bytes")
                    # 即使不完整也尝试写入，或者选择跳过
                    # continue

                # 6. 写入子文件
                try:
                    # 确保目标目录存在
                    output_dir = os.path.dirname(file_name)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir)

                    with open(file_name, 'wb') as fout:
                        fout.write(file_content)
                except IOError as e:
                    print(f"    错误: 写入文件 {file_name} 失败: {e}")
                
                fin.seek(current_pos, os.SEEK_SET) # 跳回之前的位置，继续读取下一个ChunkItem的元数据

        print("解包完成。")

    except FileNotFoundError:
        print(f"错误: 文件未找到: {archive_path}")
    except struct.error as e:
        print(f"错误: 解析文件结构失败，可能是文件损坏或格式不正确: {e}")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python unpacker.py <归档文件路径>")
    else:
        # sys.argv[1] 在Windows上会自动处理为正确的路径，无需wmain的特殊处理
        archive_file_path = sys.argv[1]
        unpack_archive(archive_file_path)

