from os import PathLike, remove

class FileManager:

    def __init__(self, directory):
        self.__directory: PathLike = directory

    def write_file(self, filename: str, content: bytes) -> None:
        with open(self.__directory / filename, "wb") as file:
            file.write(content)
    
    def delete_file(self, filename: str):
        remove(self.__directory / filename)
