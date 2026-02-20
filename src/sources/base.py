class BaseSource:
    def list_files(self):
        raise NotImplementedError

    def download_file(self, file_id, destination):
        raise NotImplementedError
