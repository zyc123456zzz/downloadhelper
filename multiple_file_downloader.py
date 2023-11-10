import file_downloader
import decoder
input_stream = []


def downloader(urls_file):
    decoder.decoder(input_stream, urls_file)
    download_manager = file_downloader.DownloadManager('ALL_TASKS_GOING_NOW')
    for item in input_stream:
        download_manager.add_download(item[0], item[1], item[2], item[3])

    download_manager.start()
