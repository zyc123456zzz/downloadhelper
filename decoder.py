import sys
import argparse

# input args are 列型的数据 需要根据内容返回不同的


def args_decoder(args):

    parser = argparse.ArgumentParser(description='单个文件下载程序')
    parser.add_argument('--url', '-u', required=True, help='要下载的文件地址')
    parser.add_argument('--output', '-o', required=True, help='输出的文件名')
    parser.add_argument('--concurrency', '-n', type=int, default=8, help='并发线程数，默认为8')
    parser.add_argument('--speed', '-s', type=int, default=1000, help='下载速度限制，默认为1000B/s')

    args_ = parser.parse_args(args.split())

    return args_


def decoder(input_stream, urls_file):
    line_split = []
    url="url"
    out_path="out_path"
    con=8
    speed=100
    # format: -u *** -o *** -n *** -s ***
    file = open(urls_file, "r")
    for line in file:
        line_split.clear()
        line_split.append(line.split()) # split by space
        flatten_list=[item for sublist in line_split for item in sublist]
        # scan and decode the information
        for __ in range(0, len(flatten_list), 2):
            if (flatten_list[__] == "-u") or (flatten_list[__] == "--url"):
                url = flatten_list[__+1]
            elif (flatten_list[__] == "-o") or (flatten_list[__] =="--output"):
                out_path = flatten_list[__+1]
            elif (flatten_list[__] == "-n") or (flatten_list[__] =="--concurrency"):
                con = int(flatten_list[__+1])
            elif (flatten_list[__] == "-s") or (flatten_list[__] =="--speed"):
                speed = int(flatten_list[__+1])
            else:
                print("ARG Format Wrong!")
                sys.exit(1)
        input_stream.append((url, out_path, con, speed))


'''if __name__ == '__main__':
    strs = input("Your args!\n>>")
    res = args_decoder(strs)
'''