# used to control file_downloader and decoder
import sys
import subprocess
import decoder
import multiple_file_downloader
import cProfile
import pstats


def main():
    basic_language = input("Your Language: En or Ch\n>>")

    while True:
        if basic_language == 'En':
            basic_function = input("Single_file_downloader(input sf) or Multiple_files_downloader(input mf), exit to leave\n>>")
            # 单个文件的下载
            if basic_function == 'sf':
                input_command = input("Please input the download command (format: -u *** -o *** -n *** -s ***), exit to leave the program\n>>")
                if input_command == 'exit':
                    sys.exit(1)
                else:
                    args = decoder.args_decoder(input_command)
                    p = subprocess.Popen(
                        ["python", ".\\file_downloader.py", "-u", args.url, "-o", args.output, "-n",
                         str(args.concurrency), "-s", str(args.speed)]
                        , stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    p.wait()
                    # 自动归类以及自动解压等等功能


            elif basic_function == 'mf':
                input_file = input("Please pack the urls as a file and input the urls_file_path, exit to leave the program\n>>")
                if input_file == 'exit':
                    sys.exit(1)
                else:
                    multiple_file_downloader.downloader(input_file)

            elif basic_function == 'exit':
                sys.exit(1)
        elif basic_language == 'Ch':
            basic_function = input("单个文件下载功能(输入”sf“开始下载)，多个文件下载功能(输入“mf”开始下载)，“exit”结束程序“\n>>")
            # 单个文件的下载
            if basic_function == 'sf':
                input_command = input("请输入下载命令（格式：-u *** -o *** -n *** -s ***）,输入“exit”离开程序\n>>")
                if input_command == 'exit':
                    sys.exit(1)
                else:
                    args = decoder.args_decoder(input_command)
                    p = subprocess.Popen(
                        ["python", ".\\file_downloader.py", "-u", args.url, "-o", args.output, "-n",
                         str(args.concurrency), "-s", str(args.speed)]
                        , stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                    p.wait()

            elif basic_function == 'mf':
                input_file = input("请将多条下载命令写入文件中并将文件路径输入，输入“exit”离开程序\n>>")
                if input_file == 'exit':
                    sys.exit(1)
                else:
                    multiple_file_downloader.downloader(input_file)
            elif basic_function == 'exit':
                sys.exit(1)

if __name__ == '__main__':
    # main()
    cProfile.run('main()', filename='download-helper.prof')

    stats = pstats.Stats('download-helper.prof')

    # 按照总运行时间排序并打印出前10个函数的信息
    stats.sort_stats('tottime').print_stats(10)
    stats.sort_stats('cumtime').print_stats(10)
    print("\n")
    sys.exit(1)
