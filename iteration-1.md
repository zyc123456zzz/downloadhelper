### 第 1 阶段 实现单个文件的下载功能

可以通过参数指定要下载的文件地址，下载的并发线程数（默认线程数为 8），存放文件的地址（默认为当前目录）。

包括以下参数：

```
--url URL, -u URL                URL to download
--output filename, -o filename   Output filename
--concurrency number, -n number  Concurrency number (default: 8)
```

下载过程中需要显示每个线程下载进度和整体的进度。

注意：并不是所有网站都支持多线程并发下载，需要先进行检测。
