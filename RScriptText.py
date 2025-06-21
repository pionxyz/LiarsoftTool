import re
import struct
import sys
import os

def dump(in_path):
    try:
        with open(in_path, 'rb') as fin:
            buffer = fin.read()
    except IOError:
        return

    # 解析 RScriptHeader 结构体
    # C++结构体: 7个DWORD (4字节无符号整型)
    if len(buffer) < 28:
        return
    header = struct.unpack('<7I', buffer[:28])
    FileSize, HeaderSize, ByteCodeSize1, ByteCodeSize2, StringPoolSize, ByteCodeSize3, ByteCodeSize4 = header

    if StringPoolSize == 0:
        return

    PostOffset = HeaderSize + ByteCodeSize1 + ByteCodeSize2
    iPos = 0

    out_path = in_path + '.txt'
    with open(out_path, 'w', encoding='utf-8') as fout:
        while iPos < StringPoolSize:
            # 找到以0结尾的字符串
            str_start = PostOffset + iPos
            str_end = buffer.find(b'\x00', str_start)
            if str_end == -1:
                break
            raw_bytes = buffer[str_start:str_end]
            # 按C++原逻辑，原始字符串是932编码（Shift-JIS）
            try:
                utf8_str = raw_bytes.decode('shift_jis')
            except UnicodeDecodeError:
                utf8_str = raw_bytes.decode('shift_jis', errors='backslashreplace')

            fout.write(f"[0x{str_start:08x}]{utf8_str}\n")
            fout.write(f">[0x{str_start:08x}]{utf8_str}\n\n")

            iPos += (str_end - str_start) + 1


def pack(path,packtype=2):
    #剧本固定字符串位置，不清楚机制是什么，只能采用不太完美的折中方案
    #type=1:如果翻译文本长于原文，则将下一行接在此行后面。
    #type=2:如果翻译文本长于原文，将此行截断，剩余内容加到下一行开头
    print(path)
    orig=open(path,'rb').read()
    orig=bytearray(orig)
    trans=open(path+'.txt','r',encoding='utf-8').read()
    addr=[int(_,16) for _ in re.findall('>\[0x(.*?)\]',trans)]
    k=0
    if packtype==1:
        for transline in trans.split('\n'):
            # if k==200:break
            if not transline.startswith('>'):continue
            newlinet = transline[13:].replace('^n','')
            newline = newlinet.encode('gbk',errors='replace')
            if k == len(addr) - 1:
                orig[addr[k]:addr[k] + len(newline)] = newline
                orig[addr[k] + len(newline)+1:addr[k] + len(newline)+2] = b'\x00'
                k += 1
                continue
            dlength=addr[k+1]-addr[k]-len(newline)
            if dlength>0:
                orig[addr[k]:addr[k]+len(newline)]=newline
                orig[addr[k] + len(newline):addr[k+1]] =b'\x00'*dlength
                k+=1
                continue
            print(newlinet)
            if dlength%2==1:newline=b' '+newline
            orig[addr[k]:addr[k]+len(newline)]=newline
            addr[k+1]=addr[k]+len(newline)
            # print(newlinet)
            k+=1
    elif packtype==2:
        remain=''
        for transline in trans.split('\n'):
            if not transline.startswith('>'):continue
            newlinet = remain+transline[13:].replace('^n','')
            newline = newlinet.encode('gbk',errors='replace')
            remain=''
            if k == len(addr) - 1:
                orig[addr[k]:addr[k] + len(newline)] = newline
                orig[addr[k] + len(newline)+1:addr[k] + len(newline)+2] = b'\x00'
                k += 1
                continue

            cut=0
            newlinet0=newlinet
            while (dlength:=addr[k+1]-addr[k]-len(newline))<=0:
                cut+=1
                newlinet = newlinet0[:-cut]
                newline = newlinet.encode('gbk',errors='replace')
            if cut!=0:
                print(newlinet0,newlinet)
                remain=newlinet0[-cut:]

            # print(dlength,repr(newlinet0),repr(newlinet),repr(remain))
            orig[addr[k]:addr[k]+len(newline)]=newline
            orig[addr[k] + len(newline):addr[k+1]] =b'\x00'*dlength
            k+=1

    if not os.path.exists('new'):os.mkdir('new')
    output=open(r'new\\'+path,'wb')
    output.write(bytes(orig))





def shelp():
    print("将剧本文件与py放于同一目录")
    print("dump：python RScriptText.py -d")
    print("pack：python RScriptText.py -p")
    exit()


if __name__ == '__main__':

    if len(sys.argv) != 2:shelp()
    if sys.argv[1]=='-d':
        for i in os.listdir():
            if not i.endswith('.gsc'):continue
            try:
                dump(i)
            except:
                print(i,'dump失败')
            else:
                print(i)
    elif sys.argv[1]=='-p':
        for i in os.listdir():
            if not i.endswith('.gsc'):continue
            if not os.path.exists(i+'.txt'):continue
            try:
                pack(i)
            except:
                print(i,'pack失败')
            else:
                print(i)
        print('注意文字替换有无波及到最后控制部分')

    else:shelp()
